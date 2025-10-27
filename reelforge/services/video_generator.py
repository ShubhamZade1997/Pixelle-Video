"""
Video Generator Service

End-to-end service for generating short videos from content.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Literal

from loguru import logger

from reelforge.models.progress import ProgressEvent
from reelforge.models.storyboard import (
    Storyboard,
    StoryboardFrame,
    StoryboardConfig,
    ContentMetadata,
    VideoGenerationResult
)


class VideoGeneratorService:
    """
    Video generation service
    
    Orchestrates the complete pipeline:
    1. Generate narrations (LLM)
    2. Generate image prompts (LLM)
    3. Process each frame (TTS + Image + Compose + Video)
    4. Concatenate all segments
    5. Add BGM (optional)
    """
    
    def __init__(self, reelforge_core):
        """
        Initialize video generator service
        
        Args:
            reelforge_core: ReelForgeCore instance
        """
        self.core = reelforge_core
    
    async def __call__(
        self,
        # === Input ===
        text: str,
        
        # === Processing Mode ===
        mode: Literal["generate", "fixed"] = "generate",
        
        # === Optional Title ===
        title: Optional[str] = None,
        
        # === Basic Config ===
        n_scenes: int = 5,  # Only used in generate mode; ignored in fixed mode
        voice_id: str = "zh-CN-YunjianNeural",
        output_path: Optional[str] = None,
        
        # === LLM Parameters ===
        min_narration_words: int = 5,
        max_narration_words: int = 20,
        min_image_prompt_words: int = 30,
        max_image_prompt_words: int = 60,
        
        # === Image Parameters ===
        image_width: int = 1024,
        image_height: int = 1024,
        image_workflow: Optional[str] = None,
        
        # === Video Parameters ===
        video_width: int = 1080,
        video_height: int = 1920,
        video_fps: int = 30,
        
        # === Frame Template ===
        frame_template: Optional[str] = None,
        
        # === Image Style ===
        prompt_prefix: Optional[str] = None,
        
        # === BGM Parameters ===
        bgm_path: Optional[str] = None,
        bgm_volume: float = 0.2,
        bgm_mode: Literal["once", "loop"] = "loop",
        
        # === Advanced Options ===
        content_metadata: Optional[ContentMetadata] = None,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
    ) -> VideoGenerationResult:
        """
        Generate short video from text input
        
        Args:
            text: Text input (required)
                  - For generate mode: topic/theme (e.g., "如何提高学习效率")
                  - For fixed mode: complete narration script (will be split into frames)
            
            mode: Processing mode (default "generate")
                  - "generate": LLM generates narrations from topic/theme, creates n_scenes
                  - "fixed": Split existing script into frames, preserves original text
                  
                  Note: In fixed mode, n_scenes is ignored (uses actual split count)
            
            title: Video title (optional)
                   - If provided, use it as the video title
                   - If not provided:
                     * generate mode → use text as title
                     * fixed mode → LLM generates title from script
            
            n_scenes: Number of storyboard scenes (default 5)
                      Only effective in generate mode; ignored in fixed mode
            
            voice_id: TTS voice ID (default "zh-CN-YunjianNeural")
            output_path: Output video path (auto-generated if None)
            
            min_narration_words: Min narration length (generate mode only)
            max_narration_words: Max narration length (generate mode only)
            min_image_prompt_words: Min image prompt length
            max_image_prompt_words: Max image prompt length
            
            image_width: Generated image width (default 1024)
            image_height: Generated image height (default 1024)
            image_workflow: Image workflow filename (e.g., "image_flux.json", None = use default)
            
            video_width: Final video width (default 1080)
            video_height: Final video height (default 1920)
            video_fps: Video frame rate (default 30)
            
            frame_template: HTML template filename or path (None = use PIL)
                           e.g., "default.html", "modern.html", "neon.html", or custom path
            
            prompt_prefix: Image prompt prefix (overrides config.yaml if provided)
                          e.g., "anime style, vibrant colors" or "" for no prefix
            
            bgm_path: BGM path (filename like "default.mp3", custom path, or None)
            bgm_volume: BGM volume 0.0-1.0 (default 0.2)
            bgm_mode: BGM mode "once" or "loop" (default "loop")
            
            content_metadata: Content metadata (optional, for display)
            progress_callback: Progress callback function(message, progress)
        
        Returns:
            VideoGenerationResult with video path and metadata
        
        Examples:
            # Generate mode: LLM creates narrations from topic
            >>> result = await reelforge.generate_video(
            ...     text="如何在信息爆炸时代保持深度思考",
            ...     mode="generate",
            ...     n_scenes=5,
            ...     bgm_path="default"
            ... )
            
            # Fixed mode: Use existing script (split by paragraphs)
            >>> script = '''大家好，今天跟你分享三个学习技巧
            ... 
            ... 第一个技巧是专注力训练，每天冥想10分钟
            ... 
            ... 第二个技巧是主动回忆，学完立即复述'''
            >>> result = await reelforge.generate_video(
            ...     text=script,
            ...     mode="fixed",
            ...     title="三个学习技巧"
            ... )
            
            # Fixed mode: Use existing script (split by sentences)
            >>> result = await reelforge.generate_video(
            ...     text="第一点是专注。第二点是复述。第三点是重复。",
            ...     mode="fixed"
            ... )
            >>> print(result.video_path)
        """
        # ========== Step 0: Process text and determine title ==========
        logger.info(f"🚀 Starting video generation in '{mode}' mode")
        logger.info(f"   Text length: {len(text)} chars")
        
        # Determine final title (priority: user-specified > auto-generated)
        if title:
            # User specified title, use it directly
            final_title = title
            logger.info(f"   Title: '{title}' (user-specified)")
        else:
            # Auto-generate title based on mode
            if mode == "generate":
                # Use text as title (it's a topic/theme)
                final_title = text[:20] if len(text) > 20 else text
                logger.info(f"   Title: '{final_title}' (from text)")
            else:  # fixed
                # Generate title from script using LLM
                self._report_progress(progress_callback, "generating_title", 0.01)
                final_title = await self._generate_title_from_content(text)
                logger.info(f"   Title: '{final_title}' (LLM-generated)")
        
        # Auto-generate output path if not provided
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # Use first 10 chars of final_title for filename
            safe_name = final_title[:10].replace('/', '_').replace(' ', '_')
            output_path = f"output/{timestamp}_{safe_name}.mp4"
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create storyboard config
        config = StoryboardConfig(
            n_storyboard=n_scenes,
            min_narration_words=min_narration_words,
            max_narration_words=max_narration_words,
            min_image_prompt_words=min_image_prompt_words,
            max_image_prompt_words=max_image_prompt_words,
            video_width=video_width,
            video_height=video_height,
            video_fps=video_fps,
            voice_id=voice_id,
            image_width=image_width,
            image_height=image_height,
            image_workflow=image_workflow,
            frame_template=frame_template
        )
        
        # Create storyboard
        storyboard = Storyboard(
            topic=final_title,  # Use final_title as video title
            config=config,
            content_metadata=content_metadata,
            created_at=datetime.now()
        )
        
        try:
            # ========== Step 1: Generate/Split narrations ==========
            if mode == "generate":
                # Generate narrations using LLM
                self._report_progress(progress_callback, "generating_narrations", 0.05)
                narrations = await self.core.narration_generator.generate_narrations(
                    config=config,
                    source_type="topic",
                    content_metadata=None,
                    topic=text,
                    content=None
                )
                logger.info(f"✅ Generated {len(narrations)} narrations")
            else:  # fixed
                # Split fixed script using LLM (preserves original text)
                self._report_progress(progress_callback, "splitting_script", 0.05)
                narrations = await self._split_narration_script(text, config)
                logger.info(f"✅ Split script into {len(narrations)} segments")
                logger.info(f"   Note: n_scenes={n_scenes} is ignored in fixed mode")
            
            # Step 2: Generate image prompts
            self._report_progress(progress_callback, "generating_image_prompts", 0.15)
            
            # Override prompt_prefix if provided (temporarily modify config)
            original_prefix = None
            if prompt_prefix is not None:
                image_config = self.core.config.get("image", {})
                original_prefix = image_config.get("prompt_prefix")
                image_config["prompt_prefix"] = prompt_prefix
                logger.info(f"Using custom prompt_prefix: '{prompt_prefix}'")
            
            try:
                # Create progress callback wrapper for image prompt generation (15%-30% range)
                def image_prompt_progress(completed: int, total: int, message: str):
                    # Map batch progress to 15%-30% range
                    batch_progress = completed / total if total > 0 else 0
                    overall_progress = 0.15 + (batch_progress * 0.15)  # 15% -> 30%
                    self._report_progress(
                        progress_callback, 
                        "generating_image_prompts", 
                        overall_progress,
                        extra_info=message
                    )
                
                image_prompts = await self.core.image_prompt_generator.generate_image_prompts(
                    narrations=narrations,
                    config=config,
                    progress_callback=image_prompt_progress
                )
            finally:
                # Restore original prompt_prefix
                if original_prefix is not None:
                    image_config["prompt_prefix"] = original_prefix
            logger.info(f"✅ Generated {len(image_prompts)} image prompts")
            
            # Step 3: Create frames
            for i, (narration, image_prompt) in enumerate(zip(narrations, image_prompts)):
                frame = StoryboardFrame(
                    index=i,
                    narration=narration,
                    image_prompt=image_prompt,
                    created_at=datetime.now()
                )
                storyboard.frames.append(frame)
            
            # Step 4: Process each frame
            for i, frame in enumerate(storyboard.frames):
                # Calculate fine-grained progress for this frame
                base_progress = 0.2  # Frames processing starts at 20%
                frame_range = 0.6    # Frames processing takes 60% (20%-80%)
                per_frame_progress = frame_range / len(storyboard.frames)
                
                # Create frame-specific progress callback
                def frame_progress_callback(event: ProgressEvent):
                    """Report sub-step progress within current frame"""
                    # Calculate overall progress: base + previous frames + current frame progress
                    overall_progress = base_progress + (per_frame_progress * i) + (per_frame_progress * event.progress)
                    # Forward the event with adjusted overall progress
                    if progress_callback:
                        adjusted_event = ProgressEvent(
                            event_type=event.event_type,
                            progress=overall_progress,
                            frame_current=event.frame_current,
                            frame_total=event.frame_total,
                            step=event.step,
                            action=event.action
                        )
                        progress_callback(adjusted_event)
                
                # Report frame start
                self._report_progress(
                    progress_callback,
                    "processing_frame",
                    base_progress + (per_frame_progress * i),
                    frame_current=i+1,
                    frame_total=len(storyboard.frames)
                )
                
                processed_frame = await self.core.storyboard_processor.process_frame(
                    frame=frame,
                    storyboard=storyboard,
                    config=config,
                    total_frames=len(storyboard.frames),
                    progress_callback=frame_progress_callback
                )
                storyboard.total_duration += processed_frame.duration
                logger.info(f"✅ Frame {i+1} completed ({processed_frame.duration:.2f}s)")
            
            # Step 5: Concatenate videos
            self._report_progress(progress_callback, "concatenating", 0.85)
            segment_paths = [frame.video_segment_path for frame in storyboard.frames]
            
            from reelforge.services.video import VideoService
            video_service = VideoService()
            
            final_video_path = video_service.concat_videos(
                videos=segment_paths,
                output=output_path,
                bgm_path=bgm_path,
                bgm_volume=bgm_volume,
                bgm_mode=bgm_mode
            )
            
            storyboard.final_video_path = final_video_path
            storyboard.completed_at = datetime.now()
            
            logger.success(f"🎬 Video generation completed: {final_video_path}")
            
            # Step 6: Create result
            self._report_progress(progress_callback, "finalizing", 1.0)
            
            video_path_obj = Path(final_video_path)
            file_size = video_path_obj.stat().st_size
            
            result = VideoGenerationResult(
                video_path=final_video_path,
                storyboard=storyboard,
                duration=storyboard.total_duration,
                file_size=file_size
            )
            
            logger.info(f"✅ Generated video: {final_video_path}")
            logger.info(f"   Duration: {storyboard.total_duration:.2f}s")
            logger.info(f"   Size: {file_size / (1024*1024):.2f} MB")
            logger.info(f"   Frames: {len(storyboard.frames)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Video generation failed: {e}")
            raise
    
    def _report_progress(
        self,
        callback: Optional[Callable[[ProgressEvent], None]],
        event_type: str,
        progress: float,
        **kwargs
    ):
        """
        Report progress via callback
        
        Args:
            callback: Progress callback function
            event_type: Type of progress event
            progress: Progress value (0.0-1.0)
            **kwargs: Additional event-specific parameters (frame_current, frame_total, etc.)
        """
        if callback:
            event = ProgressEvent(event_type=event_type, progress=progress, **kwargs)
            callback(event)
            logger.debug(f"Progress: {progress*100:.0f}% - {event_type}")
        else:
            logger.debug(f"Progress: {progress*100:.0f}% - {event_type}")
    
    def _parse_json(self, text: str) -> dict:
        """
        Parse JSON from text, with fallback to extract JSON from markdown code blocks
        
        Args:
            text: Text containing JSON
            
        Returns:
            Parsed JSON dict
        """
        import json
        import re
        
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
        
        # Try to find any JSON object in the text (flexible pattern for narrations)
        json_pattern = r'\{[^{}]*"narrations"\s*:\s*\[[^\]]*\][^{}]*\}'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        # If all fails, raise error
        raise json.JSONDecodeError("No valid JSON found", text, 0)
    
    async def _split_narration_script(self, script: str, config: StoryboardConfig) -> list[str]:
        """
        Split user-provided narration script into segments (programmatic splitting).
        
        Priority:
        1. Split by major punctuation (newline, 。！？；)
        2. If segment > max_len, split by comma (，)
        3. If still > max_len, keep original (no force split)
        4. Merge segments < min_len with next segment
        
        Args:
            script: Fixed narration script
            config: Storyboard configuration (for length guidelines)
            
        Returns:
            List of narration segments
        """
        import re
        
        min_len = config.min_narration_words
        max_len = config.max_narration_words
        
        logger.info(f"Splitting script (length: {len(script)} chars) with target: {min_len}-{max_len} chars")
        
        # Step 1: Split by major punctuation (newline, period, exclamation, question mark, semicolon)
        major_delimiters = r'[\n。！？；]'
        parts = re.split(f'({major_delimiters})', script)
        
        # Reconstruct sentences (text only, remove trailing punctuation)
        sentences = []
        for i in range(0, len(parts)-1, 2):
            text = parts[i].strip()
            if text:
                sentences.append(text)
        # Handle last part if no delimiter
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1].strip())
        
        logger.debug(f"After major split: {len(sentences)} sentences")
        
        # Step 2: For segments > max_len, try splitting by comma
        final_segments = []
        for sentence in sentences:
            sent_len = len(sentence)
            
            # If within range or short, keep as is
            if sent_len <= max_len:
                final_segments.append(sentence)
                continue
            
            # Too long: try splitting by comma
            comma_parts = re.split(r'(，)', sentence)
            sub_segments = []
            current = ""
            
            for part in comma_parts:
                if part == '，':
                    continue
                    
                if not current:
                    current = part
                elif len(current + part) <= max_len:
                    current += part
                else:
                    # Current segment is ready
                    if current:
                        sub_segments.append(current.strip())
                    current = part
            
            # Add last segment
            if current:
                sub_segments.append(current.strip())
            
            # If comma splitting worked (resulted in multiple segments), use it
            if sub_segments and len(sub_segments) > 1:
                final_segments.extend(sub_segments)
            else:
                # Keep original sentence even if > max_len
                logger.debug(f"Keeping long segment ({sent_len} chars): {sentence[:30]}...")
                final_segments.append(sentence)
        
        # Step 3: Merge segments that are too short
        merged_segments = []
        i = 0
        while i < len(final_segments):
            segment = final_segments[i]
            
            # If too short and not the last one, try merging with next
            if len(segment) < min_len and i < len(final_segments) - 1:
                next_segment = final_segments[i + 1]
                merged = segment + "，" + next_segment
                
                # If merged result is within max_len, use it
                if len(merged) <= max_len:
                    merged_segments.append(merged)
                    i += 2  # Skip next segment
                    continue
            
            # Otherwise keep as is
            merged_segments.append(segment)
            i += 1
        
        # Clean up
        result = [s.strip() for s in merged_segments if s.strip()]
        
        # Log statistics
        lengths = [len(s) for s in result]
        logger.info(f"Script split into {len(result)} segments")
        if lengths:
            logger.info(f"  Min: {min(lengths)} chars, Max: {max(lengths)} chars, Avg: {sum(lengths)//len(lengths)} chars")
            
            in_range = sum(1 for l in lengths if min_len <= l <= max_len)
            too_short = sum(1 for l in lengths if l < min_len)
            too_long = sum(1 for l in lengths if l > max_len)
            
            logger.info(f"  In range ({min_len}-{max_len}): {in_range}/{len(result)} ({in_range*100//len(result)}%)")
            if too_short:
                logger.info(f"  Too short (< {min_len}): {too_short}/{len(result)} ({too_short*100//len(result)}%)")
            if too_long:
                logger.info(f"  Too long (> {max_len}): {too_long}/{len(result)} ({too_long*100//len(result)}%)")
        
        return result
    
    async def _generate_title_from_content(self, content: str) -> str:
        """
        Generate a short, attractive title from user content using LLM
        
        Args:
            content: User-provided content
            
        Returns:
            Generated title (10 characters or less)
        """
        from reelforge.prompts import build_title_generation_prompt
        
        # Build prompt using template
        prompt = build_title_generation_prompt(content, max_length=500)
        
        # Call LLM to generate title
        response = await self.core.llm(
            prompt=prompt,
            temperature=0.7,
            max_tokens=50
        )
        
        # Clean up response
        title = response.strip()
        
        # Remove quotes if present
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1]
        if title.startswith("'") and title.endswith("'"):
            title = title[1:-1]
        
        # Limit to 20 chars max (safety)
        if len(title) > 20:
            title = title[:20]
        
        return title

