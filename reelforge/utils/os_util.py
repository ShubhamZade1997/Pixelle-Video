"""
OS utilities for file and path management

Provides utilities for managing paths and files in ReelForge.
Inspired by Pixelle-MCP's os_util.py.
"""

import os
from pathlib import Path


def get_reelforge_root_path() -> str:
    """
    Get ReelForge root path - current working directory
    
    Returns:
        Current working directory as string
    """
    return str(Path.cwd())


def ensure_reelforge_root_path() -> str:
    """
    Ensure ReelForge root path exists and return the path
    
    Creates necessary directory structure if needed:
    - temp/: for temporary files (audio, video, etc.)
    - data/: for persistent data
    - output/: for final output files
    
    Returns:
        Root path as string
    """
    root_path = get_reelforge_root_path()
    root_path_obj = Path(root_path)
    
    # Create directory structure if needed
    temp_dir = root_path_obj / 'temp'
    data_dir = root_path_obj / 'data'
    output_dir = root_path_obj / 'output'
    
    temp_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return root_path


def get_root_path(*paths: str) -> str:
    """
    Get path relative to ReelForge root path
    
    Args:
        *paths: Path components to join
    
    Returns:
        Absolute path as string
    
    Example:
        get_root_path("temp", "audio.mp3")
        # Returns: "/path/to/project/temp/audio.mp3"
    """
    root_path = ensure_reelforge_root_path()
    if paths:
        return os.path.join(root_path, *paths)
    return root_path


def get_temp_path(*paths: str) -> str:
    """
    Get path relative to ReelForge temp folder
    
    Args:
        *paths: Path components to join
    
    Returns:
        Absolute path to temp directory or file
    
    Example:
        get_temp_path("audio.mp3")
        # Returns: "/path/to/project/temp/audio.mp3"
    """
    temp_path = get_root_path("temp")
    if paths:
        return os.path.join(temp_path, *paths)
    return temp_path


def get_data_path(*paths: str) -> str:
    """
    Get path relative to ReelForge data folder
    
    Args:
        *paths: Path components to join
    
    Returns:
        Absolute path to data directory or file
    
    Example:
        get_data_path("videos", "output.mp4")
        # Returns: "/path/to/project/data/videos/output.mp4"
    """
    data_path = get_root_path("data")
    if paths:
        return os.path.join(data_path, *paths)
    return data_path


def get_output_path(*paths: str) -> str:
    """
    Get path relative to ReelForge output folder
    
    Args:
        *paths: Path components to join
    
    Returns:
        Absolute path to output directory or file
    
    Example:
        get_output_path("video.mp4")
        # Returns: "/path/to/project/output/video.mp4"
    """
    output_path = get_root_path("output")
    if paths:
        return os.path.join(output_path, *paths)
    return output_path


def save_bytes_to_file(data: bytes, file_path: str) -> str:
    """
    Save bytes data to file
    
    Creates parent directories if they don't exist.
    
    Args:
        data: Binary data to save
        file_path: Target file path
    
    Returns:
        Absolute path of saved file
    
    Example:
        save_bytes_to_file(audio_data, get_temp_path("audio.mp3"))
    """
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Write binary data
    with open(file_path, "wb") as f:
        f.write(data)
    
    return os.path.abspath(file_path)


def ensure_dir(path: str) -> str:
    """
    Ensure directory exists, create if not
    
    Args:
        path: Directory path
    
    Returns:
        Absolute path of directory
    """
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)

