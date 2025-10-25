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
        # === Content Source (Choose ONE, mutually exclusive) ===
        topic: Optional[str] = None,
        content: Optional[str] = None,
        
        # === Optional Title (works with any source) ===
        title: Optional[str] = None,
        
        # === Basic Config ===
        n_frames: int = 5,
        voice_id: str = "zh-CN-YunjianNeural",
        output_path: Optional[str] = None,
        
        # === LLM Parameters ===
        min_narration_words: int = 20,
        max_narration_words: int = 40,
        min_image_prompt_words: int = 50,
        max_image_prompt_words: int = 100,
        
        # === Image Parameters ===
        image_width: int = 1024,
        image_height: int = 1024,
        image_style_preset: Optional[str] = None,
        image_style_description: Optional[str] = None,
        
        # === Video Parameters ===
        video_width: int = 1080,
        video_height: int = 1920,
        video_fps: int = 30,
        
        # === Frame Template ===
        frame_template: Optional[str] = None,
        
        # === BGM Parameters ===
        bgm_path: Optional[str] = None,
        bgm_volume: float = 0.2,
        bgm_mode: Literal["once", "loop"] = "loop",
        
        # === Advanced Options ===
        content_metadata: Optional[ContentMetadata] = None,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
    ) -> VideoGenerationResult:
        """
        Generate short video from different content sources
        
        Args:
            topic: Topic/theme (e.g., "如何提高学习效率")
            content: User-provided content (any length)
            
            Note: Must provide exactly ONE of: topic or content
            
            title: Video title (optional)
                   - If provided, use it as the video title
                   - If not provided, auto-generate based on source:
                     * topic → use topic text
                     * content → LLM extracts title from content
            
            n_frames: Number of storyboard frames (default 5)
            voice_id: TTS voice ID (default "zh-CN-YunjianNeural")
            output_path: Output video path (auto-generated if None)
            
            min_narration_words: Min narration length
            max_narration_words: Max narration length
            min_image_prompt_words: Min image prompt length
            max_image_prompt_words: Max image prompt length
            
            image_width: Generated image width (default 1024)
            image_height: Generated image height (default 1024)
            image_style_preset: Preset style name (e.g., "minimal", "concept", "cinematic")
            image_style_description: Custom style description (overrides preset)
            
            video_width: Final video width (default 1080)
            video_height: Final video height (default 1920)
            video_fps: Video frame rate (default 30)
            
            frame_template: HTML template name or path (None = use PIL)
                           e.g., "classic", "modern", "minimal", or custom path
            
            bgm_path: BGM path ("default", "happy", custom path, or None)
            bgm_volume: BGM volume 0.0-1.0 (default 0.2)
            bgm_mode: BGM mode "once" or "loop" (default "loop")
            
            content_metadata: Content metadata (optional, for display)
            progress_callback: Progress callback function(message, progress)
        
        Returns:
            VideoGenerationResult with video path and metadata
        
        Examples:
            # Generate from topic
            >>> result = await reelforge.generate_video(
            ...     topic="如何在信息爆炸时代保持深度思考",
            ...     n_frames=5,
            ...     bgm_path="default"
            ... )
            
            # Generate from user content with auto-generated title
            >>> result = await reelforge.generate_video(
            ...     content="昨天我读了一本书，讲的是...",
            ...     n_frames=3
            ... )
            
            # Generate from user content with custom title
            >>> result = await reelforge.generate_video(
            ...     content="买房子，第一应该看的是楼盘的整体环境...",
            ...     title="买房风水指南",
            ...     n_frames=5
            ... )
            >>> print(result.video_path)
        """
        # ========== Step 0: Validate parameters (mutually exclusive) ==========
        sources = [topic, content]
        source_count = sum(x is not None for x in sources)
        
        if source_count == 0:
            raise ValueError(
                "Must provide exactly ONE of: topic or content"
            )
        elif source_count > 1:
            raise ValueError(
                "Cannot provide multiple sources. Choose ONE of: topic or content"
            )
        
        # Determine source type
        if topic:
            source_type = "topic"
        else:  # content
            source_type = "content"
        
        # Determine final title (priority: user-specified > auto-generated)
        if title:
            # User specified title, use it directly
            final_title = title
            logger.info(f"🚀 Starting video generation from {source_type} with title: '{title}'")
        else:
            # Auto-generate title based on source
            if source_type == "topic":
                final_title = topic
                logger.info(f"🚀 Starting video generation from topic: '{final_title}'")
            else:  # content
                # Will generate title from content using LLM
                logger.info(f"🚀 Starting video generation from content ({len(content)} chars)")
                final_title = None  # Will be generated later
        
        # Generate title from content if needed (before creating output path)
        if source_type == "content" and final_title is None:
            self._report_progress(progress_callback, "generating_title", 0.01)
            final_title = await self._generate_title_from_content(content)
            logger.info(f"✅ Generated title: {final_title}")
        
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
            n_storyboard=n_frames,
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
            frame_template=frame_template
        )
        
        # Create storyboard
        storyboard = Storyboard(
            topic=final_title,  # Use final_title as video title
            config=config,
            content_metadata=content_metadata,
            created_at=datetime.now()
        )
        
        # Store storyboard in core for access in storyboard processor
        self.core._current_storyboard = storyboard
        
        try:
            # ========== Step 1: Generate narrations ==========
            self._report_progress(progress_callback, "generating_narrations", 0.05)
            narrations = await self.core.narration_generator.generate_narrations(
                config=config,
                source_type=source_type,
                content_metadata=None,  # No metadata needed for topic/content
                topic=topic if source_type == "topic" else None,
                content=content if source_type == "content" else None
            )
            logger.info(f"✅ Generated {len(narrations)} narrations")
            
            # Step 2: Generate image prompts
            self._report_progress(progress_callback, "generating_image_prompts", 0.15)
            image_prompts = await self.core.image_prompt_generator.generate_image_prompts(
                narrations=narrations,
                config=config,
                image_style_preset=image_style_preset,
                image_style_description=image_style_description
            )
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
    
    async def _generate_title_from_content(self, content: str) -> str:
        """
        Generate a short, attractive title from user content using LLM
        
        Args:
            content: User-provided content
            
        Returns:
            Generated title (10 characters or less)
        """
        # Take first 500 chars to avoid overly long prompts
        content_preview = content[:500]
        
        prompt = f"""请为以下内容生成一个简短、有吸引力的标题（10字以内）。

内容：
{content_preview}

要求：
1. 简短精炼，10字以内
2. 准确概括核心内容
3. 有吸引力，适合作为视频标题
4. 只输出标题文本，不要其他内容

标题："""
        
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

