"""Regression tests for the team and player API fixes.

Expected values are computed here from the processed CSVs with plain pandas,
independently of the analytics engine, rather than hard-coded.
"""
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cricketlens.api.app import app

client = TestClient(app)
DATA = Path(__file__).resolve().parents[1] / "data" / "processed"


@pytest.fixture(scope="module")
def matches() -> pd.DataFrame:
    return pd.read_csv(DATA / "matches.csv")


@pytest.fixture(scope="module")
def deliveries() -> pd.DataFrame:
    return pd.read_csv(DATA / "deliveries.csv", usecols=["match_id", "season", "batter", "bowler"])


def team_seasons(matches: pd.DataFrame, team: str) -> list:
    played = matches[(matches["team1"] == team) | (matches["team2"] == team)]
    return sorted(int(s) for s in played["season"].unique())


def team_record(matches: pd.DataFrame, team: str, season: int) -> dict:
    tm = matches[((matches["team1"] == team) | (matches["team2"] == team)) & (matches["season"] == season)]
    wins = int((tm["final_winner"] == team).sum())
    decided = int(tm["final_winner"].notna().sum())
    return {"played": len(tm), "wins": wins, "losses": decided - wins, "win_pct": round(wins / decided * 100, 2)}


def player_id(name: str) -> str:
    res = client.get("/api/players", params={"query": name, "page_size": 100})
    assert res.status_code == 200
    return next(p["player_id"] for p in res.json()["players"] if p["name"] == name)


# ------------------------------------------------------------------ players

def first_2026_debutant(deliveries: pd.DataFrame) -> str:
    appearances = pd.concat([
        deliveries[["season", "batter"]].rename(columns={"batter": "player"}),
        deliveries[["season", "bowler"]].rename(columns={"bowler": "player"}),
    ])
    first = appearances.groupby("player")["season"].min()
    return sorted(first[first == 2026].index)[0]


@pytest.mark.parametrize("name", ["V Kohli", "JJ Bumrah", "RA Jadeja", "2026 debutant"])
def test_player_profile_returns_200(name, deliveries):
    if name == "2026 debutant":
        name = first_2026_debutant(deliveries)
    res = client.get(f"/api/players/{player_id(name)}/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == name
    assert len(data["recent_matches"]) > 0
    assert data["career_batting"] is not None or data["career_bowling"] is not None

    expected_seasons = sorted(
        int(s) for s in deliveries.loc[(deliveries["batter"] == name) | (deliveries["bowler"] == name), "season"].unique()
    )
    assert data["seasons_played"] == expected_seasons


def test_player_profile_bowling_strike_rate_uses_career_balls():
    data = client.get(f"/api/players/{player_id('JJ Bumrah')}/overview").json()
    bowl = data["career_bowling"]
    assert bowl["bowling_strike_rate"] == round(bowl["legal_deliveries"] / bowl["wickets"], 2)


# ------------------------------------------------------------------ teams

def test_list_teams_returns_200_with_derived_seasons(matches):
    res = client.get("/api/teams")
    assert res.status_code == 200
    teams = res.json()["teams"]
    assert len(teams) == 15
    for team in teams:
        assert team["active_seasons"] == team_seasons(matches, team["name"])
        assert isinstance(team["seasons_active"], str) and team["seasons_active"]


def test_every_team_overview_returns_200(matches):
    for team in client.get("/api/teams").json()["teams"]:
        res = client.get(f"/api/teams/{team['id']}/overview")
        assert res.status_code == 200, team["id"]
        data = res.json()
        assert data["team"]["active_seasons"] == team_seasons(matches, team["name"])
        tm = matches[(matches["team1"] == team["name"]) | (matches["team2"] == team["name"])]
        assert data["all_time"]["played"] == len(tm)


def test_franchise_seasons_match_known_history():
    seasons = {t["short_name"]: t["active_seasons"] for t in client.get("/api/teams").json()["teams"]}
    for team in ("CSK", "RR"):
        assert 2016 not in seasons[team] and 2017 not in seasons[team]
    assert seasons["GL"] == [2016, 2017]
    assert seasons["RPS"] == [2016, 2017]
    assert seasons["KTK"] == [2011]
    assert seasons["PWI"] == [2011, 2012, 2013]
    assert seasons["DC_OLD"] == [2008, 2009, 2010, 2011, 2012]
    assert seasons["SRH"][0] == 2013
    assert seasons["LSG"][0] == 2022


def test_team_joined_after_2008_has_no_earlier_seasons():
    gt = next(t for t in client.get("/api/teams").json()["teams"] if t["short_name"] == "GT")
    assert min(gt["active_seasons"]) == 2022
    assert client.get("/api/teams/gujarat-titans/overview?season=2021").status_code == 404


@pytest.mark.parametrize("team_id,team,season", [
    ("chennai-super-kings", "Chennai Super Kings", 2024),
    ("gujarat-titans", "Gujarat Titans", 2022),
    ("deccan-chargers", "Deccan Chargers", 2009),
])
def test_season_filter_recomputes(matches, team_id, team, season):
    res = client.get(f"/api/teams/{team_id}/overview", params={"season": season})
    assert res.status_code == 200
    record = res.json()["all_time"]
    expected = team_record(matches, team, season)
    assert {k: record[k] for k in expected} == expected

    all_time = client.get(f"/api/teams/{team_id}/overview").json()["all_time"]
    assert record["played"] < all_time["played"]


def test_toss_stats_use_api_field_names(matches):
    toss = client.get("/api/teams/chennai-super-kings/overview").json()["toss_stats"]
    won = matches[matches["toss_winner"] == "Chennai Super Kings"]
    assert toss["tosses_won"] == len(won)
    assert toss["elected_to_field"] == int((won["toss_decision"] == "field").sum())
    assert toss["elected_to_bat"] == int((won["toss_decision"] == "bat").sum())


# ------------------------------------------------------------------ schema

def test_openapi_schema_returns_200():
    res = client.get("/openapi.json")
    assert res.status_code == 200
    paths = res.json()["paths"]
    for path in (
        "/api/teams",
        "/api/teams/{team_id}/overview",
        "/api/teams/head-to-head",
        "/api/players",
        "/api/players/{player_id}/overview",
    ):
        assert path in paths
    assert client.get("/docs").status_code == 200
