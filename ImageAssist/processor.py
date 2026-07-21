import os
import glob
import math
import numpy as np
from PIL import Image, ImageFilter
Image.MAX_IMAGE_PIXELS = None
import cv2
from etsytools.paths import find_model_file

try:
    from ultralytics import YOLO
except ImportError:
    pass

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def ai_upscale(img_pil, model='realesrgan-x4plus', output_dir=None):
    """
    Shared RealESRGAN upscaling helper.
    Runs the portable ncnn-vulkan binary on img_pil (a PIL RGBA image) and
    returns the 4x upscaled PIL RGBA image.  If RealESRGAN is unavailable or
    fails, the original image is returned unchanged so callers can still
    fall back to LANCZOS for the final resize.

    Alpha handling: composites the image onto white before passing to the
    binary (which doesn't support transparency), then restores the original
    alpha mask scaled to the new dimensions.
    """
    import subprocess, tempfile
    from uuid import uuid4

    try:
        exe = init_realesrgan()
    except Exception as e:
        print(f"[RealESRGAN] Engine init failed: {e}. Falling back to LANCZOS.")
        return img_pil

    img_rgba = img_pil.convert('RGBA')
    alpha_channel = img_rgba.split()[3]

    # Composite onto white — the binary can't handle transparency
    white_bg = Image.new('RGB', img_rgba.size, (255, 255, 255))
    white_bg.paste(img_rgba, mask=alpha_channel)

    work_dir = output_dir or tempfile.gettempdir()
    uid = uuid4().hex
    temp_in  = os.path.join(work_dir, f'_resr_in_{uid}.png')
    temp_out = os.path.join(work_dir, f'_resr_out_{uid}.png')

    try:
        white_bg.save(temp_in, 'PNG')
        subprocess.run(
            [exe, '-i', temp_in, '-o', temp_out, '-n', model, '-s', '4'],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if not os.path.exists(temp_out):
            raise FileNotFoundError('RealESRGAN produced no output file.')

        upscaled_rgb = Image.open(temp_out).convert('RGB')
        # Restore alpha scaled to the new (4x) dimensions
        upscaled_alpha = alpha_channel.resize(upscaled_rgb.size, Image.Resampling.LANCZOS)
        result = upscaled_rgb.convert('RGBA')
        result.putalpha(upscaled_alpha)
        print(f"[RealESRGAN] Upscaled {img_pil.size} → {result.size} using {model}")
        return result
    except Exception as e:
        print(f"[RealESRGAN] Upscale failed: {e}. Falling back to LANCZOS.")
        return img_pil
    finally:
        for f in (temp_in, temp_out):
            if os.path.exists(f):
                try: os.remove(f)
                except Exception: pass

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
            img = Image.open(filepath).convert('RGBA')
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)

            # Use AI upscaling when growing the image
            if scale > 1.0:
                img = ai_upscale(img, output_dir=output_dir)

            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            out_path = os.path.join(output_dir, os.path.basename(filepath))
            resized.save(out_path)
            print(f"Resized and saved: {out_path}")
        except Exception as e:
            print(f"resize_images failed for {filepath}: {e}")

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

def remove_connected_background_color(img_pil, tolerance=30):
    img = img_pil.convert("RGBA")
    np_img = np.array(img)
    
    h, w, c = np_img.shape
    mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
    rgb_img = np_img[:, :, :3].copy()
    
    # We will perform flood fill from the 4 corners
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    for x, y in corners:
        # Skip if this corner is already transparent in the original
        if np_img[y, x, 3] == 0:
            continue
        cv2.floodFill(
            rgb_img, 
            mask, 
            (x, y), 
            newVal=(0, 255, 0), # Dummy fill color
            loDiff=(tolerance, tolerance, tolerance), 
            upDiff=(tolerance, tolerance, tolerance),
            flags=4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY
        )
    
    # Set alpha to 0 for all connected background pixels
    bg_mask = mask[1:-1, 1:-1] == 255
    np_img[bg_mask, 3] = 0
    return Image.fromarray(np_img)

