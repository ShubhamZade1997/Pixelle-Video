"""
TTS (Text-to-Speech) Service - ComfyUI Workflow-based implementation
"""

from typing import Optional

from comfykit import ComfyKit
from loguru import logger

from reelforge.services.comfy_base_service import ComfyBaseService


class TTSService(ComfyBaseService):
    """
    TTS (Text-to-Speech) service - Workflow-based
    
    Uses ComfyKit to execute TTS workflows.
    
    Usage:
        # Use default workflow
        audio_path = await reelforge.tts(text="Hello, world!")
        
        # Use specific workflow
        audio_path = await reelforge.tts(
            text="你好，世界！",
            workflow="tts_edge.json"
        )
        
        # List available workflows
        workflows = reelforge.tts.list_workflows()
    """
    
    WORKFLOW_PREFIX = "tts_"
    DEFAULT_WORKFLOW = None  # No hardcoded default, must be configured
    WORKFLOWS_DIR = "workflows"
    
    def __init__(self, config: dict):
        """
        Initialize TTS service
        
        Args:
            config: Full application config dict
        """
        super().__init__(config, service_name="tts")
    
    
    async def __call__(
        self,
        text: str,
        workflow: Optional[str] = None,
        # ComfyUI connection (optional overrides)
        comfyui_url: Optional[str] = None,
        runninghub_api_key: Optional[str] = None,
        # TTS parameters
        voice: str = "[Chinese] zh-CN Yunjian",
        speed: float = 1.2,
        # Output path
        output_path: Optional[str] = None,
        **params
    ) -> str:
        """
        Generate speech using ComfyUI workflow
        
        Args:
            text: Text to convert to speech
            workflow: Workflow filename (default: from config)
            comfyui_url: ComfyUI URL (optional, overrides config)
            runninghub_api_key: RunningHub API key (optional, overrides config)
            voice: Voice ID (workflow-specific)
            speed: Speech speed multiplier (1.0 = normal, >1.0 = faster, <1.0 = slower)
            output_path: Custom output path (auto-generated if None)
            **params: Additional workflow parameters
        
        Returns:
            Generated audio file path
        
        Examples:
            # Simplest: use default workflow
            audio_path = await reelforge.tts(text="Hello, world!")
            
            # Use specific workflow
            audio_path = await reelforge.tts(
                text="你好，世界！",
                workflow="tts_edge.json"
            )
            
            # With voice and speed
            audio_path = await reelforge.tts(
                text="Hello",
                workflow="tts_edge.json",
                voice="[Chinese] zh-CN Xiaoxiao",
                speed=1.2
            )
            
            # With absolute path
            audio_path = await reelforge.tts(
                text="Hello",
                workflow="/path/to/custom_tts.json"
            )
            
            # With custom ComfyUI server
            audio_path = await reelforge.tts(
                text="Hello",
                comfyui_url="http://192.168.1.100:8188"
            )
        """
        # 1. Resolve workflow (returns structured info)
        workflow_info = self._resolve_workflow(workflow=workflow)
        
        # 2. Execute ComfyUI workflow
        return await self._call_comfyui_workflow(
            workflow_info=workflow_info,
            text=text,
            comfyui_url=comfyui_url,
            runninghub_api_key=runninghub_api_key,
            voice=voice,
            speed=speed,
            output_path=output_path,
            **params
        )
    
    async def _call_comfyui_workflow(
        self,
        workflow_info: dict,
        text: str,
        comfyui_url: Optional[str] = None,
        runninghub_api_key: Optional[str] = None,
        voice: Optional[str] = None,
        speed: float = 1.0,
        output_path: Optional[str] = None,
        **params
    ) -> str:
        """
        Generate speech using ComfyUI workflow
        
        Args:
            workflow_info: Workflow info dict from _resolve_workflow()
            text: Text to convert to speech
            comfyui_url: ComfyUI URL
            runninghub_api_key: RunningHub API key
            voice: Voice ID (workflow-specific)
            speed: Speech speed multiplier (workflow-specific)
            output_path: Custom output path (downloads if URL returned)
            **params: Additional workflow parameters
        
        Returns:
            Generated audio file path (local if output_path provided, otherwise URL)
        """
        logger.info(f"🎙️  Using workflow: {workflow_info['key']}")
        
        # 1. Prepare ComfyKit config (supports both selfhost and runninghub)
        kit_config = self._prepare_comfykit_config(
            comfyui_url=comfyui_url,
            runninghub_api_key=runninghub_api_key
        )
        
        # 2. Build workflow parameters
        workflow_params = {"text": text}
        
        # Add optional TTS parameters
        if voice is not None:
            workflow_params["voice"] = voice
        if speed != 1.0:
            workflow_params["speed"] = speed
        
        # Add any additional parameters
        workflow_params.update(params)
        
        logger.debug(f"Workflow parameters: {workflow_params}")
        
        # 3. Execute workflow (ComfyKit auto-detects based on input type)
        try:
            kit = ComfyKit(**kit_config)
            
            # Determine what to pass to ComfyKit based on source
            if workflow_info["source"] == "runninghub" and "workflow_id" in workflow_info:
                # RunningHub: pass workflow_id
                workflow_input = workflow_info["workflow_id"]
                logger.info(f"Executing RunningHub TTS workflow: {workflow_input}")
            else:
                # Selfhost: pass file path
                workflow_input = workflow_info["path"]
                logger.info(f"Executing selfhost TTS workflow: {workflow_input}")
            
            result = await kit.execute(workflow_input, workflow_params)
            
            # 4. Handle result
            if result.status != "completed":
                error_msg = result.msg or "Unknown error"
                logger.error(f"TTS generation failed: {error_msg}")
                raise Exception(f"TTS generation failed: {error_msg}")
            
            # ComfyKit result can have audio files in different output types
            # Try to get audio file path from result
            audio_path = None
            
            # Check for audio files in result.audios (if available)
            if hasattr(result, 'audios') and result.audios:
                audio_path = result.audios[0]
            # Check for files in result.files
            elif hasattr(result, 'files') and result.files:
                audio_path = result.files[0]
            # Check in outputs dictionary
            elif hasattr(result, 'outputs') and result.outputs:
                # Try to find audio file in outputs
                for key, value in result.outputs.items():
                    if isinstance(value, str) and any(value.endswith(ext) for ext in ['.mp3', '.wav', '.flac']):
                        audio_path = value
                        break
            
            if not audio_path:
                logger.error("No audio file generated")
                raise Exception("No audio file generated by workflow")
            
            # If output_path provided and audio_path is URL, download to local
            if output_path and audio_path.startswith(('http://', 'https://')):
                import httpx
                import os
                
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                logger.info(f"Downloading audio from {audio_path} to {output_path}")
                async with httpx.AsyncClient() as client:
                    response = await client.get(audio_path)
                    response.raise_for_status()
                    
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                
                logger.info(f"✅ Generated audio (ComfyUI): {output_path}")
                return output_path
            
            logger.info(f"✅ Generated audio (ComfyUI): {audio_path}")
            return audio_path
        
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            raise
