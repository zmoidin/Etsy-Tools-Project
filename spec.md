# EtsyTools Seller Workspace — Technical Specification

This document details the architecture, file mapping, layout rules, and API specifications for the unified **EtsyTools Seller Workspace** dashboard application.

---

## 1. 📂 File Map & Module Responsibilities

The workspace is housed in a single, consolidated repository at `c:\QuillSketch\EtsyTools\`.

*   **`backend/main.py`**: The core FastAPI application. Sets up routes, handles file uploads, maps the templates and static folders, and triggers listing copy diagnostics and generation.
*   **`backend/templates/`**: Folder containing Jinja2 HTML layout pages:
    *   `base.html`: Main shell template housing the topbar, sidebar, layout elements, and status rows.
    *   `listing.html`: Listing Wizard subpage displaying steps, forms, metrics, and textcopy areas.
*   **`backend/static/`**: Houses static layout client-side files:
    *   `app.css`: Custom premium stylesheet specifying color tokens, grid settings, and responsive media rules.
    *   `app.js`: Script supporting sidebar collapse toggling and click-to-copy input interactions.
*   **`config.yaml`**: Contains printing presets (T-Shirt, Sweatshirt, Mug wrap, Tote bag, and Digital aspect ratios) and initial brand color theme defaults.
*   **`analyzer.py`**: The diagnostics engine. Inspects upload PNG dimensions, aspect ratios, and DPI values to verify print compliance, calculating ratio deviations.
*   **`listing_generator.py`**: Generates copyable metadata using the modern `google-genai` SDK and Pydantic structured schemas, running a Python sanitizing layer.
*   **`image_generator.py`**: The image composer. Handles overlay positioning, watermark logo opacity blending, and programmatic infographics generation (incorporating system fallback fonts like Arial and custom brand color configurations).
*   **`usage.json`**: A local JSON database tracking the current month's Tavily Search API counts.
*   **`.env`**: Stores shared secrets (`GEMINI_API_KEY`, `TAVILY_API_KEY`).
*   **`requirements.txt`**: Combined dependencies descriptor (FastAPI, Pillow, OpenCV, GenAI modern SDK, Pydantic, etc.).
*   **`mockup_templates/`**: Folder to upload blank product mockup images.
*   **`brand_assets/`**: Folder to place branding watermark files (`logo.png`, `logo.jpg`).
*   **`ImageAssist/`**: Subfolder containing `processor.py` (which houses FastSAM segmentation models and RealESRGAN upscaler libraries).
*   **`run.ps1`**: PowerShell launcher executing the local FastAPI Uvicorn boot process.

---

## 2. 🎨 UI & Layout Specification (SaaS Style)

The workspace implements a custom theme styled as a clean SaaS interface:

### Left Sidebar (Workspace Navigation Panel)
*   **Background Canvas**: Styled in solid white `#FFFFFF`.
*   **Layout Behavior**: Side navigation drawer (width `280px`) with transition effects. The collapse control button `Collapse sidebar` in the footer collapses the sidebar to the left. The `Show sidebar` button in the main content restores it.
*   **Workspace Navigation**: Consolidated down to **three core tools** styled under a brand title `EtsyTools Studio`:
    *   `Listing Wizard` (Step-by-step listing compositor)
    *   `Image Assist` (Clipart sheet splitter, batch background removal/formatting, and bundle showcase grid generator)
    *   `Trend Research` (Tavily search trends analyzer and clipart prompt builder)
*   **Active Tab**: Styled with a soft blue background (`var(--blue-soft)`) and blue text (`var(--blue)`), border-color matching `#dbeafe`.

### Main Workspace Canvas (SaaS Canvas Look)
*   **Background Canvas**: Soft neutral off-white (`#f7f8fa`).
*   **Typography**: Styled globally with **Inter** font via Google Fonts imports. Text color forced to dark charcoal (`#111827`).
*   **Content Cards**: White background (`#ffffff`), light slate borders (`1px solid #e5e7eb`), and roundings (`border-radius: 18px`) with soft shadows.
*   **Header Bar**: Inline, compact status topbar mapping connection signals:
    *   Gemini (Connected or Warning status pill)
    *   Tavily (Connected or Optional status pill)
    *   Local assets (Connected status pill)

### Input Widgets & Controls
*   **Input & Select Elements**: Styled white with charcoal text, `border-radius: 13px`, and a soft blue glow outline on focus.
*   **Interactive Copy Blocks**: Click-to-copy text input sections support easy metadata export for Etsy dashboard copy pasting.

---

## 3. 🔌 Functional & API Specifications

### Sizing & Aspect Ratio Diagnostics (`analyzer.py`)
*   **Physical Metric Thresholds**: Compares dimensions and DPI against configurations in `config.yaml`.
*   **Aspect Ratio Mismatch Calculation**: Calculates the absolute difference between target aspect ratio and artwork aspect ratio: `abs(ratio_artwork - ratio_target)`.
    *   If deviation > `0.05`, flags compliance check as incomplete (`is_ready = False`) and issues a warning recommendation to prevent visual crop or stretch print defects.
*   **Quality Indicators**: Displays dynamic color alerts based on DPI thresholds:
    *   `DPI >= 300`: `300+ DPI` Strong print resolution alert (Green success banner)
    *   `150 <= DPI < 300`: `150-300 DPI` Acceptable but potentially soft print quality warning (Orange alert banner)
    *   `DPI < 150`: `Under 150 DPI` Web quality only, not recommended for physical goods (Orange warning alert banner)

### Etsy API Tags Sanitizer (`listing_generator.py`)
*   To ensure listings are fully compliant with Etsy's product dashboard constraints, a Python post-processing layer cleans the keywords returned by Google Gemini:
    *   **Length Check**: Truncates all tags to a maximum of **20 characters** (Etsy's hard string limit).
    *   **De-duplication**: Filters out duplicate keywords to optimize search visibility.
    *   **Padding**: If the tag count is less than 13, it backfills with default high-converting keywords (e.g. `"sublimation print"`, `"digital design png"`).
    *   **Trimming**: Limits the list to **exactly 13 tags total**.
