"""Unit tests for Player Explorer API endpoints."""
from fastapi.testclient import TestClient
from cricketlens.api.app import app

client = TestClient(app)


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
    res = client.get("/api/players?experience_filter=leaderboard_only")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 69
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
    assert data["career_summary"]["milestone30_rate"] > 0.5

    # Milestone breakdown sums to 100% (within rounding)
    mb = data["milestone_breakdown"]
    total_pct = mb["below_30_pct"] + mb["score_30_to_49_pct"] + mb["score_50_plus_pct"]
    assert 99.0 <= total_pct <= 101.0

    # Recent matches should have real data
    assert len(data["recent_matches"]) > 0
    first_match = data["recent_matches"][0]
    assert "match_id" in first_match
    assert "runs" in first_match
    assert "milestone_label" in first_match


def test_player_overview_not_found():
    res = client.get("/api/players/non-existent-player-id/overview")
    assert res.status_code == 404
