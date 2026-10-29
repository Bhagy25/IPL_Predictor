"""Player profile and match log, checked against one independent pass over the raw Cricsheet JSON.

Expected values never come from the analytics engine or data/derived. They are counted
here from the raw match files; team names use Stage 1's franchise() mapping and venue
names Stage 1's matches.csv, both of which the profile is expected to agree with.
"""
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cricketlens.api.app import app
from cricketlens.api.services.canonical_data import overs_notation
from cricketlens.pipeline import franchise

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ipl_json"
NOT_A_DISMISSAL = {"retired hurt", "retired not out"}
CREDITED = {"bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket"}
# Long career, bowling specialist, all-rounders, a retired batter (last season 2021) and a
# player with Did-Not-Bat appearances; the last three are chosen from the raw data below.
PLAYERS = [
    "V Kohli", "JJ Bumrah", "RA Jadeja", "SP Narine", "AB de Villiers", "MS Dhoni",
    "2026 debutant", "most substituted in", "most substituted out",
]
BATTING_NONE = {"runs": None, "balls_faced": None, "fours": None, "sixes": None, "dismissed": None, "dismissal_kind": None}
BOWLING_NONE = {"legal_balls": None, "overs": None, "runs_conceded": None, "wickets": None, "economy": None, "economy_state": None}

needs_raw = pytest.mark.skipif(
    not RAW.is_dir() or not any(RAW.glob("*.json")), reason="raw Cricsheet JSON not available"
)


def expected_result(outcome, team):
    """Result for `team` from Cricsheet's info.outcome."""
    result = {
        "outcome": None, "outcome_state": None, "winner": None, "method": outcome.get("method"),
        "super_over_winner": None, "super_over_outcome": None, "super_over_state": None,
    }
    if "winner" in outcome:
        result["winner"] = franchise(outcome["winner"])
        result["outcome"] = "won" if result["winner"] == team else "lost"
    elif outcome.get("result") == "tie":
        result["outcome"] = "tied"
        if "eliminator" in outcome:
            result["super_over_winner"] = franchise(outcome["eliminator"])
            result["super_over_outcome"] = "won" if result["super_over_winner"] == team else "lost"
        else:
            result["super_over_state"] = "not_recorded_in_source"
    elif outcome.get("result") == "no result":
        result["outcome"] = "no_result"
    else:
        result["outcome_state"] = "not_recorded_in_source"
    return result


