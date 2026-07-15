import os
import glob
import math
import numpy as np
from PIL import Image, ImageFilter
import cv2
from etsytools.paths import find_model_file

try:
    from ultralytics import YOLO
except ImportError:
    pass

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def split_image(input_path, output_dir, grid):
    rows, cols = map(int, grid.split('x'))
    img = Image.open(input_path)
    width, height = img.size
    
    tile_width = width // cols
    tile_height = height // rows
    
    ensure_dir(output_dir)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    for r in range(rows):
        for c in range(cols):
            left = c * tile_width
            top = r * tile_height
            right = (c + 1) * tile_width
            bottom = (r + 1) * tile_height
            
            if c == cols - 1: right = width
            if r == rows - 1: bottom = height
                
            box = (left, top, right, bottom)
            tile = img.crop(box)
            
            out_path = os.path.join(output_dir, f"{base_name}_{r+1}x{c+1}.png")
            tile.save(out_path)
            print(f"Saved: {out_path}")

def resize_images(input_dir, output_dir, scale):
    ensure_dir(output_dir)
    pattern = os.path.join(input_dir, "*.*")
    
    for filepath in glob.glob(pattern):
        if not os.path.isfile(filepath): continue
        try:
            img = Image.open(filepath)
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            out_path = os.path.join(output_dir, os.path.basename(filepath))
            resized.save(out_path)
            print(f"Resized and saved: {out_path}")
        except Exception as e:
            pass

def crop_images(input_dir, output_dir, target_width, target_height):
    ensure_dir(output_dir)
    pattern = os.path.join(input_dir, "*.*")
    
    for filepath in glob.glob(pattern):
        if not os.path.isfile(filepath): continue
        try:
            img = Image.open(filepath)
            left = (img.width - target_width) / 2
            top = (img.height - target_height) / 2
            right = (img.width + target_width) / 2
            bottom = (img.height + target_height) / 2
            
            cropped = img.crop((left, top, right, bottom))
            out_path = os.path.join(output_dir, os.path.basename(filepath))
            cropped.save(out_path)
            print(f"Cropped and saved: {out_path}")
        except Exception as e:
            pass

def fastsam_remove_background(filepath):
    model = YOLO(str(find_model_file("FastSAM-s.pt")))
    results = model(filepath, retina_masks=True, conf=0.4)
    result = results[0]
    
    img_pil = Image.open(filepath).convert("RGBA")
    
    if result.masks is None:
        return img_pil
        
    np_img = np.array(img_pil)
    masks = result.masks.data.cpu().numpy()
    
    # Combine all masks found to extract the full object
    combined_mask = np.zeros(np_img.shape[:2], dtype=np.float32)
    for mask in masks:
        if mask.shape != np_img.shape[:2]:
            mask = cv2.resize(mask, (np_img.shape[1], np_img.shape[0]), interpolation=cv2.INTER_LINEAR)
        combined_mask = np.maximum(combined_mask, mask)
        
    mask_uint8 = (combined_mask * 255).astype(np.uint8)
    kernel = np.ones((3, 3), np.uint8)
    mask_uint8 = cv2.dilate(mask_uint8, kernel, iterations=1)
    item_alpha = cv2.GaussianBlur(mask_uint8, (3, 3), 0)
    
    item_rgba = np_img.copy()
    item_rgba[:, :, 3] = np.minimum(item_rgba[:, :, 3], item_alpha)
    
    return Image.fromarray(item_rgba)

def remove_background(input_dir):
    output_dir = os.path.join(input_dir, "Results")
    ensure_dir(output_dir)
    pattern = os.path.join(input_dir, "*.*")
    
    for filepath in glob.glob(pattern):
        if not os.path.isfile(filepath): continue
        try:
            print(f"Removing background for {os.path.basename(filepath)} with FastSAM...")
            out = fastsam_remove_background(filepath)
            
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            out_path = os.path.join(output_dir, f"{base_name}_nobg.png")
            out.save(out_path, "PNG")
            print(f"Removed background and saved: {out_path}")
        except Exception as e:
            print(f"Failed processing {filepath}: {e}")

def format_clipart_batch(input_dir):
    output_dir = os.path.join(input_dir, "Results")
    ensure_dir(output_dir)
    pattern = os.path.join(input_dir, "*.*")
    
    for filepath in glob.glob(pattern):
        if not os.path.isfile(filepath): continue
        try:
            print(f"Formatting {os.path.basename(filepath)}...")
            
            img_nobg = fastsam_remove_background(filepath)
            
            bbox = img_nobg.getbbox()
            if bbox:
                img_nobg = img_nobg.crop(bbox)
            
            target_size = 3000
            max_dim = 2850
            width, height = img_nobg.size
            
            if width > height:
                new_width = max_dim
                new_height = int(height * (max_dim / width))
            else:
                new_height = max_dim
                new_width = int(width * (max_dim / height))
                
            img_resized = img_nobg.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
            
            paste_x = (target_size - new_width) // 2
            paste_y = (target_size - new_height) // 2
            
            canvas.paste(img_resized, (paste_x, paste_y), img_resized)
            
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            out_path = os.path.join(output_dir, f"{base_name}_clipart.png")
            canvas.save(out_path, "PNG", dpi=(300, 300))
            print(f"Saved formatted clipart: {out_path}")
            
        except Exception as e:
            print(f"Failed processing {filepath}: {e}")

