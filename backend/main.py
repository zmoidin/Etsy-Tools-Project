from __future__ import annotations

import os
import sys
import json
import requests
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
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

active_splitter_jobs = {}
active_batch_jobs = {}

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

    def get_config():
        conf = analyzer.load_config()
        return conf.get("products", {}), conf.get("digital_formats", {})

    settings = load_environment()

    def get_upload_path(image_id: str) -> Path | None:
        safe_name = Path(image_id).name
        candidate = UPLOAD_DIR / safe_name
        if candidate.exists() and candidate.suffix.lower() == ".png":
            return candidate
        return None

    def render_listing(
        request: Request,
        *,
        selected_format: str | None = None,
        selected_targets: list[str] | None = None,
        seo_keywords: str | None = None,
        image_id: str | None = None,
        analysis: dict | None = None,
        listing: dict | None = None,
        error: str | None = None,
    ) -> HTMLResponse:
        products, digital_formats = get_config()
        selected_format = selected_format or (list(digital_formats.keys())[0] if digital_formats else "")
        selected_targets = selected_targets or []
        image_url = f"/runtime/uploads/{image_id}" if image_id else None
        active_step = 2 if listing else 1
        
        products_options = [{"key": key, "name": value.get("name", key)} for key, value in products.items()]
        formats_options = [{"key": key, "name": value} for key, value in digital_formats.items()]
        
        return templates.TemplateResponse(
            request,
            "listing.html",
            {
                "active_page": "listing",
                "products": products_options,
                "digital_formats": formats_options,
                "selected_format": selected_format,
                "selected_targets": selected_targets,
                "seo_keywords": seo_keywords,
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
        success_msg: str | None = None,
        zip_url: str | None = None,
        split_images: list[str] | None = None,
        formatted_images: list[str] | None = None,
        collage_url: str | None = None,
        upscaled_url: str | None = None,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "image_assist.html",
            {
                "active_page": "image_assist",
                "active_tool": active_tool,
                "error": error,
                "success_msg": success_msg,
                "zip_url": zip_url,
                "split_images": split_images,
                "formatted_images": formatted_images,
                "collage_url": collage_url,
                "upscaled_url": upscaled_url,
                "gemini_connected": bool(settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here"),
                "tavily_connected": bool(settings.tavily_api_key and settings.tavily_api_key != "your_tavily_api_key_here"),
            },
        )

    def render_bulk_renamer(
        request: Request,
        *,
        error: str | None = None,
        success_msg: str | None = None,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "bulk_renamer.html",
            {
                "active_page": "bulk_renamer",
                "error": error,
                "success_msg": success_msg,
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
        digital_format: str = Form(...),
        targets: list[str] = Form(None),
        seo_keywords: str = Form(None),
        artwork: UploadFile = File(...),
    ):
        target_list = targets or []
        kw_str = seo_keywords.strip() if seo_keywords else ""
        if not artwork.filename or not artwork.filename.lower().endswith(".png"):
            return render_listing(request, selected_format=digital_format, selected_targets=target_list, seo_keywords=kw_str, error="Please upload a PNG artwork file.")

        image_id = f"{uuid4().hex}.png"
        destination = UPLOAD_DIR / image_id
        data = await artwork.read()
        if not data:
            return render_listing(request, selected_format=digital_format, selected_targets=target_list, seo_keywords=kw_str, error="The uploaded file was empty.")
        destination.write_bytes(data)

        analysis = analyzer.analyze_artwork(str(destination), target_list)
        return render_listing(
            request,
            selected_format=digital_format,
            selected_targets=target_list,
            seo_keywords=kw_str,
            image_id=image_id,
            analysis=analysis,
        )

    @app.post("/listing/generate", response_class=HTMLResponse)
    async def generate_listing(
        request: Request,
        digital_format: str = Form(...),
        targets: list[str] = Form(None),
        seo_keywords: str = Form(None),
        image_id: str = Form(...),
    ):
        products, digital_formats = get_config()
        target_list = targets or []
        kw_str = seo_keywords.strip() if seo_keywords else ""
        image_path = get_upload_path(image_id)
        if image_path is None:
            return render_listing(
                request,
                selected_format=digital_format,
                selected_targets=target_list,
                seo_keywords=kw_str,
                error="Uploaded image could not be found. Please upload it again.",
            )

        analysis = analyzer.analyze_artwork(str(image_path), target_list)
        if not analysis.get("is_ready", False):
            return render_listing(
                request,
                selected_format=digital_format,
                selected_targets=target_list,
                seo_keywords=kw_str,
                image_id=image_id,
                analysis=analysis,
                error="Listing copy generation is disabled because the artwork failed diagnostics checks.",
            )

        # Retrieve competitor listings context from Tavily
        competitor_context = ""
        if kw_str and settings.tavily_api_key and settings.tavily_api_key != "your_tavily_api_key_here":
            try:
                print(f"Crawling live competitor listings on Etsy for keywords: '{kw_str}'...")
                tavily_response = requests.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.tavily_api_key,
                        "query": f"site:etsy.com digital download png {kw_str}",
                        "search_depth": "basic",
                        "max_results": 5,
                    },
                    timeout=10,
                )
                if tavily_response.status_code == 200:
                    search_data = tavily_response.json()
                    increment_tavily_usage()
                    results = search_data.get("results", [])
                    if results:
                        competitor_context = "\n\n".join([f"Competitor Listing title: {r.get('title')}\nDescription snippet: {r.get('content')}" for r in results])
                        print(f"Successfully retrieved {len(results)} competitor listings for copywriting injection.")
            except Exception as e:
                print(f"Failed to crawl competitor listings: {e}")

        format_name = digital_formats.get(digital_format, digital_format)
        target_names = [products[k]["name"] for k in target_list if k in products]
        
        product_context = format_name
        if target_names:
            product_context += f" (targeted physical applications: {', '.join(target_names)})"

        listing = listing_generator.generate_etsy_listing(
            str(image_path),
            api_key=settings.gemini_api_key,
            product_type=product_context,
            competitor_context=competitor_context,
        )
        return render_listing(
            request,
            selected_format=digital_format,
            selected_targets=target_list,
            seo_keywords=kw_str,
            image_id=image_id,
            analysis=analysis,
            listing=listing,
        )

    @app.get("/image-assist", response_class=HTMLResponse)
    async def image_assist_page(request: Request, tool: str = "splitter"):
        if tool not in {"splitter", "batch", "resizer", "upscaler"}:
            tool = "splitter"
        return render_image_assist(request, active_tool=tool)

    @app.post("/image-assist/splitter/cancel/{session_id}")
    async def cancel_splitter(session_id: str):
        print(f"Cancelling active sheet splitter job: {session_id}")
        active_splitter_jobs[session_id] = "cancelled"
        return {"status": "cancelled"}

    @app.post("/image-assist/splitter", response_class=HTMLResponse)
    async def run_splitter(
        request: Request,
        sheet: UploadFile = File(...),
        session_id: str = None,  # Optional query parameter
    ):
        if not sheet.filename:
            return render_image_assist(request, active_tool="splitter", error="Please upload a sheet image.")

        temp_id = uuid4().hex
        job_id = session_id if session_id else temp_id
        active_splitter_jobs[job_id] = "running"

        session_dir = OUTPUT_DIR / f"splitter_{temp_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        sheet_path = session_dir / Path(sheet.filename).name
        data = await sheet.read()
        sheet_path.write_bytes(data)

        try:
            def check_cancelled():
                return active_splitter_jobs.get(job_id) == "cancelled"

            processor.auto_process_sheet(
                str(sheet_path),
                check_cancelled_fn=check_cancelled
            )
        except Exception as e:
            # Clean up the output directory on failure or cancellation
            import shutil
            shutil.rmtree(session_dir, ignore_errors=True)
            return render_image_assist(request, active_tool="splitter", error=f"Error processing sheet: {str(e)}")
        finally:
            active_splitter_jobs.pop(job_id, None)

        try:

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

    @app.post("/image-assist/batch/cancel/{session_id}")
    async def cancel_batch(session_id: str):
        print(f"Cancelling active batch formatting job: {session_id}")
        active_batch_jobs[session_id] = "cancelled"
        return {"status": "cancelled"}

    @app.post("/image-assist/batch", response_class=HTMLResponse)
    async def run_batch_formatter(
        request: Request,
        files: list[UploadFile] = File(...),
        width: int = Form(...),
        height: int = Form(...),
        dpi: int = Form(...),
        remove_bg: str = Form(None),
        use_upscaler: str = Form(None),
        session_id: str = None,  # Optional query parameter
    ):
        files = [f for f in files if f.filename]
        if not files:
            return render_image_assist(request, active_tool="batch", error="Please upload one or more files.")

        if width <= 0 or height <= 0 or dpi <= 0:
            return render_image_assist(request, active_tool="batch", error="Width, height, and DPI must be positive integers.")

        should_remove_bg = (remove_bg == "true")
        should_upscale = (use_upscaler == "true")

        temp_id = uuid4().hex
        job_id = session_id if session_id else temp_id
        active_batch_jobs[job_id] = "running"

        session_dir = OUTPUT_DIR / f"batch_{temp_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            fpath = session_dir / Path(f.filename).name
            data = await f.read()
            fpath.write_bytes(data)

        try:
            def check_cancelled():
                return active_batch_jobs.get(job_id) == "cancelled"

            processor.format_clipart_batch(
                str(session_dir),
                target_width=width,
                target_height=height,
                target_dpi=dpi,
                remove_bg=should_remove_bg,
                use_upscaler=should_upscale,
                check_cancelled_fn=check_cancelled
            )

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
            import shutil
            shutil.rmtree(session_dir, ignore_errors=True)
            return render_image_assist(request, active_tool="batch", error=f"Error in batch processing: {str(e)}")
        finally:
            active_batch_jobs.pop(job_id, None)

    @app.post("/image-assist/resizer")
    async def run_resizer(
        request: Request,
        file: UploadFile = File(...),
        widths: list[str] = Form(...),
        heights: list[str] = Form(...),
    ):
        if not file.filename:
            return render_image_assist(request, active_tool="resizer", error="Please upload a PNG file.")

        if not widths or not heights or len(widths) != len(heights):
            return render_image_assist(request, active_tool="resizer", error="Invalid dimensions specified.")

        try:
            sizes = []
            for w, h in zip(widths, heights):
                sizes.append((int(w), int(h)))
        except ValueError:
            return render_image_assist(request, active_tool="resizer", error="Dimensions must be integers.")

        temp_id = uuid4().hex
        session_dir = OUTPUT_DIR / f"resizer_{temp_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        input_path = session_dir / Path(file.filename).name
        data = await file.read()
        input_path.write_bytes(data)

        base_name = Path(file.filename).stem
        zip_filename = f"{base_name}_resized.zip"
        zip_path = session_dir / zip_filename

        try:
            processor.resize_image_multiple_sizes(str(input_path), sizes, str(zip_path))
            
            # Open directory for local users
            if session_dir.exists():
                os.startfile(str(session_dir))

            zip_url = f"/runtime/outputs/resizer_{temp_id}/{zip_filename}"
            return render_image_assist(
                request,
                active_tool="resizer",
                zip_url=zip_url,
                success_msg="Successfully resized images! Use the button below to download the ZIP."
            )
        except Exception as e:
            return render_image_assist(request, active_tool="resizer", error=f"Error resizing image: {str(e)}")

    @app.get("/bulk-renamer", response_class=HTMLResponse)
    async def bulk_renamer_page(request: Request):
        return render_bulk_renamer(request)

    @app.post("/bulk-renamer", response_class=HTMLResponse)
    async def run_bulk_renamer(
        request: Request,
        folder_path: str = Form(...),
        base_text: str = Form(...),
    ):
        if not folder_path or not base_text:
            return render_bulk_renamer(request, error="Folder path and base text are required.")

        folder_path = folder_path.strip()
        base_text = base_text.strip()

        try:
            count = processor.bulk_rename_files(folder_path, base_text)
            if os.path.exists(folder_path):
                os.startfile(folder_path)
            
            success_msg = f"Successfully renamed {count} files in '{folder_path}'!"
            return render_bulk_renamer(request, success_msg=success_msg)
        except Exception as e:
            return render_bulk_renamer(request, error=f"Error renaming files: {str(e)}")

    @app.post("/image-assist/upscaler", response_class=HTMLResponse)
    async def run_custom_upscaler(
        request: Request,
        image: UploadFile = File(...),
        width: int = Form(...),
        height: int = Form(...),
        dpi: int = Form(...),
    ):
        if not image.filename:
            return render_image_assist(request, active_tool="upscaler", error="Please upload an image to upscale.")

        if width <= 0 or height <= 0 or dpi <= 0:
            return render_image_assist(request, active_tool="upscaler", error="Width, height, and DPI must be positive integers.")

        temp_id = uuid4().hex
        session_dir = OUTPUT_DIR / f"upscaler_{temp_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        image_path = session_dir / Path(image.filename).name
        data = await image.read()
        image_path.write_bytes(data)

        output_name = f"upscaled_{Path(image.filename).stem}.png"
        output_path = session_dir / output_name

        try:
            processor.upscale_and_resize_general_image(
                str(image_path),
                width,
                height,
                dpi,
                str(output_path)
            )

            if not output_path.exists():
                return render_image_assist(request, active_tool="upscaler", error="Failed to save upscaled image.")

            upscaled_url = f"/runtime/outputs/upscaler_{temp_id}/{output_name}"
            return render_image_assist(request, active_tool="upscaler", upscaled_url=upscaled_url)
        except Exception as e:
            return render_image_assist(request, active_tool="upscaler", error=f"Error during upscaling: {str(e)}")

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
