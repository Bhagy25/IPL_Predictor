"""Runtime files are found from the project root, not from the directory the server was started in."""
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cricketlens.api.app import app
from cricketlens.api.services.eda_service import EDAService
from cricketlens.api.settings import PROJECT_ROOT

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
FIGURE = ROOT / "reports" / "figures" / "stage_02" / "01_season_scoring_trend.png"
TRENDS = ROOT / "reports" / "stage_02" / "session_01" / "season_first_innings_trends.csv"


def test_project_root_is_the_repository_root():
    assert PROJECT_ROOT == ROOT.resolve()


@pytest.mark.skipif(not FIGURE.is_file(), reason="Stage 2 figures not available")
def test_figure_is_served_from_another_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = client.get(f"/api/eda/figures/{FIGURE.name}")
    assert res.status_code == 200
    assert res.content == FIGURE.read_bytes()


@pytest.mark.skipif(not TRENDS.is_file(), reason="Stage 2 tables not available")
def test_summary_tables_load_from_another_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # A fresh service: the shared one caches the tables it loaded first
    summary = EDAService().get_summary()
    assert summary.scoring_trends == pd.read_csv(TRENDS).to_dict(orient="records")
    assert summary.phase_patterns and summary.toss_crosstab and summary.venue_means and summary.missingness_audit


def test_root_can_be_overridden_by_environment(tmp_path):
    code = "from cricketlens.api.settings import PROJECT_ROOT; print(PROJECT_ROOT)"
    env = dict(os.environ, CRICKETLENS_ROOT=str(tmp_path))
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert Path(out.stdout.strip()) == tmp_path.resolve()
