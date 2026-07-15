from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import yaml
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency may not be installed yet
    load_dotenv = None

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover - dependency may not be installed yet
    BaseSettings = None
    SettingsConfigDict = None

from etsytools.paths import CONFIG_PATH, PROJECT_ROOT


if BaseSettings is not None:

    class Settings(BaseSettings):
        """Typed app settings sourced from environment variables and .env."""

        gemini_api_key: str | None = None
        tavily_api_key: str | None = None

        model_config = SettingsConfigDict(
            env_file=PROJECT_ROOT / ".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

else:

    class Settings:
        """Small fallback used until requirements are installed."""

        def __init__(self, gemini_api_key: str | None = None, tavily_api_key: str | None = None):
            self.gemini_api_key = gemini_api_key
            self.tavily_api_key = tavily_api_key


def load_environment() -> Settings:
    """Load .env using a library instead of custom parsing."""
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env", override=False)
    else:
        _load_env_fallback(PROJECT_ROOT / ".env")
    return Settings(
        gemini_api_key=os.environ.get("GEMINI_API_KEY"),
        tavily_api_key=os.environ.get("TAVILY_API_KEY"),
    )


def _load_env_fallback(env_path) -> None:
    """Minimal .env reader used only if python-dotenv is not installed yet."""
    if not env_path.exists():
        return
    try:
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip("'").strip('"'))
    except OSError:
        return


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    """Load YAML app configuration once per process."""
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def get_theme_config(config: dict[str, Any]) -> dict[str, str]:
    return config.get("infographics", {}).get("theme", {})
