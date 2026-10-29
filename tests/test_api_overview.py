"""Tests for the CricketLens FastAPI Analytical Backend."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cricketlens.api.app import app
from cricketlens.api.services.overview_service import overview_service, FRANCHISE_TITLES


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert data["archive_matches"] == 1243
    assert "timestamp" in data
    assert data["service"] == "CricketLens Analytical Backend"


def test_overview_summary_endpoint(client):
    response = client.get("/api/overview/summary")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "coverage" in data
    assert "notices" in data

    metrics = {m["id"]: m for m in data["metrics"]}
    assert len(metrics) == 8

    # Verify all 8 canonical KPI cards
    assert metrics["seasons"]["value"] == "19"
    assert metrics["seasons"]["numeric_value"] == 19.0

    assert metrics["matches"]["value"] == "1,243"
    assert metrics["matches"]["numeric_value"] == 1243.0

    assert metrics["deliveries"]["value"] == "295,557"
    assert metrics["deliveries"]["numeric_value"] == 295557.0

    assert metrics["teams"]["value"] == "15"
    assert metrics["teams"]["numeric_value"] == 15.0

    # Batter count KPI accurately labeled and defined
    assert metrics["players"]["label"] == "Batters analyzed"
    assert metrics["players"]["value"] == "736"
    assert metrics["players"]["numeric_value"] == 736.0
    assert "unique batters" in metrics["players"]["statusText"]

    assert metrics["venues"]["value"] == "38"
    assert metrics["venues"]["numeric_value"] == 38.0

    assert metrics["runs"]["value"] == "401,423"
    assert metrics["runs"]["numeric_value"] == 401423.0

    assert metrics["wickets"]["value"] == "14,655"
    assert metrics["wickets"]["numeric_value"] == 14655.0

    # Coverage verification
    coverage = data["coverage"]
    assert coverage["total_matches"] == 1243
    assert coverage["seasons_count"] == 19
    assert coverage["first_match_date"] == "2008-04-18"
    assert coverage["last_match_date"] == "2026-05-31"


def test_overview_charts_endpoint(client):
    response = client.get("/api/overview/charts")
    assert response.status_code == 200
    data = response.json()

    # 1. Matches per season
    matches_per_season = data["matches_per_season"]
    assert len(matches_per_season) == 19
    assert matches_per_season[0]["season"] == 2008
    assert matches_per_season[0]["matches"] == 58
    assert matches_per_season[-1]["season"] == 2026
    assert matches_per_season[-1]["matches"] == 74
    total_m = sum(x["matches"] for x in matches_per_season)
    assert total_m == 1243

    # 2. Scoring trends
    trends = data["scoring_trends"]
    assert len(trends) == 19
    assert trends[0]["season"] == 2008
    assert trends[0]["avg_first_innings_runs"] > 140
    assert trends[-1]["season"] == 2026
    assert trends[-1]["avg_first_innings_runs"] > 180

    # 3. Match result distribution (no double counting)
    results = {r["category"]: r for r in data["result_distribution"]}
    assert "Regulation Win" in results
    assert "Tie (Super Over)" in results
    assert "No Result" in results
    assert results["Regulation Win"]["count"] == 1218
    assert results["Tie (Super Over)"]["count"] == 16
    assert results["No Result"]["count"] == 9
    assert sum(r["count"] for r in data["result_distribution"]) == 1243

    # 4. Scoring distribution (1,237 ordinary first innings)
    bins = data["scoring_distribution"]
    assert len(bins) == 5
    spans = [b["span"] for b in bins]
    assert "< 120" in spans
    assert "150–179" in spans
    assert "210+" in spans
    total_histogram_innings = sum(b["count"] for b in bins)
    assert total_histogram_innings == 1237  # 1,243 matches - 6 matches without ordinary first innings

    # 5. Team records - verify all active franchises
    teams = {t["team"]: t for t in data["team_records"]}
    assert len(teams) == 10
    assert teams["Chennai Super Kings"]["titles"] == 5
    assert teams["Mumbai Indians"]["titles"] == 5
    assert teams["Kolkata Knight Riders"]["titles"] == 3
    assert teams["Royal Challengers Bengaluru"]["titles"] == 2
    assert teams["Royal Challengers Bengaluru"]["title_years"] == [2025, 2026]
    assert teams["Gujarat Titans"]["titles"] == 1
    assert teams["Rajasthan Royals"]["titles"] == 1
    assert teams["Sunrisers Hyderabad"]["titles"] == 1
    assert teams["Sunrisers Hyderabad"]["title_years"] == [2016]


def test_championship_records_19_seasons_complete():
    """Verify all 19 seasons (2008–2026) have champions accounted for without double-counting."""
    all_winning_years = []
    for franchise, years in FRANCHISE_TITLES.items():
        all_winning_years.extend(years)

    # Every tournament edition from 2008 to 2026 must have exactly one champion
    expected_years = list(range(2008, 2027))
    assert sorted(all_winning_years) == expected_years
    assert len(all_winning_years) == 19

    # Verify franchise breakdown
    assert FRANCHISE_TITLES["Chennai Super Kings"] == [2010, 2011, 2018, 2021, 2023]
    assert FRANCHISE_TITLES["Mumbai Indians"] == [2013, 2015, 2017, 2019, 2020]
    assert FRANCHISE_TITLES["Kolkata Knight Riders"] == [2012, 2014, 2024]
    assert FRANCHISE_TITLES["Royal Challengers Bengaluru"] == [2025, 2026]
    assert FRANCHISE_TITLES["Rajasthan Royals"] == [2008]
    assert FRANCHISE_TITLES["Sunrisers Hyderabad"] == [2016]
    assert FRANCHISE_TITLES["Gujarat Titans"] == [2022]
    # Deccan Chargers kept distinct
    assert FRANCHISE_TITLES["Deccan Chargers"] == [2009]

    # Active teams total 18 titles; defunct Deccan Chargers has 1 title
    active_titles = sum(len(years) for team, years in FRANCHISE_TITLES.items() if team != "Deccan Chargers")
    assert active_titles == 18


def test_delivery_and_innings_reconciliation():
    """Verify delivery arithmetic and first-innings sample size."""
    summary = overview_service.get_summary()
    metrics = {m.id: m for m in summary.metrics}

    total_deliveries = metrics["deliveries"].numeric_value
    assert total_deliveries == 295557.0

    # Legal balls = 284,465; illegal balls = 11,092 (wides: 9,871 + noballs: 1,221)
    legal_deliveries = 284465
    wides = 9871
    noballs = 1221
    assert legal_deliveries + wides + noballs == total_deliveries

    # Matches without ordinary first innings
    total_matches = summary.coverage.total_matches
    assert total_matches == 1243

    charts = overview_service.get_charts()
    total_first_innings = sum(b.count for b in charts.scoring_distribution)
    assert total_first_innings == 1237
    assert total_matches - total_first_innings == 6  # 6 matches had incomplete/no regular first innings


def test_service_caching_and_speed():
    # Force fresh load and verify caching
    overview_service._summary_cache = None
    overview_service._charts_cache = None

    s1 = overview_service.get_summary()
    s2 = overview_service.get_summary()
    assert s1 is s2

    c1 = overview_service.get_charts()
    c2 = overview_service.get_charts()
    assert c1 is c2
