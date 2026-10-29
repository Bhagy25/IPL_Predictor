"""Unit tests for Player Explorer API endpoints."""
from pathlib import Path

import pandas as pd
import pytest
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


# ------------------------------------------------------------------ directory rates and qualification

def directory(**params):
    """Every page of the directory for these query parameters."""
    players, page = [], 1
    while True:
        data = client.get("/api/players", params={**params, "page": page, "page_size": 100}).json()
        players += data["players"]
        if page >= data["total_pages"]:
            return players, data
        page += 1


def batting_record():
    """Innings, runs, balls and dismissals per registry ID from every crease appearance."""
    rows = pd.read_csv(DATA.parent / "derived" / "batting_appearances.csv")
    return rows.groupby("player_id").agg(
        innings=("runs", "size"), runs=("runs", "sum"), balls=("balls_faced", "sum"), outs=("dismissed", "sum"),
    )


def bowling_innings():
    """Bowling innings per registry ID: bowler names resolved through that match's squad list."""
    deliveries = pd.read_csv(DATA / "deliveries.csv", usecols=["match_id", "innings", "bowler"])
    squads = pd.read_csv(DATA.parent / "derived" / "match_players.csv", usecols=["match_id", "player_name", "player_id"])
    spells = deliveries.drop_duplicates().merge(
        squads.rename(columns={"player_name": "bowler"}), on=["match_id", "bowler"], how="left", validate="many_to_one"
    )
    assert spells["player_id"].notna().all()
    return spells.groupby("player_id").size()


def test_directory_rates_are_null_without_a_denominator():
    record = batting_record()
    listed = {p["player_id"]: p for p in directory()[0]}
    for pid, r in record.iterrows():
        p = listed[pid]
        # Plain ints: numpy scalars round 1017 / 40 = 25.425 to 25.42, Python's round() gives 25.43
        runs, balls, outs = int(r["runs"]), int(r["balls"]), int(r["outs"])
        assert p["batting_avg"] == (round(runs / outs, 2) if outs else None), pid
        assert p["strike_rate"] == (round(runs / balls * 100, 2) if balls else None), pid
    # Never dismissed: no batting average, not total runs
    never_out = record[(record["outs"] == 0) & (record["runs"] > 0)]
    assert len(never_out) and all(listed[pid]["batting_avg"] is None for pid in never_out.index)
    # Never bowled: no economy or bowling average, not 0
    non_bowlers = set(listed) - set(bowling_innings().index)
    assert non_bowlers and all(listed[pid]["economy"] is None and listed[pid]["bowling_avg"] is None for pid in non_bowlers)
    # Never batted: no batting rates
    assert all(listed[pid]["batting_avg"] is None and listed[pid]["strike_rate"] is None for pid in set(listed) - set(record.index))


def test_rate_sort_puts_undefined_rates_last_and_keeps_everyone():
    players, data = directory(sort_by="batting_avg")
    assert data["total_count"] == data["directory_counts"]["all"] and data["qualification"] is None
    values = [p["batting_avg"] for p in players]
    defined = [v for v in values if v is not None]
    assert values == defined + [None] * (len(values) - len(defined))
    assert defined == sorted(defined, reverse=True)


@pytest.mark.parametrize("sort_by,minimum,descending", [
    ("batting_avg", 10, True), ("strike_rate", 25, True), ("economy", 10, False), ("bowling_avg", 50, False),
])
def test_rate_sort_qualification(sort_by, minimum, descending):
    batting = sort_by in ("batting_avg", "strike_rate")
    innings = batting_record()["innings"] if batting else bowling_innings()
    players, data = directory(sort_by=sort_by, min_innings=minimum)
    expected = set(innings[innings >= minimum].index)
    assert data["total_count"] == len(players) == len(expected)
    assert {p["player_id"] for p in players} == expected
    assert data["qualification"] == {
        "sort_by": sort_by, "min_innings": minimum, "innings_kind": "batting" if batting else "bowling",
    }
    values = [p[sort_by] for p in players]
    defined = [v for v in values if v is not None]
    assert values == defined + [None] * (len(values) - len(defined))
    assert defined == sorted(defined, reverse=descending)


@pytest.mark.parametrize("sort_by", ["runs", "wickets", "innings"])
def test_min_innings_never_filters_without_a_rate_sort(sort_by):
    data = client.get("/api/players", params={"sort_by": sort_by, "min_innings": 50}).json()
    assert data["total_count"] == data["directory_counts"]["all"]
    assert data["qualification"] is None
