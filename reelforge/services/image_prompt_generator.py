"""
Image prompt generation service
"""

import json
import re
from typing import List, Optional, Callable

from loguru import logger

from reelforge.models.storyboard import StoryboardConfig
from reelforge.prompts import build_image_prompt_prompt


class ImagePromptGeneratorService:
    """Image prompt generation service"""
    
    def __init__(self, reelforge_core):
        """
        Initialize
        
        Args:
            reelforge_core: ReelForgeCore instance
        """
        self.core = reelforge_core
    
    async def generate_image_prompts(
        self,
        narrations: List[str],
        config: StoryboardConfig,
        batch_size: int = 10,
        max_retries: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """
        Generate image prompts based on narrations (with batching and retry)
        
        Args:
            narrations: List of narrations
            config: Storyboard configuration
            batch_size: Max narrations per batch (default: 10)
            max_retries: Max retry attempts per batch (default: 3)
            progress_callback: Optional callback(completed, total, message) for progress updates
            
        Returns:
            List of image prompts with prompt_prefix applied (from config)
            
        Raises:
            ValueError: If batch fails after max_retries
            json.JSONDecodeError: If unable to parse JSON
        """
        logger.info(f"Generating image prompts for {len(narrations)} narrations (batch_size={batch_size}, max_retries={max_retries})")
        
        # Split narrations into batches
        batches = [narrations[i:i + batch_size] for i in range(0, len(narrations), batch_size)]
        logger.info(f"Split into {len(batches)} batches")
        
        all_base_prompts = []
        
        # Process each batch
        for batch_idx, batch_narrations in enumerate(batches, 1):
            logger.info(f"Processing batch {batch_idx}/{len(batches)} ({len(batch_narrations)} narrations)")
            
            # Retry logic for this batch
            for attempt in range(1, max_retries + 1):
                try:
                    # Generate prompts for this batch
                    batch_prompts = await self._generate_batch_prompts(
                        batch_narrations, 
                        config,
                        batch_idx,
                        attempt
                    )
                    
                    # Validate count
                    if len(batch_prompts) != len(batch_narrations):
                        error_msg = (
                            f"Batch {batch_idx} prompt count mismatch (attempt {attempt}/{max_retries}):\n"
                            f"  Expected: {len(batch_narrations)} prompts\n"
                            f"  Got: {len(batch_prompts)} prompts\n"
                            f"  Difference: {abs(len(batch_prompts) - len(batch_narrations))} "
                            f"{'missing' if len(batch_prompts) < len(batch_narrations) else 'extra'}"
                        )
                        logger.warning(error_msg)
                        
                        if attempt < max_retries:
                            logger.info(f"Retrying batch {batch_idx}...")
                            continue
                        else:
                            logger.error(f"Batch {batch_idx} failed after {max_retries} attempts")
                            raise ValueError(error_msg)
                    
                    # Success!
                    logger.info(f"✅ Batch {batch_idx} completed successfully ({len(batch_prompts)} prompts)")
                    all_base_prompts.extend(batch_prompts)
                    
                    # Report progress
                    if progress_callback:
                        progress_callback(
                            len(all_base_prompts), 
                            len(narrations), 
                            f"Batch {batch_idx}/{len(batches)} completed"
                        )
                    
                    break
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Batch {batch_idx} JSON parse error (attempt {attempt}/{max_retries}): {e}")
                    if attempt >= max_retries:
                        raise
                    logger.info(f"Retrying batch {batch_idx}...")
        
        base_prompts = all_base_prompts
        logger.info(f"✅ All batches completed. Total prompts: {len(base_prompts)}")
        
        # 5. Apply prompt prefix to each prompt
        from reelforge.utils.prompt_helper import build_image_prompt
        
        # Get prompt prefix from config (fix: correct path is comfyui.image.prompt_prefix)
        image_config = self.core.config.get("comfyui", {}).get("image", {})
        prompt_prefix = image_config.get("prompt_prefix", "")
        
        # Apply prefix to each base prompt
        final_prompts = []
        for base_prompt in base_prompts:
            final_prompt = build_image_prompt(base_prompt, prompt_prefix)
            final_prompts.append(final_prompt)
        
        logger.info(f"Generated {len(final_prompts)} final image prompts with prefix applied")
        return final_prompts
    
    async def _generate_batch_prompts(
        self,
        batch_narrations: List[str],
        config: StoryboardConfig,
        batch_idx: int,
        attempt: int
    ) -> List[str]:
        """
        Generate image prompts for a single batch of narrations
        
        Args:
            batch_narrations: Batch of narrations
            config: Storyboard configuration
            batch_idx: Batch index (for logging)
            attempt: Attempt number (for logging)
            
        Returns:
            List of image prompts for this batch
            
        Raises:
            json.JSONDecodeError: If unable to parse JSON
            KeyError: If response format is invalid
        """
        logger.debug(f"Batch {batch_idx} attempt {attempt}: Generating prompts for {len(batch_narrations)} narrations")
        
        # 1. Build prompt
        prompt = build_image_prompt_prompt(
            narrations=batch_narrations,
            min_words=config.min_image_prompt_words,
            max_words=config.max_image_prompt_words
        )
        
        # 2. Call LLM
        response = await self.core.llm(
            prompt=prompt,
            temperature=0.7,
            max_tokens=8192
        )
        
        logger.debug(f"Batch {batch_idx} attempt {attempt}: LLM response length: {len(response)} chars")
        
        # 3. Parse JSON
        result = self._parse_json(response)
        
        if "image_prompts" not in result:
            logger.error("Response missing 'image_prompts' key")
            raise KeyError("Invalid response format: missing 'image_prompts'")
        
        return result["image_prompts"]
    
    def _parse_json(self, text: str) -> dict:
        """
        Parse JSON from text, with fallback to extract JSON from markdown code blocks
        
        Args:
            text: Text containing JSON
            
        Returns:
            Parsed JSON dict
        """
        # Try direct parsing first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code block
        json_pattern = r'```(?:json)?\s*([\s\S]+?)\s*```'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find any JSON object in the text
        json_pattern = r'\{[^{}]*"image_prompts"\s*:\s*\[[^\]]*\][^{}]*\}'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        # If all fails, raise error
        raise json.JSONDecodeError("No valid JSON found", text, 0)