def init_realesrgan():
    import urllib.request
    import zipfile
    import subprocess
    
    # Download portable RealESRGAN ncnn vulkan executable
    engine_dir = os.path.join(os.path.dirname(__file__), 'realesrgan_engine')
    exe_path = os.path.join(engine_dir, 'realesrgan-ncnn-vulkan.exe')
    
    if not os.path.exists(exe_path):
        ensure_dir(engine_dir)
        print("Downloading Portable RealESRGAN Engine (this only happens once)...")
        zip_path = os.path.join(engine_dir, 'realesrgan.zip')
        urllib.request.urlretrieve('https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip', zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(engine_dir)
        os.remove(zip_path)
    
    return exe_path

def auto_process_sheet(input_path, bg_type='transparent', canvas_color='transparent'):
    input_dir = os.path.dirname(os.path.abspath(input_path))
    output_dir = os.path.join(input_dir, "Split")
    ensure_dir(output_dir)
    
    bg_color = (0, 0, 0, 0)
    if canvas_color == 'black':
        bg_color = (0, 0, 0, 255)
    elif canvas_color == 'white':
        bg_color = (255, 255, 255, 255)
    elif canvas_color.startswith('#'):
        h = canvas_color.lstrip('#')
        if len(h) == 6:
            bg_color = tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    
    print(f"Auto-processing sheet {os.path.basename(input_path)} using Heavy AI...")
    
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Error: Missing ultralytics. Run pip install -r requirements.txt")
        return
        
    print("Loading AI Segmentation Model (FastSAM)...")
    model = YOLO(str(find_model_file("FastSAM-s.pt")))
    
    print("Running segmentation...")
    results = model(input_path, retina_masks=True, conf=0.4)
    result = results[0]
    
    if result.masks is None:
        print("No distinct objects found on the sheet by AI.")
        return
        
    img_pil = Image.open(input_path).convert("RGBA")
    np_img = np.array(img_pil)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    masks = result.masks.data.cpu().numpy()
    boxes = result.boxes.xyxy.cpu().numpy().astype(int)
    
    print(f"Found {len(masks)} distinct items on the sheet using AI.")
    
    realesrgan_exe = None
    try:
        realesrgan_exe = init_realesrgan()
        print("RealESRGAN portable engine ready.")
    except Exception as e:
        print(f"Could not setup RealESRGAN engine: {e}. Will fallback to basic resizing.")
    
    import subprocess
    
    for idx, (mask, box) in enumerate(zip(masks, boxes)):
        x1, y1, x2, y2 = box
        
        if mask.shape != np_img.shape[:2]:
            mask = cv2.resize(mask, (np_img.shape[1], np_img.shape[0]), interpolation=cv2.INTER_LINEAR)
            
        mask_uint8 = (mask * 255).astype(np.uint8)
        kernel = np.ones((3, 3), np.uint8)
        mask_uint8 = cv2.dilate(mask_uint8, kernel, iterations=1)
        item_alpha = cv2.GaussianBlur(mask_uint8, (3, 3), 0)
        
        item_rgba = np_img.copy()
        item_rgba[:, :, 3] = np.minimum(item_rgba[:, :, 3], item_alpha)
        
        item_crop = Image.fromarray(item_rgba).crop((x1, y1, x2, y2))
        
        bbox = item_crop.getbbox()
        if bbox:
            item_crop = item_crop.crop(bbox)
            
        # Apply Portable RealESRGAN AI Upscaling
        if realesrgan_exe is not None:
            print(f"Upscaling item {idx+1} with Portable RealESRGAN...")
            temp_in = os.path.join(output_dir, "temp_in.png")
            temp_out = os.path.join(output_dir, "temp_out.png")
            item_crop.save(temp_in, "PNG")
            try:
                subprocess.run([realesrgan_exe, '-i', temp_in, '-o', temp_out, '-n', 'realesrgan-x4plus', '-s', '4'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(temp_out):
                    item_crop = Image.open(temp_out).convert("RGBA")
                    os.remove(temp_out)
                os.remove(temp_in)
            except Exception as e:
                print(f"Upscale failed for item {idx+1}: {e}")
        
        target_size = 3000
        max_dim = 2850
        width, height = item_crop.size
        
        if width > height:
            new_width = max_dim
            new_height = int(height * (max_dim / width))
        else:
            new_height = max_dim
            new_width = int(width * (max_dim / height))
            
        if new_width != width or new_height != height:
            img_resized = item_crop.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            img_resized = item_crop
            
        canvas = Image.new("RGBA", (target_size, target_size), bg_color)
        
        paste_x = (target_size - img_resized.width) // 2
        paste_y = (target_size - img_resized.height) // 2
        
        canvas.paste(img_resized, (paste_x, paste_y), img_resized if img_resized.mode == 'RGBA' else None)
        
        out_path = os.path.join(output_dir, f"{base_name}_{idx+1}.png")
        canvas.save(out_path, "PNG", dpi=(300, 300))
        print(f"Processed item {idx+1}: {out_path}")
        
    print(f"All {len(masks)} items formatted into: {output_dir}")


def add_drop_shadow(image, offset=(15, 15), background_color=(0, 0, 0, 100), blur_radius=15):
    if image.mode != "RGBA":
        image = image.convert("RGBA")
        
    shadow = Image.new("RGBA", image.size, color=background_color)
    shadow.putalpha(image.getchannel('A'))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))
    
    canvas_width = image.width + abs(offset[0]) + blur_radius * 2
    canvas_height = image.height + abs(offset[1]) + blur_radius * 2
    canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
    
    shadow_x = blur_radius + (offset[0] if offset[0] > 0 else 0)
    shadow_y = blur_radius + (offset[1] if offset[1] > 0 else 0)
    canvas.paste(shadow, (shadow_x, shadow_y), shadow)
    
    orig_x = blur_radius - (offset[0] if offset[0] < 0 else 0)
    orig_y = blur_radius - (offset[1] if offset[1] < 0 else 0)
    canvas.paste(image, (orig_x, orig_y), image)
    
    return canvas

def create_showcase_mockup(input_dir, background_path, output_path=None):
    print(f"Generating Showcase Mockup from {input_dir}...")
    
    if background_path and os.path.exists(background_path):
        bg = Image.open(background_path).convert("RGBA")
    else:
        print("No custom background provided. Generating a clean minimalist canvas automatically...")
        bg = Image.new("RGBA", (3000, 2000), (245, 245, 245, 255))
        
    pattern = os.path.join(input_dir, "*.png")
    image_paths = [p for p in glob.glob(pattern) if os.path.isfile(p)]
    
    if not image_paths:
        print("No PNG images found in input folder.")
        return
        
    images = []
    for p in image_paths:
        try:
            img = Image.open(p).convert("RGBA")
            images.append(img)
        except:
            pass
            
    num_images = len(images)
    print(f"Loaded {num_images} images for the showcase.")
    
    cols = math.ceil(math.sqrt(num_images))
    rows = math.ceil(num_images / cols)
    
    margin_x = int(bg.width * 0.1)
    margin_y = int(bg.height * 0.1)
    
    available_width = bg.width - (margin_x * 2)
    available_height = bg.height - (margin_y * 2)
    
    cell_w = available_width // cols
    cell_h = available_height // rows
    
    target_w = int(cell_w * 0.9)
    target_h = int(cell_h * 0.9)
    
    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx >= num_images:
                break
                
            img = images[idx]
            
            scale = min(target_w / img.width, target_h / img.height)
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            cell_x = margin_x + (c * cell_w)
            cell_y = margin_y + (r * cell_h)
            
            paste_x = cell_x + (cell_w - resized.width) // 2
            paste_y = cell_y + (cell_h - resized.height) // 2
            
            bg.paste(resized, (paste_x, paste_y), resized)
            idx += 1
            
    if not output_path:
        output_path = os.path.join(input_dir, "Bundle_Showcase.png")
        
    bg = bg.convert("RGB")
    bg.save(output_path, "PNG", dpi=(300,300))
    print(f"Showcase Mockup saved to: {output_path}")

def _apply_hue_shift(img, hue_shift_degrees):
    img_array = np.array(img.convert('RGBA'))
    r, g, b, a = img_array.T
    
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0
    
    maxc = np.maximum(np.maximum(r_norm, g_norm), b_norm)
    minc = np.minimum(np.minimum(r_norm, g_norm), b_norm)
    v = maxc
    
    deltac = maxc - minc
    s = np.zeros_like(maxc)
    h = np.zeros_like(maxc)
    
    mask = maxc > 0
    s[mask] = deltac[mask] / maxc[mask]
    
    rc = np.zeros_like(maxc)
    gc = np.zeros_like(maxc)
    bc = np.zeros_like(maxc)
    
    mask2 = deltac > 0
    rc[mask2] = (maxc[mask2] - r_norm[mask2]) / deltac[mask2]
    gc[mask2] = (maxc[mask2] - g_norm[mask2]) / deltac[mask2]
    bc[mask2] = (maxc[mask2] - b_norm[mask2]) / deltac[mask2]
    
    mask_r = (maxc == r_norm) & mask2
    mask_g = (maxc == g_norm) & mask2
    mask_b = (maxc == b_norm) & mask2
    
    h[mask_r] = bc[mask_r] - gc[mask_r]
    h[mask_g] = 2.0 + rc[mask_g] - bc[mask_g]
    h[mask_b] = 4.0 + gc[mask_b] - rc[mask_b]
    
    h = (h / 6.0) % 1.0
    
    hue_shift_normalized = hue_shift_degrees / 360.0
    h = (h + hue_shift_normalized) % 1.0
    
    i = (h * 6.0).astype(int)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    
    conditions = [(i == 0), (i == 1), (i == 2), (i == 3), (i == 4), (i == 5)]
    
    rgb_r = np.select(conditions, [v, q, p, p, t, v])
    rgb_g = np.select(conditions, [t, v, v, q, p, p])
    rgb_b = np.select(conditions, [p, p, t, v, v, q])
    
    out_img_array = np.zeros_like(img_array)
    out_img_array.T[0] = rgb_r * 255
    out_img_array.T[1] = rgb_g * 255
    out_img_array.T[2] = rgb_b * 255
    out_img_array.T[3] = a
    
    return Image.fromarray(out_img_array, 'RGBA')

def color_shift_interactive(input_path, output_dir):
    import tkinter as tk
    from tkinter import ttk
    from PIL import ImageTk
    
    img = Image.open(input_path).convert("RGBA")
    
    preview_size = (600, 600)
    img_preview = img.copy()
    img_preview.thumbnail(preview_size, Image.Resampling.LANCZOS)
    
    root = tk.Tk()
    root.title(f"Color Preview: {os.path.basename(input_path)}")
    
    current_shift = tk.DoubleVar(value=0)
    
    frame = ttk.Frame(root, padding="10")
    frame.pack(fill=tk.BOTH, expand=True)
    
    image_label = ttk.Label(frame)
    image_label.pack(pady=10)
    
    def update_preview(*args):
        shift = current_shift.get()
        shifted = _apply_hue_shift(img_preview, shift)
        tk_img = ImageTk.PhotoImage(shifted)
        image_label.configure(image=tk_img)
        image_label.image = tk_img
        
    slider = ttk.Scale(frame, from_=-180, to=180, orient=tk.HORIZONTAL, variable=current_shift, command=update_preview)
    slider.pack(fill=tk.X, padx=20, pady=10)
    
    value_label = ttk.Label(frame, textvariable=current_shift)
    value_label.pack()
    
    def save_and_close():
        shift = current_shift.get()
        print(f"Applying {int(shift)} degree shift to original image...")
        final_img = _apply_hue_shift(img, shift)
        
        ensure_dir(output_dir)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        out_path = os.path.join(output_dir, f"{base_name}_hue{int(shift)}.png")
        
        final_img.save(out_path, "PNG")
        print(f"Saved: {out_path}")
        root.destroy()
        
    save_btn = ttk.Button(frame, text="Save High-Res Image", command=save_and_close)
    save_btn.pack(pady=10)
    
    update_preview()
    root.mainloop()


def upscale_and_resize_general_image(input_path, target_width, target_height, target_dpi, output_path):
    print(f"Upscaling general image {os.path.basename(input_path)} to {target_width}x{target_height} at {target_dpi} DPI...")
    
    img = Image.open(input_path).convert("RGBA")
    
    # Try initializing RealESRGAN
    realesrgan_exe = None
    try:
        realesrgan_exe = init_realesrgan()
    except Exception as e:
        print(f"Could not setup RealESRGAN engine: {e}. Will fallback to basic resizing.")
        
    if realesrgan_exe is not None:
        import subprocess
        output_dir = os.path.dirname(output_path)
        temp_in = os.path.join(output_dir, "temp_upscale_in.png")
        temp_out = os.path.join(output_dir, "temp_upscale_out.png")
        img.save(temp_in, "PNG")
        try:
            subprocess.run([realesrgan_exe, '-i', temp_in, '-o', temp_out, '-n', 'realesrgan-x4plus', '-s', '4'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(temp_out):
                img = Image.open(temp_out).convert("RGBA")
                os.remove(temp_out)
            if os.path.exists(temp_in):
                os.remove(temp_in)
        except Exception as e:
            print(f"AI Upscale failed: {e}. Falling back to basic resizing.")
            if os.path.exists(temp_in):
                os.remove(temp_in)
            if os.path.exists(temp_out):
                os.remove(temp_out)
                
    # Resize to exact target size
    img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    # Save with custom DPI settings
    img_resized.save(output_path, "PNG", dpi=(target_dpi, target_dpi))
    print(f"Upscaled image successfully saved to: {output_path}")
