"""Runtime settings for the CricketLens API, read once at import."""
from __future__ import annotations

import os
from pathlib import Path

# The directory holding data/, models/ and reports/. Every runtime file path is resolved from it:
# CRICKETLENS_ROOT when set, otherwise the repository root found from this file's location
# (src/cricketlens/api/settings.py), never the current working directory.
PROJECT_ROOT = Path(os.environ.get("CRICKETLENS_ROOT") or Path(__file__).resolve().parents[3]).resolve()
