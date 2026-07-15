import glob
import json
import os
import tempfile
import zipfile

import streamlit as st

import processor
import ui_components

def render_image_assist():
    ui_components.inject_page_theme("image")
    ui_components.render_page_hero(
        "Creative tools",
        "Image Assist",
        "Prepare clipart sheets, batch format artwork, and build showcase collages.",
    )

    tool_select = st.radio(
        "Choose an Image Assist tool:",
        ["Sheet Splitter", "Batch Formatter", "Showcase Collage"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.markdown(
        f"""
        <div class="tool-card-row">
            <div class="tool-card {'active' if tool_select == 'Sheet Splitter' else ''}">
                <div class="tool-card-title">Sheet Splitter</div>
                <div class="tool-card-text">Split clipart sheets into individual print-ready images.</div>
            </div>
            <div class="tool-card {'active' if tool_select == 'Batch Formatter' else ''}">
                <div class="tool-card-title">Batch Formatter</div>
                <div class="tool-card-text">Remove backgrounds, resize, crop, and format multiple files.</div>
            </div>
            <div class="tool-card {'active' if tool_select == 'Showcase Collage' else ''}">
                <div class="tool-card-title">Showcase Collage</div>
                <div class="tool-card-text">Create clean bundle gallery images for listings.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # TOOL 1: SHEET SPLITTER
    if tool_select == "Sheet Splitter":
        st.markdown("#### Sheet Splitter")
        
        col_split_opts, col_split_res = st.columns([2, 3])
        
        with col_split_opts:
            with st.container(border=True):
                st.markdown("#### Split Options")
                uploaded_sheet = st.file_uploader(
                    "Upload Clipart Sheet Image",
                    type=["png", "jpg", "jpeg"],
                    key="sheet_splitter_uploader"
                )
                
                canvas_color_mode = st.selectbox(
                    "Output Canvas Background color",
                    ["transparent", "white", "black", "custom hex"]
                )
                
                canvas_custom_hex = "#ffffff"
                if canvas_color_mode == "custom hex":
                    canvas_custom_hex = st.text_input("Custom Hex Color Code", value="#FAF8F5")
                    
                bg_color_arg = canvas_color_mode if canvas_color_mode != "custom hex" else canvas_custom_hex
                
                run_splitter = st.button("Run Processor", type="primary")
            
        with col_split_res:
            if run_splitter and uploaded_sheet:
                with st.spinner("AI is processing sheet (Detecting, Segmenting, Upscaling)... this may take a moment"):
                    temp_dir = tempfile.mkdtemp()
                    sheet_path = os.path.join(temp_dir, os.path.basename(uploaded_sheet.name))
                    with open(sheet_path, "wb") as f:
                        f.write(uploaded_sheet.getbuffer())
                        
                    try:
                        processor.auto_process_sheet(sheet_path, bg_type='transparent', canvas_color=bg_color_arg)
                        
                        split_out_dir = os.path.join(temp_dir, "Split")
                        split_files = glob.glob(os.path.join(split_out_dir, "*.png"))
                        
                        if split_files:
                            with st.container(border=True):
                                st.success(f"🎉 Successfully split sheet into {len(split_files)} designs!")
                                
                                # Zip files for download
                                zip_path = tempfile.mktemp(suffix=".zip")
                                with zipfile.ZipFile(zip_path, 'w') as zf:
                                    for idx, file_path in enumerate(split_files):
                                        zf.write(file_path, arcname=os.path.basename(file_path))
                                
                                with open(zip_path, "rb") as zfile:
                                    st.download_button(
                                        label="📥 Download Split Clipart Pack (.ZIP)",
                                        data=zfile.read(),
                                        file_name="split_clipart_pack.zip",
                                        mime="application/zip",
                                        type="primary"
                                    )
                            
                            # Preview gallery
                            st.markdown("#### Isolated Clipart Previews")
                            cols_gal = st.columns(3)
                            for idx, file_path in enumerate(split_files):
                                with cols_gal[idx % 3]:
                                    with st.container(border=True):
                                        st.markdown(f"<p class='small text-muted mb-2 text-truncate'>{os.path.basename(file_path)}</p>", unsafe_allow_html=True)
                                        st.image(file_path, width="stretch")
                        else:
                            st.warning("No distinct items could be isolated on the sheet. Ensure images are distinct and high contrast.")
                    except Exception as e:
                        st.error(f"Error processing sheet: {e}")
            elif run_splitter and not uploaded_sheet:
                st.warning("Please upload a clipart sheet first.")
            else:
                st.markdown("""
                <div class="alert alert-light border border-light-subtle shadow-sm rounded-4 p-4 text-center">
                    <p class="mb-0 text-secondary">Upload a clipart sheet and click 'Run AI Sheet Splitter' on the left to extract designs.</p>
                </div>
                """, unsafe_allow_html=True)

    # TOOL 2: BATCH FORMATTER
    elif tool_select == "Batch Formatter":
        st.markdown("#### Batch Formatter")
        
        col_batch_opts, col_batch_res = st.columns([2, 3])
        
        with col_batch_opts:
            with st.container(border=True):
                st.markdown("#### Batch Options")
                uploaded_batch_files = st.file_uploader(
                    "Upload Raw Clipart Files (Multiple)",
                    type=["png", "jpg", "jpeg", "webp"],
                    accept_multiple_files=True,
                    key="batch_clipart_uploader"
                )
                
                run_batch = st.button("Run Processor", type="primary")
            
        with col_batch_res:
            if run_batch and uploaded_batch_files:
                with st.spinner("Processing batch background removal..."):
                    temp_dir = tempfile.mkdtemp()
                    
                    for file in uploaded_batch_files:
                        path = os.path.join(temp_dir, os.path.basename(file.name))
                        with open(path, "wb") as f:
                            f.write(file.getbuffer())
                            
                    try:
                        processor.format_clipart_batch(temp_dir)
                        
                        results_out_dir = os.path.join(temp_dir, "Results")
                        result_files = glob.glob(os.path.join(results_out_dir, "*.png"))
                        
                        if result_files:
                            with st.container(border=True):
                                st.success(f"🎉 Successfully formatted {len(result_files)} clipart files!")
                                
                                zip_path = tempfile.mktemp(suffix=".zip")
                                with zipfile.ZipFile(zip_path, 'w') as zf:
                                    for idx, file_path in enumerate(result_files):
                                        zf.write(file_path, arcname=os.path.basename(file_path))
                                
                                with open(zip_path, "rb") as zfile:
                                    st.download_button(
                                        label="📥 Download Formatted Clipart (.ZIP)",
                                        data=zfile.read(),
                                        file_name="formatted_cliparts.zip",
                                        mime="application/zip",
                                        type="primary"
                                    )
                            
                            # Preview gallery
                            st.markdown("#### Formatted Clipart Previews")
                            cols_gal = st.columns(3)
                            for idx, file_path in enumerate(result_files):
                                with cols_gal[idx % 3]:
                                    with st.container(border=True):
                                        st.markdown(f"<p class='small text-muted mb-2 text-truncate'>{os.path.basename(file_path)}</p>", unsafe_allow_html=True)
                                        st.image(file_path, width="stretch")
                        else:
                            st.warning("No files were successfully processed.")
                    except Exception as e:
                        st.error(f"Error in batch processing: {e}")
            elif run_batch and not uploaded_batch_files:
                st.warning("Please upload files to format.")
            else:
                st.markdown("""
                <div class="alert alert-light border border-light-subtle shadow-sm rounded-4 p-4 text-center">
                    <p class="mb-0 text-secondary">Upload raw design files and click 'Run Batch Formatter' on the left to process them.</p>
                </div>
                """, unsafe_allow_html=True)

    # TOOL 3: SHOWCASE GRID COLLAGE
    elif tool_select == "Showcase Collage":
        st.markdown("#### Showcase Collage")
        
        col_show_opts, col_show_res = st.columns([2, 3])
        
        with col_show_opts:
            with st.container(border=True):
                st.markdown("#### Showcase Options")
                uploaded_cliparts = st.file_uploader(
                    "Upload Transparent Clipart PNGs (Multiple)",
                    type=["png"],
                    accept_multiple_files=True,
                    key="showcase_cliparts_uploader"
                )
                
                uploaded_show_bg = st.file_uploader(
                    "Upload Mockup Background Texture (Optional)",
                    type=["png", "jpg", "jpeg"],
                    key="showcase_bg_uploader"
                )
                
                run_showcase = st.button("Generate Showcase", type="primary")
            
        with col_show_res:
            if run_showcase and uploaded_cliparts:
                with st.spinner("Generating grid collage with drop-shadows..."):
                    temp_dir = tempfile.mkdtemp()
                    clipart_dir = os.path.join(temp_dir, "Clipart")
                    os.makedirs(clipart_dir, exist_ok=True)
                    
                    for file in uploaded_cliparts:
                        path = os.path.join(clipart_dir, os.path.basename(file.name))
                        with open(path, "wb") as f:
                            f.write(file.getbuffer())
                            
                    bg_path = None
                    if uploaded_show_bg:
                        bg_path = os.path.join(temp_dir, os.path.basename(uploaded_show_bg.name))
                        with open(bg_path, "wb") as f:
                            f.write(uploaded_show_bg.getbuffer())
                            
                    try:
                        output_showcase_path = os.path.join(temp_dir, "Bundle_Showcase.png")
                        processor.create_showcase_mockup(clipart_dir, bg_path, output_path=output_showcase_path)
                        
                        if os.path.exists(output_showcase_path):
                            with st.container(border=True):
                                st.success("🎉 Bundle Showcase Collage Generated Successfully!")
                                st.image(output_showcase_path, width="stretch")
                                
                                with open(output_showcase_path, "rb") as fimg:
                                    st.download_button(
                                        label="📥 Download Showcase Image (.PNG)",
                                        data=fimg.read(),
                                        file_name="bundle_showcase_mockup.png",
                                        mime="image/png",
                                        type="primary"
                                    )
                        else:
                            st.error("Failed to generate showcase collage image.")
                    except Exception as e:
                        st.error(f"Error generating showcase: {e}")
            elif run_showcase and not uploaded_cliparts:
                st.warning("Please upload clipart files to arrange.")
            else:
                st.markdown("""
                <div class="alert alert-light border border-light-subtle shadow-sm rounded-4 p-4 text-center">
                    <p class="mb-0 text-secondary">Upload transparent cliparts and background, then click 'Generate Bundle Showcase' on the left to create your collage grid.</p>
                </div>
                """, unsafe_allow_html=True)

