"""
TTS (Text-to-Speech) endpoints
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.dependencies import ReelForgeDep
from api.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse
from reelforge.utils.tts_util import get_audio_duration

router = APIRouter(prefix="/tts", tags=["TTS"])


@router.post("/synthesize", response_model=TTSSynthesizeResponse)
async def tts_synthesize(
    request: TTSSynthesizeRequest,
    reelforge: ReelForgeDep
):
    """
    Text-to-Speech synthesis endpoint
    
    Convert text to speech audio.
    
    - **text**: Text to synthesize
    - **voice_id**: Voice ID (e.g., '[Chinese] zh-CN Yunjian', '[English] en-US Aria')
    
    Returns path to generated audio file and duration.
    """
    try:
        logger.info(f"TTS synthesis request: {request.text[:50]}...")
        
        # Call TTS service
        audio_path = await reelforge.tts(
            text=request.text,
            voice_id=request.voice_id
        )
        
        # Get audio duration
        duration = get_audio_duration(audio_path)
        
        return TTSSynthesizeResponse(
            audio_path=audio_path,
            duration=duration
        )
        
    except Exception as e:
        logger.error(f"TTS synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

