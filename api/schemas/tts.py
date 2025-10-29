"""
TTS API schemas
"""

from pydantic import BaseModel, Field


class TTSSynthesizeRequest(BaseModel):
    """TTS synthesis request"""
    text: str = Field(..., description="Text to synthesize")
    voice_id: str = Field("[Chinese] zh-CN Yunjian", description="Voice ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hello, welcome to ReelForge!",
                "voice_id": "[Chinese] zh-CN Yunjian"
            }
        }


class TTSSynthesizeResponse(BaseModel):
    """TTS synthesis response"""
    success: bool = True
    message: str = "Success"
    audio_path: str = Field(..., description="Path to generated audio file")
    duration: float = Field(..., description="Audio duration in seconds")

