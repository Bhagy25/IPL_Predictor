"""Tests for Stage 4.3B Complete IPL History (2008–2026) Canonical Analytics."""
from fastapi.testclient import TestClient
from cricketlens.api.app import app
from cricketlens.api.services.canonical_data import canonical_engine

client = TestClient(app)


def test_canonical_engine_initialization():
    """Verify that the canonical engine loads all 1,243 matches, 295,557 deliveries, and 806 players."""
    canonical_engine.ensure_loaded()
    assert len(canonical_engine._matches) == 1243
    assert len(canonical_engine._deliveries) == 295557
    assert len(canonical_engine._player_master_list) == 806
    assert canonical_engine._matches["season"].min() == 2008
    assert canonical_engine._matches["season"].max() == 2026


def test_team_analysis_canonical_15_teams():
    """Verify all 15 canonical teams are returned with correct status and titles."""
    res = client.get("/api/teams")
    assert res.status_code == 200
    data = res.json()
    assert data["total_active"] == 10
    assert data["total_defunct"] == 5
    assert len(data["teams"]) == 15

    teams_map = {t["name"]: t for t in data["teams"]}
    assert "Chennai Super Kings" in teams_map
    assert "Mumbai Indians" in teams_map
    assert "Deccan Chargers" in teams_map
    assert "Gujarat Titans" in teams_map

    # Title verification
    assert teams_map["Mumbai Indians"]["titles"] == 5
    assert teams_map["Chennai Super Kings"]["titles"] == 5
    assert teams_map["Kolkata Knight Riders"]["titles"] == 3
    assert teams_map["Royal Challengers Bengaluru"]["titles"] == 2
    assert teams_map["Deccan Chargers"]["titles"] == 1
    assert teams_map["Deccan Chargers"]["status"] == "Defunct"


def test_team_overview_all_time_and_season_filter():
    """Verify all-time record and dynamic season filter for CSK."""
    # All-time
    res = client.get("/api/teams/chennai-super-kings/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["team"]["short_name"] == "CSK"
    assert data["all_time"]["played"] == 266
    assert data["all_time"]["wins"] == 148
    assert data["all_time"]["losses"] == 117
    assert data["all_time"]["win_pct"] == 55.85
    assert data["all_time"]["runs_scored"] > 40000
    assert data["all_time"]["runs_conceded"] > 39000
    assert data["all_time"]["wickets_lost"] > 1400
    assert data["all_time"]["wickets_taken"] > 1600

    # Dynamic season filter: 2024
    res_2024 = client.get("/api/teams/chennai-super-kings/overview?season=2024")
    assert res_2024.status_code == 200
    data_2024 = res_2024.json()
    assert data_2024["all_time"]["played"] == 14
    assert data_2024["all_time"]["wins"] == 7
    assert data_2024["all_time"]["losses"] == 7
    assert data_2024["all_time"]["win_pct"] == 50.0


def test_team_head_to_head_full_history():
    """Verify full 2008-2026 head-to-head records between CSK and MI."""
    res = client.get("/api/teams/head-to-head?team1=chennai-super-kings&team2=mumbai-indians")
    assert res.status_code == 200
    data = res.json()
    assert data["total_matches"] == 38
    assert data["team1_wins"] == 17
    assert data["team2_wins"] == 21
    assert len(data["recent_meetings"]) == 38
    assert data["recent_meetings"][0]["match_id"] > 0
    assert "vs" in data["recent_meetings"][0]["margin_or_summary"]


def test_player_explorer_total_806_and_roles():
    """Verify Player Explorer covers all 806 players and supports role filtering."""
    # All players
    res_all = client.get("/api/players?page_size=1")
    assert res_all.status_code == 200
    assert res_all.json()["total_count"] == 806

    # Batters only
    res_bat = client.get("/api/players?role=batters&page_size=1")
    assert res_bat.status_code == 200
    assert res_bat.json()["total_count"] == 736

    # Bowlers only
    res_bowl = client.get("/api/players?role=bowlers&page_size=1")
    assert res_bowl.status_code == 200
    assert res_bowl.json()["total_count"] == 577


def test_player_profile_dual_career_kohli():
    """Verify Virat Kohli's batting and bowling figures across 2008–2026."""
    res = client.get("/api/players/ba607b88/overview")
    assert res.status_code == 200
    data = res.json()
    assert "Kohli" in data["name"]
    
    # Batting
    bat = data["career_batting"]
    assert bat is not None
    assert bat["runs"] == 9336
    assert bat["innings"] == 267
    assert bat["scores_100_plus"] == 9
    assert bat["highest_score"] == "113*"
    assert bat["fours"] == 788
    assert bat["sixes"] == 307

    # Bowling (part-time bowler)
    bowl = data["career_bowling"]
    assert bowl is not None
    assert bowl["wickets"] == 4
    assert bowl["innings"] == 26

    # Match logs
    assert len(data["recent_matches"]) == 267
    first_log = data["recent_matches"][0]
    assert "runs" in first_log
    assert "overs_bowled" in first_log


def test_player_profile_pure_bowler_bumrah():
    """Verify Jasprit Bumrah's profile has proper bowling metrics and clean batting handling."""
    # Find Bumrah by search
    res_search = client.get("/api/players?query=Bumrah")
    assert res_search.status_code == 200
    pid = res_search.json()["players"][0]["player_id"]

    res_jb = client.get(f"/api/players/{pid}/overview")
    assert res_jb.status_code == 200
    jb = res_jb.json()
    assert "Bumrah" in jb["name"]
    
    # Bowling
    bowl = jb["career_bowling"]
    assert bowl is not None
    assert bowl["wickets"] == 199
    assert bowl["economy_rate"] < 7.5
    assert bowl["best_bowling"] == "5/10"


def test_eda_full_history_19_seasons():
    """Verify the 2008–2026 full history EDA endpoint covers all 15 analysis areas."""
    res = client.get("/api/eda/full-history")
    assert res.status_code == 200
    data = res.json()
    
    # 19 seasons
    assert len(data["season_evolution"]) == 19
    assert data["season_evolution"][0]["season"] == 2008
    assert data["season_evolution"][-1]["season"] == 2026
    
    # First innings trends across 19 seasons
    assert len(data["first_innings_trends"]) == 19

    # 5 tournament eras
    eras = set(p["era"] for p in data["era_phase_patterns"])
    assert len(eras) == 5

    # Boundary evolution
    assert len(data["boundaries_by_season"]) == 19

    # Toss and chasing across all 19 seasons
    assert len(data["toss_and_chasing"]) == 19

    # Venue par scoring
    assert len(data["venue_par"]) >= 15

    # Leaders
    assert data["top_all_time_batters"][0]["batter"] == "V Kohli"
    assert data["top_all_time_bowlers"][0]["bowler"] == "YS Chahal"
