"""Bowling and boundary statistics served by the API, checked against the raw match data.

Expected values come from one independent pass over the raw Cricsheet JSON (and
deliveries.csv for runs conceded and legal balls), not from data/derived or the engine.
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
DELIVERIES = ROOT / "data" / "processed" / "deliveries.csv"
CREDITED = {"bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket"}

pytestmark = pytest.mark.skipif(
    not RAW.is_dir() or not any(RAW.glob("*.json")), reason="raw Cricsheet JSON not available"
)


@pytest.fixture(scope="module")
def raw():
    """Per bowling innings: credited wickets, runs conceded, legal balls; plus dot-ball run outs and boundaries."""
    innings = defaultdict(lambda: {"wickets": 0, "runs": 0, "balls": 0})  # (match_id, pos, bowler) -> totals
    season_of = {}
    dot_ball_run_outs = []  # (match_id, bowler) where the old estimate would have credited the bowler
    fours = sixes = 0
    for path in sorted(RAW.glob("*.json")):
        match = json.loads(path.read_text(encoding="utf-8"))
        match_id = int(path.stem)
        season_of[match_id] = int(match["info"]["dates"][0][:4])
        for pos, inn in enumerate(match["innings"], start=1):
            if inn.get("super_over"):
                continue
            for over in inn["overs"]:
                for ball in over["deliveries"]:
                    extras = ball.get("extras", {})
                    totals = innings[(match_id, pos, ball["bowler"])]
                    totals["runs"] += ball["runs"]["batter"] + extras.get("wides", 0) + extras.get("noballs", 0)
                    totals["balls"] += int("wides" not in extras and "noballs" not in extras)
                    for wicket in ball.get("wickets", []):
                        totals["wickets"] += wicket["kind"] in CREDITED
                        if (wicket["kind"] == "run out" and ball["runs"]["batter"] == 0
                                and "byes" not in extras and "legbyes" not in extras):
                            dot_ball_run_outs.append((match_id, ball["bowler"]))
                    if not ball["runs"].get("non_boundary"):
                        fours += ball["runs"]["batter"] == 4
                        sixes += ball["runs"]["batter"] == 6
    return {"innings": innings, "season_of": season_of, "dot_ball_run_outs": dot_ball_run_outs,
            "fours": fours, "sixes": sixes}


def bowler_innings(raw, name):
    return [v for (mid, pos, bowler), v in raw["innings"].items() if bowler == name]


def profile(name):
    players = client.get("/api/players", params={"query": name, "page_size": 100}).json()["players"]
    pid = next(p["player_id"] for p in players if p["name"] == name)
    res = client.get(f"/api/players/{pid}/overview")
    assert res.status_code == 200
    return res.json()


def best_figures(rows):
    best = max(rows, key=lambda r: (r["wickets"], -r["runs"]))
    return f"{best['wickets']}/{best['runs']}"


def test_narine_best_figures_and_wickets(raw):
    rows = bowler_innings(raw, "SP Narine")
    bowl = profile("SP Narine")["career_bowling"]
    assert bowl["wickets"] == sum(r["wickets"] for r in rows)
    assert bowl["best_bowling"] == best_figures(rows)
    assert (bowl["wickets"], bowl["best_bowling"]) == (207, "5/19")  # baseline; the old estimate gave 220 and 5/13


@pytest.mark.parametrize("name,baseline", [("B Kumar", 226), ("YS Chahal", 233)])
def test_career_wickets(raw, name, baseline):
    expected = sum(r["wickets"] for r in bowler_innings(raw, name))
    assert profile(name)["career_bowling"]["wickets"] == expected == baseline


def test_bumrah_average_and_strike_rate(raw):
    deliveries = pd.read_csv(DELIVERIES, usecols=["bowler", "runs_batter", "wides", "noballs", "legal_delivery"])
    own = deliveries[deliveries["bowler"] == "JJ Bumrah"]
    runs = int((own["runs_batter"] + own["wides"] + own["noballs"]).sum())
    balls = int(own["legal_delivery"].sum())
    wickets = sum(r["wickets"] for r in bowler_innings(raw, "JJ Bumrah"))

    bowl = profile("JJ Bumrah")["career_bowling"]
    assert (bowl["runs_conceded"], bowl["legal_deliveries"], bowl["wickets"]) == (runs, balls, wickets)
    assert bowl["bowling_average"] == round(runs / wickets, 2)
    assert bowl["bowling_strike_rate"] == round(balls / wickets, 2)
    assert bowl["economy_rate"] == round(runs / (balls / 6), 2)


def test_haul_counts(raw):
    per_innings = [r["wickets"] for r in bowler_innings(raw, "B Kumar")]
    bowl = profile("B Kumar")["career_bowling"]
    assert bowl["three_wicket_hauls"] == sum(w == 3 for w in per_innings)
    assert bowl["four_wicket_hauls"] == sum(w == 4 for w in per_innings)
    assert bowl["five_wicket_hauls"] == sum(w >= 5 for w in per_innings)
    assert bowl["five_wicket_hauls"] == 2


def test_run_out_off_a_bowlers_delivery_is_not_credited(raw):
    match_id, bowler = sorted(raw["dot_ball_run_outs"])[0]
    credited = sum(v["wickets"] for (mid, pos, b), v in raw["innings"].items() if mid == match_id and b == bowler)
    pid = profile(bowler)["player_id"]
    season = raw["season_of"][match_id]
    log = client.get(f"/api/players/{pid}/matches", params={"season": season, "page_size": 100}).json()["matches"]
    row = next(m for m in log if m["match_id"] == int(match_id))
    assert row["bowling"]["wickets"] == credited


def test_csk_team_wickets_unchanged():
    innings = pd.read_csv(ROOT / "data" / "processed" / "innings.csv")
    record = client.get("/api/teams/chennai-super-kings/overview").json()["all_time"]
    assert record["wickets_taken"] == int(innings.loc[innings["bowling_team"] == "Chennai Super Kings", "wickets"].sum())
    assert record["wickets_lost"] == int(innings.loc[innings["batting_team"] == "Chennai Super Kings", "wickets"].sum())
    assert (record["wickets_taken"], record["wickets_lost"]) == (1644, 1421)  # values before Part 4


def test_season_split_recomputes_bowler_wickets(raw):
    season = 2024
    expected = sum(
        v["wickets"] for (mid, pos, b), v in raw["innings"].items()
        if b == "JJ Bumrah" and raw["season_of"][mid] == season
    )
    split = next(s for s in profile("JJ Bumrah")["bowling_by_season"] if s["season"] == season)
    assert split["wickets"] == expected


def test_top10_bowler_leaderboard(raw):
    totals = pd.DataFrame(
        [{"bowler": b, "wickets": v["wickets"], "runs": v["runs"]} for (mid, pos, b), v in raw["innings"].items()]
    ).groupby("bowler", as_index=False).sum()
    expected = totals.sort_values(["wickets", "runs", "bowler"], ascending=[False, True, True]).head(10)

    board = client.get("/api/eda/analysis").json()["areas"]["bowling"]["data"]["leaders"]
    assert [(b["name"], b["wickets"]) for b in board] == list(zip(expected["bowler"], expected["wickets"]))


def test_boundaries_by_season_exclude_non_boundary_runs(raw):
    seasons = client.get("/api/eda/analysis").json()["areas"]["boundaries"]["data"]["by_season"]
    assert sum(s["fours"] for s in seasons) == raw["fours"]
    assert sum(s["sixes"] for s in seasons) == raw["sixes"]
