"""Unit tests for Statistics & EDA API endpoints."""
from fastapi.testclient import TestClient
from cricketlens.api.app import app

client = TestClient(app)


def test_eda_catalog_endpoint():
    res = client.get("/api/eda/catalog")
    assert res.status_code == 200
    data = res.json()
    assert "figures" in data
    assert data["total_figures"] == 20
    assert len(data["figures"]) == 20
    assert len(data["categories"]) >= 5

    first_fig = data["figures"][0]
    assert first_fig["figure_num"] == 1
    assert "Scoring Trend" in first_fig["title"]
    assert len(first_fig["key_findings"]) > 0
    assert "source_file" in first_fig


def test_eda_summary_endpoint():
    res = client.get("/api/eda/summary")
    assert res.status_code == 200
    data = res.json()

    # Scoring trends
    assert "scoring_trends" in data
    assert len(data["scoring_trends"]) == 18

    # Phase patterns
    assert "phase_patterns" in data
    assert len(data["phase_patterns"]) == 3
    phases = [p["phase"] for p in data["phase_patterns"]]
    assert "Powerplay (1-6)" in phases
    assert "Death (17-20)" in phases

    # Correlations
    assert "correlations" in data
    corr = data["correlations"]
    assert "runs" in corr["pearson"]
    assert "wickets" in corr["pearson"]["runs"]
    assert corr["pearson"]["runs"]["wickets"] < 0  # Negative correlation

    # Toss and Venue
    assert len(data["toss_crosstab"]) > 0
    assert len(data["venue_means"]) >= 10
    assert len(data["missingness_audit"]) > 0


def test_eda_figure_stream():
    res = client.get("/api/eda/figures/01_season_scoring_trend.png")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert len(res.content) > 10000


def test_eda_figure_invalid_name():
    res = client.get("/api/eda/figures/../../etc/passwd")
    assert res.status_code == 400 or res.status_code == 404
