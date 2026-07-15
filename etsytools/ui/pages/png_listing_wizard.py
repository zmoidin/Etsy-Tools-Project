import glob
import json
import os
import tempfile
import zipfile

import streamlit as st

import analyzer
import image_generator
import listing_generator
import ui_components

def render_png_listing_wizard(config, product_defs, selected_product, mockup_dir, logo_path, theme_config, api_key):
    ui_components.inject_page_theme("listing")
    ui_components.render_page_hero(
        "",
        "Listing Wizard",
        "Upload artwork, verify print readiness, generate mockups, and draft Etsy copy.",
    )

    # Permanent file uploader locked at the top
    uploaded_artwork = st.file_uploader(
        "Upload Artwork PNG",
        type=["png"],
        help="For best Etsy print quality, upload transparent 300 DPI files.",
        key="wizard_artwork_uploader"
    )

    if uploaded_artwork:
        if "artwork_file_name" not in st.session_state or st.session_state.artwork_file_name != uploaded_artwork.name:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(uploaded_artwork.getbuffer())
                temp_artwork_path = temp_file.name
            st.session_state.artwork_file = temp_artwork_path
            st.session_state.artwork_file_name = uploaded_artwork.name
    else:
        st.session_state.artwork_file = None
        st.session_state.artwork_file_name = None
        
    if not st.session_state.artwork_file:
        st.markdown("""
        <div class="alert alert-info border-0 shadow-sm rounded-4 p-4 d-flex align-items-center mt-3">
            <span class="fs-3 me-3">ℹ️</span>
            <div>Please upload your transparent PNG artwork at the top to activate the Listing Wizard steps.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Step indicator
        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            is_step1 = (st.session_state.wizard_step == 1)
            if st.button("1 Upload & Check", key="w_btn_step1", type="primary" if is_step1 else "secondary", width="stretch"):
                st.session_state.wizard_step = 1
                st.rerun()
        with col_w2:
            is_step2 = (st.session_state.wizard_step == 2)
            if st.button("2 Mockups", key="w_btn_step2", type="primary" if is_step2 else "secondary", width="stretch"):
                st.session_state.wizard_step = 2
                st.rerun()
        with col_w3:
            is_step3 = (st.session_state.wizard_step == 3)
            if st.button("3 Listing Copy", key="w_btn_step3", type="primary" if is_step3 else "secondary", width="stretch"):
                st.session_state.wizard_step = 3
                st.rerun()
                
        st.markdown("<hr class='my-3 border-light-subtle'>", unsafe_allow_html=True)
        
        # STEP 1: ARTWORK DIAGNOSTICS
        if st.session_state.wizard_step == 1:
            st.markdown("#### Upload & Check")
            col1, col2 = st.columns([1, 2])
            
            with col1:
                with st.container(border=True):
                    st.markdown("##### Configuration")
                    product_options = {key: prod["name"] for key, prod in product_defs.items()}
                    selected_product = st.selectbox(
                        "What is this artwork intended for?",
                        options=list(product_options.keys()),
                        format_func=lambda x: product_options[x],
                        key="selected_product"
                    )
                with st.container(border=True):
                    st.markdown("##### Artwork Preview")
                    st.image(st.session_state.artwork_file, width="stretch")
                    
            with col2:
                res = analyzer.analyze_artwork(st.session_state.artwork_file, selected_product)
                st.session_state.analysis_results = res
                
                with st.container(border=True):
                    st.markdown("##### Diagnostic Report")
                    
                    # Metrics Cards
                    cols = st.columns(3)
                    with cols[0]:
                        ui_components.render_metric_card("Dimensions", f"{res['width']}x{res['height']}", "px")
                    with cols[1]:
                        ui_components.render_metric_card("DPI Quality", res['dpi'], "DPI")
                    with cols[2]:
                        ui_components.render_metric_card("Aspect Ratio", res['aspect_ratio_str'], "")
                        
                    st.write("")
                    
                    # Render dynamic DPI print-fidelity quality badge (Optimization 3)
                    ui_components.render_dpi_badge(res.get("dpi", 72))
                    
                    # Compliance status
                    ui_components.render_status_alert(res.get("is_ready", False))
                        
                    st.markdown("<h6 class='fw-bold text-dark mb-3'>Findings & Recommendations:</h6>", unsafe_allow_html=True)
                    for rec in res.get("recommendations", []):
                        ui_components.render_recommendation_item(rec)
                    
                    st.write("")
                    if st.button("Next: Mockups", key="step1_next_btn", type="primary", width="stretch"):
                        st.session_state.wizard_step = 2
                        st.rerun()

        # STEP 2: MOCKUPS & GRAPHICS
        elif st.session_state.wizard_step == 2:
            st.markdown("#### Mockups")
            local_mockup_files = [f for f in os.listdir(mockup_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            col_mock_opts, col_mock_pre = st.columns([2, 3])
            
            with col_mock_opts:
                with st.container(border=True):
                    st.markdown("##### 1. Setup & Configure Assets")
                    
                    uploaded_mockup_files = st.file_uploader(
                        "Upload custom mockup templates (.jpg, .png)",
                        type=["jpg", "jpeg", "png"],
                        accept_multiple_files=True,
                        key="mockup_pack_uploader"
                    )
                    
                    if uploaded_mockup_files:
                        for file in uploaded_mockup_files:
                            path = os.path.join(mockup_dir, file.name)
                            with open(path, "wb") as f:
                                f.write(file.getbuffer())
                        local_mockup_files = [f for f in os.listdir(mockup_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    
                    with st.expander("Selection: Mockup Templates"):
                        if local_mockup_files:
                            selected_mockups = st.multiselect(
                                "Select Mockup Base Files:",
                                options=local_mockup_files,
                                default=local_mockup_files[:1] if local_mockup_files else []
                            )
                        else:
                            st.warning("No mockup templates found in brand folder. Upload some above.")
                            selected_mockups = []
                            
                    with st.expander("Settings: Artwork Sizing & Position"):
                        default_pos = config["mockup_overlay_defaults"].get(selected_product, {"center_x": 0.50, "center_y": 0.45, "width_fraction": 0.35})
                        offset_x = st.slider("Center X (Horizontal Position)", 0.0, 1.0, float(default_pos["center_x"]), 0.01)
                        offset_y = st.slider("Center Y (Vertical Position)", 0.0, 1.0, float(default_pos["center_y"]), 0.01)
                        scale_art = st.slider("Artwork Size (Relative width scale)", 0.05, 1.0, float(default_pos["width_fraction"]), 0.01)
                        position_config = {
                            "center_x": offset_x,
                            "center_y": offset_y,
                            "width_fraction": scale_art
                        }
                        
                    with st.expander("Settings: Watermark & Anti-Theft"):
                        apply_wm = st.checkbox("Enable logo watermark overlay", value=True if logo_path else False)
                        wm_opacity = st.slider("Watermark Logo Opacity", 0.05, 0.50, float(config["brand"]["default_alpha"]), 0.01)
                        
                    with st.expander("Settings: Informative Graphics List"):
                        gen_download = st.checkbox("Instant Download Infographic", value=True)
                        gen_license = st.checkbox("Commercial License Infographic", value=True)
                        gen_sizing = st.checkbox("File Sizing & Specification Card", value=True)
                        
                    st.write("")
                    generate_assets_btn = st.button("Generate Asset Pack", type="primary", width="stretch")
                    
                st.write("")
                if st.button("Next: Listing Copy", key="step2_next_btn", type="primary", width="stretch"):
                    st.session_state.wizard_step = 3
                    st.rerun()
                    
            with col_mock_pre:
                if generate_assets_btn:
                    generated_images = {}
                    
                    if selected_mockups:
                        for mock_filename in selected_mockups:
                            m_path = os.path.join(mockup_dir, mock_filename)
                            try:
                                mockup_res = image_generator.composite_mockup(
                                    st.session_state.artwork_file,
                                    m_path,
                                    position_config,
                                    logo_path=logo_path if apply_wm else None,
                                    logo_opacity=wm_opacity
                                )
                                name = f"mockup_{os.path.splitext(mock_filename)[0]}.jpg"
                                generated_images[name] = mockup_res
                            except Exception as e:
                                st.error(f"Error generating mockup {mock_filename}: {e}")
                                
                    if gen_download:
                        img_dl = image_generator.generate_instant_download_graphic(theme_config, logo_path=logo_path if apply_wm else None)
                        generated_images["infographic_instant_download.jpg"] = img_dl
                        
                    if gen_license:
                        img_lic = image_generator.generate_commercial_license_graphic(theme_config, logo_path=logo_path if apply_wm else None)
                        generated_images["infographic_commercial_license.jpg"] = img_lic
                        
                    if gen_sizing:
                        res_data = st.session_state.analysis_results or analyzer.analyze_artwork(st.session_state.artwork_file, selected_product)
                        p_name = product_defs[selected_product]["name"]
                        img_sz = image_generator.generate_sizing_graphic(
                            theme_config,
                            p_name,
                            res_data["width"],
                            res_data["height"],
                            res_data["dpi"],
                            logo_path=logo_path if apply_wm else None
                        )
                        generated_images["infographic_sizing_specs.jpg"] = img_sz
                        
                    if generated_images:
                        temp_zip_path = tempfile.mktemp(suffix=".zip")
                        with zipfile.ZipFile(temp_zip_path, 'w') as zf:
                            for img_name, img_obj in generated_images.items():
                                temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                                img_obj.save(temp_img.name, "JPEG", quality=90)
                                temp_img.close()
                                zf.write(temp_img.name, arcname=img_name)
                                os.unlink(temp_img.name)
                                
                        with st.container(border=True):
                            st.markdown("##### 📥 Download Pack")
                            with open(temp_zip_path, "rb") as zfile:
                                st.download_button(
                                    label="📥 Download Complete Asset Pack (.ZIP)",
                                    data=zfile.read(),
                                    file_name="etsy_listing_assets.zip",
                                    mime="application/zip",
                                    type="primary"
                                )
                                
                        # Render mockup previews in a 2-column layout grid (Optimization 3)
                        img_items = list(generated_images.items())
                        for row_idx in range(0, len(img_items), 2):
                            cols_pre = st.columns(2)
                            for col_idx in range(2):
                                item_idx = row_idx + col_idx
                                if item_idx < len(img_items):
                                    img_name, img_obj = img_items[item_idx]
                                    with cols_pre[col_idx]:
                                        with st.container(border=True):
                                            st.markdown(f"<p class='small text-muted mb-2 text-truncate' style='font-family: monospace;'>{img_name}</p>", unsafe_allow_html=True)
                                            st.image(img_obj, width="stretch")
                    else:
                        st.info("Select mockups or infographics to generate items.")
                else:
                    st.markdown("""
                    <div class="alert alert-light border border-light-subtle shadow-sm rounded-4 p-4 text-center">
                        <p class="mb-0 text-secondary">Configure mockups on the left and click 'Generate Asset Pack'.</p>
                    </div>
                    """, unsafe_allow_html=True)

        # STEP 3: SEO & LISTING DETAILS
        elif st.session_state.wizard_step == 3:
            st.markdown("#### Listing Copy")
            prod_name = product_defs[selected_product]["name"]
            
            with st.container(border=True):
                col_gen_btn, col_gen_info = st.columns([1, 2])
                with col_gen_btn:
                    run_gemini = st.button("Generate SEO Details (Gemini AI)", type="primary")
                with col_gen_info:
                    st.markdown(f"Generate metadata specifically target-tailored for a **{prod_name}**.")
                    
            if run_gemini:
                with st.spinner("Analyzing artwork details and drafting copy..."):
                    st.session_state.etsy_copy = listing_generator.generate_etsy_listing(
                        st.session_state.artwork_file,
                        api_key=api_key,
                        product_type=prod_name
                    )
                    
            if st.session_state.etsy_copy:
                copy_data = st.session_state.etsy_copy
                safety_warnings = copy_data.get("safety_warnings", [])
                if safety_warnings:
                    with st.container(border=True):
                        st.markdown("##### Seller Safety Review")
                        for warning in safety_warnings:
                            st.warning(warning)

                col_copy_left, col_copy_right = st.columns([1, 1])
                
                with col_copy_left:
                    with st.container(border=True):
                        st.markdown("##### 📌 Title & Tags")
                        title_text = st.text_input("Title (max 140 chars)", value=copy_data.get("title", ""), max_chars=140)
                        st.caption(f"Character count: {len(title_text)}/140")
                        
                        st.markdown("<hr class='my-4 border-light-subtle'>", unsafe_allow_html=True)
                        st.markdown("###### SEO Search Tags (13 tags)")
                        tags = copy_data.get("tags", [])
                        
                        # Generate inline badges nicely using custom Bootstrap badge rules
                        tag_badges = "".join([f"<span class='badge rounded-pill bg-light text-dark border border-secondary-subtle px-3 py-2 m-1 fw-medium fs-6 badge-etsy'>{tag}</span>" for tag in tags])
                        st.markdown(f"<div class='d-flex flex-wrap mb-3'>{tag_badges}</div>", unsafe_allow_html=True)
                        
                        st.text_input("Tags (comma-separated copy list)", value=", ".join(tags))
                        st.markdown("<hr class='my-4 border-light-subtle'>", unsafe_allow_html=True)
                        st.text_input("Suggested Materials", value=", ".join(copy_data.get("materials", [])))
                        
                with col_copy_right:
                    with st.container(border=True):
                        st.markdown("##### 📝 Description Text")
                        desc_text = st.text_area("Description details", value=copy_data.get("description", ""), height=400)
                        st.success("SEO copy generated! Double click input fields to copy values into your Etsy listing.")
            else:
                st.markdown("""
                <div class="alert alert-light border border-light-subtle shadow-sm rounded-4 p-4 text-center">
                    <p class="mb-0 text-secondary">Click the generate button above to write your Etsy SEO details.</p>
                </div>
                """, unsafe_allow_html=True)

