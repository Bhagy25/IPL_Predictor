"""Player identity by Cricsheet registry ID, batting innings from crease appearances, and team guards.

Expected values come from one independent pass over the raw Cricsheet JSON or from
Stage 1's batter_innings.csv, not from the analytics engine.
"""
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cricketlens.api.app import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ipl_json"
NOT_A_DISMISSAL = {"retired hurt", "retired not out"}

needs_raw = pytest.mark.skipif(
    not RAW.is_dir() or not any(RAW.glob("*.json")), reason="raw Cricsheet JSON not available"
)


@pytest.fixture(scope="module")
def raw():
    """Registry IDs per listed name, crease appearances and batting dismissals per player."""
    ids_by_name = defaultdict(set)
    innings = defaultdict(set)  # player_id -> {(match_id, innings position)}
    dismissals = defaultdict(int)
    for path in RAW.glob("*.json"):
        match = json.loads(path.read_text(encoding="utf-8"))
        registry = match["info"]["registry"]["people"]
        for names in match["info"]["players"].values():
            for name in names:
                ids_by_name[name].add(registry[name])
        for pos, inn in enumerate(match["innings"], start=1):
            if inn.get("super_over"):
                continue
            for over in inn["overs"]:
                for ball in over["deliveries"]:
                    for name in (ball["batter"], ball["non_striker"]):
                        innings[registry[name]].add((path.stem, pos))
                    for wicket in ball.get("wickets", []):
                        if wicket["kind"] not in NOT_A_DISMISSAL:
                            dismissals[registry[wicket["player_out"]]] += 1
    return {"ids_by_name": ids_by_name, "innings": innings, "dismissals": dismissals}


def search(query):
    res = client.get("/api/players", params={"query": query, "page_size": 100})
    assert res.status_code == 200
    return res.json()["players"]


def all_players():
    players, page = [], 1
    while True:
        data = client.get("/api/players", params={"page": page, "page_size": 100}).json()
        players += data["players"]
        if page >= data["total_pages"]:
            return players
        page += 1


def single_id(raw, name):
    (pid,) = raw["ids_by_name"][name]
    return pid


@needs_raw
@pytest.mark.parametrize("variants", [
    ("Arshad Khan", "Arshad Khan (2)"),
    ("S Arora", "Salil Arora"),
    ("NA Saini", "Navdeep Saini"),
])
def test_name_variants_resolve_to_one_player(raw, variants):
    registry_ids = set().union(*(raw["ids_by_name"][v] for v in variants))
    assert len(registry_ids) == 1
    for variant in variants:
        hits = [p for p in search(variant) if variant in [p["name"], *p["name_variants"]]]
        assert [p["player_id"] for p in hits] == list(registry_ids), variant
        assert set(variants) <= set(hits[0]["name_variants"])


@needs_raw
def test_two_harmeet_singhs_are_separate_entries(raw):
    expected = raw["ids_by_name"]["Harmeet Singh"]
    assert len(expected) == 2
    hits = search("Harmeet Singh")
    assert {p["player_id"] for p in hits} == expected
    assert len({p["name"] for p in hits}) == 2  # display names are disambiguated
    assert client.get("/api/players/Harmeet Singh/overview").status_code == 404  # ambiguous by name
    for pid in expected:
        assert client.get(f"/api/players/{pid}/overview").status_code == 200


def test_directory_ids_are_registry_ids():
    people = set(pd.read_csv(ROOT / "data" / "derived" / "people.csv", usecols=["player_id"])["player_id"])
    ids = [p["player_id"] for p in all_players()]
    assert len(ids) == len(set(ids))
    assert set(ids) <= people


@needs_raw
def test_bumrah_batting_dismissals_include_non_striker_run_out(raw):
    pid = single_id(raw, "JJ Bumrah")
    batting = client.get(f"/api/players/{pid}/overview").json()["career_batting"]
    assert batting["dismissals"] == raw["dismissals"][pid] == 8  # Stage 1 rows give 7
    assert batting["not_outs"] == batting["innings"] - batting["dismissals"]


@needs_raw
@pytest.mark.parametrize("name", ["V Kohli", "JJ Bumrah", "SP Narine"])
def test_batting_innings_count_crease_appearances(raw, name):
    pid = single_id(raw, name)
    batting = client.get(f"/api/players/{pid}/overview").json()["career_batting"]
    assert batting["innings"] == len(raw["innings"][pid])


def test_runs_and_milestones_unchanged_against_stage1():
    stage1 = pd.read_csv(ROOT / "data" / "processed" / "batter_innings.csv")
    expected = stage1.groupby("batter_id").agg(
        runs=("runs", "sum"), r30=("reached_30", "sum"), r50=("reached_50", "sum"),
    )
    listed = {p["player_id"]: p for p in all_players()}
    for pid, row in expected.iterrows():
        p = listed[pid]
        assert (p["total_runs"], p["scores_30_plus"], p["scores_50_plus"]) == (row["runs"], row["r30"], row["r50"]), pid
    # Players with no Stage 1 row were only ever at the non-striker's end or never batted
    assert all(listed[pid]["total_runs"] == 0 for pid in set(listed) - set(expected.index))


@pytest.mark.parametrize("team1,team2", [("csk", "csk"), ("csk", "chennai-super-kings")])
def test_same_team_head_to_head_is_rejected(team1, team2):
    res = client.get("/api/teams/head-to-head", params={"team1": team1, "team2": team2})
    assert res.status_code == 400
    assert "distinct" in res.json()["detail"]
