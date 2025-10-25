"""
Configuration system for ReelForge
"""

import os
from pathlib import Path
from typing import Any

import yaml
from loguru import logger


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    """
    Load configuration from YAML file
    
    User-friendly flat format (no internal conversion):
        project_name: ReelForge
        llm:
          api_key: xxx
          base_url: xxx
          model: xxx
        tts:
          default: edge
          edge: null
        image:
          default: comfykit
          comfykit:
            comfyui_url: http://xxx
    
    Args:
        config_path: Path to config file (default: config.yaml)
    
    Returns:
        Configuration dict (as-is from YAML)
    """
    # Check if config file exists
    config_file = Path(config_path)
    if not config_file.exists():
        logger.warning(f"Config file not found: {config_path}")
        logger.info("Using default configuration")
        return _get_default_config()
    
    # Load config
    logger.info(f"Loading config from: {config_path}")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Handle None (empty YAML file)
    if config is None:
        config = {}
    
    # Ensure project_name exists
    if "project_name" not in config:
        config["project_name"] = "ReelForge"
    
    return config


def _get_default_config() -> dict[str, Any]:
    """Get default configuration"""
    return {
        "project_name": "ReelForge",
        "llm": {
            "api_key": "",
            "base_url": "",
            "model": ""
        },
        "tts": {
            "default": "edge",
            "edge": None
        },
        "image": {
            "default": "comfykit",
            "comfykit": {
                "comfyui_url": "http://127.0.0.1:8188"
            }
        }
    }

