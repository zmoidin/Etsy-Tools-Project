import os
from PIL import Image
from etsytools.config import load_config as _load_config

def load_config():
    """Loads the config.yaml file."""
    return _load_config()

def analyze_artwork(image_path, target_product_key=None):
    """
    Analyzes the uploaded PNG artwork:
    - Dimensions (pixels)
    - DPI (Dots Per Inch)
    - Match against configurations in config.yaml
    """
    config = load_config()
    products = config.get('products', {})
    
    result = {
        "filename": os.path.basename(image_path),
        "width": 0,
        "height": 0,
        "dpi": None,
        "aspect_ratio": 1.0,
        "aspect_ratio_str": "1:1",
        "is_ready": False,
        "checks": {},
        "recommendations": []
    }
    
    try:
        with Image.open(image_path) as img:
            result["width"], result["height"] = img.size
            result["aspect_ratio"] = result["width"] / result["height"]
            
            eps = 0.02
            if abs(result["aspect_ratio"] - 1.0) < eps:
                result["aspect_ratio_str"] = "1:1"
            elif abs(result["aspect_ratio"] - (2/3)) < eps:
                result["aspect_ratio_str"] = "2:3"
            elif abs(result["aspect_ratio"] - (3/2)) < eps:
                result["aspect_ratio_str"] = "3:2"
            elif abs(result["aspect_ratio"] - (3/4)) < eps:
                result["aspect_ratio_str"] = "3:4"
            elif abs(result["aspect_ratio"] - (4/3)) < eps:
                result["aspect_ratio_str"] = "4:3"
            elif abs(result["aspect_ratio"] - (4/5)) < eps:
                result["aspect_ratio_str"] = "4:5"
            elif abs(result["aspect_ratio"] - (5/4)) < eps:
                result["aspect_ratio_str"] = "5:4"
            elif abs(result["aspect_ratio"] - (11/14)) < eps:
                result["aspect_ratio_str"] = "11:14"
            elif abs(result["aspect_ratio"] - (14/11)) < eps:
                result["aspect_ratio_str"] = "14:11"
            else:
                from math import gcd
                common_divisor = gcd(result["width"], result["height"])
                w_ratio = round(result["width"] / common_divisor)
                h_ratio = round(result["height"] / common_divisor)
                if w_ratio < 100 and h_ratio < 100:
                    result["aspect_ratio_str"] = f"{w_ratio}:{h_ratio}"
                else:
                    result["aspect_ratio_str"] = f"{result['aspect_ratio']:.2f}:1"
            
            dpi_info = img.info.get('dpi')
            if dpi_info:
                result["dpi"] = int(round(dpi_info[0]))
            else:
                phys = img.info.get('pHYs')
                if phys:
                    x_pm, y_pm, unit = phys
                    if unit == 1:
                        result["dpi"] = int(round(x_pm / 39.3701))
            
            if not result["dpi"]:
                result["dpi"] = 72
                result["recommendations"].append("DPI metadata was not found. Defaulted to web-standard 72 DPI. Print files should explicitly embed 300 DPI metadata.")

        if target_product_key and target_product_key in products:
            target = products[target_product_key]
            target_w = target["width"]
            target_h = target["height"]
            target_dpi = target["dpi"]
            product_name = target["name"]
            
            # DPI Check
            dpi_ok = result["dpi"] >= target_dpi
            result["checks"]["dpi"] = {
                "ok": dpi_ok,
                "current": result["dpi"],
                "required": target_dpi,
                "label": f"DPI Check (Has {result['dpi']}, Needs {target_dpi})"
            }
            if not dpi_ok:
                result["recommendations"].append(f"DPI is too low for a physical {product_name}. Etsy buyers and Print-On-Demand providers require at least {target_dpi} DPI. Resave artwork with 300 DPI settings.")
                
            # Dimensions Check
            dim_ok = (result["width"] >= target_w) and (result["height"] >= target_h)
            result["checks"]["dimensions"] = {
                "ok": dim_ok,
                "current": f"{result['width']}x{result['height']}",
                "required": f"{target_w}x{target_h}",
                "label": f"Dimensions Check (Has {result['width']}x{result['height']}, Needs at least {target_w}x{target_h})"
            }
            if not dim_ok:
                result["recommendations"].append(f"Image dimensions ({result['width']}x{result['height']} px) are smaller than the recommended size for a {product_name} ({target_w}x{target_h} px). Printing at this resolution may cause blurriness or pixelation.")
            
            # Aspect Ratio Check (Optimization 1)
            target_ratio = target_w / target_h
            ratio_diff = abs(result["aspect_ratio"] - target_ratio)
            ratio_ok = ratio_diff <= 0.05
            
            result["checks"]["aspect_ratio"] = {
                "ok": ratio_ok,
                "current": f"{result['aspect_ratio']:.2f}",
                "required": f"{target_ratio:.2f}",
                "label": f"Aspect Ratio Check (Has {result['aspect_ratio']:.2f}, Needs ~{target_ratio:.2f})"
            }
            if not ratio_ok:
                result["recommendations"].append(
                    f"Aspect ratio mismatch! The artwork ratio ({result['aspect_ratio']:.2f}) does not match the product template "
                    f"'{product_name}' aspect ratio ({target_ratio:.2f}). Composing mockups or printing directly may result in "
                    f"unwanted cropping, stretching, or empty borders."
                )
            
            result["is_ready"] = dpi_ok and dim_ok and ratio_ok
            
        else:
            best_match = None
            for key, prod in products.items():
                if result["width"] == prod["width"] and result["height"] == prod["height"] and result["dpi"] == prod["dpi"]:
                    best_match = prod
                    break
            
            if best_match:
                result["is_ready"] = True
                result["recommendations"].append(f"Perfect match found for product category: **{best_match['name']}**.")
            else:
                closest_prod = None
                closest_diff = 999.0
                for key, prod in products.items():
                    prod_ratio = prod["width"] / prod["height"]
                    diff = abs(result["aspect_ratio"] - prod_ratio)
                    if diff < closest_diff:
                        closest_diff = diff
                        closest_prod = prod
                
                result["is_ready"] = False
                if closest_prod:
                    result["recommendations"].append(
                        f"Artwork does not exactly match any standard template. The closest template by aspect ratio is **{closest_prod['name']}** "
                        f"(needs {closest_prod['width']}x{closest_prod['height']} px at {closest_prod['dpi']} DPI)."
                    )
                
    except Exception as e:
        result["recommendations"].append(f"Failed to analyze image file: {str(e)}")
        
    return result
