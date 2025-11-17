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
Session state management for web UI
"""

import streamlit as st
from loguru import logger

from web.i18n import get_language, set_language
from web.utils.async_helpers import run_async


def init_session_state():
    """Initialize session state variables"""
    if "language" not in st.session_state:
        # Use auto-detected system language
        st.session_state.language = get_language()


def init_i18n():
    """Initialize internationalization"""
    # Locales are already loaded and system language detected on import
    # Get language from session state or use auto-detected system language
    if "language" not in st.session_state:
        st.session_state.language = get_language()  # Use auto-detected language
    
    # Set current language
    set_language(st.session_state.language)


def get_pixelle_video():
    """Get initialized Pixelle-Video instance (no caching - always fresh)"""
    from pixelle_video.service import PixelleVideoCore
    
    logger.info("Initializing Pixelle-Video...")
    pixelle_video = PixelleVideoCore()
    run_async(pixelle_video.initialize())
    logger.info("Pixelle-Video initialized")
    
    return pixelle_video

