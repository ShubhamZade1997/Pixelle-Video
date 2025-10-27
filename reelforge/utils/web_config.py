"""
Lightweight configuration utility for Web UI

Simple wrapper around config.yaml without heavy dependencies.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from loguru import logger


class WebConfig:
    """Lightweight configuration manager for Web UI"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """Load configuration from file"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using default")
            self.config = self._create_default_config()
            self.save()
        else:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"Configuration loaded from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self.config = self._create_default_config()
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def validate(self) -> bool:
        """
        Validate configuration completeness
        
        Returns:
            True if required fields are present
        """
        # Check LLM configuration (required)
        llm_config = self.config.get("llm", {})
        if not all([
            llm_config.get("api_key"),
            llm_config.get("base_url"),
            llm_config.get("model")
        ]):
            return False
        
        return True
    
    def get_llm_config(self) -> Dict[str, str]:
        """Get LLM configuration"""
        llm = self.config.get("llm", {})
        return {
            "api_key": llm.get("api_key", ""),
            "base_url": llm.get("base_url", ""),
            "model": llm.get("model", "")
        }
    
    def set_llm_config(self, api_key: str, base_url: str, model: str):
        """Set LLM configuration"""
        if "llm" not in self.config:
            self.config["llm"] = {}
        
        self.config["llm"]["api_key"] = api_key
        self.config["llm"]["base_url"] = base_url
        self.config["llm"]["model"] = model
    
    def get_image_config(self) -> Dict[str, Any]:
        """Get image generation configuration"""
        return self.config.get("image", {})
    
    def set_image_config(self, comfyui_url: Optional[str] = None, runninghub_api_key: Optional[str] = None):
        """Set image generation configuration"""
        if "image" not in self.config:
            self.config["image"] = {}
        
        if comfyui_url is not None:
            self.config["image"]["comfyui_url"] = comfyui_url
        
        if runninghub_api_key is not None:
            self.config["image"]["runninghub_api_key"] = runninghub_api_key
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        return {
            "project_name": "ReelForge",
            "llm": {
                "api_key": "",
                "base_url": "",
                "model": ""
            },
            "tts": {
                "default_workflow": "edge"
            },
            "image": {
                "comfyui_url": "http://127.0.0.1:8188",
                "runninghub_api_key": "",
                "prompt_prefix": "Pure white background, minimalist illustration, matchstick figure style, black and white line drawing, simple clean lines"
            }
        }

