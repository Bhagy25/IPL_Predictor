"""Tests for Stage 4.3B Complete IPL History (2008–2026) Canonical Analytics."""
import json
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient
from cricketlens.api.app import app
from cricketlens.api.services.canonical_data import canonical_engine

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
DERIVED = ROOT / "data" / "derived"


def directory_ids():
    """Registry IDs at the crease or bowling in an ordinary innings, computed from data/derived."""
    squads = pd.read_csv(DERIVED / "match_players.csv", usecols=["match_id", "player_name", "player_id"])
    bowling = pd.read_csv(DATA / "deliveries.csv", usecols=["match_id", "bowler"]).drop_duplicates()
    bowlers = set(
        bowling.merge(squads, left_on=["match_id", "bowler"], right_on=["match_id", "player_name"])["player_id"]
    )
    batters = set(pd.read_csv(DERIVED / "batting_appearances.csv", usecols=["player_id"])["player_id"])
    return batters, bowlers


def test_canonical_engine_initialization():
    """Verify that the canonical engine loads all 1,243 matches, 295,557 deliveries and every player."""
    canonical_engine.ensure_loaded()
    batters, bowlers = directory_ids()
    assert len(canonical_engine._matches) == 1243
    assert len(canonical_engine._deliveries) == 295557
    assert len(canonical_engine._player_master_list) == len(batters | bowlers)
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
    # Win % = wins / (matches - no results) to one decimal: 148 / 265 = 55.849...
    assert data["all_time"]["no_results"] == 1 and data["all_time"]["win_pct_denominator"] == 265
    assert data["all_time"]["win_pct"] == 55.8
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
    matches = pd.read_csv(DATA / "matches.csv")
    pair = {"Chennai Super Kings", "Mumbai Indians"}
    meetings = matches[[{a, b} == pair for a, b in zip(matches["team1"], matches["team2"])]]

    res = client.get("/api/teams/head-to-head?team1=chennai-super-kings&team2=mumbai-indians")
    assert res.status_code == 200
    data = res.json()
    assert data["total_matches"] == len(meetings)
    assert data["team1_wins"] == int((meetings["final_winner"] == "Chennai Super Kings").sum())
    assert data["team2_wins"] == int((meetings["final_winner"] == "Mumbai Indians").sum())
    assert len(data["recent_meetings"]) == len(meetings)
    assert data["recent_meetings"][0]["match_id"] > 0
    assert "vs" in data["recent_meetings"][0]["margin_or_summary"]


REFERENCE_ROLES = {
    "Batter": ["V Kohli", "RG Sharma", "SK Raina", "DA Warner", "MS Dhoni", "AB de Villiers", "S Dhawan"],
    "Bowler": ["JJ Bumrah", "YS Chahal", "SL Malinga", "B Kumar", "Rashid Khan", "A Mishra"],
    "All-Rounder": ["RA Jadeja", "HH Pandya", "AD Russell", "SR Watson", "DJ Bravo"],
}


def test_player_explorer_totals_and_roles():
    """Directory totals match registry IDs in the derived tables; role filters and reference roles hold."""
    batters, bowlers = directory_ids()
    people = set(pd.read_csv(DERIVED / "people.csv", usecols=["player_id"])["player_id"])
    assert (batters | bowlers) <= people
    # 805 / 741 / 576 at the time of writing: 736 batters faced a ball, 5 more were only at the crease
    assert (len(batters | bowlers), len(batters), len(bowlers)) == (805, 741, 576)

    res_all = client.get("/api/players?page_size=1")
    assert res_all.status_code == 200
    counts = res_all.json()["directory_counts"]
    assert res_all.json()["total_count"] == counts["all"] == len(batters | bowlers)
    assert client.get("/api/players?role=batters&page_size=1").json()["total_count"] == counts["batters"] == len(batters)
    assert client.get("/api/players?role=bowlers&page_size=1").json()["total_count"] == counts["bowlers"] == len(bowlers)
    assert client.get("/api/players?role=all-rounders&page_size=1").json()["total_count"] == counts["all_rounders"]

    for role, names in REFERENCE_ROLES.items():
        for name in names:
            players = client.get("/api/players", params={"query": name, "page_size": 50}).json()["players"]
            assert next(p for p in players if p["name"] == name)["role"] == role, name


