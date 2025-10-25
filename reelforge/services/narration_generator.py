"""
Narration generation service

Supports two content sources:
1. Topic: Generate narrations from a topic/theme
2. Content: Extract/refine narrations from user-provided content
"""

import json
import re
from typing import List, Optional, Literal

from loguru import logger

from reelforge.models.storyboard import StoryboardConfig, ContentMetadata
from reelforge.prompts.narration_template import (
    build_topic_narration_prompt,
    build_content_narration_prompt,
    build_narration_prompt  # Keep for backward compatibility
)


class NarrationGeneratorService:
    """Narration generation service"""
    
    def __init__(self, reelforge_core):
        """
        Initialize
        
        Args:
            reelforge_core: ReelForgeCore instance (for calling llm)
        """
        self.core = reelforge_core
    
    async def generate_narrations(
        self,
        config: StoryboardConfig,
        source_type: Literal["topic", "content"],
        content_metadata: Optional[ContentMetadata] = None,
        topic: Optional[str] = None,
        content: Optional[str] = None,
    ) -> List[str]:
        """
        Generate storyboard narrations from different sources
        
        Args:
            config: Storyboard configuration
            source_type: Type of content source ("topic" or "content")
            content_metadata: Content metadata (optional, not currently used)
            topic: Topic/theme (required if source_type="topic")
            content: User-provided content (required if source_type="content")
            
        Returns:
            List of narration texts
            
        Raises:
            ValueError: If parameters don't match source_type or narration count mismatch
            json.JSONDecodeError: If unable to parse LLM response as JSON
            
        Examples:
            # Generate from topic
            >>> narrations = await service.generate_narrations(
            ...     config=config,
            ...     source_type="topic",
            ...     topic="如何提高学习效率"
            ... )
            
            # Generate from user content
            >>> narrations = await service.generate_narrations(
            ...     config=config,
            ...     source_type="content",
            ...     content="昨天我读了一本书..."
            ... )
        """
        # 1. Build prompt based on source_type
        if source_type == "topic":
            if topic is None:
                raise ValueError("topic is required when source_type='topic'")
            logger.info(f"Generating topic narrations for: {topic}")
            prompt = build_topic_narration_prompt(
                topic=topic,
                n_storyboard=config.n_storyboard,
                min_words=config.min_narration_words,
                max_words=config.max_narration_words
            )
        
        else:  # content
            if content is None:
                raise ValueError("content is required when source_type='content'")
            logger.info(f"Generating narrations from user content ({len(content)} chars)")
            prompt = build_content_narration_prompt(
                content=content,
                n_storyboard=config.n_storyboard,
                min_words=config.min_narration_words,
                max_words=config.max_narration_words
            )
        
        # 2. Call LLM (using self.core.llm)
        response = await self.core.llm(
            prompt=prompt,
            temperature=0.8,  # Higher temperature for more creativity
            max_tokens=2000
        )
        
        logger.debug(f"LLM response: {response[:200]}...")
        
        # 3. Parse JSON
        try:
            result = self._parse_json(response)
            narrations = result["narrations"]
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response: {response}")
            raise
        except KeyError:
            logger.error("Response JSON missing 'narrations' key")
            logger.error(f"Response: {response}")
            raise ValueError("Invalid response format")
        
        # 4. Validate count (take first N if got more)
        if len(narrations) > config.n_storyboard:
            logger.warning(
                f"Got {len(narrations)} narrations, taking first {config.n_storyboard}"
            )
            narrations = narrations[:config.n_storyboard]
        elif len(narrations) < config.n_storyboard:
            raise ValueError(
                f"Expected at least {config.n_storyboard} narrations, "
                f"got only {len(narrations)}"
            )
        
        # 5. Validate word count for each narration
        for i, text in enumerate(narrations):
            word_count = len(text)
            if word_count < config.min_narration_words:
                logger.warning(
                    f"Narration {i} too short: {word_count} chars "
                    f"(min: {config.min_narration_words})"
                )
        
        logger.info(f"Generated {len(narrations)} narrations successfully")
        return narrations
    
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
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find any JSON object in the text
        json_pattern = r'\{[^{}]*"narrations"\s*:\s*\[[^\]]*\][^{}]*\}'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        # If all fails, raise error
        raise json.JSONDecodeError("No valid JSON found", text, 0)