@pytest.fixture(scope="module")
def raw():
    """Appearances, batting innings, bowling spells and substitutions for every registry ID."""
    venues = dict(pd.read_csv(ROOT / "data" / "processed" / "matches.csv", usecols=["match_id", "venue_canonical"])
                  .itertuples(index=False))
    ids_by_name = defaultdict(set)
    appearances = defaultdict(dict)  # player_id -> {match_id: appearance}
    batting, bowling = {}, {}        # (player_id, match_id) -> innings / spell
    substitutions = defaultdict(list)

    for path in RAW.glob("*.json"):
        match = json.loads(path.read_text(encoding="utf-8"))
        info, mid = match["info"], int(path.stem)
        registry = info["registry"]["people"]
        date = str(info["dates"][0])
        season = int(date[:4])
        teams = [franchise(t) for t in info["teams"]]
        other = {teams[0]: teams[1], teams[1]: teams[0]}
        for listed_team, names in info["players"].items():
            team = franchise(listed_team)
            for name in names:
                ids_by_name[name].add(registry[name])
                appearances[registry[name]][mid] = {
                    "match_id": mid, "date": date, "season": season, "team": team, "opposition": other[team],
                    "venue": venues[mid], "result": expected_result(info["outcome"], team),
                }

        for position, innings in enumerate(match["innings"], start=1):
            team = franchise(innings["team"])
            context = {"season": season, "venue": venues[mid]}

            def at_crease(name):
                return batting.setdefault((registry[name], mid), {
                    **context, "team": team, "opposition": other[team],
                    "runs": 0, "balls_faced": 0, "fours": 0, "sixes": 0, "kinds": [],
                })

            for over in innings["overs"]:
                for ball in over["deliveries"]:
                    for sub in ball.get("replacements", {}).get("match", []):
                        for direction, pid, counterpart in (("in", sub["in"], sub["out"]), ("out", sub["out"], sub["in"])):
                            substitutions[(mid, registry[pid])].append({
                                "direction": direction, "reason": sub["reason"], "innings": position,
                                "counterpart_id": registry[counterpart], "counterpart_name": counterpart,
                            })
                    if innings.get("super_over"):
                        continue
                    runs, extras = ball["runs"], ball.get("extras", {})
                    striker = at_crease(ball["batter"])
                    at_crease(ball["non_striker"])
                    boundary = not runs.get("non_boundary")
                    striker["runs"] += runs["batter"]
                    striker["balls_faced"] += "wides" not in extras
                    striker["fours"] += runs["batter"] == 4 and boundary
                    striker["sixes"] += runs["batter"] == 6 and boundary
                    spell = bowling.setdefault((registry[ball["bowler"]], mid), {
                        **context, "opposition": team, "legal": 0, "runs": 0, "wickets": 0,
                    })
                    spell["legal"] += "wides" not in extras and "noballs" not in extras
                    spell["runs"] += runs["batter"] + extras.get("wides", 0) + extras.get("noballs", 0)
                    for wicket in ball.get("wickets", []):
                        at_crease(wicket["player_out"])["kinds"].append(wicket["kind"])
                        spell["wickets"] += wicket["kind"] in CREDITED

    for inns in batting.values():
        counting = [k for k in inns["kinds"] if k not in NOT_A_DISMISSAL]
        inns["dismissed"] = bool(counting)
        inns["dismissal_kind"] = (counting or inns["kinds"] or [None])[-1]
    return {
        "ids_by_name": ids_by_name, "appearances": appearances, "batting": batting,
        "bowling": bowling, "substitutions": substitutions,
    }


@pytest.fixture(scope="module")
def players(raw):
    """Registry ID for each key in PLAYERS."""
    ids = {}
    for name in PLAYERS[:6]:
        (ids[name],) = raw["ids_by_name"][name]
    performers = {pid for pid, _ in raw["batting"]} | {pid for pid, _ in raw["bowling"]}
    debut = {pid: min(a["season"] for a in apps.values()) for pid, apps in raw["appearances"].items()}
    ids["2026 debutant"] = max(
        (pid for pid in performers if debut[pid] == 2026), key=lambda p: (len(raw["appearances"][p]), p)
    )
    for direction in ("in", "out"):
        counts = defaultdict(int)
        for (_, pid), subs in raw["substitutions"].items():
            counts[pid] += sum(s["direction"] == direction for s in subs)
        ids[f"most substituted {direction}"] = max((p for p in counts if p in performers), key=lambda p: (counts[p], p))
    return ids


@lru_cache(maxsize=None)
def _get(url, season=None):
    res = client.get(url, params={"season": season} if season is not None else {})
    assert res.status_code == 200, res.text
    return res.json()


def profile(pid, season=None):
    return _get(f"/api/players/{pid}/overview", season)


