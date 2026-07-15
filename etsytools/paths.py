from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BRAND_ASSETS_DIR = PROJECT_ROOT / "brand_assets"
MOCKUP_TEMPLATES_DIR = PROJECT_ROOT / "mockup_templates"
MODELS_DIR = DATA_DIR / "models"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
USAGE_PATH = PROJECT_ROOT / "usage.json"


def ensure_workspace_dirs() -> None:
    """Create local data directories used by the app."""
    for path in (DATA_DIR, BRAND_ASSETS_DIR, MOCKUP_TEMPLATES_DIR, MODELS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def find_model_file(filename: str) -> Path:
    """Prefer data/models but keep compatibility with the historical root location."""
    preferred = MODELS_DIR / filename
    if preferred.exists():
        return preferred
    return PROJECT_ROOT / filename

