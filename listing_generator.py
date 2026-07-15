import os
import json
from PIL import Image
from pydantic import BaseModel, Field
from typing import List
from etsytools.safety.listing_checks import listing_safety_warnings, sanitize_etsy_tags

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

class EtsyListing(BaseModel):
    title: str = Field(description="SEO-optimized Etsy listing title, up to 140 characters, using keywords separated by slashes or commas.")
    description: str = Field(description="Formatted listing description, including an about the design section, ideas for use, and a generic care/sizing guide. Make it engaging and easy to read with bullet points.")
    tags: List[str] = Field(description="Exactly 13 SEO search tags/keywords, each under 20 characters, relevant to the design.")
    materials: List[str] = Field(description="Up to 5 materials associated with this design/product (e.g. PNG, Digital Download, T-shirt, Mug, DTG).")

def generate_mock_listing(filename):
    """Fallback generator in case Gemini API is not configured or fails."""
    base_name = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
    return {
        "title": f"{base_name} PNG Shirt Design, Retro Graphic Tee Design, Instant Digital Download Clipart PNG",
        "description": (
            f"Thank you for visiting our shop!\n\n"
            f"This is a high-quality digital download of the '{base_name}' artwork. "
            f"Perfect for sublimation, DTG printing, heat transfer, mugs, tote bags, and more!\n\n"
            f"★ WHAT YOU WILL RECEIVE ★\n"
            f"- 1 High-resolution PNG file (transparency preserved)\n"
            f"- Sized for direct print compatibility (300 DPI)\n\n"
            f"★ HOW TO DOWNLOAD ★\n"
            f"After payment is confirmed, Etsy will send an email with the download link, or you can retrieve it directly from your Etsy 'Purchases' page.\n\n"
            f"★ TERMS OF USE ★\n"
            f"- Suitable for personal and commercial projects.\n"
            f"- Reselling of the digital file itself is strictly prohibited."
        ),
        "tags": [
            "digital download", "png sublimation", "retro shirt design", "tshirt transfer",
            "diy craft print", "aesthetic clipart", "commercial use png", "mug design wrap",
            "hoodie svg clip", "trendy shirt graphic", "printable art", "instant download", "high resolution png"
        ][:13],
        "materials": ["PNG", "Digital Download", "High Resolution", "Transparent Background"]
    }

def generate_etsy_listing(image_path, api_key=None, product_type="T-Shirt"):
    """
    Sends the PNG artwork to Gemini and uses structured outputs to extract 
    optimized Etsy listing details (title, description, 13 tags, materials).
    """
    effective_api_key = api_key or os.environ.get("GEMINI_API_KEY")
    
    if not GENAI_AVAILABLE or not effective_api_key:
        print("Gemini API key or google-genai SDK not available. Using fallback mock generator.")
        data = generate_mock_listing(os.path.basename(image_path))
        data["tags"] = sanitize_etsy_tags(data.get("tags", []))
        data["safety_warnings"] = listing_safety_warnings(data)
        return data
        
    try:
        client = genai.Client(api_key=effective_api_key)
        img = Image.open(image_path)
        
        prompt = (
            f"Analyze this artwork and generate professional Etsy listing details. "
            f"The listing is primarily intended for a {product_type}. "
            f"Generate a catchy SEO title, a highly structured description with spacing, "
            f"exactly 13 relevant search tags (under 20 characters each), and up to 5 materials."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[img, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EtsyListing,
                temperature=0.7
            ),
        )
        
        data = json.loads(response.text)
        
        # Post-process tags to ensure strict compliance with Etsy constraints.
        data["tags"] = sanitize_etsy_tags(data.get("tags", []))
        data["safety_warnings"] = listing_safety_warnings(data)
        
        return data
        
    except Exception as e:
        print(f"Error generating listing from Gemini API: {e}")
        data = generate_mock_listing(os.path.basename(image_path))
        data["tags"] = sanitize_etsy_tags(data.get("tags", []))
        data["safety_warnings"] = listing_safety_warnings(data)
        return data