def full_log(pid, season=None, page_size=37):
    """Every page of the match log, checking page bookkeeping on the way."""
    entries, page = [], 1
    while True:
        params = {"page": page, "page_size": page_size, **({"season": season} if season is not None else {})}
        data = client.get(f"/api/players/{pid}/matches", params=params).json()
        assert (data["page"], data["page_size"]) == (page, page_size)
        assert data["total_pages"] == max(1, -(-data["total_count"] // page_size))
        assert len(data["matches"]) == min(page_size, data["total_count"] - (page - 1) * page_size)
        entries += data["matches"]
        if page >= data["total_pages"]:
            return entries, data["total_count"]
        page += 1


def grouped(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    return groups


def without(record, key):
    return {k: v for k, v in record.items() if k != key}


def bat_stats(rows):
    inns, runs = len(rows), sum(r["runs"] for r in rows)
    balls, outs = sum(r["balls_faced"] for r in rows), sum(r["dismissed"] for r in rows)
    top = max(r["runs"] for r in rows)
    not_out = any(r["runs"] == top and not r["dismissed"] for r in rows)
    return {
        "innings": inns, "runs": runs, "balls_faced": balls, "dismissals": outs, "not_outs": inns - outs,
        "average": round(runs / outs, 2) if outs else None, "average_state": None if outs else "no_dismissals",
        "strike_rate": round(runs / balls * 100, 2) if balls else None,
        "strike_rate_state": None if balls else "no_balls_faced",
        "highest_score": f"{top}*" if not_out else str(top),
        "fours": sum(r["fours"] for r in rows), "sixes": sum(r["sixes"] for r in rows),
        "ducks": sum(r["runs"] == 0 and r["dismissed"] for r in rows),
        "scores_30_plus": sum(r["runs"] >= 30 for r in rows), "scores_50_plus": sum(r["runs"] >= 50 for r in rows),
        "scores_100_plus": sum(r["runs"] >= 100 for r in rows),
    }


def bowl_stats(rows):
    balls, runs, wkts = sum(r["legal"] for r in rows), sum(r["runs"] for r in rows), sum(r["wickets"] for r in rows)
    best = max(rows, key=lambda r: (r["wickets"], -r["runs"]))
    return {
        "innings": len(rows), "legal_deliveries": balls, "overs_bowled": f"{balls // 6}.{balls % 6}",
        "runs_conceded": runs, "wickets": wkts,
        "bowling_average": round(runs / wkts, 2) if wkts else None,
        "bowling_average_state": None if wkts else "no_wickets",
        "bowling_strike_rate": round(balls / wkts, 2) if wkts else None,
        "bowling_strike_rate_state": None if wkts else "no_wickets",
        "economy_rate": round(runs / (balls / 6), 2) if balls else None,
        "economy_rate_state": None if balls else "no_legal_balls",
        "best_bowling": f"{best['wickets']}/{best['runs']}",
        "three_wicket_hauls": sum(r["wickets"] == 3 for r in rows),
        "four_wicket_hauls": sum(r["wickets"] == 4 for r in rows),
        "five_wicket_hauls": sum(r["wickets"] >= 5 for r in rows),
    }


def player_rows(raw, pid, season=None):
    """The player's raw batting innings and bowling spells, optionally for one season."""
    return tuple(
        [r for (p, _), r in raw[table].items() if p == pid and (season is None or r["season"] == season)]
        for table in ("batting", "bowling")
    )


def assert_profile_matches_raw(raw, pid, season=None):
    """Every number in the profile (career, or one season) against the raw data."""
    p = profile(pid, season)
    apps = {m: a for m, a in raw["appearances"][pid].items() if season is None or a["season"] == season}
    bat, bowl = player_rows(raw, pid, season)

    # Career summary: appearances from the squad lists, nothing outside them
    seasons = sorted({a["season"] for a in apps.values()})
    assert p["season_filter"] == season
    assert p["matches"] == len(apps)
    assert (p["first_season"], p["last_season"], p["seasons_played"], p["seasons_count"]) == \
        (seasons[0], seasons[-1], seasons, len(seasons))
    teams = grouped(apps.values(), "team")
    expected_history = sorted(
        (team, sorted({a["season"] for a in rows}), len(rows)) for team, rows in teams.items()
    )
    assert sorted((t["team"], t["seasons"], t["matches"]) for t in p["team_history"]) == expected_history
    assert [t["seasons"][0] for t in p["team_history"]] == sorted(t["seasons"][0] for t in p["team_history"])
    assert p["teams"] == sorted(teams)
    assert sorted(e["match_id"] for e in full_log(pid, season)[0]) == sorted(apps)
    # The removed pre-6A fields stay removed
    assert not {"recent_matches", "opposition_splits", "venue_splits", "season_splits"} & set(p)

    # Batting: career, season by season, and team / opposition / venue splits
    if bat:
        assert p["batting_state"] == "batted"
        assert p["career_batting"] == bat_stats(bat)
    else:
        assert (p["batting_state"], p["career_batting"]) == ("did_not_bat", None)
    for table, key in (("batting_by_season", "season"), ("batting_by_team", "team"),
                       ("batting_by_opposition", "opposition"), ("batting_by_venue", "venue")):
        assert {r[key]: without(r, key) for r in p[table]} == \
            {k: bat_stats(rows) for k, rows in grouped(bat, key).items()}, table

    # Bowling: career, season by season, and opposition / venue splits
    if bowl:
        assert p["bowling_state"] == "bowled"
        assert p["career_bowling"] == bowl_stats(bowl)
    else:
        assert (p["bowling_state"], p["career_bowling"]) == ("did_not_bowl", None)
    for table, key in (("bowling_by_season", "season"), ("bowling_by_opposition", "opposition"),
                       ("bowling_by_venue", "venue")):
        assert {r[key]: without(r, key) for r in p[table]} == \
            {k: bowl_stats(rows) for k, rows in grouped(bowl, key).items()}, table
    return p


def expected_entry(raw, pid, mid):
    """One match-log row from the raw data."""
    app = raw["appearances"][pid][mid]
    inns, spell = raw["batting"].get((pid, mid)), raw["bowling"].get((pid, mid))
    subs = raw["substitutions"].get((mid, pid), [])
    directions = {s["direction"] for s in subs}
    state = {frozenset(): "playing_xi", frozenset({"in"}): "substituted_in",
             frozenset({"out"}): "substituted_out"}.get(frozenset(directions), "substituted_in_and_out")
    if inns:
        batting = {"state": "batted", **{k: inns[k] for k in ("runs", "balls_faced", "fours", "sixes")},
                   "dismissed": inns["dismissed"], "dismissal_kind": inns["dismissal_kind"]}
    else:
        batting = {"state": "did_not_bat", **BATTING_NONE}
    if spell:
        balls = spell["legal"]
        bowling = {
            "state": "bowled", "legal_balls": balls, "overs": f"{balls // 6}.{balls % 6}",
            "runs_conceded": spell["runs"], "wickets": spell["wickets"],
            "economy": round(spell["runs"] / (balls / 6), 2) if balls else None,
            "economy_state": None if balls else "no_legal_balls",
        }
    else:
        bowling = {"state": "did_not_bowl", **BOWLING_NONE}
    return {
        **{k: app[k] for k in ("match_id", "date", "season", "team", "opposition", "venue")},
        "appearance_state": state, "substitutions": subs,
        "batting": batting, "bowling": bowling, "result": app["result"],
    }


# ------------------------------------------------------------------ overs notation

def test_overs_notation():
    assert overs_notation(22) == "3.4"
    assert overs_notation(24) == "4.0"
    assert (overs_notation(0), overs_notation(5), overs_notation(6), overs_notation(4255)) == ("0.0", "0.5", "1.0", "709.1")


@needs_raw
@pytest.mark.parametrize("legal_balls,overs", [(22, "3.4"), (24, "4.0")])
def test_overs_notation_in_match_log(raw, legal_balls, overs):
    pid, mid = min(key for key, spell in raw["bowling"].items() if spell["legal"] == legal_balls)
    entries, _ = full_log(pid, raw["appearances"][pid][mid]["season"], page_size=100)
    row = next(e for e in entries if e["match_id"] == mid)
    assert (row["bowling"]["legal_balls"], row["bowling"]["overs"]) == (legal_balls, overs)


# ------------------------------------------------------------------ profile

@needs_raw
@pytest.mark.parametrize("key", PLAYERS)
def test_career_profile_matches_raw(raw, players, key):
    p = assert_profile_matches_raw(raw, players[key])
    if key == "AB de Villiers":
        assert p["last_season"] == 2021
    if key == "2026 debutant":
        assert p["seasons_played"] == [2026]


@needs_raw
@pytest.mark.parametrize("key", PLAYERS)
def test_single_season_profile_recomputes_every_number(raw, players, key):
    pid = players[key]
    bat, bowl = player_rows(raw, pid)
    seasons = {a["season"] for a in raw["appearances"][pid].values()}
    # Debut season, best batting season and best bowling season
    picks = {min(seasons)}
    if bat:
        picks.add(max(grouped(bat, "season").items(), key=lambda kv: (sum(r["runs"] for r in kv[1]), kv[0]))[0])
    if bowl:
        picks.add(max(grouped(bowl, "season").items(), key=lambda kv: (sum(r["wickets"] for r in kv[1]), kv[0]))[0])
    for season in sorted(picks):
        p = assert_profile_matches_raw(raw, pid, season)
        assert p["seasons_played"] == [season]
        entries, total = full_log(pid, season)
        assert total == p["matches"] and all(e["season"] == season for e in entries)
    if len(seasons) > 1:
        assert profile(pid, min(seasons))["matches"] < profile(pid)["matches"]


@needs_raw
@pytest.mark.parametrize("key", PLAYERS)
def test_splits_sum_to_career_totals(players, key):
    p = profile(players[key])
    if p["career_batting"]:
        for table in ("batting_by_team", "batting_by_opposition", "batting_by_venue", "batting_by_season"):
            assert sum(r["runs"] for r in p[table]) == p["career_batting"]["runs"], table
            assert sum(r["innings"] for r in p[table]) == p["career_batting"]["innings"], table
    if p["career_bowling"]:
        for table in ("bowling_by_opposition", "bowling_by_venue", "bowling_by_season"):
            assert sum(r["wickets"] for r in p[table]) == p["career_bowling"]["wickets"], table
            assert sum(r["legal_deliveries"] for r in p[table]) == p["career_bowling"]["legal_deliveries"], table


def test_season_without_appearances_is_not_found():
    res = client.get("/api/players/ba607b88/overview", params={"season": 2030})
    assert res.status_code == 404
    assert "no IPL match appearances in 2030" in res.json()["detail"]


# ------------------------------------------------------------------ match log

@needs_raw
@pytest.mark.parametrize("key", PLAYERS)
def test_match_log_lists_every_appearance(raw, players, key):
    pid = players[key]
    apps = raw["appearances"][pid]
    entries, total = full_log(pid)
    ids = [e["match_id"] for e in entries]
    # One row per squad appearance: no duplicates, no gaps, most recent first
    assert total == len(entries) == len(apps) == profile(pid)["matches"]
    assert len(set(ids)) == len(ids) and set(ids) == set(apps)
    assert [(e["date"], e["match_id"]) for e in entries] == sorted(((e["date"], e["match_id"]) for e in entries), reverse=True)
    for entry in entries:
        assert entry == expected_entry(raw, pid, entry["match_id"])

    # Per-match rows add up to the career figures
    batted = [e["batting"] for e in entries if e["batting"]["state"] == "batted"]
    bowled = [e["bowling"] for e in entries if e["bowling"]["state"] == "bowled"]
    p = profile(pid)
    assert (len(batted), sum(b["runs"] for b in batted)) == \
        ((p["career_batting"]["innings"], p["career_batting"]["runs"]) if p["career_batting"] else (0, 0))
    assert (len(bowled), sum(b["wickets"] for b in bowled), sum(b["legal_balls"] for b in bowled)) == (
        (p["career_bowling"]["innings"], p["career_bowling"]["wickets"], p["career_bowling"]["legal_deliveries"])
        if p["career_bowling"] else (0, 0, 0)
    )
    if key == "MS Dhoni":
        assert any(e["batting"]["state"] == "did_not_bat" for e in entries)
    if key.startswith("most substituted"):
        direction = key.rsplit(" ", 1)[1]
        assert any(e["appearance_state"] == f"substituted_{direction}" for e in entries)


@needs_raw
def test_match_log_pages_are_stable(players):
    pid = players["V Kohli"]
    first, total = full_log(pid, page_size=20)
    second, _ = full_log(pid, page_size=100)
    assert [e["match_id"] for e in first] == [e["match_id"] for e in second] and len(first) == total
    beyond = client.get(f"/api/players/{pid}/matches", params={"page": total + 1, "page_size": 1}).json()
    assert beyond["matches"] == [] and beyond["total_count"] == total
    assert client.get(f"/api/players/{pid}/matches", params={"page_size": 101}).status_code == 422
    assert client.get(f"/api/players/{pid}/matches", params={"page": 0}).status_code == 422
    assert client.get("/api/players/not-a-player/matches").status_code == 404


# ------------------------------------------------------------------ null states

@needs_raw
def test_undefined_rates_are_null_with_a_state(raw, players):
    batting_by_player = defaultdict(list)
    for (pid, _), inns in raw["batting"].items():
        batting_by_player[pid].append(inns)
    bowling_innings = defaultdict(int)
    for pid, _ in raw["bowling"]:
        bowling_innings[pid] += 1

    # The bowler with the most bowling innings among those who batted but were never dismissed
    never_out = [pid for pid, rows in batting_by_player.items() if not any(r["dismissed"] for r in rows)]
    bowler = max((pid for pid in never_out if bowling_innings[pid]), key=lambda p: (bowling_innings[p], p))
    p = profile(bowler)
    assert p["career_batting"]["dismissals"] == 0
    assert (p["career_batting"]["average"], p["career_batting"]["average_state"]) == (None, "no_dismissals")
    assert p["career_summary"]["avg_per_appearance"] is None

    # Only ever at the non-striker's end: no balls faced, so no strike rate
    non_striker = min(pid for pid, rows in batting_by_player.items() if sum(r["balls_faced"] for r in rows) == 0)
    b = profile(non_striker)["career_batting"]
    assert (b["balls_faced"], b["strike_rate"], b["strike_rate_state"]) == (0, None, "no_balls_faced")

    # A spell of only wides or no-balls has no economy rate
    pid, mid = min(key for key, spell in raw["bowling"].items() if spell["legal"] == 0)
    entries, _ = full_log(pid, raw["appearances"][pid][mid]["season"], page_size=100)
    row = next(e for e in entries if e["match_id"] == mid)["bowling"]
    assert (row["state"], row["overs"], row["economy"], row["economy_state"]) == ("bowled", "0.0", None, "no_legal_balls")

    # Never bowled: no bowling block, and the state says why
    de_villiers = profile(players["AB de Villiers"])
    assert not player_rows(raw, players["AB de Villiers"])[1]
    assert (de_villiers["bowling_state"], de_villiers["career_bowling"], de_villiers["bowling_by_season"]) == \
        ("did_not_bowl", None, [])


def test_profile_has_no_model_output_and_defines_every_state():
    p = client.get("/api/players/ba607b88/overview").json()
    assert not any("forecast" in k or "model" in k or "predict" in k for k in p)
    states = {v for block in (p["career_batting"], p["career_bowling"]) for k, v in block.items() if k.endswith("_state")}
    assert states - {None} <= set(p["state_definitions"])
    for key in ("ducks", "batting_innings", "not_outs", "overs", "wickets", "appearance_state", "result"):
        assert key in p["metric_definitions"]
