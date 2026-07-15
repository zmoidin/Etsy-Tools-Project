import os
import sys
import streamlit as st
from etsytools.config import load_environment
from etsytools.paths import BRAND_ASSETS_DIR, MOCKUP_TEMPLATES_DIR, ensure_workspace_dirs

# Import refactored UI components library
import ui_components

# Load environment variables from .env using a typed settings wrapper.
settings = load_environment()
api_key = settings.gemini_api_key

# Add ImageAssist to system import paths to reuse processor.py
IMAGE_ASSIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ImageAssist")
if IMAGE_ASSIST_DIR not in sys.path:
    sys.path.append(IMAGE_ASSIST_DIR)

import analyzer
from etsytools.ui.pages.image_assist import render_image_assist
from etsytools.ui.pages.png_listing_wizard import render_png_listing_wizard
from etsytools.ui.pages.trend_research import render_trend_research

# Page Config
st.set_page_config(
    page_title="EtsyTools - Seller Workspace",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Workspace directories setup
ensure_workspace_dirs()
MOCKUP_DIR = str(MOCKUP_TEMPLATES_DIR)
BRAND_DIR = str(BRAND_ASSETS_DIR)

# Load configuration values
config = analyzer.load_config()
product_defs = config.get('products', {})

# Initialize session state for navigation
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Listing Wizard"


# Initialize session state for analysis, listing, and navigation
if "artwork_file" not in st.session_state:
    st.session_state.artwork_file = None
if "artwork_file_name" not in st.session_state:
    st.session_state.artwork_file_name = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "etsy_copy" not in st.session_state:
    st.session_state.etsy_copy = None
if "selected_product" not in st.session_state:
    st.session_state.selected_product = list(product_defs.keys())[0] if product_defs else None
if "wizard_step" not in st.session_state:
    st.session_state.wizard_step = 1

# Establish active variables across all layout tabs
selected_tab = st.session_state.active_tab
selected_product = st.session_state.selected_product

# SIDEBAR CONFIGURATIONS - Slack Workspace Design
ui_components.render_sidebar_header()
ui_components.render_sidebar_section("TOOLS")

menu_mappings = {
    "Listing Wizard": "Listing Wizard",
    "Image Assist": "Image Assist",
    "Trend Research": "Trend Research"
}
if st.session_state.active_tab not in menu_mappings:
    st.session_state.active_tab = "Listing Wizard"
selected_tab = st.session_state.active_tab

# Render sidebar menu buttons like Slack channels
for raw_tab, label in menu_mappings.items():
    is_active = (selected_tab == raw_tab)
    if st.sidebar.button(
        label,
        key=f"slack_nav_{raw_tab}",
        type="primary" if is_active else "secondary"
    ):
        st.session_state.active_tab = raw_tab
        st.rerun()

st.sidebar.divider()

# Collapsible Settings Drawer at the bottom
with st.sidebar.expander("Settings & Branding"):
    # Branding logo auto-detection
    st.markdown("<h4 style='font-size: 13px; font-weight: bold; margin-bottom: 5px;'>Brand Asset</h4>", unsafe_allow_html=True)
    
    logo_path = None
    detected_logo = None
    for filename in ["logo.png", "logo.jpg", "logo.jpeg"]:
        test_path = os.path.join(BRAND_DIR, filename)
        if os.path.exists(test_path):
            detected_logo = filename
            logo_path = test_path
            break
            
    if detected_logo:
        st.success(f"Logo: `{detected_logo}`")
        st.image(logo_path, width=80)
    else:
        st.warning("Place `logo.png` inside `brand_assets/` to enable watermarks.")
        
    st.markdown("<h4 style='font-size: 13px; font-weight: bold; margin-top: 10px; margin-bottom: 5px;'>Infographic Theme</h4>", unsafe_allow_html=True)
    theme_bg = st.color_picker("Background Color", config["infographics"]["theme"]["bg_color"])
    theme_text = st.color_picker("Text Color", config["infographics"]["theme"]["text_color"])
    theme_accent = st.color_picker("Accent Color", config["infographics"]["theme"]["accent_color"])
    theme_muted = st.color_picker("Muted Text Color", config["infographics"]["theme"]["muted_color"])
    theme_border = st.color_picker("Border Color", config["infographics"]["theme"]["border_color"])

theme_config = {
    "bg_color": theme_bg,
    "text_color": theme_text,
    "accent_color": theme_accent,
    "muted_color": theme_muted,
    "border_color": theme_border
}

# Inject Bootstrap + Stylesheet overrides using clean UI components library
ui_components.inject_slack_stylesheet(theme_config)

# App Header
ui_components.render_top_header(theme_config)

# MAIN CANVAS WORKSPACE ROUTING
tab_keys = list(menu_mappings.keys())
if selected_tab == tab_keys[0]:
    render_png_listing_wizard(config, product_defs, selected_product, MOCKUP_DIR, logo_path, theme_config, api_key)
elif selected_tab == tab_keys[1]:
    render_image_assist()
elif selected_tab == tab_keys[2]:
    render_trend_research(settings)
