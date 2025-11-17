# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Pixelle-Video Web UI - Main Entry Point

A modular web interface for generating short videos from content.
"""

import sys
from pathlib import Path

# Add project root to sys.path for module imports
# This ensures imports work correctly in both development and packaged environments
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st

# Import state management
from web.state.session import init_session_state, init_i18n, get_pixelle_video

# Import components
from web.components.header import render_header
from web.components.settings import render_advanced_settings
from web.components.content_input import render_content_input, render_bgm_section, render_version_info
from web.components.style_config import render_style_config
from web.components.output_preview import render_output_preview

# Setup page config (must be first Streamlit command)
st.set_page_config(
    page_title="Pixelle-Video - AI Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main():
    """Main UI entry point"""
    # Initialize session state and i18n
    init_session_state()
    init_i18n()
    
    # Render header (title + language selector)
    render_header()
    
    # Initialize Pixelle-Video
    pixelle_video = get_pixelle_video()
    
    # Render system configuration (LLM + ComfyUI)
    render_advanced_settings()
    
    # Three-column layout
    left_col, middle_col, right_col = st.columns([1, 1, 1])
    
    # ========================================================================
    # Left Column: Content Input & BGM
    # ========================================================================
    with left_col:
        # Content input (mode, text, title, n_scenes)
        content_params = render_content_input()
        
        # BGM selection (bgm_path, bgm_volume)
        bgm_params = render_bgm_section()
        
        # Version info & GitHub link
        render_version_info()
    
    # ========================================================================
    # Middle Column: Style Configuration
    # ========================================================================
    with middle_col:
        # Style configuration (TTS, template, workflow, etc.)
        style_params = render_style_config(pixelle_video)
    
    # ========================================================================
    # Right Column: Output Preview
    # ========================================================================
    with right_col:
        # Combine all parameters
        video_params = {
            **content_params,
            **bgm_params,
            **style_params
        }
        
        # Render output preview (generate button, progress, video preview)
        render_output_preview(pixelle_video, video_params)


if __name__ == "__main__":
    main()
