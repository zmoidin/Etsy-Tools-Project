import glob
import json
import os
import tempfile
import zipfile

import requests
import streamlit as st
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False

import ui_components
from etsytools.models import PromptsResponse, TrendsResponse
from etsytools.storage.usage_store import get_tavily_usage, increment_tavily_usage

def render_trend_research(settings):
    ui_components.inject_page_theme("trend")
    ui_components.render_page_hero(
        "Market research",
        "Trend Research",
        "Search current design signals, review sources, and generate prompt starters.",
    )

    # Initialize session state variables for trend outputs
    if "trends_list" not in st.session_state:
        st.session_state.trends_list = None
    if "prompt_elements" not in st.session_state:
        st.session_state.prompt_elements = None
    if "selected_trend_idx" not in st.session_state:
        st.session_state.selected_trend_idx = 0
        
    col_trend_left, col_trend_right = st.columns([2, 3])

    with col_trend_left:
        with st.container(border=True):
            st.markdown("#### Search Trends")
            user_topic = st.text_input("Enter Design Topic (e.g. Cat stickers, Fall florals, Retro coffee)", placeholder="retro cottagecore")
            
            run_trends = st.button("Analyze Graphic Trends", type="primary")
            
            usage_data = get_tavily_usage()
            searches_used = usage_data.get("tavily_searches", 0)
            
            # Render Tavily quota tracker via UI library
            ui_components.render_tavily_usage_card(searches_used)
            
        if run_trends:
            tavily_key = settings.tavily_api_key
            gemini_key = settings.gemini_api_key
            
            if not tavily_key or tavily_key == "your_tavily_api_key_here":
                st.error("Tavily API key is not configured. Please add TAVILY_API_KEY to your .env file.")
            elif not gemini_key or gemini_key == "your_gemini_api_key_here":
                st.error("Gemini API key is not configured. Please check your .env file.")
            elif not GENAI_AVAILABLE:
                st.error("Gemini SDK is not installed. Run `pip install -r requirements.txt` in the project environment.")
            elif not user_topic.strip():
                st.warning("Please enter a valid topic.")
            else:
                with st.spinner("Searching and analyzing design trends..."):
                    try:
                        modified_query = f"current graphic design trends illustration styles for {user_topic}"
                        tavily_response = requests.post(
                            "https://api.tavily.com/search",
                            json={
                                "api_key": tavily_key,
                                "query": modified_query,
                                "search_depth": "basic",
                                "include_answer": False,
                                "include_raw_content": False,
                                "max_results": 5
                              },
                              timeout=10
                        )
                        tavily_response.raise_for_status()
                        search_data = tavily_response.json()
                        increment_tavily_usage()
                        
                        results = search_data.get("results", [])
                        if not results:
                            search_context = f"No active search results found for: {user_topic}"
                        else:
                            search_context = "\n\n".join([f"Title: {r.get('title')}\nContent: {r.get('content')}" for r in results])
                            
                        # Query Gemini using modern SDK
                        client = genai.Client(api_key=gemini_key)
                        prompt_str = (
                            f"You are a design trends expert. Analyze the following web search results regarding current graphic "
                            f"design trends and illustration styles for the topic: '{user_topic}'.\n\n"
                            f"Search Context:\n{search_context}\n\n"
                            f"Based on this information, extract the top 10 most relevant and visually distinct design elements and "
                            f"illustration style combinations. For each item, evaluate the search context to assign an accurate "
                            f"trend_score (1-100) and trend_direction ('Surging', 'Rising', 'Stable', or 'Declining'). Ensure the output strictly conforms to the JSON schema."
                        )
                        
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt_str,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=TrendsResponse,
                                temperature=0.7
                            )
                        )
                        trends_data = json.loads(response.text)
                        st.session_state.trends_list = trends_data.get("trends", [])
                        st.session_state.prompt_elements = None  # Clear previous prompts
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error querying design trends: {e}")
                        
    with col_trend_right:
        if st.session_state.trends_list:
            with st.container(border=True):
                st.markdown(f"#### Top Design Trends for `{user_topic}`")
                
                # Display top 10 trends using UI library row renderer
                for idx, trend in enumerate(st.session_state.trends_list):
                    ui_components.render_trend_row(
                        idx + 1,
                        trend.get('design'),
                        trend.get('style'),
                        trend.get('trend_direction', 'Stable'),
                        trend.get('trend_score', 50)
                    )
                    
            # Clipart Prompt Generator
            with st.container(border=True):
                st.markdown("#### Prompt Generator")
                trend_options = [f"{t.get('design')} ({t.get('style')})" for t in st.session_state.trends_list]
                selected_idx = st.selectbox(
                    "Select a trend theme to build clipart prompts:",
                    options=range(len(trend_options)),
                    format_func=lambda x: trend_options[x]
                )
                
                run_prompts = st.button("Generate Clipart Prompts", type="primary")
                
                if run_prompts:
                    with st.spinner("Generating copyable clipart prompts via Gemini..."):
                        try:
                            target_trend = st.session_state.trends_list[selected_idx]
                            design_val = target_trend.get("design")
                            style_val = target_trend.get("style")
                            
                            gemini_key = settings.gemini_api_key
                            if not GENAI_AVAILABLE:
                                st.error("Gemini SDK is not installed. Run `pip install -r requirements.txt` in the project environment.")
                                st.stop()
                            client = genai.Client(api_key=gemini_key)
                            
                            prompt_str = (
                                f"You are an expert Prompt Engineer optimizing text-to-image prompts for models like Midjourney, DALL-E 3, and Stable Diffusion.\n"
                                f"Generate between 5 to 10 distinct, isolated clipart assets/elements for the design theme: '{design_val}' in the style: '{style_val}'.\n\n"
                                f"For each generated element, you MUST follow this exact prompt template:\n"
                                f"\"An isolated [Element Name] asset, {style_val} style, vibrant colors, studio lighting, die-cut sticker look, pure solid white background, high-resolution 8k texture, print-ready quality, centered composition --no shadows, background scenery, realistic photographic elements, grid\"\n\n"
                                f"Ensure you replace '[Element Name]' with the specific element (e.g. if the element is 'Seashell', the prompt becomes 'An isolated Seashell asset, {style_val} style...') and keep the rest of the template exactly intact."
                            )
                            
                            response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=prompt_str,
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json",
                                    response_schema=PromptsResponse,
                                    temperature=0.7
                                )
                            )
                            prompts_data = json.loads(response.text)
                            st.session_state.prompt_elements = prompts_data.get("elements", [])
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error generating prompts: {e}")
                            
                if st.session_state.prompt_elements:
                    st.markdown("<hr class='my-4 border-light-subtle'>", unsafe_allow_html=True)
                    st.markdown("##### 📋 Midjourney & DALL-E Prompts")
                    for el in st.session_state.prompt_elements:
                        with st.container(border=True):
                            st.markdown(f"**Element: `{el.get('name')}`**")
                            st.code(el.get("prompt"), language="text")
        else:
            st.markdown("""
            <div class="alert alert-light border border-light-subtle shadow-sm rounded-4 p-4 text-center">
                <p class="mb-0 text-secondary">Input a topic on the left and click 'Analyze Graphic Trends' to start crawling search momentum and generating prompts.</p>
            </div>
            """, unsafe_allow_html=True)
