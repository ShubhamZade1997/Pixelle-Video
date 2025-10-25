"""
ReelForge - AI-powered video generator with pluggable capabilities

Convention-based capability system using FastMCP and LiteLLM.

Usage:
    from reelforge import reelforge
    
    # Initialize
    await reelforge.initialize()
    
    # Use capabilities
    answer = await reelforge.llm("Explain atomic habits")
    audio = await reelforge.tts("Hello world")
    
    # Generate video
    result = await reelforge.generate_video(topic="AI in 2024")
"""

from reelforge.service import ReelForgeCore, reelforge

__version__ = "0.1.0"

__all__ = ["ReelForgeCore", "reelforge"]

