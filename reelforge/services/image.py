"""
Image Generation Service
"""

from typing import Optional

from reelforge.services.base import BaseService


class ImageService(BaseService):
    """
    Image generation service
    
    Provides unified access to various image generation providers (ComfyKit, etc.)
    Returns path or URL to generated image.
    
    Usage:
        # Direct call with workflow path
        image_path = await reelforge.image(
            workflow="workflows/t2i_by_local_flux.json",
            prompt="A peaceful mountain landscape"
        )
        # Returns: "http://comfyui.local/view?filename=..."
        
        # Or use workflow ID (if using RunningHub)
        image_path = await reelforge.image(
            workflow="12345",
            prompt="a beautiful landscape"
        )
        
        # Check active image generator
        print(f"Using: {reelforge.image.active}")
    """
    
    def __init__(self, router):
        super().__init__(router, "image")
    
    async def __call__(
        self,
        workflow: str,
        **params
    ) -> str:
        """
        Generate image using workflow
        
        Args:
            workflow: Workflow path, ID, or URL
            **params: Workflow parameters (e.g., prompt, title, author, etc.)
        
        Returns:
            Image URL or path (str)
        
        Example:
            # Generate image
            image_url = await reelforge.image(
                workflow="workflows/t2i_by_local_flux.json",
                prompt="A beautiful landscape",
                author="James Clear",
                genre="Self-Help"
            )
            
            # Generate from text prompt
            image_url = await reelforge.image(
                workflow="workflows/text2img.json",
                prompt="a cute cat playing with yarn",
                width=1024,
                height=768
            )
        """
        call_params = {"workflow": workflow}
        call_params.update(params)
        
        return await self._config_manager.call(self._capability_type, **call_params)

