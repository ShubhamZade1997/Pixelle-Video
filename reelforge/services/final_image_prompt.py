"""
Final Image Prompt Service

Generates final complete image prompts by converting style descriptions
and combining them with base prompts in consistent order.
"""

from collections import namedtuple
from enum import Enum
from typing import Optional

from loguru import logger


# Define preset value structure
PresetValue = namedtuple('PresetValue', ['display_name', 'prompt'])


class StylePreset(Enum):
    """Predefined style presets for image generation"""
    
    STICK_FIGURE = PresetValue(
        display_name="Stick Figure",
        prompt=(
            "Pure white background, minimalist illustration, matchstick figure style, "
            "black and white line drawing, simple clean lines"
        ),
    )
    
    MINIMAL = PresetValue(
        display_name="Minimal",
        prompt=(
            "Simple and clean background, minimal design, soft colors, "
            "professional look, modern aesthetic, uncluttered composition"
        ),
    )
    
    FUTURISTIC = PresetValue(
        display_name="Futuristic",
        prompt=(
            "Futuristic sci-fi style, high-tech city background, "
            "blue and silver tones, technology sense, soft neon lights, "
            "cyberpunk aesthetics, digital art, advanced technology"
        ),
    )
    
    CINEMATIC = PresetValue(
        display_name="Cinematic",
        prompt=(
            "Cinematic lighting, dramatic composition, film grain, "
            "professional photography, depth of field, movie still quality"
        ),
    )


class FinalImagePromptService:
    """
    Final Image Prompt Service
    
    Generates the final complete image prompt by:
    1. Converting style description (preset or custom)
    2. Combining style + base prompt in correct order
    
    This ensures:
    - Consistent style conversion logic across all scenarios
    - Consistent prompt concatenation order (style first, then prompt)
    - Single source of truth for image prompt generation
    
    Usage:
        # With preset style
        final = await reelforge.generate_final_image_prompt(
            prompt="A peaceful mountain landscape",
            style_preset=StylePreset.FUTURISTIC
        )
        
        # With custom style (any language)
        final = await reelforge.generate_final_image_prompt(
            prompt="A coffee cup on table",
            custom_style_description="温馨的咖啡馆，暖色调"
        )
        
        # Only prompt (no style)
        final = await reelforge.generate_final_image_prompt(
            prompt="A sunset over the ocean"
        )
    """
    
    def __init__(self, reelforge_core):
        """
        Initialize service
        
        Args:
            reelforge_core: ReelForgeCore instance for accessing LLM
        """
        self.core = reelforge_core
    
    async def __call__(
        self,
        prompt: str = "",
        style_preset: Optional[StylePreset] = None,
        custom_style_description: str = ""
    ) -> str:
        """
        Generate final image prompt with style
        
        Priority:
        1. custom_style_description (if provided) → convert via LLM
        2. style_preset (if provided) → use predefined English prompt
        3. Neither → just return prompt
        
        Concatenation:
        - Style part (if exists) comes first
        - Base prompt (if exists) comes second
        - Join with comma: "{style_part}, {prompt}"
        
        Args:
            prompt: Base prompt (optional, e.g., "A peaceful landscape")
            style_preset: Preset style from StylePreset enum (optional)
            custom_style_description: Custom description in any language (optional)
                                     Overrides style_preset if provided
        
        Returns:
            Final complete image prompt in English
        
        Examples:
            # With preset style (IDE autocomplete!)
            final = await service(
                prompt="A mountain landscape",
                style_preset=StylePreset.FUTURISTIC
            )
            # Returns: "Futuristic sci-fi style..., A mountain landscape"
            
            # With custom style (any language)
            final = await service(
                prompt="A coffee cup",
                custom_style_description="温馨的咖啡馆，暖色调"
            )
            # Returns: "Cozy coffee shop interior..., A coffee cup"
            
            # Only prompt
            final = await service(prompt="A sunset scene")
            # Returns: "A sunset scene"
            
            # Only style
            final = await service(style_preset=StylePreset.MINIMAL)
            # Returns: "Simple and clean background..."
        """
        
        # Step 1: Determine style part
        style_part = ""
        
        if custom_style_description:
            # Priority 1: Custom description (convert via LLM)
            logger.debug(f"Converting custom style description: {custom_style_description}")
            style_part = await self._convert_custom_style(custom_style_description)
            
        elif style_preset:
            # Priority 2: Preset style (use prompt from enum value)
            style_part = style_preset.value.prompt
            logger.debug(f"Using preset style: {style_preset.name}")
        
        # Step 2: Combine parts with comma
        parts = [p for p in [style_part, prompt] if p]
        final_prompt = ", ".join(parts)
        
        if final_prompt:
            logger.debug(f"Final image prompt: {final_prompt}")
        else:
            logger.warning("Generated empty image prompt")
        
        return final_prompt
    
    async def _convert_custom_style(self, description: str) -> str:
        """
        Convert custom style description to English image prompt via LLM
        
        Args:
            description: User's style description in any language
        
        Returns:
            Converted English image prompt suitable for image generation models
        """
        
        llm_prompt = f"""Convert this style description into a detailed image generation prompt for Stable Diffusion/FLUX:

Style Description: {description}

Requirements:
- Focus on visual elements, colors, lighting, mood, atmosphere
- Be specific and detailed
- Use professional photography/art terminology
- Output ONLY the prompt in English (no explanations)
- Keep it under 100 words
- Use comma-separated descriptive phrases

Image Prompt:"""
        
        style_prompt = await self.core.llm(llm_prompt)
        
        # Clean up the result (remove extra whitespace, newlines)
        style_prompt = " ".join(style_prompt.strip().split())
        
        logger.debug(f"Converted custom style to: {style_prompt}")
        
        return style_prompt

