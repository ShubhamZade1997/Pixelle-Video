"""
Frame processor - Process single frame through complete pipeline

Orchestrates: TTS → Image Generation → Frame Composition → Video Segment
"""

from typing import Callable, Optional

import httpx
from loguru import logger

from reelforge.models.progress import ProgressEvent
from reelforge.models.storyboard import Storyboard, StoryboardFrame, StoryboardConfig


class FrameProcessor:
    """Frame processor"""
    
    def __init__(self, reelforge_core):
        """
        Initialize
        
        Args:
            reelforge_core: ReelForgeCore instance
        """
        self.core = reelforge_core
    
    async def __call__(
        self,
        frame: StoryboardFrame,
        storyboard: 'Storyboard',
        config: StoryboardConfig,
        total_frames: int = 1,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None
    ) -> StoryboardFrame:
        """
        Process single frame through complete pipeline
        
        Steps:
        1. Generate audio (TTS)
        2. Generate image (ComfyKit)
        3. Compose frame (add subtitle)
        4. Create video segment (image + audio)
        
        Args:
            frame: Storyboard frame to process
            storyboard: Storyboard instance
            config: Storyboard configuration
            total_frames: Total number of frames in storyboard
            progress_callback: Optional callback for progress updates (receives ProgressEvent)
            
        Returns:
            Processed frame with all paths filled
        """
        logger.info(f"Processing frame {frame.index}...")
        
        frame_num = frame.index + 1
        
        try:
            # Step 1: Generate audio (TTS)
            await self._step_generate_audio(frame, config)
            if progress_callback:
                progress_callback(ProgressEvent(
                    event_type="frame_step",
                    progress=0.25,
                    frame_current=frame_num,
                    frame_total=total_frames,
                    step=1,
                    action="audio"
                ))
            
            # Step 2: Generate image (ComfyKit)
            await self._step_generate_image(frame, config)
            if progress_callback:
                progress_callback(ProgressEvent(
                    event_type="frame_step",
                    progress=0.50,
                    frame_current=frame_num,
                    frame_total=total_frames,
                    step=2,
                    action="image"
                ))
            
            # Step 3: Compose frame (add subtitle)
            await self._step_compose_frame(frame, storyboard, config)
            if progress_callback:
                progress_callback(ProgressEvent(
                    event_type="frame_step",
                    progress=0.75,
                    frame_current=frame_num,
                    frame_total=total_frames,
                    step=3,
                    action="compose"
                ))
            
            # Step 4: Create video segment
            await self._step_create_video_segment(frame, config)
            if progress_callback:
                progress_callback(ProgressEvent(
                    event_type="frame_step",
                    progress=1.0,
                    frame_current=frame_num,
                    frame_total=total_frames,
                    step=4,
                    action="video"
                ))
            
            logger.info(f"✅ Frame {frame.index} completed")
            return frame
            
        except Exception as e:
            logger.error(f"❌ Failed to process frame {frame.index}: {e}")
            raise
    
    async def _step_generate_audio(
        self,
        frame: StoryboardFrame,
        config: StoryboardConfig
    ):
        """Step 1: Generate audio using TTS"""
        logger.debug(f"  1/4: Generating audio for frame {frame.index}...")
        
        # Generate output path using task_id
        from reelforge.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(config.task_id, frame.index, "audio")
        
        # Call TTS with specific output path and workflow
        audio_path = await self.core.tts(
            text=frame.narration,
            workflow=config.tts_workflow,  # Use workflow from config
            voice=config.voice_id,
            speed=config.tts_speed,  # Use speed (not rate) from config
            output_path=output_path,
        )
        
        frame.audio_path = audio_path
        
        # Get audio duration
        frame.duration = await self._get_audio_duration(audio_path)
        
        logger.debug(f"  ✓ Audio generated: {audio_path} ({frame.duration:.2f}s)")
    
    async def _step_generate_image(
        self,
        frame: StoryboardFrame,
        config: StoryboardConfig
    ):
        """Step 2: Generate image using ComfyKit"""
        logger.debug(f"  2/4: Generating image for frame {frame.index}...")
        
        # Call Image generation (with optional preset)
        image_url = await self.core.image(
            prompt=frame.image_prompt,
            workflow=config.image_workflow,  # Pass workflow from config (None = use default)
            width=config.image_width,
            height=config.image_height
        )
        
        # Download image to local (pass task_id)
        local_path = await self._download_image(image_url, frame.index, config.task_id)
        frame.image_path = local_path
        
        logger.debug(f"  ✓ Image generated: {local_path}")
    
    async def _step_compose_frame(
        self,
        frame: StoryboardFrame,
        storyboard: 'Storyboard',
        config: StoryboardConfig
    ):
        """Step 3: Compose frame with subtitle using HTML template"""
        logger.debug(f"  3/4: Composing frame {frame.index}...")
        
        # Generate output path using task_id
        from reelforge.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(config.task_id, frame.index, "composed")
        
        # Use HTML template to compose frame
        composed_path = await self._compose_frame_html(frame, storyboard, config, output_path)
        
        frame.composed_image_path = composed_path
        
        logger.debug(f"  ✓ Frame composed: {composed_path}")
    
    async def _compose_frame_html(
        self,
        frame: StoryboardFrame,
        storyboard: 'Storyboard',
        config: StoryboardConfig,
        output_path: str
    ) -> str:
        """Compose frame using HTML template"""
        from reelforge.services.frame_html import HTMLFrameGenerator
        from pathlib import Path
        
        # Resolve template path
        template_filename = config.frame_template
        
        # Try templates/ directory first
        template_path = Path(f"templates/{template_filename}")
        if not template_path.exists():
            # Try as absolute/relative path
            template_path = Path(template_filename)
            if not template_path.exists():
                raise FileNotFoundError(
                    f"Template not found: {template_filename}. "
                    f"Built-in templates: default.html, modern.html, neon.html"
                )
        
        # Get content metadata from storyboard
        content_metadata = storyboard.content_metadata if storyboard else None
        
        # Build ext data
        ext = {}
        if content_metadata:
            ext["content_title"] = content_metadata.title or ""
            ext["content_author"] = content_metadata.author or ""
            ext["content_subtitle"] = content_metadata.subtitle or ""
            ext["content_genre"] = content_metadata.genre or ""
        
        # Generate frame using HTML
        generator = HTMLFrameGenerator(str(template_path))
        composed_path = await generator.generate_frame(
            title=storyboard.title,
            text=frame.narration,
            image=frame.image_path,
            ext=ext,
            width=config.video_width,
            height=config.video_height,
            output_path=output_path
        )
        
        return composed_path
    
    async def _step_create_video_segment(
        self,
        frame: StoryboardFrame,
        config: StoryboardConfig
    ):
        """Step 4: Create video segment from image + audio"""
        logger.debug(f"  4/4: Creating video segment for frame {frame.index}...")
        
        # Generate output path using task_id
        from reelforge.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(config.task_id, frame.index, "segment")
        
        # Call video compositor to create video from image + audio
        from reelforge.services.video import VideoService
        video_service = VideoService()
        
        segment_path = video_service.create_video_from_image(
            image=frame.composed_image_path,
            audio=frame.audio_path,
            output=output_path,
            fps=config.video_fps
        )
        
        frame.video_segment_path = segment_path
        
        logger.debug(f"  ✓ Video segment created: {segment_path}")
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds"""
        try:
            # Try using ffmpeg-python
            import ffmpeg
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}, using estimate")
            # Fallback: estimate based on file size (very rough)
            import os
            file_size = os.path.getsize(audio_path)
            # Assume ~16kbps for MP3, so 2KB per second
            estimated_duration = file_size / 2000
            return max(1.0, estimated_duration)  # At least 1 second
    
    async def _download_image(self, url: str, frame_index: int, task_id: str) -> str:
        """Download image from URL to local file"""
        from reelforge.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(task_id, frame_index, "image")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
        
        return output_path

