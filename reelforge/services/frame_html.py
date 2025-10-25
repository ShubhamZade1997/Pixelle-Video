"""
HTML-based Frame Generator Service

Renders HTML templates to frame images with variable substitution
"""

import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from html2image import Html2Image
from loguru import logger


class HTMLFrameGenerator:
    """
    HTML-based frame generator
    
    Renders HTML templates to frame images with variable substitution.
    Users can create custom templates using any HTML/CSS.
    
    Usage:
        >>> generator = HTMLFrameGenerator("templates/modern.html")
        >>> frame_path = await generator.generate_frame(
        ...     topic="Why reading matters",
        ...     text="Reading builds new neural pathways...",
        ...     image="/path/to/image.png",
        ...     ext={"content_title": "Sample Title", "content_author": "Author Name"}
        ... )
    """
    
    def __init__(self, template_path: str):
        """
        Initialize HTML frame generator
        
        Args:
            template_path: Path to HTML template file
        """
        self.template_path = template_path
        self.template = self._load_template(template_path)
        self.hti = None  # Lazy init to avoid overhead
        logger.debug(f"Loaded HTML template: {template_path}")
    
    def _load_template(self, template_path: str) -> str:
        """Load HTML template from file"""
        path = Path(template_path)
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.debug(f"Template loaded: {len(content)} chars")
        return content
    
    def _ensure_hti(self, width: int, height: int):
        """Lazily initialize Html2Image instance"""
        if self.hti is None:
            self.hti = Html2Image(size=(width, height))
            logger.debug(f"Initialized Html2Image with size ({width}, {height})")
    
    async def generate_frame(
        self,
        topic: str,
        text: str,
        image: str,
        ext: Optional[Dict[str, Any]] = None,
        width: int = 1080,
        height: int = 1920
    ) -> str:
        """
        Generate frame from HTML template
        
        Args:
            topic: Video topic/theme
            text: Narration text for this frame
            image: Path to AI-generated image
            ext: Additional data (content_title, content_author, etc.)
            width: Frame width in pixels
            height: Frame height in pixels
        
        Returns:
            Path to generated frame image
        """
        # Build variable context
        context = {
            # Required variables
            "topic": topic,
            "text": text,
            "image": image,
        }
        
        # Add all ext fields
        if ext:
            context.update(ext)
        
        # Replace variables in HTML
        html = self.template
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            html = html.replace(placeholder, str(value) if value is not None else "")
        
        # Generate unique output path
        from reelforge.utils.os_util import get_output_path
        output_filename = f"frame_{uuid.uuid4().hex[:16]}.png"
        output_path = get_output_path(output_filename)
        
        # Ensure Html2Image is initialized
        self._ensure_hti(width, height)
        
        # Render HTML to image
        logger.debug(f"Rendering HTML template to {output_path}")
        try:
            self.hti.screenshot(
                html_str=html,
                save_as=output_filename,
                size=(width, height)
            )
            
            # html2image saves to current directory by default, move to output
            import os
            import shutil
            if os.path.exists(output_filename):
                shutil.move(output_filename, output_path)
            
            logger.info(f"✅ Frame generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to render HTML template: {e}")
            raise RuntimeError(f"HTML rendering failed: {e}")

