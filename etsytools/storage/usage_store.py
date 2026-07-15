from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from etsytools.paths import USAGE_PATH


def get_tavily_usage(usage_file: Path = USAGE_PATH) -> dict[str, int | str]:
    """Return this month's Tavily usage counter."""
    current_month = datetime.now().strftime("%Y-%m")
    default_data: dict[str, int | str] = {
        "current_month": current_month,
        "tavily_searches": 0,
    }

    if not usage_file.exists():
        return default_data

    try:
        with usage_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return default_data

    if data.get("current_month") != current_month:
        return default_data

    searches = data.get("tavily_searches", 0)
    if not isinstance(searches, int):
        searches = 0
    return {"current_month": current_month, "tavily_searches": searches}


def increment_tavily_usage(usage_file: Path = USAGE_PATH) -> int:
    """Increment and persist the monthly Tavily usage counter."""
    usage = get_tavily_usage(usage_file)
    usage["tavily_searches"] = int(usage.get("tavily_searches", 0)) + 1

    usage_file.parent.mkdir(parents=True, exist_ok=True)
    with usage_file.open("w", encoding="utf-8") as f:
        json.dump(usage, f, indent=2)

    return int(usage["tavily_searches"])

