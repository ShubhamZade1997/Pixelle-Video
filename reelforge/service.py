"""
ReelForge Core - Capability Layer

Provides unified access to all capabilities (LLM, TTS, etc.)
"""

from typing import Optional

from loguru import logger

from reelforge.config import load_config
from reelforge.core.discovery import CapabilityRegistry
from reelforge.core.mcp_server import reelforge_mcp
from reelforge.core.config_manager import ConfigManager
from reelforge.services import LLMService, TTSService, ImageService


class ReelForgeCore:
    """
    ReelForge Core - Capability Layer
    
    Provides unified access to all capabilities.
    This is the foundation layer, no business logic here.
    
    Usage:
        from reelforge import reelforge
        
        # Initialize
        await reelforge.initialize()
        
        # Use capabilities directly
        answer = await reelforge.llm("Explain atomic habits")
        audio = await reelforge.tts("Hello world")
        
        # Check active capabilities
        print(f"Using LLM: {reelforge.llm.active}")
        print(f"Available: {reelforge.llm.available}")
    
    Architecture (Simplified):
        ReelForgeCore (this class)
          ├── config (configuration)
          ├── config_manager (config injection + MCP calls)
          ├── llm (LLM service)
          ├── tts (TTS service)
          └── image (Image service)
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize ReelForge Core
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.registry: Optional[CapabilityRegistry] = None
        self.config_manager: Optional[ConfigManager] = None
        self._initialized = False
        
        # Services (initialized in initialize())
        self.llm: Optional[LLMService] = None
        self.tts: Optional[TTSService] = None
        self.image: Optional[ImageService] = None
        
        # Content generation services
        self.narration_generator = None
        self.image_prompt_generator = None
        self.generate_final_image_prompt = None
        
        # Frame processing services
        self.frame_composer = None
        self.storyboard_processor = None
        
        # Video generation service (named as verb for direct calling)
        self.generate_video = None
    
    async def initialize(self):
        """
        Initialize core capabilities
        
        This registers built-in capabilities and initializes services.
        Must be called before using any capabilities.
        
        Example:
            await reelforge.initialize()
        """
        if self._initialized:
            logger.warning("ReelForge already initialized")
            return
        
        logger.info("🚀 Initializing ReelForge...")
        
        # 1. Import all built-in capabilities (registers them with reelforge_mcp)
        self._import_builtin_capabilities()
        
        # 2. Register all built-in capabilities
        self.registry = CapabilityRegistry(reelforge_mcp)
        await self.registry.register_all()
        
        # 3. Create config manager
        self.config_manager = ConfigManager(self.registry, self.config)
        
        # 4. Initialize services
        self.llm = LLMService(self.config_manager)
        self.tts = TTSService(self.config_manager)
        self.image = ImageService(self.config_manager)
        
        # 5. Initialize content generation services
        from reelforge.services.narration_generator import NarrationGeneratorService
        from reelforge.services.image_prompt_generator import ImagePromptGeneratorService
        from reelforge.services.final_image_prompt import FinalImagePromptService
        
        self.narration_generator = NarrationGeneratorService(self)
        self.image_prompt_generator = ImagePromptGeneratorService(self)
        self.generate_final_image_prompt = FinalImagePromptService(self)
        
        # 6. Initialize frame processing services
        from reelforge.services.frame_composer import FrameComposerService
        from reelforge.services.storyboard_processor import StoryboardProcessorService
        
        self.frame_composer = FrameComposerService()
        self.storyboard_processor = StoryboardProcessorService(self)
        
        # 7. Initialize video generation service
        from reelforge.services.video_generator import VideoGeneratorService
        
        self.generate_video = VideoGeneratorService(self)
        
        self._initialized = True
        logger.info("✅ ReelForge initialized successfully\n")
    
    def _import_builtin_capabilities(self):
        """Import all built-in capability modules to register them"""
        # This triggers the @reelforge_mcp.tool decorators
        from reelforge.capabilities import llm  # noqa: F401
        from reelforge.capabilities import tts  # noqa: F401
        from reelforge.capabilities import image  # noqa: F401
    
    @property
    def project_name(self) -> str:
        """Get project name from config"""
        return self.config.get("project_name", "ReelForge")
    
    def __repr__(self) -> str:
        """String representation"""
        status = "initialized" if self._initialized else "not initialized"
        return f"<ReelForgeCore project={self.project_name!r} status={status}>"


# Global instance
reelforge = ReelForgeCore()

