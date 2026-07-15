# EtsyTools Seller Workspace — Technical Specification

This document details the architecture, file mapping, layout rules, and API specifications for the unified **EtsyTools Seller Workspace** dashboard application.

---

## 1. 📂 File Map & Module Responsibilities

The workspace is housed in a single, consolidated repository at `c:\QuillSketch\EtsyTools\`.

*   **`app.py`**: The core Streamlit application. Manages session states, handles page routing, runs the PNG Listing Wizard steps, and initiates AI processing.
*   **`ui_components.py`**: The UI template library. Houses all HTML markup wrappers, CSS custom stylesheets (including Slack sidebar locked-open overrides), diagnostic cards, and trend table rows, separating visual design from code logic.
*   **`config.yaml`**: Contains printing presets (T-Shirt, Sweatshirt, Mug wrap, Tote bag, and Digital aspect ratios) and initial brand color theme defaults.
*   **`analyzer.py`**: The diagnostics engine. Inspects upload PNG dimensions, aspect ratios, and DPI values to verify print compliance, calculating ratio deviations.
*   **`listing_generator.py`**: Generates copyable metadata using the modern `google-genai` SDK and Pydantic structured schemas, running a Python sanitizing layer.
*   **`image_generator.py`**: The image composer. Handles overlay positioning, watermark logo opacity blending, and programmatic infographics generation (incorporating Montserrat fonts and custom brand color configurations).
*   **`usage.json`**: A local JSON database tracking the current month's Tavily Search API counts.
*   **`.env`**: Stores shared secrets (`GEMINI_API_KEY`, `TAVILY_API_KEY`).
*   **`.streamlit/config.toml`**: Custom Streamlit boot configurations mapping the default background theme values.
*   **`requirements.txt`**: Combined dependencies descriptor (Streamlit, Pillow, requests, GenAI modern SDK, Pydantic, etc.).
*   **`mockup_templates/`**: Folder to upload blank product mockup images.
*   **`brand_assets/`**: Folder to place branding watermark files (`logo.png`, `logo.jpg`) and Montserrat font weights.
*   **`ImageAssist/`**: Subfolder containing `processor.py` (which houses FastSAM segmentation models and RealESRGAN upscaler libraries).
*   **`run.ps1`**: PowerShell launcher executing the local Streamlit boot process.

---

## 2. 🎨 UI & Layout Specification (Slack Style)

The workspace implements a custom, high-end theme inspired by modern Slack workspaces, styled dynamically in response to colors selected via the color pickers:

### Left Sidebar (Slack Workspace channels List)
*   **Background Canvas**: Fixed to dark charcoal `#1A1D21`.
*   **Layout Behavior**: Pinned permanently open in browser views. Streamlit's native close/collapse arrow button (`collapsedControl`) is hidden via CSS inside the sidebar to prevent accidental clicks. The expand control arrow remains visible in the main canvas if the sidebar is ever collapsed.
*   **Workspace Navigation**: Consolidated down to **three core tools** styled as flat channel button list items under an uppercase `CHANNELS` header:
    *   `# png-listing-wizard` (Step-by-step listing compositor)
    *   `# image-assist` (Clipart segmentation and upscaling suite)
    *   `# trend-research` (Tavily search trends analyzer and prompt builder)
*   **Active Tab**: Colored in the selected theme accent color (`{theme_accent}`), text bolded in white.
*   **Settings Panel**: Logo watermarks and infographic theme color pickers are cleanly collapsed inside a `⚙️ Settings & Branding` expander drawer at the bottom of the sidebar.

### Main Workspace Canvas (Slack Canvas Look)
*   **Background Canvas**: Soft neutral off-white (`{theme_bg}`).
*   **Typography**: Montserrat/Outfit for body text, elegant Playfair Display (serif) for headers. Text color strictly forced to dark charcoal (`{theme_text}`) inside the main canvas, and light gray (`#D1D2D3`) inside the sidebar to prevent visual clashes.
*   **Content Cards**: White background (`#FFFFFF`), light slate borders (`1px solid #E2E8F0`), and flat roundings (`border-radius: 8px`) with subtle, soft shadows.
*   **Header Bar**: Inline, compact title bar fixed at the very top edge with a negative margin (`margin-top: -15px`) and thin separating line.

### Input Widgets & Controls
*   **Reverted Fields & Popovers**: Direct CSS overrides prevent theme colors from turning dropdown selectboxes, text fields, textareas, and file upload dropzones black on the main page. Expanded dropdown option overlay lists (`div[data-baseweb="popover"]` and `div[role="option"]`) are explicitly styled white with charcoal text and brand-colored hover highlights.
*   **Interactive Glow**: Hovering over inputs triggers a soft glowing border matching your custom brand accent color (`{theme_accent}`).

---

## 3. 🔌 Functional & API Specifications

### Sizing & Aspect Ratio Diagnostics (`analyzer.py`)
*   **Physical Metric Thresholds**: Compares dimensions and DPI against configurations in `config.yaml`.
*   **Aspect Ratio Mismatch Calculation**: Calculates the absolute difference between target aspect ratio and artwork aspect ratio: `abs(ratio_artwork - ratio_target)`.
    *   If deviation > `0.05`, flags compliance check as incomplete (`is_ready = False`) and issues a warning recommendation to prevent visual crop or stretch print defects.
*   **Quality Indicators**: Displays dynamic color alerts based on DPI thresholds:
    *   `DPI >= 300`: `🏆 300+ DPI Ultra-HD` (Green badge)
    *   `150 <= DPI < 300`: `⚠️ Medium Quality` (Orange badge)
    *   `DPI < 150`: `🚨 Low Resolution Web-Only` (Red badge)

### Etsy API Tags Sanitizer (`listing_generator.py`)
*   To ensure listings are fully compliant with Etsy's product dashboard constraints, a Python post-processing layer cleans the keywords returned by Google Gemini:
    *   **Length Check**: Truncates all tags to a maximum of **20 characters** (Etsy's hard string limit).
    *   **De-duplication**: Filters out duplicate keywords to optimize search visibility.
    *   **Padding**: If the tag count is less than 13, it backfills with default high-converting keywords (e.g. `"sublimation print"`, `"digital design png"`).
    *   **Trimming**: Limits the list to **exactly 13 tags total**.

### Mockup Compositor Grid Gallery (`app.py`)
*   Generated mockup templates and programmatic infographics cards in Step 2 are arranged inside a structured, side-by-side **2-column responsive layout grid** instead of a single vertical list, optimizing canvas scrolling.
