"""
Edge TTS Utility - Temporarily not used

This is the original edge-tts implementation, kept here for potential future use.
Currently, TTS service uses ComfyUI workflows only.
"""

import asyncio
import ssl
import random
import edge_tts as edge_tts_sdk
from loguru import logger
from aiohttp import WSServerHandshakeError, ClientResponseError


# Global flag for SSL verification (set to False for development only)
_SSL_VERIFY_ENABLED = False

# Retry configuration for Edge TTS (to handle 401 errors)
_RETRY_COUNT = 5       # Default retry count (increased from 3 to 5)
_RETRY_BASE_DELAY = 1.0     # Base retry delay in seconds (for exponential backoff)
_MAX_RETRY_DELAY = 10.0     # Maximum retry delay in seconds

# Rate limiting configuration
_REQUEST_DELAY = 0.5        # Minimum delay before each request (seconds)
_MAX_CONCURRENT_REQUESTS = 3  # Maximum concurrent requests

# Global semaphore for rate limiting
_request_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)


async def edge_tts(
    text: str,
    voice: str = "[Chinese] zh-CN Yunjian",
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    output_path: str = None,
    retry_count: int = _RETRY_COUNT,
    retry_base_delay: float = _RETRY_BASE_DELAY,
) -> bytes:
    """
    Convert text to speech using Microsoft Edge TTS
    
    This service is free and requires no API key.
    Supports 400+ voices across 100+ languages.
    
    Returns audio data as bytes (MP3 format).
    
    Includes automatic retry mechanism with exponential backoff and jitter
    to handle 401 authentication errors and temporary network issues.
    Also includes concurrent request limiting and rate limiting.
    
    Args:
        text: Text to convert to speech
        voice: Voice ID (e.g., [Chinese] zh-CN Yunjian, [English] en-US Jenny)
        rate: Speech rate (e.g., +0%, +50%, -20%)
        volume: Speech volume (e.g., +0%, +50%, -20%)
        pitch: Speech pitch (e.g., +0Hz, +10Hz, -5Hz)
        output_path: Optional output file path to save audio
        retry_count: Number of retries on failure (default: 5)
        retry_base_delay: Base delay for exponential backoff (default: 1.0s)
    
    Returns:
        Audio data as bytes (MP3 format)
    
    Popular Chinese voices:
    - [Chinese] zh-CN Yunjian (male, default)
    - [Chinese] zh-CN Xiaoxiao (female)
    - [Chinese] zh-CN Yunxi (male)
    - [Chinese] zh-CN Xiaoyi (female)
    
    Popular English voices:
    - [English] en-US Jenny (female)
    - [English] en-US Guy (male)
    - [English] en-GB Sonia (female, British)
    
    Example:
        audio_bytes = await edge_tts(
            text="你好，世界！",
            voice="[Chinese] zh-CN Yunjian",
            rate="+20%"
        )
    """
    logger.debug(f"Calling Edge TTS with voice: {voice}, rate: {rate}, retry_count: {retry_count}")
    
    # Use semaphore to limit concurrent requests
    async with _request_semaphore:
        # Add a small random delay before each request to avoid rate limiting
        pre_delay = _REQUEST_DELAY + random.uniform(0, 0.3)
        logger.debug(f"Waiting {pre_delay:.2f}s before request (rate limiting)")
        await asyncio.sleep(pre_delay)
        
        last_error = None
        
        # Retry loop
        for attempt in range(retry_count + 1):  # +1 because first attempt is not a retry
            if attempt > 0:
                # Exponential backoff with jitter
                # delay = base * (2 ^ attempt) + random jitter
                exponential_delay = retry_base_delay * (2 ** (attempt - 1))
                jitter = random.uniform(0, retry_base_delay)
                retry_delay = min(exponential_delay + jitter, _MAX_RETRY_DELAY)
                
                logger.info(f"🔄 Retrying Edge TTS (attempt {attempt + 1}/{retry_count + 1}) after {retry_delay:.2f}s delay...")
                await asyncio.sleep(retry_delay)
            
            # Monkey patch ssl.create_default_context if SSL verification is disabled
            if not _SSL_VERIFY_ENABLED:
                if attempt == 0:  # Only log warning once
                    logger.warning("SSL verification is disabled for development. This is NOT recommended for production!")
                original_create_default_context = ssl.create_default_context
                
                def create_unverified_context(*args, **kwargs):
                    ctx = original_create_default_context(*args, **kwargs)
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    return ctx
                
                # Temporarily replace the function
                ssl.create_default_context = create_unverified_context
            
            try:
                # Create communicate instance
                communicate = edge_tts_sdk.Communicate(
                    text=text,
                    voice=voice,
                    rate=rate,
                    volume=volume,
                    pitch=pitch,
                )
                
                # Collect audio chunks
                audio_chunks = []
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_chunks.append(chunk["data"])
                
                audio_data = b"".join(audio_chunks)
                
                if attempt > 0:
                    logger.success(f"✅ Retry succeeded on attempt {attempt + 1}")
                
                logger.info(f"Generated {len(audio_data)} bytes of audio data")
                
                # Save to file if output_path is provided
                if output_path:
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
                    logger.info(f"Audio saved to: {output_path}")
                
                return audio_data
            
            except (WSServerHandshakeError, ClientResponseError) as e:
                # Network/authentication errors - retry
                last_error = e
                error_code = getattr(e, 'status', 'unknown')
                error_msg = str(e)
                
                # Log more detailed information for 401 errors
                if error_code == 401 or '401' in error_msg:
                    logger.warning(f"⚠️  Edge TTS 401 Authentication Error (attempt {attempt + 1}/{retry_count + 1})")
                    logger.debug(f"Error details: {error_msg}")
                    logger.debug(f"This is usually caused by rate limiting. Will retry with exponential backoff...")
                else:
                    logger.warning(f"⚠️  Edge TTS error (attempt {attempt + 1}/{retry_count + 1}): {error_code} - {e}")
                
                if attempt >= retry_count:
                    # Last attempt failed
                    logger.error(f"❌ All {retry_count + 1} attempts failed. Last error: {error_code}")
                    raise
                # Otherwise, continue to next retry
            
            except Exception as e:
                # Other errors - don't retry, raise immediately
                logger.error(f"Edge TTS error (non-retryable): {type(e).__name__} - {e}")
                raise
            
            finally:
                # Restore original function if we patched it
                if not _SSL_VERIFY_ENABLED:
                    ssl.create_default_context = original_create_default_context
        
        # Should not reach here, but just in case
        if last_error:
            raise last_error
        else:
            raise RuntimeError("Edge TTS failed without error (unexpected)")


