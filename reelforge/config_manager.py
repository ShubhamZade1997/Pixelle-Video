"""
Configuration manager for WebUI

Handles loading, saving, and validating configuration
from the web interface.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
from loguru import logger


class ConfigStatus:
    """Configuration validation status"""
    
    def __init__(self):
        self.is_complete: bool = True
        self.missing_fields: List[str] = []
        self.warnings: List[str] = []
    
    def add_missing(self, field: str):
        """Add a missing required field"""
        self.is_complete = False
        self.missing_fields.append(field)
    
    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)


class ConfigManager:
    """Manage configuration for WebUI"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config: Optional[Dict[str, Any]] = None
    
    def load_or_create_default(self) -> Dict[str, Any]:
        """
        Load config from file, or create default if not exists
        
        Returns:
            Configuration dictionary
        """
        if not self.config_path.exists():
            logger.warning("Config file not found, creating default")
            self.config = self._create_default_config()
            self.save()
        else:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        
        logger.info(f"Configuration loaded from {self.config_path}")
        return self.config
    
    def save(self):
        """Save config to file"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info(f"Configuration saved to {self.config_path}")
    
    def update_from_ui(self, ui_values: Dict[str, Any]):
        """
        Update config from UI form values
        
        Args:
            ui_values: Dictionary of form values from Streamlit
        """
        # Update LLM configuration
        if "llm_provider" in ui_values:
            provider = ui_values["llm_provider"]
            self.config["llm"]["default"] = provider
            
            # Ensure provider config exists
            if provider not in self.config["llm"]:
                self.config["llm"][provider] = {}
            
            # Update provider-specific config
            if f"llm_{provider}_api_key" in ui_values and ui_values[f"llm_{provider}_api_key"]:
                self.config["llm"][provider]["api_key"] = ui_values[f"llm_{provider}_api_key"]
            
            if f"llm_{provider}_base_url" in ui_values and ui_values[f"llm_{provider}_base_url"]:
                self.config["llm"][provider]["base_url"] = ui_values[f"llm_{provider}_base_url"]
            
            if f"llm_{provider}_model" in ui_values and ui_values[f"llm_{provider}_model"]:
                self.config["llm"][provider]["model"] = ui_values[f"llm_{provider}_model"]
        
        # Update TTS configuration
        if "tts_provider" in ui_values:
            self.config["tts"]["default"] = ui_values["tts_provider"]
        
        # Update Image configuration
        if "image_provider" in ui_values:
            self.config["image"]["default"] = ui_values["image_provider"]
        
        # Update ComfyKit configuration
        if "comfykit_mode" in ui_values:
            if "comfykit" not in self.config["image"]:
                self.config["image"]["comfykit"] = {}
            
            mode = ui_values["comfykit_mode"]
            if mode == "local":
                if "comfyui_url" in ui_values:
                    self.config["image"]["comfykit"]["comfyui_url"] = ui_values["comfyui_url"]
                # Remove cloud config
                self.config["image"]["comfykit"].pop("runninghub_api_key", None)
            else:  # cloud
                if "runninghub_api_key" in ui_values:
                    self.config["image"]["comfykit"]["runninghub_api_key"] = ui_values["runninghub_api_key"]
                # Remove local config
                self.config["image"]["comfykit"].pop("comfyui_url", None)
        
        self.save()
    
    def _is_valid_api_key(self, api_key: str) -> bool:
        """
        Check if an API key is valid (not empty or placeholder)
        
        Args:
            api_key: API key to validate
        
        Returns:
            True if valid, False if empty or placeholder
        """
        if not api_key:
            return False
        
        # Remove whitespace
        api_key = api_key.strip()
        
        if not api_key:
            return False
        
        # Common placeholders to reject
        invalid_patterns = [
            "your_",  # your_openai_api_key_here, your_dashscope_api_key_here
            "replace", # replace_me, replace_with_your_key
            "placeholder",
            "example_key",
        ]
        
        api_key_lower = api_key.lower()
        for pattern in invalid_patterns:
            if pattern in api_key_lower:
                return False
        
        # Accept any non-empty string (allow short keys for testing/custom services)
        return True
    
    def validate(self) -> ConfigStatus:
        """
        Validate configuration completeness (simple 3-field format)
        
        Returns:
            ConfigStatus with validation results
        """
        status = ConfigStatus()
        
        # Check LLM configuration (simple format)
        llm_config = self.config.get("llm", {})
        
        # Check API key
        api_key = llm_config.get("api_key", "")
        if not self._is_valid_api_key(api_key):
            status.add_missing("llm.api_key")
        
        # Check base_url
        base_url = llm_config.get("base_url", "")
        if not base_url or not base_url.strip():
            status.add_missing("llm.base_url")
        
        # Check model
        model = llm_config.get("model", "")
        if not model or not model.strip():
            status.add_missing("llm.model")
        
        return status
    
    def get_comfykit_mode(self) -> str:
        """
        Get current ComfyKit mode
        
        Returns:
            "local" or "cloud"
        """
        comfykit_config = self.config.get("image", {}).get("comfykit", {})
        
        if comfykit_config.get("runninghub_api_key"):
            return "cloud"
        else:
            return "local"
    
    def get_llm_config(self) -> Dict[str, str]:
        """
        Get LLM configuration (simple 3-field format)
        
        Returns:
            Dict with api_key, base_url, model
        """
        if self.config is None:
            return {"api_key": "", "base_url": "", "model": ""}
        
        llm_config = self.config.get("llm", {})
        return {
            "api_key": llm_config.get("api_key", ""),
            "base_url": llm_config.get("base_url", ""),
            "model": llm_config.get("model", ""),
        }
    
    def set_llm_config(self, api_key: str, base_url: str, model: str):
        """
        Set LLM configuration
        
        Args:
            api_key: API key
            base_url: Base URL
            model: Model name
        """
        self.config["llm"] = {
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
        }
    
    def is_llm_configured(self) -> bool:
        """
        Check if LLM is configured
        
        Returns:
            True if all three fields are non-empty
        """
        llm_config = self.get_llm_config()
        return bool(
            llm_config["api_key"] and llm_config["api_key"].strip() and
            llm_config["base_url"] and llm_config["base_url"].strip() and
            llm_config["model"] and llm_config["model"].strip()
        )
    
    def get_tts_providers(self) -> List[str]:
        """Get list of available TTS providers"""
        return ["edge"]
    
    def get_image_providers(self) -> List[str]:
        """Get list of available image providers"""
        return ["comfykit"]
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        return {
            "project_name": "ReelForge",
            "llm": {
                "api_key": "",  # User must fill in
                "base_url": "",  # User must fill in
                "model": "",  # User must fill in
            },
            "tts": {
                "default": "edge",  # Edge TTS is free
                "edge": {}
            },
            "image": {
                "default": "comfykit",
                "comfykit": {
                    "comfyui_url": "http://127.0.0.1:8188"
                }
            },
            "mcp_servers": []
        }