def test_player_profile_dual_career_kohli():
    """Verify Virat Kohli's batting and bowling figures across 2008–2026."""
    deliveries = pd.read_csv(DATA / "deliveries.csv", usecols=["match_id", "innings", "batter", "bowler"])
    batted = deliveries.loc[deliveries["batter"] == "V Kohli", ["match_id", "innings"]].drop_duplicates()
    bowled_matches = set(deliveries.loc[deliveries["bowler"] == "V Kohli", "match_id"])

    res = client.get("/api/players/ba607b88/overview")
    assert res.status_code == 200
    data = res.json()
    assert "Kohli" in data["name"]

    # Batting
    bat = data["career_batting"]
    assert bat is not None
    assert bat["runs"] == 9336
    assert bat["innings"] == len(batted)
    assert bat["scores_100_plus"] == 9
    assert bat["highest_score"] == "113*"

    # Bowling (part-time bowler)
    bowl = data["career_bowling"]
    assert bowl is not None
    assert bowl["wickets"] == 4
    assert bowl["innings"] == 26

    # Match logs: every squad appearance, which includes every match in which he batted or bowled
    squads = pd.read_csv(DATA.parent / "derived" / "match_players.csv", usecols=["match_id", "player_id"])
    log = client.get("/api/players/ba607b88/matches", params={"page_size": 100}).json()
    logged = [m["match_id"] for page in range(1, log["total_pages"] + 1) for m in client.get(
        "/api/players/ba607b88/matches", params={"page": page, "page_size": 100}).json()["matches"]]
    assert sorted(logged) == sorted(squads.loc[squads["player_id"] == "ba607b88", "match_id"])
    assert set(batted["match_id"]) | bowled_matches <= set(logged)
    first_log = log["matches"][0]
    assert "runs" in first_log["batting"]
    assert "overs" in first_log["bowling"]


def test_player_profile_kohli_boundaries():
    """Fours and sixes count boundaries only.

    Cricsheet marks scoring shots that were not boundaries with `non_boundary`
    (all-run fours, overthrows), so the expected counts come from the raw JSON.
    """
    fours = sixes = 0
    for path in (ROOT / "data" / "raw" / "ipl_json").glob("*.json"):
        match = json.loads(path.read_text(encoding="utf-8"))
        for innings in match["innings"]:
            if innings.get("super_over"):
                continue
            for over in innings["overs"]:
                for ball in over["deliveries"]:
                    if ball["batter"] != "V Kohli" or ball["runs"].get("non_boundary"):
                        continue
                    fours += ball["runs"]["batter"] == 4
                    sixes += ball["runs"]["batter"] == 6

    bat = client.get("/api/players/ba607b88/overview").json()["career_batting"]
    assert bat["fours"] == fours
    assert bat["sixes"] == sixes


def test_player_profile_pure_bowler_bumrah():
    """Verify Jasprit Bumrah's profile has proper bowling metrics and clean batting handling."""
    # Bowler-credited wickets counted directly from the raw JSON (ordinary innings only)
    credited_kinds = {"bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket"}
    expected_wickets = 0
    for path in (ROOT / "data" / "raw" / "ipl_json").glob("*.json"):
        match = json.loads(path.read_text(encoding="utf-8"))
        for innings in match["innings"]:
            if innings.get("super_over"):
                continue
            for over in innings["overs"]:
                for ball in over["deliveries"]:
                    if ball["bowler"] == "JJ Bumrah":
                        expected_wickets += sum(w["kind"] in credited_kinds for w in ball.get("wickets", []))
    assert expected_wickets == 187  # sanity check against the Part 3 baseline

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
    assert bowl["wickets"] == expected_wickets
    assert bowl["economy_rate"] < 7.5
    assert bowl["best_bowling"] == "5/10"


def test_eda_analysis_covers_19_seasons():
    """The filterable EDA analysis (which replaced /api/eda/full-history) covers 2008–2026 by default."""
    res = client.get("/api/eda/analysis")
    assert res.status_code == 200
    areas = res.json()["areas"]

    # 19 seasons
    seasons = areas["matches_runs"]["data"]["by_season"]
    assert len(seasons) == 19
    assert seasons[0]["season"] == 2008
    assert seasons[-1]["season"] == 2026

    # First innings trends across 19 seasons
    assert sum(s["first_innings_mean"] is not None for s in areas["scoring_trends"]["data"]["by_season"]) == 19

    # Phases: powerplay, middle and death in each of the 19 seasons (replaces the five-era table)
    phases = areas["phases"]["data"]["by_season"]
    assert len(phases) == 19 and all(len(s["phases"]) == 3 for s in phases)

    # Boundary evolution
    assert len(areas["boundaries"]["data"]["by_season"]) == 19

    # Toss and chasing across all 19 seasons
    assert len(areas["toss"]["data"]["by_season"]) == 19
    assert len(areas["innings_order"]["data"]["by_season"]) == 19

    # Venue scoring: grounds with at least 10 matches
    venues = client.get("/api/eda/analysis", params={"venue_min_matches": 10}).json()["areas"]["venues"]["data"]
    assert venues["venues_shown"] >= 15

    # Leaders
    assert areas["batting_distribution"]["data"]["leaders"][0]["name"] == "V Kohli"
    assert areas["bowling"]["data"]["leaders"][0]["name"] == "YS Chahal"
