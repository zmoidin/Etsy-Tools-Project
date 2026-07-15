# EtsyTools

Local personal Streamlit workspace for Etsy seller production tasks:

- PNG artwork diagnostics
- mockup and infographic generation
- AI-assisted Etsy listing drafts
- clipart sheet splitting/background removal
- trend research and prompt generation

## Run locally

```powershell
.\run.ps1
```

or:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

## Structure

```text
app.py                    Streamlit UI entrypoint
etsytools/ui/pages/       Split Streamlit page renderers
etsytools/                Shared app package
etsytools/config.py       Env/config loading
etsytools/paths.py        Workspace paths
etsytools/storage/        Local JSON usage state
etsytools/safety/         Seller/IP/claim review checks
etsytools/services/       Business-logic wrappers
tests/                    Lightweight unit tests
```

The Streamlit shell stays in `app.py`; each major tool page lives under
`etsytools/ui/pages/`. New business logic should go into `etsytools/` first,
then the page renderers should call that logic.

## Safety note

AI-generated titles, tags, descriptions, and trend inferences are drafts only.
Review rights ownership, Etsy policy compliance, AI disclosure requirements,
and unsupported commercial or quality claims before publishing.
