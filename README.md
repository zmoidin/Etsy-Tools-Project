# EtsyTools

Local personal FastAPI workspace for Etsy seller production tasks:

- PNG artwork diagnostics
- AI-assisted Etsy listing drafts

## Run locally

FastAPI/Jinja2 UI for the Listing Wizard:

```powershell
.\run.ps1
```

Then open:

```text
http://127.0.0.1:8000/listing
```

## Structure

```text
backend/main.py           FastAPI server entrypoint & router
backend/templates/        Jinja2 HTML templates
backend/static/           Custom CSS and client-side JS scripts
etsytools/                Core application package
etsytools/config.py       Env/config loading
etsytools/paths.py        Workspace paths
etsytools/storage/        Local JSON usage state
etsytools/safety/         Seller/IP/claim review checks
etsytools/services/       Business-logic wrappers
tests/                    Lightweight unit tests
```

All web application routers and endpoints live inside `backend/main.py`. Page layout structures are housed inside the Jinja2 templates under `backend/templates/`. Core business logic resides under `etsytools/`.

## Safety note

AI-generated titles, tags, descriptions, and trend inferences are drafts only.
Review rights ownership, Etsy policy compliance, AI disclosure requirements,
and unsupported commercial or quality claims before publishing.
