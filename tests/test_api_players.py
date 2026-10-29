"""Unit tests for Player Explorer API endpoints."""
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient
from cricketlens.api.app import app

client = TestClient(app)
DATA = Path(__file__).resolve().parents[1] / "data" / "processed"


def test_list_players_default():
    res = client.get("/api/players")
    assert res.status_code == 200
    data = res.json()
    assert "players" in data
    assert data["total_count"] >= 69
    assert len(data["players"]) <= 20

    # Top player should have highest runs
    top = data["players"][0]
    assert "batter_id" in top
    assert "name" in top
    assert top["total_runs"] > 3000
    assert top["milestone30_rate"] > 0


def test_list_players_filter_leaderboard():
    # The 40+ innings tier covers the full 2008-2026 history; 69 was the size of
    # the 2018-2025 Stage 2 cohort. A batting innings is any crease appearance,
    # including non-striker-only ones, counted per registry ID.
    appearances = pd.read_csv(DATA.parent / "derived" / "batting_appearances.csv", usecols=["player_id"])
    expected = int((appearances.groupby("player_id").size() >= 40).sum())

    res = client.get("/api/players?experience_filter=leaderboard_only")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == expected
    assert all(p["is_stage02_leaderboard"] for p in data["players"])


def test_list_players_search():
    res = client.get("/api/players?query=Kohli")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 1
    names = [p["name"] for p in data["players"]]
    assert any("Kohli" in n for n in names)


def test_player_overview_kohli():
    res = client.get("/api/players/ba607b88/overview")
    assert res.status_code == 200
    data = res.json()

    assert data["batter_id"] == "ba607b88"
    assert "Kohli" in data["name"]
    assert data["career_summary"]["innings"] >= 100
    assert data["career_summary"]["total_runs"] > 4000

    # Full-history 30+ rate from ball-by-ball runs; the old "> 0.5" threshold came
    # from the 2018-2025 Stage 2 cohort, where Kohli's rate was 0.534.
    deliveries = pd.read_csv(DATA / "deliveries.csv", usecols=["match_id", "innings", "batter", "runs_batter"])
    kohli = deliveries[deliveries["batter"] == "V Kohli"].groupby(["match_id", "innings"])["runs_batter"].sum()
    assert data["career_summary"]["milestone30_rate"] == round(float((kohli >= 30).mean()), 3)

    # Milestone breakdown sums to 100% (within rounding)
    mb = data["milestone_breakdown"]
    total_pct = mb["below_30_pct"] + mb["score_30_to_49_pct"] + mb["score_50_plus_pct"]
    assert 99.0 <= total_pct <= 101.0

    # Recent matches should have real data
    assert len(data["recent_matches"]) > 0
    first_match = data["recent_matches"][0]
    assert "match_id" in first_match
    assert "runs" in first_match
    assert "milestone_badge" in first_match


def test_player_overview_not_found():
    res = client.get("/api/players/non-existent-player-id/overview")
    assert res.status_code == 404
