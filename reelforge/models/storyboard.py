"""
Storyboard data models for video generation
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class StoryboardConfig:
    """Storyboard configuration parameters"""
    n_storyboard: int = 5                      # Number of storyboard frames
    min_narration_words: int = 30              # Min narration word count
    max_narration_words: int = 50              # Max narration word count
    min_image_prompt_words: int = 60           # Min image prompt word count
    max_image_prompt_words: int = 100          # Max image prompt word count
    
    # Video parameters
    video_width: int = 1080                    # Video width
    video_height: int = 1920                   # Video height (9:16 portrait)
    video_fps: int = 30                        # Frame rate
    
    # Audio parameters
    voice_id: str = "zh-CN-YunjianNeural"     # Default voice
    
    # Image parameters
    image_width: int = 1024
    image_height: int = 1024
    
    # Frame template
    frame_template: Optional[str] = None       # HTML template name or path (None = use PIL)


@dataclass
class StoryboardFrame:
    """Single storyboard frame"""
    index: int                                 # Frame index (0-based)
    narration: str                             # Narration text
    image_prompt: str                          # Image generation prompt
    
    # Generated resource paths
    audio_path: Optional[str] = None           # Audio file path
    image_path: Optional[str] = None           # Original image path
    composed_image_path: Optional[str] = None  # Composed image path (with subtitles)
    video_segment_path: Optional[str] = None   # Video segment path
    
    # Metadata
    duration: float = 0.0                      # Audio duration (seconds)
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class ContentMetadata:
    """Content metadata for visual display and narration generation"""
    title: str                                 # Content title
    author: Optional[str] = None               # Author/creator
    subtitle: Optional[str] = None             # Subtitle
    genre: Optional[str] = None                # Genre/category
    summary: Optional[str] = None              # Content summary
    publication_year: Optional[str] = None     # Publication year
    cover_url: Optional[str] = None            # Cover/thumbnail image URL


@dataclass
class Storyboard:
    """Complete storyboard"""
    topic: str                                 # Topic or content title
    config: StoryboardConfig                   # Configuration
    frames: List[StoryboardFrame] = field(default_factory=list)
    
    # Content metadata (optional)
    content_metadata: Optional[ContentMetadata] = None
    
    # Final output
    final_video_path: Optional[str] = None
    total_duration: float = 0.0
    
    # Metadata
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def is_completed(self) -> bool:
        """Check if all frames are processed"""
        return all(
            frame.video_segment_path is not None
            for frame in self.frames
        )
    
    @property
    def progress(self) -> float:
        """Return processing progress (0.0-1.0)"""
        if not self.frames:
            return 0.0
        completed = sum(
            1 for frame in self.frames
            if frame.video_segment_path is not None
        )
        return completed / len(self.frames)


@dataclass
class VideoGenerationResult:
    """Video generation result"""
    video_path: str                            # Final video path
    storyboard: Storyboard                     # Complete storyboard
    duration: float                            # Total duration
    file_size: int                             # File size (bytes)
    created_at: datetime = field(default_factory=datetime.now)

