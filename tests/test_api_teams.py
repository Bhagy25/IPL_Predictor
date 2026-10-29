"""Unit tests for Team Analysis API endpoints."""
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient
from cricketlens.api.app import app

DATA = Path(__file__).resolve().parents[1] / "data" / "processed"

client = TestClient(app)


def test_list_teams_endpoint():
    res = client.get("/api/teams")
    assert res.status_code == 200
    data = res.json()
    assert "teams" in data
    assert data["total_active"] == 10
    assert data["total_defunct"] == 5
    assert len(data["teams"]) == 15

    names = [t["name"] for t in data["teams"]]
    assert "Chennai Super Kings" in names
    assert "Mumbai Indians" in names
    assert "Royal Challengers Bengaluru" in names
    assert "Deccan Chargers" in names

    # Deccan Chargers must be marked Defunct and separate from SRH
    dc = next(t for t in data["teams"] if t["name"] == "Deccan Chargers")
    assert dc["status"] == "Defunct"
    assert dc["titles"] == 1
    assert dc["title_years"] == [2009]

    # RCB must have 2 titles
    rcb = next(t for t in data["teams"] if t["name"] == "Royal Challengers Bengaluru")
    assert rcb["titles"] == 2
    assert rcb["title_years"] == [2025, 2026]


def test_team_overview_endpoint():
    res = client.get("/api/teams/chennai-super-kings/overview")
    assert res.status_code == 200
    data = res.json()

    assert data["team"]["name"] == "Chennai Super Kings"
    assert data["all_time"]["played"] > 200
    assert data["all_time"]["wins"] > 100
    assert 40.0 < data["all_time"]["win_pct"] < 65.0
    assert "denominator_description" in data["all_time"]

    # Comparative window for an active team: the homepage window, counted here from matches.csv
    m = pd.read_csv(DATA / "matches.csv")
    last = m["season"].max()
    current = set(m.loc[m["season"] == last, "team1"]) | set(m.loc[m["season"] == last, "team2"])
    start = max(m[(m["team1"] == t) | (m["team2"] == t)]["season"].min() for t in current)
    rows = m[m["season"].between(start, last) & ((m["team1"] == "Chennai Super Kings") | (m["team2"] == "Chennai Super Kings"))]
    c = data["comparative_window"]
    assert (c["first_season"], c["last_season"], c["window"]) == (start, last, f"{start}–{last}")
    assert c["played"] == len(rows)
    assert c["wins"] == (rows["final_winner"] == "Chennai Super Kings").sum()
    assert c["losses"] == (rows["final_winner"].notna() & (rows["final_winner"] != "Chennai Super Kings")).sum()
    homepage = {r["team"]: r for r in client.get("/api/overview/charts").json()["team_records"]}["Chennai Super Kings"]
    assert (c["played"], c["wins"], c["losses"], c["win_pct"]) == (homepage["played"], homepage["wins"], homepage["losses"], homepage["win_pct"])

    # Conditions & Phase
    assert data["batting_first"]["played"] > 0
    assert data["chasing"]["played"] > 0
    assert len(data["season_history"]) > 10
    assert len(data["venue_records"]) > 0
    assert [p["phase"] for p in data["phases"]] == ["powerplay", "middle", "death"]
    assert data["phases"][0]["batting_run_rate"] > 0 and data["phases"][0]["economy"] > 0


def test_team_overview_not_found():
    res = client.get("/api/teams/non-existent-team/overview")
    assert res.status_code == 404


def test_head_to_head_endpoint():
    res = client.get("/api/teams/head-to-head?team1=chennai-super-kings&team2=mumbai-indians")
    assert res.status_code == 200
    data = res.json()

    assert data["team1"]["name"] == "Chennai Super Kings"
    assert data["team2"]["name"] == "Mumbai Indians"
    assert data["total_matches"] >= 35
    assert data["team1_wins"] + data["team2_wins"] <= data["total_matches"]
    assert len(data["recent_meetings"]) > 0

    first_meeting = data["recent_meetings"][0]
    assert "match_id" in first_meeting
    assert "venue" in first_meeting
    assert "margin_or_summary" in first_meeting


def test_head_to_head_invalid_team():
    res = client.get("/api/teams/head-to-head?team1=chennai-super-kings&team2=fake-team")
    assert res.status_code == 404
