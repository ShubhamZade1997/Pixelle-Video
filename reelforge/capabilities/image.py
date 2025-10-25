"""
Image Generation Capabilities using ComfyKit

ComfyKit provides unified access to ComfyUI workflows:
- Local ComfyUI execution
- RunningHub cloud execution
- Flexible workflow-based generation
- Structured result handling

Convention: Tool names must be image_{id}
"""

import os
from typing import Any

from comfykit import ComfyKit
from loguru import logger
from pydantic import Field

from reelforge.core.mcp_server import reelforge_mcp


@reelforge_mcp.tool(
    description="Generate images using ComfyKit (local ComfyUI or RunningHub cloud)",
    meta={
        "reelforge": {
            "display_name": "ComfyKit Image Generator",
            "description": "基于 ComfyKit 的图像生成 - 支持本地和云端",
            "is_default": True,
        }
    },
)
async def image_comfykit(
    workflow: str = Field(description="Workflow path, ID, or URL"),
    comfyui_url: str | None = Field(default=None, description="ComfyUI server URL (default: http://127.0.0.1:8188)"),
    runninghub_api_key: str | None = Field(default=None, description="RunningHub API key (for cloud execution)"),
    # Common workflow parameters
    prompt: str | None = Field(default=None, description="Image generation prompt"),
    width: int | None = Field(default=None, description="Image width"),
    height: int | None = Field(default=None, description="Image height"),
    negative_prompt: str | None = Field(default=None, description="Negative prompt"),
    steps: int | None = Field(default=None, description="Sampling steps"),
    seed: int | None = Field(default=None, description="Random seed"),
    cfg: float | None = Field(default=None, description="CFG scale"),
    sampler: str | None = Field(default=None, description="Sampler name"),
) -> str:
    """
    Generate image using ComfyKit
    
    Supports both local ComfyUI and RunningHub cloud execution.
    Returns the first generated image URL.
    
    Environment variables (optional):
    - COMFYUI_BASE_URL: ComfyUI server URL
    - RUNNINGHUB_API_KEY: RunningHub API key
    
    Example:
        # Local ComfyUI (default)
        image_url = await image_comfykit(
            workflow="workflows/t2i_by_local_flux.json",
            prompt="A peaceful mountain landscape"
        )
        
        # RunningHub cloud
        image_url = await image_comfykit(
            workflow="12345",  # RunningHub workflow ID
            runninghub_api_key="rh-key-xxx",
            prompt="a beautiful landscape"
        )
        
        # Custom ComfyUI server
        image_url = await image_comfykit(
            workflow="workflows/text2img.json",
            comfyui_url="http://192.168.1.100:8188",
            prompt="a cute cat"
        )
    """
    logger.debug(f"Generating image with workflow: {workflow}")
    
    try:
        # Initialize ComfyKit
        kit_config = {}
        
        # Local ComfyUI configuration
        if comfyui_url:
            kit_config["comfyui_url"] = comfyui_url
        elif os.getenv("COMFYUI_BASE_URL"):
            kit_config["comfyui_url"] = os.getenv("COMFYUI_BASE_URL")
        
        # RunningHub cloud configuration
        if runninghub_api_key:
            kit_config["runninghub_api_key"] = runninghub_api_key
        elif os.getenv("RUNNINGHUB_API_KEY"):
            kit_config["runninghub_api_key"] = os.getenv("RUNNINGHUB_API_KEY")
        
        kit = ComfyKit(**kit_config)
        
        # Build workflow parameters
        workflow_params = {}
        if prompt is not None:
            workflow_params["prompt"] = prompt
        if width is not None:
            workflow_params["width"] = width
        if height is not None:
            workflow_params["height"] = height
        if negative_prompt is not None:
            workflow_params["negative_prompt"] = negative_prompt
        if steps is not None:
            workflow_params["steps"] = steps
        if seed is not None:
            workflow_params["seed"] = seed
        if cfg is not None:
            workflow_params["cfg"] = cfg
        if sampler is not None:
            workflow_params["sampler"] = sampler
        
        logger.debug(f"Workflow parameters: {workflow_params}")
        
        # Execute workflow
        result = await kit.execute(workflow, workflow_params)
        
        # Check execution status
        if result.status != "completed":
            error_msg = result.msg or "Unknown error"
            logger.error(f"Image generation failed: {error_msg}")
            raise Exception(f"Image generation failed: {error_msg}")
        
        # Return first image URL
        if result.images:
            image_url = result.images[0]
            logger.info(f"Generated image: {image_url}")
            return image_url
        else:
            logger.error("No images generated")
            raise Exception("No images generated")
    
    except Exception as e:
        logger.error(f"ComfyKit error: {e}")
        raise