def fastsam_remove_background(filepath):
    """
    Two-stage background removal:
      Stage 1 (primary): Corner flood-fill on the original image — reliable for
                         solid/plain backgrounds regardless of subject shape.
      Stage 2 (refiner): FastSAM segmentation mask applied only as a soft trim
                         on pixels that stage 1 already left semi-transparent,
                         so FastSAM can never destroy subject pixels.
    Falls back to the original image if either stage produces a fully transparent result.
    """
    basename = os.path.basename(filepath)
    img_pil = Image.open(filepath).convert("RGBA")
    orig_arr = np.array(img_pil)
    print(f"[BgRemoval] {basename}: loaded {img_pil.size}, mode RGBA")

    # ── Stage 1: corner flood-fill ────────────────────────────────────────────
    stage1 = remove_connected_background_color(img_pil, tolerance=30)
    stage1_arr = np.array(stage1)
    opaque_after_stage1 = int((stage1_arr[:, :, 3] > 0).sum())
    total_px = stage1_arr.shape[0] * stage1_arr.shape[1]
    print(f"[BgRemoval] {basename}: after flood-fill {opaque_after_stage1}/{total_px} opaque pixels "
          f"({100*opaque_after_stage1/total_px:.1f}%)")

    if opaque_after_stage1 == 0:
        print(f"[BgRemoval] {basename}: flood-fill wiped everything — falling back to original.")
        return img_pil

    # ── Stage 2: FastSAM refinement (optional, non-destructive) ──────────────
    try:
        model = YOLO(str(find_model_file("FastSAM-s.pt")))
        results = model(filepath, retina_masks=True, conf=0.4)
        result = results[0]

        if result.masks is not None:
            masks = result.masks.data.cpu().numpy()
            combined_mask = np.zeros(orig_arr.shape[:2], dtype=np.float32)
            for mask in masks:
                if mask.shape != orig_arr.shape[:2]:
                    mask = cv2.resize(mask, (orig_arr.shape[1], orig_arr.shape[0]),
                                      interpolation=cv2.INTER_LINEAR)
                combined_mask = np.maximum(combined_mask, mask)

            mask_uint8 = (combined_mask * 255).astype(np.uint8)
            kernel = np.ones((3, 3), np.uint8)
            mask_uint8 = cv2.dilate(mask_uint8, kernel, iterations=1)
            fastsam_alpha = cv2.GaussianBlur(mask_uint8, (3, 3), 0)

            fastsam_coverage = int((fastsam_alpha > 127).sum())
            print(f"[BgRemoval] {basename}: FastSAM mask covers "
                  f"{100*fastsam_coverage/total_px:.1f}% of pixels")

            # Non-destructive merge: only REDUCE alpha where FastSAM is confident
            # the pixel is background (fastsam_alpha < 30).  Never zero out pixels
            # that stage-1 kept, unless FastSAM is very sure they are background.
            refined_arr = stage1_arr.copy()
            background_by_fastsam = fastsam_alpha < 30  # FastSAM says "not subject"
            refined_arr[background_by_fastsam, 3] = 0

            opaque_after_stage2 = int((refined_arr[:, :, 3] > 0).sum())
            print(f"[BgRemoval] {basename}: after FastSAM refine {opaque_after_stage2}/{total_px} opaque pixels "
                  f"({100*opaque_after_stage2/total_px:.1f}%)")

            if opaque_after_stage2 == 0:
                print(f"[BgRemoval] {basename}: FastSAM refine wiped everything — keeping stage-1 result.")
            else:
                return Image.fromarray(refined_arr)
        else:
            print(f"[BgRemoval] {basename}: FastSAM found no masks — using stage-1 result only.")
    except Exception as e:
        print(f"[BgRemoval] {basename}: FastSAM stage failed ({e}) — using stage-1 result only.")

    return stage1

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

