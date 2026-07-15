import os
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from etsytools.paths import BRAND_ASSETS_DIR

def download_font_if_missing():
    """No-op font hook.

    The previous implementation downloaded Montserrat from stale GitHub URLs,
    which now return 404s. For a local tool, avoiding runtime font downloads is
    safer and quieter. Place Montserrat files in brand_assets/fonts manually if
    you want that exact brand font; otherwise get_font falls back to system
    fonts.
    """
    return

# Safe Font Loader
def get_font(font_style="Regular", size=40):
    """Safely loads Montserrat font, falling back to system arial or PIL default."""
    download_font_if_missing()
    
    font_name = f"Montserrat-{font_style}.ttf"
    font_path = os.path.join(str(BRAND_ASSETS_DIR / "fonts"), font_name)
    
    try:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
    except Exception as e:
        print(f"Error loading Montserrat: {e}")
        
    try:
        return ImageFont.truetype("arial.ttf", size)
    except IOError:
        win_dir = os.environ.get("WINDIR", "C:\\Windows")
        win_font = os.path.join(win_dir, "Fonts", "arial.ttf")
        if os.path.exists(win_font):
            try:
                return ImageFont.truetype(win_font, size)
            except:
                pass
        return ImageFont.load_default()

def draw_premium_card(canvas, box, radius=20, fill_color="#FFFFFF", border_color="#E6DFD5", shadow_offset=(0, 10), shadow_blur=20, shadow_color=(0, 0, 0, 15)):
    """
    Draws a beautiful rounded rectangle card with a soft blurred drop shadow.
    - box is [x1, y1, x2, y2]
    """
    x1, y1, x2, y2 = box
    
    # 1. Create a transparent layer for the shadow
    shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    
    # Draw the shadow shape offset
    sx1 = x1 + shadow_offset[0]
    sy1 = y1 + shadow_offset[1]
    sx2 = x2 + shadow_offset[0]
    sy2 = y2 + shadow_offset[1]
    s_draw.rounded_rectangle([sx1, sy1, sx2, sy2], radius=radius, fill=shadow_color)
    
    # Blur the shadow
    blurred_shadow = shadow_layer.filter(ImageFilter.GaussianBlur(shadow_blur))
    
    # Composite the shadow onto the main canvas
    canvas.alpha_composite(blurred_shadow)
    
    # 2. Draw the actual card on the main canvas
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill_color, outline=border_color, width=2)
    return draw

def apply_watermark(base_img, logo_path, position="bottom-right", opacity=0.15, padding=40, scale=0.12):
    """
    Applies a brand logo as a semi-transparent watermark on a base image.
    """
    if not logo_path or not os.path.exists(logo_path):
        return base_img
        
    try:
        logo = Image.open(logo_path).convert("RGBA")
        base_w, base_h = base_img.size
        
        logo_w = int(base_w * scale)
        logo_h = int(logo_w * (logo.height / logo.width))
        logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        logo.putalpha(alpha)
        
        if position == "top-left":
            x, y = padding, padding
        elif position == "top-right":
            x, y = base_w - logo_w - padding, padding
        elif position == "bottom-left":
            x, y = padding, base_h - logo_h - padding
        elif position == "center":
            x, y = (base_w - logo_w) // 2, (base_h - logo_h) // 2
        else:  # default bottom-right
            x, y = base_w - logo_w - padding, base_h - logo_h - padding
            
        base_img_rgba = base_img.convert("RGBA")
        base_img_rgba.alpha_composite(logo, dest=(x, y))
        return base_img_rgba.convert("RGB")
    except Exception as e:
        print(f"Error applying watermark: {e}")
        return base_img

