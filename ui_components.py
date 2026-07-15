import html

import streamlit as st


def hex_to_rgb(hex_str):
    """Converts a hex color string to a comma-separated decimal RGB string."""
    hex_str = hex_str.lstrip("#")
    try:
        return ",".join(str(int(hex_str[i : i + 2], 16)) for i in (0, 2, 4))
    except Exception:
        return "37,99,235"


def inject_slack_stylesheet(theme):
    """Injects the app-wide clean SaaS stylesheet.

    Kept under the historical function name so the Streamlit shell does not
    need to change.
    """
    st.markdown(
        """
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --saas-bg: #F7F8FA;
            --saas-card: #FFFFFF;
            --saas-text: #111827;
            --saas-muted: #6B7280;
            --saas-border: #E5E7EB;
            --saas-blue: #2563EB;
            --saas-blue-soft: #EFF6FF;
            --saas-indigo: #4F46E5;
            --saas-indigo-soft: #EEF2FF;
            --saas-amber: #D97706;
            --saas-amber-soft: #FFF7ED;
            --saas-green: #16A34A;
            --saas-red: #DC2626;
            --page-accent: #2563EB;
            --page-soft: #EFF6FF;
            --saas-shadow: 0 1px 2px rgba(16, 24, 40, 0.04), 0 10px 24px rgba(16, 24, 40, 0.06);
        }

        .stApp {
            background: var(--saas-bg) !important;
        }

        html, body, p, label, input, select, textarea,
        .stMarkdown, .stApp, .stApp p, .stApp label, .stApp li {
            font-family: 'Inter', sans-serif !important;
            color: var(--saas-text) !important;
        }

        h1, h2, h3, h4, h5, h6, .premium-header {
            font-family: 'Inter', sans-serif !important;
            font-weight: 780 !important;
            letter-spacing: -0.035em !important;
            color: var(--saas-text) !important;
        }

        .block-container {
            max-width: 1240px !important;
            padding-top: 1.25rem !important;
            padding-bottom: 2rem !important;
        }

        header[data-testid="stHeader"] {
            display: none !important;
        }

        div[data-testid="stContainer"] {
            background: var(--saas-card) !important;
            border: 1px solid var(--saas-border) !important;
            border-radius: 16px !important;
            padding: 22px !important;
            box-shadow: var(--saas-shadow) !important;
        }

        div[data-testid="stContainer"]:hover {
            border-color: #D1D5DB !important;
        }

        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"],
        section[data-testid="stSidebar"] > div {
            background: #FFFFFF !important;
            border-right: 1px solid var(--saas-border) !important;
            padding-top: 10px !important;
        }

        [data-testid="collapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            color: var(--saas-text) !important;
            background: #FFFFFF !important;
            border: 1px solid var(--saas-border) !important;
            border-radius: 999px !important;
            box-shadow: 0 4px 12px rgba(16, 24, 40, 0.10) !important;
        }

        section[data-testid="stSidebar"] {
            width: 260px !important;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] h4,
        section[data-testid="stSidebar"] h5,
        section[data-testid="stSidebar"] h6,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] li,
        section[data-testid="stSidebar"] div,
        section[data-testid="stSidebar"] .stMarkdown {
            color: var(--saas-text) !important;
        }

        section[data-testid="stSidebar"] hr {
            border-color: var(--saas-border) !important;
        }

        .sidebar-section-header {
            color: #9CA3AF !important;
            font-size: 11px !important;
            font-weight: 750 !important;
            letter-spacing: 0.08em !important;
            margin: 18px 0 8px;
            padding-left: 10px;
        }

        section[data-testid="stSidebar"] div.stButton > button {
            width: 100% !important;
            justify-content: flex-start !important;
            text-align: left !important;
            color: #374151 !important;
            border: 1px solid transparent !important;
            border-radius: 12px !important;
            padding: 10px 14px !important;
            font-size: 14px !important;
            font-weight: 650 !important;
            background: transparent !important;
            box-shadow: none !important;
            transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
        }

        section[data-testid="stSidebar"] div.stButton > button:hover {
            background: #F3F4F6 !important;
            color: var(--saas-blue) !important;
            transform: none !important;
            box-shadow: none !important;
        }

        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
            background: var(--saas-blue-soft) !important;
            color: var(--saas-blue) !important;
            border-color: #DBEAFE !important;
            box-shadow: none !important;
        }

        div.stButton > button {
            border-radius: 12px !important;
            padding: 0.62rem 1rem !important;
            border: 1px solid var(--saas-border) !important;
            background: #FFFFFF !important;
            color: #374151 !important;
            box-shadow: none !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 650 !important;
        }

        div.stButton > button:hover {
            transform: none !important;
            border-color: #CBD5E1 !important;
            background: #F9FAFB !important;
            color: var(--saas-text) !important;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06) !important;
        }

        div.stButton > button[kind="primary"] {
            background: var(--page-accent) !important;
            border-color: var(--page-accent) !important;
            color: #FFFFFF !important;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.20) !important;
        }

        div.stButton > button[kind="primary"]:hover {
            background: var(--page-accent) !important;
            color: #FFFFFF !important;
            opacity: 0.94 !important;
        }

        div[data-baseweb="select"],
        div[data-baseweb="select"] > div,
        div[data-baseweb="select"] div,
        div[data-baseweb="select"] span,
        div[data-baseweb="input"],
        div[data-baseweb="input"] > div,
        div[data-baseweb="input"] input,
        div[data-baseweb="textarea"],
        div[data-baseweb="textarea"] > div,
        div[data-baseweb="textarea"] textarea,
        div[data-baseweb="checkbox"],
        div[data-baseweb="radio"],
        div[data-testid="stFileUploaderDropzone"],
        div[data-testid="stFileUploaderDropzone"] > div,
        div[data-testid="stFileUploaderDropzone"] section,
        div[data-testid="stFileUploaderDropzone"] small,
        div[data-testid="stFileUploaderDropzone"] span,
        div[data-testid="stFileUploaderDropzone"] div,
        div[data-testid="stSelectbox"] div,
        div[data-testid="stTextInput"] div,
        div[data-testid="stTextArea"] div,
        div[data-testid="stNumberInput"] div,
        textarea,
        input,
        div[data-baseweb="popover"],
        div[role="listbox"],
        div[role="option"],
        [data-baseweb="menu-item"] {
            background-color: #FFFFFF !important;
            color: var(--saas-text) !important;
            border-color: var(--saas-border) !important;
            border-radius: 12px !important;
        }

        button,
        button * {
            background-color: transparent;
        }

        div.stButton > button,
        div.stButton > button *,
        div[data-testid="stDownloadButton"] > button,
        div[data-testid="stDownloadButton"] > button * {
            color: inherit !important;
        }

        div.stButton > button[kind="primary"],
        div.stButton > button[kind="primary"] *,
        div[data-testid="stDownloadButton"] > button[kind="primary"],
        div[data-testid="stDownloadButton"] > button[kind="primary"] * {
            color: #FFFFFF !important;
        }

        div[data-baseweb="select"]:hover,
        div[data-baseweb="input"]:hover,
        div[data-testid="stFileUploaderDropzone"]:hover,
        textarea:hover {
            border-color: var(--page-accent) !important;
            box-shadow: 0 0 0 3px color-mix(in srgb, var(--page-accent) 14%, transparent) !important;
        }

        div[data-testid="stFileUploader"] {
            border: 1.5px dashed color-mix(in srgb, var(--page-accent) 45%, white) !important;
            border-radius: 16px !important;
            background: #FFFFFF !important;
            padding: 12px !important;
        }

        div[data-testid="stFileUploader"] button,
        div[data-testid="stFileUploaderDropzone"] button {
            background: #FFFFFF !important;
            color: var(--page-accent) !important;
            border: 1px solid color-mix(in srgb, var(--page-accent) 35%, white) !important;
            border-radius: 12px !important;
            box-shadow: none !important;
        }

        div[data-testid="stFileUploader"] button:hover,
        div[data-testid="stFileUploaderDropzone"] button:hover {
            background: var(--page-soft) !important;
            color: var(--page-accent) !important;
        }

        div[data-testid="stExpander"] {
            border: 1px solid var(--saas-border) !important;
            background: #FFFFFF !important;
            border-radius: 14px !important;
            box-shadow: none !important;
        }

        .app-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: 0 0 18px 0;
            border-bottom: 1px solid var(--saas-border);
        }

        .app-title {
            font-size: 22px;
            line-height: 1;
            font-weight: 800;
            letter-spacing: -0.04em;
        }

        .status-strip {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            border: 1px solid var(--saas-border);
            background: #FFFFFF;
            border-radius: 999px;
            padding: 8px 12px;
            font-size: 12px;
            font-weight: 650;
            color: #374151;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: var(--saas-green);
        }

        .page-hero {
            margin: 18px 0 18px 0;
        }

        .page-kicker {
            color: var(--page-accent) !important;
            font-weight: 750;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
        }

        .page-title {
            font-size: 34px;
            font-weight: 800;
            letter-spacing: -0.05em;
            margin: 0;
            color: var(--saas-text);
        }

        .page-subtitle {
            margin-top: 8px;
            color: var(--saas-muted) !important;
            font-size: 15px;
        }

        .tool-card-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 16px;
            margin: 12px 0 22px;
        }

        .tool-card {
            background: #FFFFFF;
            border: 1px solid var(--saas-border);
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        }

        .tool-card.active {
            border-color: var(--page-accent);
            background: var(--page-soft);
        }

        .tool-card-title {
            font-weight: 750;
            margin-bottom: 6px;
        }

        .tool-card-text {
            color: var(--saas-muted) !important;
            font-size: 13px;
            line-height: 1.45;
        }

        .metric-card-saas {
            border: 1px solid var(--saas-border);
            border-radius: 14px;
            padding: 16px;
            background: #FFFFFF;
        }

        .metric-label {
            color: var(--saas-muted) !important;
            font-size: 12px;
            font-weight: 650;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .metric-value {
            color: var(--page-accent);
            font-size: 23px;
            font-weight: 800;
            margin-top: 6px;
        }

        .saas-alert {
            border: 1px solid var(--saas-border);
            border-radius: 14px;
            padding: 14px 16px;
            background: #FFFFFF;
            margin-bottom: 12px;
            color: var(--saas-text);
        }

        .saas-alert.success {
            background: #F0FDF4;
            border-color: #BBF7D0;
        }

        .saas-alert.warning {
            background: #FFFBEB;
            border-color: #FDE68A;
        }

        .badge-etsy {
            border-radius: 999px !important;
            background: var(--page-soft) !important;
            color: var(--page-accent) !important;
            border-color: color-mix(in srgb, var(--page-accent) 20%, white) !important;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )


def inject_page_theme(page):
    """Applies page-specific SaaS accent colors."""
    palettes = {
        "listing": ("#2563EB", "#EFF6FF"),
        "trend": ("#111827", "#FFF7ED"),
        "image": ("#4F46E5", "#EEF2FF"),
    }
    accent, soft = palettes.get(page, palettes["listing"])
    st.markdown(
        f"""
    <style>
        :root {{
            --page-accent: {accent};
            --page-soft: {soft};
        }}
    </style>
    """,
        unsafe_allow_html=True,
    )


def render_page_hero(kicker, title, subtitle):
    """Render a page heading using native Streamlit elements.

    This avoids raw HTML appearing if Streamlit sanitization or markdown
    rendering behavior changes.
    """
    st.write("")
    if kicker:
        st.caption(kicker.upper())
    st.title(title)
    st.caption(subtitle)


def render_sidebar_header():
    """Renders the app branding header inside the sidebar."""
    st.sidebar.markdown(
        """
    <div class="py-3 px-1 mb-3 border-bottom" style="border-color: #E5E7EB !important;">
        <div class="fw-bold fs-5" style="font-family: 'Inter', sans-serif; letter-spacing: -0.04em; color: #111827 !important;">EtsyTools <span style="color:#2563EB;">Studio</span></div>
        <div class="small" style="font-size: 12px; color: #6B7280 !important;">Local seller workspace</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_sidebar_section(title):
    """Renders a section label in the sidebar."""
    st.sidebar.markdown(f"<div class='sidebar-section-header'>{html.escape(title)}</div>", unsafe_allow_html=True)


def render_top_header(theme):
    """Renders the app top status bar."""
    st.markdown(
        """
    <div class="app-topbar">
        <div>
            <div class="app-title">EtsyTools Studio</div>
            <div style="font-size: 13px; color: #6B7280 !important; margin-top: 4px;">Diagnostics, mockups, listing copy, and image prep</div>
        </div>
        <div class="status-strip">
            <span class="status-pill"><span class="status-dot"></span> Gemini</span>
            <span class="status-pill"><span class="status-dot"></span> Tavily</span>
            <span class="status-pill"><span class="status-dot"></span> Local assets</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_metric_card(title, value, unit):
    """Renders a metric card."""
    st.markdown(
        f"""
    <div class="metric-card-saas">
        <div class="metric-label">{html.escape(str(title))}</div>
        <div class="metric-value">{html.escape(str(value))} <span style="font-size: 13px; color: #6B7280; font-weight: 650;">{html.escape(str(unit))}</span></div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_status_alert(is_ready):
    """Renders the success or warning status alert box for artwork compliance."""
    if is_ready:
        st.markdown(
            """
        <div class="saas-alert success" role="alert">
            <strong>Artwork is Etsy ready.</strong> Sizing and resolution meet the selected requirements.
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
        <div class="saas-alert warning" role="alert">
            <strong>Sizing optimization recommended.</strong> Review the findings before publishing.
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_recommendation_item(rec_text):
    """Renders a single diagnostic recommendation."""
    st.markdown(
        f"""
    <div class="saas-alert">
        <div class="small text-secondary">{html.escape(str(rec_text))}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_tavily_usage_card(searches_used):
    """Renders the Tavily Search API monthly quota usage card."""
    percentage = min((int(searches_used) / 1000) * 100, 100)
    st.markdown(
        f"""
    <div class="metric-card-saas mt-3">
        <div class="metric-label">Tavily monthly usage</div>
        <div class="metric-value">{int(searches_used)} / 1000 <span style="font-size: 13px; color: #6B7280; font-weight: 650;">searches</span></div>
        <div class="progress mt-2" style="height: 6px;">
            <div class="progress-bar" role="progressbar" style="width: {percentage}%; background: var(--page-accent);"></div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_trend_row(idx, design, style, direction, score):
    """Renders a single row in the top trends list."""
    direction = direction or "Stable"
    score = int(score or 50)
    badge_color = "#16A34A" if direction in {"Surging", "Rising"} else "#6B7280"

    st.markdown(
        f"""
    <div class="d-flex align-items-center justify-content-between border-bottom py-3">
        <div style="flex: 2;">
            <span class="fw-bold text-dark">{idx}. {html.escape(str(design))}</span><br>
            <span class="small text-muted">Style: {html.escape(str(style))}</span>
        </div>
        <div style="flex: 1; text-align: center;">
            <span class="badge rounded-pill" style="background: #F9FAFB; color: {badge_color}; border: 1px solid #E5E7EB;">{html.escape(str(direction))}</span>
        </div>
        <div style="flex: 1;">
            <div class="small text-secondary text-end">Score: {score}%</div>
            <div class="progress" style="height: 5px;">
                <div class="progress-bar" role="progressbar" style="width: {score}%; background: var(--page-accent);"></div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_dpi_badge(dpi):
    """Renders a print-readiness quality badge based on DPI."""
    dpi = int(dpi or 72)
    if dpi >= 300:
        st.markdown(
            """
        <div class="saas-alert success"><strong>300+ DPI:</strong> Strong print resolution for large artwork.</div>
        """,
            unsafe_allow_html=True,
        )
    elif dpi >= 150:
        st.markdown(
            """
        <div class="saas-alert warning"><strong>150-300 DPI:</strong> Acceptable for smaller uses, but apparel may look soft.</div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
        <div class="saas-alert warning"><strong>Under 150 DPI:</strong> Web quality only. Not recommended for physical products.</div>
        """,
            unsafe_allow_html=True,
        )
