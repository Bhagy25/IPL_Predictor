"""Vercel Python Function entrypoint: serves the existing CricketLens FastAPI app for every /api/* request.

vercel.json rewrites /api/* here. The cricketlens package lives in src/ and is not pip-installed in the
function, so src/ is put on the import path before the app is imported.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cricketlens.api.app import app  # noqa: E402

__all__ = ["app"]
