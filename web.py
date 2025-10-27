"""
ReelForge Web UI

A simple web interface for generating short videos from content.
"""

import asyncio
import base64
import os
from pathlib import Path

import streamlit as st
from loguru import logger

# Import i18n and config manager
from reelforge.i18n import load_locales, set_language, tr, get_available_languages
from reelforge.config_manager import ConfigManager
from reelforge.models.progress import ProgressEvent

# Setup page config (must be first)
st.set_page_config(
    page_title="ReelForge - AI Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================================
# Async Helper
# ============================================================================

def run_async(coro):
    """Run async coroutine in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def safe_rerun():
    """Safe rerun that works with both old and new Streamlit versions"""
    if hasattr(st, 'rerun'):
        st.rerun()
    else:
        st.experimental_rerun()


# ============================================================================
# Configuration & i18n Initialization
# ============================================================================

def get_config_manager():
    """Get ConfigManager instance (no caching - always fresh)"""
    manager = ConfigManager()
    manager.load_or_create_default()
    return manager


def init_i18n():
    """Initialize internationalization"""
    # Load locales if not already loaded
    load_locales()
    
    # Get language from session state or default to Chinese
    if "language" not in st.session_state:
        st.session_state.language = "zh_CN"
    
    # Set current language
    set_language(st.session_state.language)


# ============================================================================
# Preview Cache Functions
# ============================================================================

def generate_style_preview_cached(prompt_prefix: str):
    """
    Generate and cache visual style preview
    
    Args:
        prompt_prefix: Prompt prefix to test
    
    Returns:
        Generated image path
    """
    from reelforge.utils.prompt_helper import build_image_prompt
    
    reelforge = get_reelforge()
    
    # Build final prompt with prefix
    test_prompt = "A peaceful mountain landscape"
    final_prompt = build_image_prompt(test_prompt, prompt_prefix)
    
    # Generate preview image (small size for speed)
    preview_image_path = run_async(reelforge.image(
        prompt=final_prompt,
        width=512,
        height=512
    ))
    
    return preview_image_path


# ============================================================================
# Initialize ReelForge
# ============================================================================

def get_reelforge():
    """Get initialized ReelForge instance (no caching - always fresh)"""
    from reelforge.service import ReelForgeCore
    
    logger.info("Initializing ReelForge...")
    reelforge = ReelForgeCore()
    run_async(reelforge.initialize())
    logger.info("ReelForge initialized")
    
    return reelforge


# ============================================================================
# Session State
# ============================================================================

def init_session_state():
    """Initialize session state variables"""
    if "language" not in st.session_state:
        st.session_state.language = "zh_CN"


# ============================================================================
# System Configuration (Required)
# ============================================================================

def render_advanced_settings(config_manager: ConfigManager):
    """Render system configuration (required) with 2-column layout"""
    # Check if system is configured
    is_configured = config_manager.validate()
    
    # Expand if not configured, collapse if configured
    with st.expander(tr("settings.title"), expanded=not is_configured):
        # 2-column layout: LLM | Image
        llm_col, image_col = st.columns(2)
        
        # ====================================================================
        # Column 1: LLM Settings (Simplified 3-field format)
        # ====================================================================
        with llm_col:
            with st.container(border=True):
                st.markdown(f"**{tr('settings.llm.title')}**")
                
                # Quick preset selection
                from reelforge.llm_presets import get_preset_names, get_preset, find_preset_by_base_url_and_model
                
                # Custom at the end
                preset_names = get_preset_names() + ["Custom"]
                
                # Get current config
                current_llm = config_manager.get_llm_config()
                
                # Auto-detect which preset matches current config
                current_preset = find_preset_by_base_url_and_model(
                    current_llm["base_url"], 
                    current_llm["model"]
                )
                
                # Determine default index based on current config
                if current_preset:
                    # Current config matches a preset
                    default_index = preset_names.index(current_preset)
                else:
                    # Current config doesn't match any preset -> Custom
                    default_index = len(preset_names) - 1
                
                selected_preset = st.selectbox(
                    tr("settings.llm.quick_select"),
                    options=preset_names,
                    index=default_index,
                    help=tr("settings.llm.quick_select_help"),
                    key="llm_preset_select"
                )
                
                # Auto-fill based on selected preset
                if selected_preset != "Custom":
                    # Preset selected
                    preset_config = get_preset(selected_preset)
                    
                    # If user switched to a different preset (not current one), clear API key
                    # If it's the same as current config, keep API key
                    if selected_preset == current_preset:
                        # Same preset as saved config: keep API key
                        default_api_key = current_llm["api_key"]
                    else:
                        # Different preset: clear API key
                        default_api_key = ""
                    
                    default_base_url = preset_config.get("base_url", "")
                    default_model = preset_config.get("model", "")
                    
                    # Show API key URL if available
                    if preset_config.get("api_key_url"):
                        st.markdown(f"🔑 [{tr('settings.llm.get_api_key')}]({preset_config['api_key_url']})")
                else:
                    # Custom: show current saved config (if any)
                    default_api_key = current_llm["api_key"]
                    default_base_url = current_llm["base_url"]
                    default_model = current_llm["model"]
                
                st.markdown("---")
                
                # API Key (use unique key to force refresh when switching preset)
                llm_api_key = st.text_input(
                    f"{tr('settings.llm.api_key')} *",
                    value=default_api_key,
                    type="password",
                    help=tr("settings.llm.api_key_help"),
                    key=f"llm_api_key_input_{selected_preset}"
                )
                
                # Base URL (use unique key based on preset to force refresh)
                llm_base_url = st.text_input(
                    f"{tr('settings.llm.base_url')} *",
                    value=default_base_url,
                    help=tr("settings.llm.base_url_help"),
                    key=f"llm_base_url_input_{selected_preset}"
                )
                
                # Model (use unique key based on preset to force refresh)
                llm_model = st.text_input(
                    f"{tr('settings.llm.model')} *",
                    value=default_model,
                    help=tr("settings.llm.model_help"),
                    key=f"llm_model_input_{selected_preset}"
                )
        
        # ====================================================================
        # Column 2: Image Settings
        # ====================================================================
        with image_col:
            with st.container(border=True):
                st.markdown(f"**{tr('settings.image.title')}**")
                
                # Get current configuration (flat structure)
                image_config = config_manager.config.get("image", {})
                
                # Local/Self-hosted ComfyUI configuration
                st.markdown(f"**{tr('settings.image.local_title')}**")
                comfyui_url = st.text_input(
                    tr("settings.image.comfyui_url"),
                    value=image_config.get("comfyui_url", "http://127.0.0.1:8188"),
                    help=tr("settings.image.comfyui_url_help"),
                    key="comfyui_url_input"
                )
                
                # Test connection button
                if st.button(tr("btn.test_connection"), key="test_comfyui", use_container_width=True):
                    try:
                        import requests
                        response = requests.get(f"{comfyui_url}/system_stats", timeout=5)
                        if response.status_code == 200:
                            st.success(tr("status.connection_success"))
                        else:
                            st.error(tr("status.connection_failed"))
                    except Exception as e:
                        st.error(f"{tr('status.connection_failed')}: {str(e)}")
                
                st.markdown("---")
                
                # RunningHub cloud configuration
                st.markdown(f"**{tr('settings.image.cloud_title')}**")
                runninghub_api_key = st.text_input(
                    tr("settings.image.runninghub_api_key"),
                    value=image_config.get("runninghub_api_key", ""),
                    type="password",
                    help=tr("settings.image.runninghub_api_key_help"),
                    key="runninghub_api_key_input"
                )
        
        # ====================================================================
        # Action Buttons (full width at bottom)
        # ====================================================================
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(tr("btn.save_config"), use_container_width=True, key="save_config_btn"):
                try:
                    # Save LLM configuration (simple 3-field format)
                    if llm_api_key and llm_base_url and llm_model:
                        config_manager.set_llm_config(llm_api_key, llm_base_url, llm_model)
                    
                    # Save Image configuration (flat structure)
                    config_manager.config["image"]["default"] = "default"
                    if comfyui_url:
                        config_manager.config["image"]["comfyui_url"] = comfyui_url
                    if runninghub_api_key:
                        config_manager.config["image"]["runninghub_api_key"] = runninghub_api_key
                    
                    # Save to file
                    config_manager.save()
                    
                    st.success(tr("status.config_saved"))
                    safe_rerun()
                except Exception as e:
                    st.error(f"{tr('status.save_failed')}: {str(e)}")
        
        with col2:
            if st.button(tr("btn.reset_config"), use_container_width=True, key="reset_config_btn"):
                config_manager.config = config_manager._create_default_config()
                config_manager.save()
                st.success(tr("status.config_reset"))
                safe_rerun()


# ============================================================================
# Language Selector
# ============================================================================

def render_language_selector():
    """Render language selector at the top"""
    languages = get_available_languages()
    lang_options = [f"{code} - {name}" for code, name in languages.items()]
    
    current_lang = st.session_state.get("language", "zh_CN")
    current_index = list(languages.keys()).index(current_lang) if current_lang in languages else 0
    
    selected = st.selectbox(
        tr("language.select"),
        options=lang_options,
        index=current_index,
        label_visibility="collapsed"
    )
    
    selected_code = selected.split(" - ")[0]
    if selected_code != current_lang:
        st.session_state.language = selected_code
        set_language(selected_code)
        safe_rerun()


# ============================================================================
# Main UI
# ============================================================================

def main():
    # Initialize
    init_session_state()
    init_i18n()
    
    config_manager = get_config_manager()
    
    # Top bar: Title + Language selector
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"<h3>{tr('app.title')}</h3>", unsafe_allow_html=True)
    with col2:
        render_language_selector()
    
    # Initialize ReelForge
    reelforge = get_reelforge()
    
    # ========================================================================
    # System Configuration (Required)
    # Auto-expands if not configured, collapses if configured
    # ========================================================================
    render_advanced_settings(config_manager)
    
    # Three-column layout
    left_col, middle_col, right_col = st.columns([1, 1, 1])
    
    # ========================================================================
    # Left Column: Content Input
    # ========================================================================
    with left_col:
        with st.container(border=True):
            st.markdown(f"**{tr('section.content_input')}**")
            
            # Processing mode selection
            mode = st.radio(
                "Processing Mode",
                ["generate", "fixed"],
                horizontal=True,
                format_func=lambda x: tr(f"mode.{x}"),
                label_visibility="collapsed",
                help=tr("mode.help")
            )
            
            # Text input (unified for both modes)
            text_placeholder = tr("input.topic_placeholder") if mode == "generate" else tr("input.content_placeholder")
            text_height = 100 if mode == "generate" else 200
            text_help = tr("input.text_help_generate") if mode == "generate" else tr("input.text_help_fixed")
            
            text = st.text_area(
                tr("input.text"),
                placeholder=text_placeholder,
                height=text_height,
                help=text_help
            )
            
            # Title input (optional for both modes)
            title = st.text_input(
                tr("input.title"),
                placeholder=tr("input.title_placeholder"),
                help=tr("input.title_help")
            )
        
        # ====================================================================
        # Video Settings (moved from right column)
        # ====================================================================
        with st.container(border=True):
            st.markdown(f"**{tr('video.title')}**")
            
            # Number of scenes (only show in generate mode)
            if mode == "generate":
                n_scenes = st.slider(
                    tr("video.frames"),
                    min_value=3,
                    max_value=30,
                    value=5,
                    help=tr("video.frames_help"),
                    label_visibility="collapsed"
                )
                st.caption(tr("video.frames_label", n=n_scenes))
                
                st.markdown("---")
            else:
                # Fixed mode: n_scenes is ignored, set default value
                n_scenes = 5
                st.info(tr("video.frames_fixed_mode_hint"))
            
            st.markdown("---")
            
            # Voice selection (moved from middle column)
            st.markdown(f"**{tr('voice.title')}**")
            voice_id = st.selectbox(
                "Voice",
                [
                    "zh-CN-YunjianNeural",  # 男声-专业
                    "zh-CN-YunxiNeural",    # 男声-年轻
                    "zh-CN-XiaoxiaoNeural", # 女声-温柔
                    "zh-CN-XiaoyiNeural",   # 女声-活力
                ],
                format_func=lambda x: {
                    "zh-CN-YunjianNeural": tr("voice.male_professional"),
                    "zh-CN-YunxiNeural": tr("voice.male_young"),
                    "zh-CN-XiaoxiaoNeural": tr("voice.female_gentle"),
                    "zh-CN-XiaoyiNeural": tr("voice.female_energetic"),
                }[x],
                label_visibility="collapsed"
            )
            
            # Voice preview button
            if st.button(tr("voice.preview"), key="preview_voice", use_container_width=True):
                with st.spinner(tr("voice.previewing")):
                    try:
                        # Generate preview audio
                        preview_text = "大家好，这是一段测试语音。"
                        
                        # Use TTS service to generate audio (auto temp path)
                        audio_path = run_async(reelforge.tts(
                            text=preview_text,
                            voice=voice_id
                        ))
                        
                        # Play the audio
                        if os.path.exists(audio_path):
                            st.audio(audio_path, format="audio/mp3")
                        else:
                            st.error("Failed to generate preview audio")
                    except Exception as e:
                        st.error(tr("voice.preview_failed", error=str(e)))
                        logger.exception(e)
    
    # ========================================================================
    # Middle Column: Custom Settings (BGM & Visual Style & Template)
    # ========================================================================
    with middle_col:
        with st.container(border=True):
            st.markdown(f"**{tr('section.style_settings')}**")
            
            # Background music (moved from left column)
            st.markdown(f"**{tr('bgm.title')}**")
            st.caption(tr("bgm.custom_help"))
            
            # Dynamically scan bgm folder for music files (support common audio formats)
            bgm_folder = Path("bgm")
            bgm_files = []
            if bgm_folder.exists():
                audio_extensions = ["*.mp3", "*.wav", "*.flac", "*.m4a", "*.aac", "*.ogg"]
                for ext in audio_extensions:
                    bgm_files.extend([f.name for f in bgm_folder.glob(ext)])
                bgm_files.sort()
            
            # Add special "None" option
            bgm_options = [tr("bgm.none")] + bgm_files
            
            # Default to "default.mp3" if exists, otherwise first option
            default_index = 0
            if "default.mp3" in bgm_files:
                default_index = bgm_options.index("default.mp3")
            
            bgm_choice = st.selectbox(
                "BGM",
                bgm_options,
                index=default_index,
                label_visibility="collapsed"
            )
            
            # BGM preview button (only if BGM is not "None")
            if bgm_choice != tr("bgm.none"):
                if st.button(tr("bgm.preview"), key="preview_bgm", use_container_width=True):
                    bgm_file_path = f"bgm/{bgm_choice}"
                    if os.path.exists(bgm_file_path):
                        st.audio(bgm_file_path)
                    else:
                        st.error(tr("bgm.preview_failed", file=bgm_choice))
            
            # Use full filename for bgm_path (including extension)
            bgm_path = None if bgm_choice == tr("bgm.none") else bgm_choice
            
            
            # Visual style (Workflow + Prompt Prefix)
            st.markdown(f"**{tr('style.title')}**")
            
            # 1. ComfyUI Workflow selection
            st.caption(tr("style.workflow"))
            st.caption(tr("style.workflow_help"))
            
            # Dynamically scan workflows folder for image_*.json files
            workflows_folder = Path("workflows")
            workflow_files = []
            if workflows_folder.exists():
                workflow_files = sorted([f.name for f in workflows_folder.glob("image_*.json")])
            
            # Default to "image_default.json" if exists, otherwise first option
            default_workflow_index = 0
            if "image_default.json" in workflow_files:
                default_workflow_index = workflow_files.index("image_default.json")
            
            workflow_filename = st.selectbox(
                "Workflow",
                workflow_files if workflow_files else ["image_default.json"],
                index=default_workflow_index,
                label_visibility="collapsed",
                key="image_preset_select"
            )
            
            # Extract preset name from filename: "image_default.json" -> "default"
            image_preset = workflow_filename.replace("image_", "").replace(".json", "") if workflow_filename else None
            
            
            # 2. Prompt prefix input
            st.caption(tr("style.prompt_prefix"))
            
            # Get current prompt_prefix from config
            image_config = config_manager.config.get("image", {})
            current_prefix = image_config.get("prompt_prefix", "")
            
            # Prompt prefix input (temporary, not saved to config)
            prompt_prefix = st.text_area(
                "Prompt Prefix",
                value=current_prefix,
                placeholder=tr("style.prompt_prefix_placeholder"),
                height=80,
                label_visibility="collapsed",
                help=tr("style.prompt_prefix_help")
            )
            
            # Visual style preview button
            if st.button(tr("style.preview"), key="preview_style", use_container_width=True):
                with st.spinner(tr("style.previewing")):
                    try:
                        # Generate preview using cached function
                        preview_image_path = generate_style_preview_cached(prompt_prefix)
                        
                        # Display preview (support both URL and local path)
                        if preview_image_path:
                            # Read and encode image
                            if preview_image_path.startswith('http'):
                                # URL - use directly
                                img_html = f'<div class="preview-image"><img src="{preview_image_path}" alt="Style Preview"/></div>'
                            else:
                                # Local file - encode as base64
                                with open(preview_image_path, 'rb') as f:
                                    img_data = base64.b64encode(f.read()).decode()
                                img_html = f'<div class="preview-image"><img src="data:image/png;base64,{img_data}" alt="Style Preview"/></div>'
                            
                            st.markdown(img_html, unsafe_allow_html=True)
                            st.caption("Preview with test prompt: 'A peaceful mountain landscape'")
                            
                            # Show the final prompt used
                            from reelforge.utils.prompt_helper import build_image_prompt
                            test_prompt = "A peaceful mountain landscape"
                            final_prompt = build_image_prompt(test_prompt, prompt_prefix)
                            st.info(f"Final prompt used: {final_prompt}")
                        else:
                            st.error("Failed to generate preview image")
                    except Exception as e:
                        st.error(tr("style.preview_failed", error=str(e)))
                        logger.exception(e)
            
            
            # Frame template (moved from right column)
            st.markdown(f"**{tr('template.title')}**")
            st.caption(tr("template.custom_help"))
            
            # Dynamically scan templates folder for HTML files
            templates_folder = Path("templates")
            template_files = []
            if templates_folder.exists():
                template_files = sorted([f.name for f in templates_folder.glob("*.html")])
            
            # Default to default.html if exists, otherwise first option
            default_template_index = 0
            if "default.html" in template_files:
                default_template_index = template_files.index("default.html")
            
            frame_template = st.selectbox(
                "Template",
                template_files if template_files else ["default.html"],
                index=default_template_index,
                label_visibility="collapsed"
            )
    
    # ========================================================================
    # Right Column: Generate Button + Progress + Video Preview
    # ========================================================================
    with right_col:
        with st.container(border=True):
            st.markdown(f"**{tr('section.video_generation')}**")
            
            # Check if system is configured
            if not config_manager.validate():
                st.warning(tr("settings.not_configured"))
            
            # Generate Button
            if st.button(tr("btn.generate"), type="primary", use_container_width=True):
                # Validate system configuration
                if not config_manager.validate():
                    st.error(tr("settings.not_configured"))
                    st.stop()
                
                # Validate input
                if not text:
                    st.error(tr("error.input_required"))
                    st.stop()
                
                # Show progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Progress callback to update UI
                    def update_progress(event: ProgressEvent):
                        """Update progress bar and status text from ProgressEvent"""
                        # Translate event to user-facing message
                        if event.event_type == "frame_step":
                            # Frame step: "分镜 3/5 - 步骤 2/4: 生成插图"
                            action_key = f"progress.step_{event.action}"
                            action_text = tr(action_key)
                            message = tr(
                                "progress.frame_step",
                                current=event.frame_current,
                                total=event.frame_total,
                                step=event.step,
                                action=action_text
                            )
                        elif event.event_type == "processing_frame":
                            # Processing frame: "分镜 3/5"
                            message = tr(
                                "progress.frame",
                                current=event.frame_current,
                                total=event.frame_total
                            )
                        else:
                            # Simple events: use i18n key directly
                            message = tr(f"progress.{event.event_type}")
                        
                        # Append extra_info if available (e.g., batch progress)
                        if event.extra_info:
                            message = f"{message} - {event.extra_info}"
                        
                        status_text.text(message)
                        progress_bar.progress(min(int(event.progress * 100), 99))  # Cap at 99% until complete
                    
                    # Generate video (directly pass parameters)
                    result = run_async(reelforge.generate_video(
                        text=text,
                        mode=mode,
                        title=title if title else None,
                        n_scenes=n_scenes,
                        voice_id=voice_id,
                        image_preset=image_preset,  # Pass image_preset
                        frame_template=frame_template,
                        prompt_prefix=prompt_prefix,  # Pass prompt_prefix
                        bgm_path=bgm_path,
                        progress_callback=update_progress,
                    ))
                    
                    progress_bar.progress(100)
                    status_text.text(tr("status.success"))
                    
                    # Display success message
                    st.success(tr("status.video_generated", path=result.video_path))
                    
                    st.markdown("---")
                    
                    # Video information (compact display)
                    file_size_mb = result.file_size / (1024 * 1024)
                    info_text = (
                        f"⏱️ {result.duration:.1f}s   "
                        f"📦 {file_size_mb:.2f}MB   "
                        f"🎬 {len(result.storyboard.frames)}{tr('info.scenes_unit')}   "
                        f"📐 {result.storyboard.config.video_width}x{result.storyboard.config.video_height}"
                    )
                    st.caption(info_text)
                    
                    st.markdown("---")
                    
                    # Video preview
                    if os.path.exists(result.video_path):
                        st.video(result.video_path)
                    else:
                        st.error(tr("status.video_not_found", path=result.video_path))
                    
                except Exception as e:
                    status_text.text("")
                    progress_bar.empty()
                    st.error(tr("status.error", error=str(e)))
                    logger.exception(e)
                    st.stop()


if __name__ == "__main__":
    main()