def get_audio_duration(audio_path: str) -> float:
    """
    Get audio file duration in seconds
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        Duration in seconds
    """
    try:
        # Try using ffmpeg-python
        import ffmpeg
        probe = ffmpeg.probe(audio_path)
        duration = float(probe['format']['duration'])
        return duration
    except Exception as e:
        logger.warning(f"Failed to get audio duration: {e}, using estimate")
        # Fallback: estimate based on file size (very rough)
        import os
        file_size = os.path.getsize(audio_path)
        # Assume ~16kbps for MP3, so 2KB per second
        estimated_duration = file_size / 2000
        return max(1.0, estimated_duration)  # At least 1 second


async def list_voices(locale: str = None, retry_count: int = _RETRY_COUNT, retry_base_delay: float = _RETRY_BASE_DELAY) -> list[str]:
    """
    List all available voices for Edge TTS
    
    Returns a list of voice IDs (ShortName).
    Optionally filter by locale.
    
    Includes automatic retry mechanism with exponential backoff and jitter
    to handle network errors and rate limiting.
    
    Args:
        locale: Filter by locale (e.g., zh-CN, en-US, ja-JP)
        retry_count: Number of retries on failure (default: 5)
        retry_base_delay: Base delay for exponential backoff (default: 1.0s)
    
    Returns:
        List of voice IDs
    
    Example:
        # List all voices
        voices = await list_voices()
        # Returns: ['[Chinese] zh-CN Yunjian', '[Chinese] zh-CN Xiaoxiao', ...]
        
        # List Chinese voices only
        voices = await list_voices(locale="zh-CN")
        # Returns: ['[Chinese] zh-CN Yunjian', '[Chinese] zh-CN Xiaoxiao', ...]
    """
    logger.debug(f"Fetching Edge TTS voices, locale filter: {locale}, retry_count: {retry_count}")
    
    # Use semaphore to limit concurrent requests
    async with _request_semaphore:
        # Add a small random delay before each request to avoid rate limiting
        pre_delay = _REQUEST_DELAY + random.uniform(0, 0.3)
        logger.debug(f"Waiting {pre_delay:.2f}s before request (rate limiting)")
        await asyncio.sleep(pre_delay)
        
        last_error = None
        
        # Retry loop
        for attempt in range(retry_count + 1):
            if attempt > 0:
                # Exponential backoff with jitter
                exponential_delay = retry_base_delay * (2 ** (attempt - 1))
                jitter = random.uniform(0, retry_base_delay)
                retry_delay = min(exponential_delay + jitter, _MAX_RETRY_DELAY)
                
                logger.info(f"🔄 Retrying list voices (attempt {attempt + 1}/{retry_count + 1}) after {retry_delay:.2f}s delay...")
                await asyncio.sleep(retry_delay)
            
            # Monkey patch SSL if verification is disabled
            if not _SSL_VERIFY_ENABLED:
                if attempt == 0:  # Only log warning once
                    logger.warning("SSL verification is disabled for development. This is NOT recommended for production!")
                original_create_default_context = ssl.create_default_context
                
                def create_unverified_context(*args, **kwargs):
                    ctx = original_create_default_context(*args, **kwargs)
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    return ctx
                
                ssl.create_default_context = create_unverified_context
            
            try:
                # Get all voices
                voices = await edge_tts_sdk.list_voices()
                
                # Filter by locale if specified
                if locale:
                    voices = [v for v in voices if v["Locale"].startswith(locale)]
                
                # Extract voice IDs (ShortName)
                voice_ids = [voice["ShortName"] for voice in voices]
                
                if attempt > 0:
                    logger.success(f"✅ Retry succeeded on attempt {attempt + 1}")
                
                logger.info(f"Found {len(voice_ids)} voices" + (f" for locale '{locale}'" if locale else ""))
                return voice_ids
            
            except (WSServerHandshakeError, ClientResponseError) as e:
                # Network/authentication errors - retry
                last_error = e
                error_code = getattr(e, 'status', 'unknown')
                error_msg = str(e)
                
                # Log more detailed information for 401 errors
                if error_code == 401 or '401' in error_msg:
                    logger.warning(f"⚠️  Edge TTS 401 Authentication Error (list_voices attempt {attempt + 1}/{retry_count + 1})")
                    logger.debug(f"Error details: {error_msg}")
                    logger.debug(f"This is usually caused by rate limiting. Will retry with exponential backoff...")
                else:
                    logger.warning(f"⚠️  List voices error (attempt {attempt + 1}/{retry_count + 1}): {error_code} - {e}")
                
                if attempt >= retry_count:
                    logger.error(f"❌ All {retry_count + 1} attempts failed. Last error: {error_code}")
                    raise
            
            except Exception as e:
                # Other errors - don't retry, raise immediately
                logger.error(f"List voices error (non-retryable): {type(e).__name__} - {e}")
                raise
            
            finally:
                # Restore original function if we patched it
                if not _SSL_VERIFY_ENABLED:
                    ssl.create_default_context = original_create_default_context
        
        # Should not reach here, but just in case
        if last_error:
            raise last_error
        else:
            raise RuntimeError("List voices failed without error (unexpected)")

