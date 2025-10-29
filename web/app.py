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
from web.i18n import load_locales, set_language, tr, get_available_languages
from reelforge.config import config_manager
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
    return asyncio.run(coro)


def safe_rerun():
    """Safe rerun that works with both old and new Streamlit versions"""
    if hasattr(st, 'rerun'):
        st.rerun()
    else:
        st.experimental_rerun()


# ============================================================================
# Configuration & i18n Initialization
# ============================================================================

# Config manager is already a global singleton, use it directly


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

def render_advanced_settings():
    """Render system configuration (required) with 2-column layout"""
    # Check if system is configured
    is_configured = config_manager.validate()
    
    # Expand if not configured, collapse if configured
    with st.expander(tr("settings.title"), expanded=not is_configured):
        # 2-column layout: LLM | ComfyUI
        llm_col, comfyui_col = st.columns(2)
        
        # ====================================================================
        # Column 1: LLM Settings
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
        # Column 2: ComfyUI Settings
        # ====================================================================
        with comfyui_col:
            with st.container(border=True):
                st.markdown(f"**{tr('settings.comfyui.title')}**")
                
                # Get current configuration
                comfyui_config = config_manager.get_comfyui_config()
                
                # Local/Self-hosted ComfyUI configuration
                st.markdown(f"**{tr('settings.comfyui.local_title')}**")
                comfyui_url = st.text_input(
                    tr("settings.comfyui.comfyui_url"),
                    value=comfyui_config.get("comfyui_url", "http://127.0.0.1:8188"),
                    help=tr("settings.comfyui.comfyui_url_help"),
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
                st.markdown(f"**{tr('settings.comfyui.cloud_title')}**")
                runninghub_api_key = st.text_input(
                    tr("settings.comfyui.runninghub_api_key"),
                    value=comfyui_config.get("runninghub_api_key", ""),
                    type="password",
                    help=tr("settings.comfyui.runninghub_api_key_help"),
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
                    # Save LLM configuration
                    if llm_api_key and llm_base_url and llm_model:
                        config_manager.set_llm_config(llm_api_key, llm_base_url, llm_model)
                    
                    # Save ComfyUI configuration
                    config_manager.set_comfyui_config(
                        comfyui_url=comfyui_url if comfyui_url else None,
                        runninghub_api_key=runninghub_api_key if runninghub_api_key else None
                    )
                    
                    # Save to file
                    config_manager.save()
                    
                    st.success(tr("status.config_saved"))
                    safe_rerun()
                except Exception as e:
                    st.error(f"{tr('status.save_failed')}: {str(e)}")
        
        with col2:
            if st.button(tr("btn.reset_config"), use_container_width=True, key="reset_config_btn"):
                # Reset to default
                from reelforge.config.schema import ReelForgeConfig
                config_manager.config = ReelForgeConfig()
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
    render_advanced_settings()
    
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
                label_visibility="collapsed"
            )
            
            # Text input (unified for both modes)
            text_placeholder = tr("input.topic_placeholder") if mode == "generate" else tr("input.content_placeholder")
            text_height = 120 if mode == "generate" else 200
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
            else:
                # Fixed mode: n_scenes is ignored, set default value
                n_scenes = 5
                st.info(tr("video.frames_fixed_mode_hint"))
        
        # ====================================================================
        # Audio Settings (BGM + TTS)
        # ====================================================================
        with st.container(border=True):
            st.markdown(f"**{tr('section.audio_settings')}**")
            
            # Background music (moved to top)
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
            
            
            # TTS Workflow selection
            st.markdown(f"**{tr('tts.title')}**")
            st.caption(tr("tts.workflow_help"))
            
            # Get available TTS workflows
            tts_workflows = reelforge.tts.list_workflows()
            
            # Build options for selectbox
            tts_workflow_options = [wf["display_name"] for wf in tts_workflows]
            tts_workflow_keys = [wf["key"] for wf in tts_workflows]
            
            # Default to saved workflow if exists
            default_tts_index = 0
            comfyui_config = config_manager.get_comfyui_config()
            saved_tts_workflow = comfyui_config["tts"]["default_workflow"]
            if saved_tts_workflow and saved_tts_workflow in tts_workflow_keys:
                default_tts_index = tts_workflow_keys.index(saved_tts_workflow)
            
            tts_workflow_display = st.selectbox(
                "TTS Workflow",
                tts_workflow_options if tts_workflow_options else ["No TTS workflows found"],
                index=default_tts_index,
                label_visibility="collapsed",
                key="tts_workflow_select"
            )
            
            # Get the actual workflow key
            if tts_workflow_options:
                tts_selected_index = tts_workflow_options.index(tts_workflow_display)
                tts_workflow_key = tts_workflow_keys[tts_selected_index]
            else:
                tts_workflow_key = "selfhost/tts_edge.json"  # fallback
            
            # TTS preview expander (simplified, uses default voice and speed)
            with st.expander(tr("tts.preview_title"), expanded=False):
                # Preview text input
                preview_text = st.text_input(
                    tr("tts.preview_text"),
                    value="大家好，这是一段测试语音。",
                    placeholder=tr("tts.preview_text_placeholder"),
                    key="tts_preview_text"
                )
                
                # Preview button
                if st.button(tr("tts.preview_button"), key="preview_tts", use_container_width=True):
                    with st.spinner(tr("tts.previewing")):
                        try:
                            # Generate preview audio using selected workflow (use default voice and speed)
                            audio_path = run_async(reelforge.tts(
                                text=preview_text,
                                workflow=tts_workflow_key
                            ))
                            
                            # Play the audio
                            if audio_path:
                                st.success(tr("tts.preview_success"))
                                if os.path.exists(audio_path):
                                    st.audio(audio_path, format="audio/mp3")
                                elif audio_path.startswith('http'):
                                    st.audio(audio_path)
                                else:
                                    st.error("Failed to generate preview audio")
                                
                                # Show file path
                                st.caption(f"📁 {audio_path}")
                            else:
                                st.error("Failed to generate preview audio")
                        except Exception as e:
                            st.error(tr("tts.preview_failed", error=str(e)))
                            logger.exception(e)
    
    # ========================================================================
    # Middle Column: Visual Settings (Style & Template)
    # ========================================================================
    with middle_col:
        with st.container(border=True):
            st.markdown(f"**{tr('section.visual_settings')}**")
            
            # Visual style (Workflow + Prompt Prefix)
            st.markdown(f"**{tr('style.title')}**")
            
            # 1. ComfyUI Workflow selection
            st.caption(tr("style.workflow"))
            st.caption(tr("style.workflow_help"))
            
            # Get available workflows from reelforge (with source info)
            workflows = reelforge.image.list_workflows()
            
            # Build options for selectbox
            # Display: "image_flux.json - Runninghub"
            # Value: "runninghub/image_flux.json"
            workflow_options = [wf["display_name"] for wf in workflows]
            workflow_keys = [wf["key"] for wf in workflows]
            
            # Default to first option (should be runninghub by sorting)
            default_workflow_index = 0
            
            # If user has a saved preference in config, try to match it
            comfyui_config = config_manager.get_comfyui_config()
            saved_workflow = comfyui_config["image"]["default_workflow"]
            if saved_workflow and saved_workflow in workflow_keys:
                default_workflow_index = workflow_keys.index(saved_workflow)
            
            workflow_display = st.selectbox(
                "Workflow",
                workflow_options if workflow_options else ["No workflows found"],
                index=default_workflow_index,
                label_visibility="collapsed",
                key="image_workflow_select"
            )
            
            # Get the actual workflow key (e.g., "runninghub/image_flux.json")
            if workflow_options:
                workflow_selected_index = workflow_options.index(workflow_display)
                workflow_key = workflow_keys[workflow_selected_index]
            else:
                workflow_key = "runninghub/image_flux.json"  # fallback
            
            
            # 2. Prompt prefix input
            st.caption(tr("style.prompt_prefix"))
            
            # Get current prompt_prefix from config
            current_prefix = comfyui_config["image"]["prompt_prefix"]
            
            # Prompt prefix input (temporary, not saved to config)
            prompt_prefix = st.text_area(
                "Prompt Prefix",
                value=current_prefix,
                placeholder=tr("style.prompt_prefix_placeholder"),
                height=80,
                label_visibility="collapsed",
                help=tr("style.prompt_prefix_help")
            )
            
            # Style preview expander (similar to template preview)
            with st.expander(tr("style.preview_title"), expanded=False):
                # Test prompt input
                test_prompt = st.text_input(
                    tr("style.test_prompt"),
                    value="a dog",
                    help=tr("style.test_prompt_help"),
                    key="style_test_prompt"
                )
                
                # Preview button
                if st.button(tr("style.preview"), key="preview_style", use_container_width=True):
                    with st.spinner(tr("style.previewing")):
                        try:
                            from reelforge.utils.prompt_helper import build_image_prompt
                            
                            # Build final prompt with prefix
                            final_prompt = build_image_prompt(test_prompt, prompt_prefix)
                            
                            # Generate preview image (small size for speed)
                            preview_image_path = run_async(reelforge.image(
                                prompt=final_prompt,
                                workflow=workflow_key,
                                width=512,
                                height=512
                            ))
                            
                            # Display preview (support both URL and local path)
                            if preview_image_path:
                                st.success(tr("style.preview_success"))
                                
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
                                
                                # Show the final prompt used
                                st.info(f"**{tr('style.final_prompt_label')}**\n{final_prompt}")
                                
                                # Show file path
                                st.caption(f"📁 {preview_image_path}")
                            else:
                                st.error(tr("style.preview_failed_general"))
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
            
            # Template preview expander
            with st.expander(tr("template.preview_title"), expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    preview_title = st.text_input(
                        tr("template.preview_param_title"), 
                        value=tr("template.preview_default_title"),
                        key="preview_title"
                    )
                    preview_image = st.text_input(
                        tr("template.preview_param_image"), 
                        value="resources/example.png",
                        help=tr("template.preview_image_help"),
                        key="preview_image"
                    )
                
                with col2:
                    preview_text = st.text_area(
                        tr("template.preview_param_text"), 
                        value=tr("template.preview_default_text"),
                        height=100,
                        key="preview_text"
                    )
                
                # Size settings in a compact row
                col3, col4 = st.columns(2)
                with col3:
                    preview_width = st.number_input(
                        tr("template.preview_param_width"), 
                        value=1080, 
                        min_value=100, 
                        max_value=4096,
                        step=10,
                        key="preview_width"
                    )
                with col4:
                    preview_height = st.number_input(
                        tr("template.preview_param_height"), 
                        value=1920, 
                        min_value=100, 
                        max_value=4096,
                        step=10,
                        key="preview_height"
                    )
                
                # Preview button
                if st.button(tr("template.preview_button"), key="btn_preview_template", use_container_width=True):
                    with st.spinner(tr("template.preview_generating")):
                        try:
                            from reelforge.services.frame_html import HTMLFrameGenerator
                            
                            # Use the currently selected template
                            template_path = f"templates/{frame_template}"
                            generator = HTMLFrameGenerator(template_path)
                            
                            # Generate preview
                            preview_path = run_async(generator.generate_frame(
                                title=preview_title,
                                text=preview_text,
                                image=preview_image,
                                width=preview_width,
                                height=preview_height
                            ))
                            
                            # Display preview
                            if preview_path:
                                st.success(tr("template.preview_success"))
                                st.image(
                                    preview_path, 
                                    caption=tr("template.preview_caption", template=frame_template),
                                )
                                
                                # Show file path
                                st.caption(f"📁 {preview_path}")
                            else:
                                st.error("Failed to generate preview")
                                
                        except Exception as e:
                            st.error(tr("template.preview_failed", error=str(e)))
                            logger.exception(e)
    
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
                        tts_workflow=tts_workflow_key,  # Pass TTS workflow key
                        image_workflow=workflow_key,  # Pass workflow key (e.g., "runninghub/image_flux.json")
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

