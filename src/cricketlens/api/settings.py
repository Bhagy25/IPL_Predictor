"""Runtime settings for the CricketLens API, read once at import."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

# The directory holding data/, models/ and reports/. Every runtime file path is resolved from it:
# CRICKETLENS_ROOT when set, otherwise the repository root found from this file's location
# (src/cricketlens/api/settings.py), never the current working directory.
PROJECT_ROOT = Path(os.environ.get("CRICKETLENS_ROOT") or Path(__file__).resolve().parents[3]).resolve()

# The local Vite dev server; a same-origin deployment needs no cross-origin access at all
DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def cors_allow_origins(value: Optional[str] = None) -> List[str]:
    """Origins allowed to call the API from another origin.

    Read from CORS_ALLOW_ORIGINS (comma-separated, e.g. "https://a.example,https://b.example") unless
    `value` is given; unset means the local dev server origins, and an empty value allows none.
    """
    raw = os.environ.get("CORS_ALLOW_ORIGINS") if value is None else value
    if raw is None:
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
