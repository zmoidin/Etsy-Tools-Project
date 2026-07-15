from __future__ import annotations

import os
import sys
import json
import requests
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import analyzer
import listing_generator
from etsytools.config import load_environment
from etsytools.paths import PROJECT_ROOT, ensure_workspace_dirs
from etsytools.models import PromptsResponse, TrendsResponse
from etsytools.storage.usage_store import get_tavily_usage, increment_tavily_usage

# Add ImageAssist to python path to import processor.py
IMAGE_ASSIST_DIR = str(PROJECT_ROOT / "ImageAssist")
if IMAGE_ASSIST_DIR not in sys.path:
    sys.path.append(IMAGE_ASSIST_DIR)
import processor

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False


APP_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
RUNTIME_DIR = PROJECT_ROOT / "data" / "web_runtime"
UPLOAD_DIR = RUNTIME_DIR / "uploads"
OUTPUT_DIR = RUNTIME_DIR / "outputs"


def create_app() -> FastAPI:
    ensure_workspace_dirs()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="EtsyTools Studio")
    templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
    # Python 3.14 + current Starlette/Jinja can produce an unhashable cache key
    # through TemplateResponse globals. Disable template caching for this local
    # development UI; templates are tiny and this avoids the compatibility edge.
    templates.env.cache = None

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.mount("/runtime", StaticFiles(directory=str(RUNTIME_DIR)), name="runtime")

    config = analyzer.load_config()
    products = config.get("products", {})
    settings = load_environment()

    def product_options():
        return [{"key": key, "name": value.get("name", key)} for key, value in products.items()]

    def get_upload_path(image_id: str) -> Path | None:
        safe_name = Path(image_id).name
        candidate = UPLOAD_DIR / safe_name
        if candidate.exists() and candidate.suffix.lower() == ".png":
            return candidate
        return None

    def render_listing(
        request: Request,
        *,
        selected_product: str | None = None,
        image_id: str | None = None,
        analysis: dict | None = None,
        listing: dict | None = None,
        error: str | None = None,
    ) -> HTMLResponse:
        selected_product = selected_product or (product_options()[0]["key"] if product_options() else "")
        image_url = f"/runtime/uploads/{image_id}" if image_id else None
        active_step = 2 if listing else 1
        return templates.TemplateResponse(
            request,
            "listing.html",
            {
                "active_page": "listing",
                "products": product_options(),
                "selected_product": selected_product,
                "image_id": image_id,
                "image_url": image_url,
                "analysis": analysis,
                "listing": listing,
                "error": error,
                "active_step": active_step,
                "gemini_connected": bool(settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here"),
                "tavily_connected": bool(settings.tavily_api_key and settings.tavily_api_key != "your_tavily_api_key_here"),
            },
        )

    def render_image_assist(
        request: Request,
        *,
        active_tool: str = "splitter",
        error: str | None = None,
        zip_url: str | None = None,
        split_images: list[str] | None = None,
        formatted_images: list[str] | None = None,
        collage_url: str | None = None,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "image_assist.html",
            {
                "active_page": "image_assist",
                "active_tool": active_tool,
                "error": error,
                "zip_url": zip_url,
                "split_images": split_images,
                "formatted_images": formatted_images,
                "collage_url": collage_url,
                "gemini_connected": bool(settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here"),
                "tavily_connected": bool(settings.tavily_api_key and settings.tavily_api_key != "your_tavily_api_key_here"),
            },
        )

    def render_trend_research(
        request: Request,
        *,
        topic: str | None = None,
        trends: list | None = None,
        trends_json: str | None = None,
        selected_trend: str | None = None,
        prompts: list | None = None,
        error: str | None = None,
    ) -> HTMLResponse:
        usage_data = get_tavily_usage()
        searches_used = usage_data.get("tavily_searches", 0)
        searches_percentage = min((int(searches_used) / 1000) * 100, 100)

        return templates.TemplateResponse(
            request,
            "trend_research.html",
            {
                "active_page": "trend_research",
                "topic": topic,
                "trends": trends,
                "trends_json": trends_json,
                "selected_trend": selected_trend,
                "prompts": prompts,
                "searches_used": searches_used,
                "searches_percentage": searches_percentage,
                "error": error,
                "gemini_connected": bool(settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here"),
                "tavily_connected": bool(settings.tavily_api_key and settings.tavily_api_key != "your_tavily_api_key_here"),
            },
        )

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return render_listing(request)

    @app.get("/listing", response_class=HTMLResponse)
    async def listing_page(request: Request):
        return render_listing(request)

    @app.post("/listing/analyze", response_class=HTMLResponse)
    async def analyze_listing(
        request: Request,
        product_type: str = Form(...),
        artwork: UploadFile = File(...),
    ):
        if not artwork.filename or not artwork.filename.lower().endswith(".png"):
            return render_listing(request, selected_product=product_type, error="Please upload a PNG artwork file.")

        image_id = f"{uuid4().hex}.png"
        destination = UPLOAD_DIR / image_id
        data = await artwork.read()
        if not data:
            return render_listing(request, selected_product=product_type, error="The uploaded file was empty.")
        destination.write_bytes(data)

        analysis = analyzer.analyze_artwork(str(destination), product_type)
        return render_listing(
            request,
            selected_product=product_type,
            image_id=image_id,
            analysis=analysis,
        )

    @app.post("/listing/generate", response_class=HTMLResponse)
    async def generate_listing(
        request: Request,
        product_type: str = Form(...),
        image_id: str = Form(...),
    ):
        image_path = get_upload_path(image_id)
        if image_path is None:
            return render_listing(
                request,
                selected_product=product_type,
                error="Uploaded image could not be found. Please upload it again.",
            )

        analysis = analyzer.analyze_artwork(str(image_path), product_type)
        if not analysis.get("is_ready", False):
            return render_listing(
                request,
                selected_product=product_type,
                image_id=image_id,
                analysis=analysis,
                error="Listing copy generation is disabled because the artwork failed diagnostics checks.",
            )

        product_name = products.get(product_type, {}).get("name", product_type)
        listing = listing_generator.generate_etsy_listing(
            str(image_path),
            api_key=settings.gemini_api_key,
            product_type=product_name,
        )
        return render_listing(
            request,
            selected_product=product_type,
            image_id=image_id,
            analysis=analysis,
            listing=listing,
        )

    @app.get("/image-assist", response_class=HTMLResponse)
    async def image_assist_page(request: Request, tool: str = "splitter"):
        if tool not in {"splitter", "batch", "collage"}:
            tool = "splitter"
        return render_image_assist(request, active_tool=tool)

    @app.post("/image-assist/splitter", response_class=HTMLResponse)
    async def run_splitter(
        request: Request,
        sheet: UploadFile = File(...),
        canvas_color: str = Form(...),
        custom_hex: str = Form(None),
    ):
        if not sheet.filename:
            return render_image_assist(request, active_tool="splitter", error="Please upload a sheet image.")

        temp_id = uuid4().hex
        session_dir = OUTPUT_DIR / f"splitter_{temp_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        sheet_path = session_dir / Path(sheet.filename).name
        data = await sheet.read()
        sheet_path.write_bytes(data)

        bg_color_arg = canvas_color
        if canvas_color == "custom hex" and custom_hex:
            bg_color_arg = custom_hex

        try:
            processor.auto_process_sheet(str(sheet_path), bg_type="transparent", canvas_color=bg_color_arg)

            split_dir = session_dir / "Split"
            split_files = list(split_dir.glob("*.png"))

            if not split_files:
                return render_image_assist(
                    request,
                    active_tool="splitter",
                    error="No items could be isolated on the sheet. Ensure elements are distinct and high contrast.",
                )

            zip_name = f"split_pack_{temp_id}.zip"
            zip_path = OUTPUT_DIR / zip_name
            import zipfile

            with zipfile.ZipFile(zip_path, "w") as zf:
                for fpath in split_files:
                    zf.write(fpath, arcname=fpath.name)

            split_urls = [f"/runtime/outputs/splitter_{temp_id}/Split/{fpath.name}" for fpath in split_files]
            zip_url = f"/runtime/outputs/{zip_name}"

            return render_image_assist(request, active_tool="splitter", zip_url=zip_url, split_images=split_urls)
        except Exception as e:
            return render_image_assist(request, active_tool="splitter", error=f"Error processing sheet: {str(e)}")

    @app.post("/image-assist/batch", response_class=HTMLResponse)
    async def run_batch_formatter(
        request: Request,
        files: list[UploadFile] = File(...),
    ):
        files = [f for f in files if f.filename]
        if not files:
            return render_image_assist(request, active_tool="batch", error="Please upload one or more files.")

        temp_id = uuid4().hex
        session_dir = OUTPUT_DIR / f"batch_{temp_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            fpath = session_dir / Path(f.filename).name
            data = await f.read()
            fpath.write_bytes(data)

        try:
            processor.format_clipart_batch(str(session_dir))

            results_dir = session_dir / "Results"
            result_files = list(results_dir.glob("*.png"))

            if not result_files:
                return render_image_assist(
                    request,
                    active_tool="batch",
                    error="No files were successfully processed.",
                )

            zip_name = f"formatted_pack_{temp_id}.zip"
            zip_path = OUTPUT_DIR / zip_name
            import zipfile

            with zipfile.ZipFile(zip_path, "w") as zf:
                for fpath in result_files:
                    zf.write(fpath, arcname=fpath.name)

            formatted_urls = [f"/runtime/outputs/batch_{temp_id}/Results/{fpath.name}" for fpath in result_files]
            zip_url = f"/runtime/outputs/{zip_name}"

            return render_image_assist(request, active_tool="batch", zip_url=zip_url, formatted_images=formatted_urls)
        except Exception as e:
            return render_image_assist(request, active_tool="batch", error=f"Error in batch processing: {str(e)}")

    @app.post("/image-assist/collage", response_class=HTMLResponse)
    async def run_collage(
        request: Request,
        cliparts: list[UploadFile] = File(...),
        background: UploadFile = File(None),
    ):
        cliparts = [c for c in cliparts if c.filename]
        if not cliparts:
            return render_image_assist(request, active_tool="collage", error="Please upload clipart files to arrange.")

        temp_id = uuid4().hex
        session_dir = OUTPUT_DIR / f"collage_{temp_id}"
        clipart_dir = session_dir / "Clipart"
        clipart_dir.mkdir(parents=True, exist_ok=True)

        for c in cliparts:
            fpath = clipart_dir / Path(c.filename).name
            data = await c.read()
            fpath.write_bytes(data)

        bg_path = None
        if background and background.filename:
            bg_path = session_dir / Path(background.filename).name
            data = await background.read()
            bg_path.write_bytes(data)

        try:
            output_showcase_path = session_dir / "Bundle_Showcase.png"
            processor.create_showcase_mockup(
                str(clipart_dir),
                str(bg_path) if bg_path else None,
                output_path=str(output_showcase_path),
            )

            if not output_showcase_path.exists():
                return render_image_assist(
                    request,
                    active_tool="collage",
                    error="Failed to generate showcase collage image.",
                )

            collage_url = f"/runtime/outputs/collage_{temp_id}/Bundle_Showcase.png"
            return render_image_assist(request, active_tool="collage", collage_url=collage_url)
        except Exception as e:
            return render_image_assist(request, active_tool="collage", error=f"Error generating collage: {str(e)}")

    @app.get("/trend-research", response_class=HTMLResponse)
    async def trend_research_page(request: Request):
        return render_trend_research(request)

    @app.post("/trend-research/search", response_class=HTMLResponse)
    async def run_trend_search(
        request: Request,
        topic: str = Form(...),
    ):
        topic = topic.strip()
        if not topic:
            return render_trend_research(request, error="Please enter a valid design topic.")

        tavily_key = settings.tavily_api_key
        gemini_key = settings.gemini_api_key

        if not tavily_key or tavily_key == "your_tavily_api_key_here":
            return render_trend_research(
                request, topic=topic, error="Tavily API key is not configured. Check your .env file."
            )
        if not gemini_key or gemini_key == "your_gemini_api_key_here":
            return render_trend_research(
                request, topic=topic, error="Gemini API key is not configured. Check your .env file."
            )
        if not GENAI_AVAILABLE:
            return render_trend_research(
                request, topic=topic, error="Gemini SDK is not installed in the environment."
            )

        try:
            modified_query = f"current graphic design trends illustration styles for {topic}"
            tavily_response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": modified_query,
                    "search_depth": "basic",
                    "include_answer": False,
                    "include_raw_content": False,
                    "max_results": 5,
                },
                timeout=10,
            )
            tavily_response.raise_for_status()
            search_data = tavily_response.json()
            increment_tavily_usage()

            results = search_data.get("results", [])
            if not results:
                search_context = f"No active search results found for: {topic}"
            else:
                search_context = "\n\n".join(
                    [f"Title: {r.get('title')}\nContent: {r.get('content')}" for r in results]
                )

            # Query Gemini using SDK
            client = genai.Client(api_key=gemini_key)
            prompt_str = (
                f"You are a design trends expert. Analyze the following web search results regarding current graphic "
                f"design trends and illustration styles for the topic: '{topic}'.\n\n"
                f"Search Context:\n{search_context}\n\n"
                f"Based on this information, extract the top 10 most relevant and visually distinct design elements and "
                f"illustration style combinations. For each item, evaluate the search context to assign an accurate "
                f"trend_score (1-100) and trend_direction ('Surging', 'Rising', 'Stable', or 'Declining'). Ensure the output strictly conforms to the JSON schema."
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_str,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TrendsResponse,
                    temperature=0.7,
                ),
            )
            trends_data = json.loads(response.text)
            trends_list = trends_data.get("trends", [])

            # Serialize trends to json string to pass to the client
            trends_json_str = json.dumps(trends_list)

            return render_trend_research(request, topic=topic, trends=trends_list, trends_json=trends_json_str)
        except Exception as e:
            return render_trend_research(request, topic=topic, error=f"Error querying design trends: {str(e)}")

    @app.post("/trend-research/prompts", response_class=HTMLResponse)
    async def run_prompt_generator(
        request: Request,
        topic: str = Form(...),
        trends_json: str = Form(...),
        selected_trend: str = Form(...),
    ):
        gemini_key = settings.gemini_api_key
        if not gemini_key or gemini_key == "your_gemini_api_key_here":
            return render_trend_research(request, topic=topic, error="Gemini API key is not configured.")
        if not GENAI_AVAILABLE:
            return render_trend_research(request, topic=topic, error="Gemini SDK is not installed.")

        try:
            # Deserialize trends to display them again
            trends_list = json.loads(trends_json)

            # Split selected_trend values
            design_val, style_val = selected_trend.split("|", 1)

            client = genai.Client(api_key=gemini_key)
            prompt_str = (
                f"You are an expert Prompt Engineer optimizing text-to-image prompts for models like Midjourney, DALL-E 3, and Stable Diffusion.\n"
                f"Generate between 5 to 10 distinct, isolated clipart assets/elements for the design theme: '{design_val}' in the style: '{style_val}'.\n\n"
                f"For each generated element, you MUST follow this exact prompt template:\n"
                f"\"An isolated [Element Name] asset, {style_val} style, vibrant colors, studio lighting, die-cut sticker look, pure solid white background, high-resolution 8k texture, print-ready quality, centered composition --no shadows, background scenery, realistic photographic elements, grid\"\n\n"
                f"Ensure you replace '[Element Name]' with the specific element (e.g. if the element is 'Seashell', the prompt becomes 'An isolated Seashell asset, {style_val} style...') and keep the rest of the template exactly intact."
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_str,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PromptsResponse,
                    temperature=0.7,
                ),
            )
            prompts_data = json.loads(response.text)
            prompts_list = prompts_data.get("elements", [])

            return render_trend_research(
                request,
                topic=topic,
                trends=trends_list,
                trends_json=trends_json,
                selected_trend=selected_trend,
                prompts=prompts_list,
            )
        except Exception as e:
            # Attempt to recover trends
            try:
                recovered_trends = json.loads(trends_json)
            except:
                recovered_trends = None
            return render_trend_research(
                request,
                topic=topic,
                trends=recovered_trends,
                trends_json=trends_json,
                error=f"Error generating prompts: {str(e)}",
            )

    return app


app = create_app()


app = create_app()