def format_clipart_batch(input_dir, target_width=3000, target_height=3000, target_dpi=300, remove_bg=True, use_upscaler=False, check_cancelled_fn=None):
    output_dir = os.path.join(input_dir, "Results")
    ensure_dir(output_dir)
    pattern = os.path.join(input_dir, "*.*")
    
    for filepath in glob.glob(pattern):
        if not os.path.isfile(filepath): continue
        if check_cancelled_fn and check_cancelled_fn():
            print("format_clipart_batch cancelled by callback. Terminating.")
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
            raise RuntimeError("Batch formatting cancelled by user.")
        try:
            print(f"[Batch] Formatting {os.path.basename(filepath)}...")

            if remove_bg:
                img_nobg = fastsam_remove_background(filepath)
                bbox = img_nobg.getbbox()
                print(f"[Batch]   bbox after bg removal: {bbox}")
                if bbox:
                    img_nobg = img_nobg.crop(bbox)
                else:
                    # bbox is None means fully transparent — fastsam fallback should
                    # prevent this, but guard here just in case.
                    print(f"[Batch]   WARNING: bbox is None after bg removal, using original.")
                    img_nobg = Image.open(filepath).convert("RGBA")
            else:
                img_nobg = Image.open(filepath).convert("RGBA")

            width, height = img_nobg.size
            print(f"[Batch]   image size after crop: {width}x{height}")
            
            # Use AI upscaling when the target canvas is larger than the source
            if use_upscaler and (target_width > width or target_height > height):
                img_nobg = ai_upscale(img_nobg, model='realesrgan-x4plus-anime', output_dir=output_dir)
                width, height = img_nobg.size
            
            if remove_bg:
                # Scale to fit inside target size (leaving 5% margins for clipart)
                max_target_w = int(target_width * 0.95)
                max_target_h = int(target_height * 0.95)
                scale = min(max_target_w / width, max_target_h / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                
                img_resized = img_nobg.resize((new_width, new_height), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
                
                paste_x = (target_width - new_width) // 2
                paste_y = (target_height - new_height) // 2
                canvas.paste(img_resized, (paste_x, paste_y), img_resized)
                output_image = canvas
            else:
                # Resize the image directly to the target dimensions
                output_image = img_nobg.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            out_path = os.path.join(output_dir, f"{base_name}_clipart.png")
            final_arr = np.array(output_image)
            opaque_final = int((final_arr[:, :, 3] > 0).sum())
            total_final = final_arr.shape[0] * final_arr.shape[1]
            print(f"[Batch]   final canvas opaque pixels: {opaque_final}/{total_final} "
                  f"({100*opaque_final/total_final:.1f}%)")
            if opaque_final == 0:
                print(f"[Batch]   WARNING: output is fully transparent — saving anyway.")
            output_image.save(out_path, "PNG", dpi=(target_dpi, target_dpi))
            print(f"[Batch] Saved: {out_path}")
            
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

def auto_process_sheet(input_path, check_cancelled_fn=None):
    input_dir = os.path.dirname(os.path.abspath(input_path))
    output_dir = os.path.join(input_dir, "Split")
    ensure_dir(output_dir)
    
    print(f"Auto-processing sheet {os.path.basename(input_path)}...")
    
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
    
    for idx, (mask, box) in enumerate(zip(masks, boxes)):
        if check_cancelled_fn and check_cancelled_fn():
            print("auto_process_sheet cancelled by callback. Terminating.")
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
            raise RuntimeError("Splitting cancelled by user.")
            
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
        item_crop = remove_connected_background_color(item_crop, tolerance=30)
        
        bbox = item_crop.getbbox()
        if bbox:
            # Skip noise crops that are extremely small (less than 10px wide or high)
            x_w = bbox[2] - bbox[0]
            y_h = bbox[3] - bbox[1]
            if x_w < 10 or y_h < 10:
                print(f"Skipping tiny noise item {idx+1}: size={x_w}x{y_h}")
                continue
            item_crop = item_crop.crop(bbox)
        else:
            print(f"Skipping empty transparent item {idx+1}")
            continue
            
        out_path = os.path.join(output_dir, f"{base_name}_{idx+1}.png")
        item_crop.save(out_path, "PNG")
        print(f"Processed item {idx+1}: {out_path}")
        
    print(f"All items formatted into: {output_dir}")


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
    output_dir = os.path.dirname(output_path)

    # AI upscale first if growing the image
    if target_width > img.width or target_height > img.height:
        img = ai_upscale(img, model='realesrgan-x4plus', output_dir=output_dir)
                
    # Final resize to exact target dimensions (LANCZOS after AI 4x pass)
    img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    # Save with custom DPI settings
    img_resized.save(output_path, "PNG", dpi=(target_dpi, target_dpi))
    print(f"Upscaled image successfully saved to: {output_path}")

def resize_image_multiple_sizes(input_path, sizes, output_zip_path):
    """
    Resizes a single PNG image into multiple target dimensions (width, height)
    using high-quality PIL Lanczos resampling (preserving resolution)
    and packages them into a ZIP archive.
    """
    import zipfile
    
    img = Image.open(input_path).convert("RGBA")
    
    base_dir = os.path.dirname(output_zip_path)
    temp_files = []
    
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    try:
        # AI upscale the source once if any target is larger than the original.
        # We upscale the master copy once, then fit each requested size from it.
        max_target_w = max(w for w, h in sizes)
        max_target_h = max(h for w, h in sizes)
        src = img  # img already RGBA from above
        if max_target_w > src.width or max_target_h > src.height:
            src = ai_upscale(src, model='realesrgan-x4plus', output_dir=base_dir)

        # Generate each resized version from the (possibly AI-upscaled) master
        for width, height in sizes:
            # Fit-with-padding: scale to fit inside target, preserve aspect ratio
            canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            scale = min(width / src.width, height / src.height)
            new_size = (int(src.width * scale), int(src.height * scale))
            resized_img = src.resize(new_size, Image.Resampling.LANCZOS)

            # Center on the canvas
            paste_x = (width - new_size[0]) // 2
            paste_y = (height - new_size[1]) // 2
            canvas.paste(resized_img, (paste_x, paste_y))
            
            # Save the resized image
            out_filename = f"{base_name}_{width}x{height}.png"
            out_path = os.path.join(base_dir, out_filename)
            
            # Save with 300 DPI by default to preserve print-ready resolution
            canvas.save(out_path, "PNG", dpi=(300, 300))
            temp_files.append((out_path, out_filename))
            print(f"Resized image to {width}x{height} (AI-upscaled, fitted) and saved to {out_path}")
            
        # Create ZIP file
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path, arc_name in temp_files:
                zip_file.write(file_path, arc_name)
                
    finally:
        # Clean up the individual files as they are now zipped
        for file_path, _ in temp_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Could not clean up temporary file {file_path}: {e}")

def bulk_rename_files(folder_path, base_text):
    """
    Sequentially renames all files in a folder using the format:
    XX_base_text.ext (where XX is padded 01, 02, etc.)
    Returns the total number of files renamed.
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder path does not exist: {folder_path}")
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"Path is not a directory: {folder_path}")
        
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    # Filter out hidden or system files
    files = [f for f in files if not f.startswith('.') and f.lower() not in ('desktop.ini', 'thumbs.db')]
    
    total_files = len(files)
    if total_files == 0:
        return 0
        
    files.sort()
    padding_len = max(2, len(str(total_files)))
    
    # Pass 1: Rename files to unique temporary names to prevent collisions
    temp_renames = []
    import uuid
    for filename in files:
        old_path = os.path.join(folder_path, filename)
        ext = os.path.splitext(filename)[1]
        temp_name = f"temp_{uuid.uuid4().hex}{ext}"
        temp_path = os.path.join(folder_path, temp_name)
        os.rename(old_path, temp_path)
        temp_renames.append((temp_path, ext))
        
    # Pass 2: Rename temporary files to sequential names
    for i, (temp_path, ext) in enumerate(temp_renames):
        num_str = f"{i+1:0{padding_len}d}"
        new_filename = f"{num_str}_{base_text}{ext}"
        new_path = os.path.join(folder_path, new_filename)
        os.rename(temp_path, new_path)
        
    return total_files