def composite_mockup(artwork_path, mockup_path, position_config, logo_path=None, logo_opacity=0.15):
    """
    Overlays PNG artwork onto a base mockup image based on positional configurations.
    """
    try:
        mockup = Image.open(mockup_path).convert("RGBA")
        artwork = Image.open(artwork_path).convert("RGBA")
        
        mock_w, mock_h = mockup.size
        
        target_w = int(mock_w * position_config.get("width_fraction", 0.35))
        target_h = int(target_w * (artwork.height / artwork.width))
        
        artwork_resized = artwork.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        center_x = int(mock_w * position_config.get("center_x", 0.50))
        center_y = int(mock_h * position_config.get("center_y", 0.45))
        
        x = center_x - (target_w // 2)
        y = center_y - (target_h // 2)
        
        mockup.alpha_composite(artwork_resized, dest=(x, y))
        
        result_img = mockup.convert("RGB")
        if logo_path:
            result_img = apply_watermark(result_img, logo_path, opacity=logo_opacity)
            
        return result_img
    except Exception as e:
        print(f"Error compositing mockup: {e}")
        raise e

def create_infographic_base(title_text, theme_config, size=(2000, 2000)):
    """
    Creates a baseline square canvas with double border and centered header.
    """
    bg_color = theme_config.get("bg_color", "#FAF8F5")
    text_color = theme_config.get("text_color", "#2C2C2C")
    accent_color = theme_config.get("accent_color", "#D4A373")
    border_color = theme_config.get("border_color", "#E6DFD5")
    
    # Create background canvas (RGBA for overlay composites)
    canvas = Image.new("RGBA", size, bg_color)
    draw = ImageDraw.Draw(canvas)
    
    # Draw double border for elegance
    draw.rectangle([20, 20, size[0] - 20, size[1] - 20], outline=border_color, width=4)
    draw.rectangle([35, 35, size[0] - 35, size[1] - 35], outline=accent_color, width=2)
    
    # Render main title
    font_title = get_font("Bold", size=70)
    
    text_len = draw.textlength(title_text, font=font_title)
    x = (size[0] - text_len) // 2
    draw.text((x, 140), title_text, fill=text_color, font=font_title)
    
    # Draw terracotta line under title
    line_w = 400
    draw.line(
        [(size[0] - line_w) // 2, 240, (size[0] + line_w) // 2, 240], 
        fill=accent_color, 
        width=4
    )
    
    return canvas, draw

def generate_instant_download_graphic(theme_config, logo_path=None):
    """
    Generates a high-quality "Instant Download" infographic.
    """
    canvas, draw = create_infographic_base("INSTANT DIGITAL DOWNLOAD", theme_config)
    text_color = theme_config.get("text_color", "#2C2C2C")
    accent_color = theme_config.get("accent_color", "#D4A373")
    muted_color = theme_config.get("muted_color", "#8D99AE")
    border_color = theme_config.get("border_color", "#E6DFD5")
    
    font_sub = get_font("Bold", size=42)
    font_body = get_font("Regular", size=32)
    font_step_title = get_font("Bold", size=36)
    
    # 1. Main Info Banner Card (Notice)
    draw_premium_card(canvas, [150, 320, 1850, 480], radius=15, fill_color="#FFFFFF", border_color=border_color)
    
    # Text on Main Banner
    notice_text = "⚡ DIGITAL FILE ONLY — NO PHYSICAL ITEM SHIPPED"
    notice_w = draw.textlength(notice_text, font=font_sub)
    draw.text(((2000 - notice_w) // 2, 355), notice_text, fill=accent_color, font=font_sub)
    
    notice_desc = "Get access to your printable files immediately after checking out."
    desc_w = draw.textlength(notice_desc, font=font_body)
    draw.text(((2000 - desc_w) // 2, 415), notice_desc, fill=muted_color, font=font_body)
    
    # 2. Four Steps Grid (Draw as separate cards)
    steps = [
        {"icon": "🛍️", "num": "1", "title": "Place Order", "desc": "Add this design to cart & check out."},
        {"icon": "💳", "num": "2", "title": "Confirm", "desc": "Etsy processes your payment instantly."},
        {"icon": "📥", "num": "3", "title": "Get Link", "desc": "Receive download link in your inbox."},
        {"icon": "🖨️", "num": "4", "title": "Print & Sell", "desc": "Make shirts, mugs, bags, and more!"}
    ]
    
    card_w = 360
    card_h = 420
    start_x = 150
    gap = 70
    
    for i, step in enumerate(steps):
        x = start_x + (i * (card_w + gap))
        y = 560
        
        # Draw step card
        draw_premium_card(canvas, [x, y, x + card_w, y + card_h], radius=20, fill_color="#FFFFFF", border_color=border_color)
        
        # Icon inside card
        icon_w = draw.textlength(step["icon"], font=get_font("Regular", size=70))
        draw.text((x + (card_w - icon_w) // 2, y + 40), step["icon"], fill=text_color, font=get_font("Regular", size=70))
        
        # Step Number badge
        num_str = f"STEP {step['num']}"
        num_w = draw.textlength(num_str, font=get_font("Bold", size=24))
        draw.text((x + (card_w - num_w) // 2, y + 140), num_str, fill=accent_color, font=get_font("Bold", size=24))
        
        # Step Title
        title_w = draw.textlength(step["title"], font=font_step_title)
        draw.text((x + (card_w - title_w) // 2, y + 185), step["title"], fill=text_color, font=font_step_title)
        
        # Step Description (Wrap text into multiple lines)
        desc_words = step["desc"].split(" ")
        lines = []
        curr_line = ""
        for word in desc_words:
            test_line = curr_line + (" " if curr_line else "") + word
            if draw.textlength(test_line, font=font_body) < (card_w - 40):
                curr_line = test_line
            else:
                lines.append(curr_line)
                curr_line = word
        if curr_line:
            lines.append(curr_line)
            
        for line_idx, line in enumerate(lines[:3]):
            line_w = draw.textlength(line, font=font_body)
            draw.text((x + (card_w - line_w) // 2, y + 250 + (line_idx * 45)), line, fill=muted_color, font=font_body)
            
        # Draw dynamic arrow connectors (minimalist thin lines)
        if i < len(steps) - 1:
            arrow_start_x = x + card_w + 10
            arrow_end_x = arrow_start_x + gap - 20
            arrow_y = y + (card_h // 2)
            draw.line([arrow_start_x, arrow_y, arrow_end_x, arrow_y], fill=border_color, width=3)
            draw.line([arrow_end_x - 12, arrow_y - 12, arrow_end_x, arrow_y], fill=border_color, width=3)
            draw.line([arrow_end_x - 12, arrow_y + 12, arrow_end_x, arrow_y], fill=border_color, width=3)

    # 3. Footer Bullet Cards
    footer_y = 1060
    draw_premium_card(canvas, [150, footer_y, 1850, footer_y + 190], radius=15, fill_color="#FFFFFF", border_color=border_color)
    
    bullets = [
        "★ Compatible with: Sublimation, Heat Press, Cricut, Silhouette, DTG printing.",
        "★ Format: High-Resolution transparency PNG (clean edges, no watermarks)."
    ]
    for idx, bullet in enumerate(bullets):
        draw.text((200, footer_y + 40 + (idx * 60)), bullet, fill=text_color, font=font_body)
        
    result_img = canvas.convert("RGB")
    if logo_path:
        result_img = apply_watermark(result_img, logo_path, opacity=0.3, position="bottom-right", padding=80)
        
    return result_img

def generate_commercial_license_graphic(theme_config, logo_path=None):
    """
    Generates a high-quality "Commercial License & Terms" infographic.
    """
    canvas, draw = create_infographic_base("COMMERCIAL LICENSE & TERMS", theme_config)
    text_color = theme_config.get("text_color", "#2C2C2C")
    accent_color = theme_config.get("accent_color", "#D4A373")
    muted_color = theme_config.get("muted_color", "#8D99AE")
    border_color = theme_config.get("border_color", "#E6DFD5")
    
    font_box_title = get_font("Bold", size=40)
    font_body = get_font("Regular", size=32)
    
    box_w = 780
    box_h = 750
    
    # LEFT CARD: WHAT IS PERMITTED
    box1_x = 150
    box1_y = 330
    draw_premium_card(canvas, [box1_x, box1_y, box1_x + box_w, box1_y + box_h], radius=20, fill_color="#FFFFFF", border_color=border_color)
    
    # Header Accent for YES (soft green card top)
    header1_canvas = Image.new("RGBA", (box_w - 4, 100), (232, 245, 233, 255))
    canvas.paste(header1_canvas, (box1_x + 2, box1_y + 2))
    
    draw.text((box1_x + 50, box1_y + 28), "✓ WHAT IS ALLOWED", fill="#2E7D32", font=font_box_title)
    
    yes_rules = [
        "Create physical products (shirts, mugs, bags)",
        "Sell up to 100 physical goods per design",
        "Use for personal crafts, gifts & DIY projects",
        "Crop, rotate, resize, or flip to fit products",
        "Sublimation printing, screenprint, & HTV transfers"
    ]
    
    for i, rule in enumerate(yes_rules):
        y_pos = box1_y + 160 + (i * 115)
        # Checkmark Icon
        draw.text((box1_x + 50, y_pos), "✓", fill="#2E7D32", font=get_font("Bold", size=38))
        
        # Wrap rule text
        rule_words = rule.split(" ")
        lines = []
        curr_line = ""
        for word in rule_words:
            test_line = curr_line + (" " if curr_line else "") + word
            if draw.textlength(test_line, font=font_body) < (box_w - 140):
                curr_line = test_line
            else:
                lines.append(curr_line)
                curr_line = word
        if curr_line:
            lines.append(curr_line)
            
        for line_idx, line in enumerate(lines[:2]):
            draw.text((box1_x + 100, y_pos + (line_idx * 40)), line, fill=text_color, font=font_body)
            
    # RIGHT CARD: WHAT IS PROHIBITED
    box2_x = 1070
    box2_y = 330
    draw_premium_card(canvas, [box2_x, box2_y, box2_x + box_w, box2_y + box_h], radius=20, fill_color="#FFFFFF", border_color=border_color)
    
    # Header Accent for NO (soft red card top)
    header2_canvas = Image.new("RGBA", (box_w - 4, 100), (255, 235, 238, 255))
    canvas.paste(header2_canvas, (box2_x + 2, box2_y + 2))
    
    draw.text((box2_x + 50, box2_y + 28), "✗ WHAT IS PROHIBITED", fill="#C62828", font=font_box_title)
    
    no_rules = [
        "Resell, share, or redistribute the digital file",
        "Upload designs to POD (Printful, Redbubble, etc.)",
        "Give away files as freebies, bundles, or downloads",
        "Claim artwork copyrights or design as your own",
        "Convert to SVG vectors to resell digitally"
    ]
    
    for i, rule in enumerate(no_rules):
        y_pos = box2_y + 160 + (i * 115)
        # Cross Icon
        draw.text((box2_x + 50, y_pos), "✗", fill="#C62828", font=get_font("Bold", size=38))
        
        # Wrap rule text
        rule_words = rule.split(" ")
        lines = []
        curr_line = ""
        for word in rule_words:
            test_line = curr_line + (" " if curr_line else "") + word
            if draw.textlength(test_line, font=font_body) < (box_w - 140):
                curr_line = test_line
            else:
                lines.append(curr_line)
                curr_line = word
        if curr_line:
            lines.append(curr_line)
            
        for line_idx, line in enumerate(lines[:2]):
            draw.text((box2_x + 100, y_pos + (line_idx * 40)), line, fill=text_color, font=font_body)
            
    # Bottom Disclaimer Card
    disclaimer_y = 1140
    draw_premium_card(canvas, [150, disclaimer_y, 1850, disclaimer_y + 110], radius=15, fill_color="#FFFFFF", border_color=border_color)
    disclaimer_text = "⚠️ Notice: Purchase of this design does not transfer copyrights. All design rights remain reserved."
    disc_w = draw.textlength(disclaimer_text, font=font_body)
    draw.text(((2000 - disc_w) // 2, disclaimer_y + 35), disclaimer_text, fill=muted_color, font=font_body)
    
    result_img = canvas.convert("RGB")
    if logo_path:
        result_img = apply_watermark(result_img, logo_path, opacity=0.3, position="bottom-right", padding=80)
        
    return result_img

def generate_sizing_graphic(theme_config, product_name, width_px, height_px, dpi, logo_path=None):
    """
    Generates a custom "Size & Specifications" infographic for the design.
    """
    canvas, draw = create_infographic_base("FILE SPECIFICATIONS", theme_config)
    text_color = theme_config.get("text_color", "#2C2C2C")
    accent_color = theme_config.get("accent_color", "#D4A373")
    muted_color = theme_config.get("muted_color", "#8D99AE")
    border_color = theme_config.get("border_color", "#E6DFD5")
    
    font_val = get_font("Bold", size=48)
    font_label = get_font("Bold", size=32)
    font_desc = get_font("Regular", size=30)
    
    specs = [
        {"icon": "📐", "label": "FORMAT", "val": "Transparent PNG", "desc": "Background removed. High-fidelity colors print ready on any material color."},
        {"icon": "🖥️", "label": "RESOLUTION", "val": f"{width_px} x {height_px} PX", "desc": f"Extra large canvas resolution, ideal fit for physical {product_name} and apparel."},
        {"icon": "🎯", "label": "DPI QUALITY", "val": f"{dpi} DPI Print Output", "desc": "Meets professional print-on-demand standards. Zero blurriness, pixelation, or artifacts."},
        {"icon": "🔌", "label": "COMPATIBILITY", "val": "Sublimation & DIY Craft Ready", "desc": "Works perfectly with Cricut Design Space, Silhouette Studio, heat press, and screenprinting."}
    ]
    
    start_y = 320
    card_h = 200
    gap = 25
    
    for i, spec in enumerate(specs):
        y = start_y + (i * (card_h + gap))
        
        # Draw specification card
        draw_premium_card(canvas, [150, y, 1850, y + card_h], radius=15, fill_color="#FFFFFF", border_color=border_color)
        
        # Draw Icon circle badge
        draw.ellipse([190, y + 45, 300, y + 155], fill=accent_color)
        icon_w = draw.textlength(spec["icon"], font=get_font("Regular", size=48))
        draw.text((190 + (110 - icon_w) // 2, y + 68), spec["icon"], fill="#FFFFFF", font=get_font("Regular", size=48))
        
        # Spec Label (e.g. FORMAT)
        draw.text((340, y + 40), spec["label"], fill=muted_color, font=font_label)
        
        # Spec Value (e.g. Transparent PNG)
        draw.text((340, y + 90), spec["val"], fill=text_color, font=font_val)
        
        # Spec Description
        desc_words = spec["desc"].split(" ")
        lines = []
        curr_line = ""
        for word in desc_words:
            test_line = curr_line + (" " if curr_line else "") + word
            if draw.textlength(test_line, font=font_desc) < 1000:
                curr_line = test_line
            else:
                lines.append(curr_line)
                curr_line = word
        if curr_line:
            lines.append(curr_line)
            
        for line_idx, line in enumerate(lines[:2]):
            draw.text((780, y + 60 + (line_idx * 40)), line, fill=muted_color, font=font_desc)
            
    # Bottom Note
    note_y = 1240
    draw_premium_card(canvas, [150, note_y, 1850, note_y + 110], radius=15, fill_color="#FFFFFF", border_color=border_color)
    note_text = "★ High print fidelity guaranteed. Recommended for DTG, sublimation, and vinyl cut files."
    note_w = draw.textlength(note_text, font=get_font("Regular", size=32))
    draw.text(((2000 - note_w) // 2, note_y + 35), note_text, fill=text_color, font=get_font("Regular", size=32))
    
    result_img = canvas.convert("RGB")
    if logo_path:
        result_img = apply_watermark(result_img, logo_path, opacity=0.3, position="bottom-right", padding=80)
        
    return result_img
