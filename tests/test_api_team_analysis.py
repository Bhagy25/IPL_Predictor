"""Team analysis checked against independent calculations.

Results, toss and venues come from matches.csv; runs, wickets, innings order and phases from
deliveries.csv (the engine uses innings.csv for totals); Super Over, no-result and renamed-franchise
checks read the raw Cricsheet JSON. Nothing here reads the engine's tables.
"""
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cricketlens.api.app import app
from cricketlens.pipeline import franchise

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "ipl_json"
SLUGS = {
    "Chennai Super Kings": "chennai-super-kings", "Mumbai Indians": "mumbai-indians",
    "Gujarat Titans": "gujarat-titans", "Deccan Chargers": "deccan-chargers", "Delhi Capitals": "delhi-capitals",
}
# All seasons and one season for each team (Delhi 2012 was played as Delhi Daredevils)
CASES = [
    ("Chennai Super Kings", None), ("Chennai Super Kings", 2024),
    ("Mumbai Indians", None), ("Mumbai Indians", 2019),
    ("Gujarat Titans", None), ("Gujarat Titans", 2022),
    ("Deccan Chargers", None), ("Deccan Chargers", 2009),
    ("Delhi Capitals", None), ("Delhi Capitals", 2012),
]
PHASE_OF = [(0, 5, "powerplay"), (6, 15, "middle"), (16, 19, "death")]

needs_raw = pytest.mark.skipif(not RAW.is_dir() or not any(RAW.glob("*.json")), reason="raw Cricsheet JSON not available")


def pct(part, whole):
    """One-decimal percentage with halves rounded up; None without a denominator."""
    if not whole:
        return None
    return float((Decimal(int(part) * 100) / Decimal(int(whole))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def rate(runs, balls):
    return round(int(runs) / (int(balls) / 6.0), 2) if balls else None


@pytest.fixture(scope="module")
def matches():
    return pd.read_csv(DATA / "matches.csv")


@pytest.fixture(scope="module")
def deliveries():
    d = pd.read_csv(DATA / "deliveries.csv", usecols=[
        "match_id", "season", "innings", "batting_team", "bowling_team", "over_index",
        "runs_total", "legal_delivery", "team_wickets_on_ball",
    ])
    d["phase"] = pd.cut(d["over_index"], [-1, 5, 15, 19], labels=["powerplay", "middle", "death"]).astype(str)
    return d


def team_matches(matches, team, season=None):
    m = matches[(matches["team1"] == team) | (matches["team2"] == team)]
    return m if season is None else m[m["season"] == season]


def results(m, team):
    """Expected result counts for `team` over matches m (see the API definitions)."""
    no_result = m["outcome_type"] == "no result"
    won = m["final_winner"] == team
    lost = m["final_winner"].notna() & ~won
    tied = (m["outcome_type"] == "tie") & m["final_winner"].isna()
    super_over = m["decided_by"] == "super_over"
    denominator = len(m) - int(no_result.sum())
    return {
        "played": len(m), "wins": int(won.sum()), "losses": int(lost.sum()), "ties": int(tied.sum()),
        "no_results": int(no_result.sum()),
        "super_over_wins": int((won & super_over).sum()), "super_over_losses": int((lost & super_over).sum()),
        "win_pct": pct(won.sum(), denominator), "win_pct_denominator": denominator,
    }


def overview(team, season=None):
    res = client.get(f"/api/teams/{SLUGS[team]}/overview", params={"season": season} if season else {})
    assert res.status_code == 200, res.text
    return res.json()


def first_batting_team(deliveries):
    first = deliveries[deliveries["innings"] == 1].drop_duplicates("match_id")
    return dict(zip(first["match_id"], first["batting_team"]))


# ------------------------------------------------------------------ results, runs, wickets, innings order, phases, toss

@pytest.mark.parametrize("team,season", CASES)
def test_results_and_win_percentage(matches, team, season):
    a = overview(team, season)["all_time"]
    expected = results(team_matches(matches, team, season), team)
    assert {k: a[k] for k in expected} == expected
    assert a["played"] == a["wins"] + a["losses"] + a["ties"] + a["no_results"]
    assert a["win_pct_denominator"] == a["played"] - a["no_results"]


@pytest.mark.parametrize("team,season", CASES)
def test_runs_and_wickets_from_deliveries(deliveries, team, season):
    a = overview(team, season)["all_time"]
    d = deliveries if season is None else deliveries[deliveries["season"] == season]
    bat, bowl = d[d["batting_team"] == team], d[d["bowling_team"] == team]
    assert (a["runs_scored"], a["wickets_lost"], a["balls_faced"]) == (
        int(bat["runs_total"].sum()), int(bat["team_wickets_on_ball"].sum()), int(bat["legal_delivery"].sum()))
    assert (a["runs_conceded"], a["wickets_taken"], a["balls_bowled"]) == (
        int(bowl["runs_total"].sum()), int(bowl["team_wickets_on_ball"].sum()), int(bowl["legal_delivery"].sum()))
    assert a["run_rate"] == rate(bat["runs_total"].sum(), bat["legal_delivery"].sum())
    assert a["economy"] == rate(bowl["runs_total"].sum(), bowl["legal_delivery"].sum())


@pytest.mark.parametrize("team,season", CASES)
def test_batting_first_and_chasing(matches, deliveries, team, season):
    data = overview(team, season)
    m = team_matches(matches, team, season)
    first = first_batting_team(deliveries)
    assert m["match_id"].isin(first).all()  # every match has a first innings
    decided = m[m["outcome_type"] != "no result"]
    batted_first = decided["match_id"].map(first) == team
    for key, subset in (("batting_first", decided[batted_first]), ("chasing", decided[~batted_first])):
        expected = results(subset, team)
        assert {k: data[key][k] for k in expected} == expected, key
    assert data["innings_order_no_results"] == len(m) - len(decided)


@pytest.mark.parametrize("team,season", CASES)
def test_phase_batting_and_conceded_rates(deliveries, team, season):
    phases = {p["phase"]: p for p in overview(team, season)["phases"]}
    assert list(phases) == ["powerplay", "middle", "death"]
    d = deliveries if season is None else deliveries[deliveries["season"] == season]
    for name in phases:
        bat = d[(d["batting_team"] == team) & (d["phase"] == name)]
        bowl = d[(d["bowling_team"] == team) & (d["phase"] == name)]
        p = phases[name]
        assert p["batting_run_rate"] == rate(bat["runs_total"].sum(), bat["legal_delivery"].sum()), name
        assert p["economy"] == rate(bowl["runs_total"].sum(), bowl["legal_delivery"].sum()), name
        assert (p["wickets_lost"], p["wickets_taken"]) == (
            int(bat["team_wickets_on_ball"].sum()), int(bowl["team_wickets_on_ball"].sum())), name


@pytest.mark.parametrize("team,season", CASES)
def test_toss_decisions_and_outcomes(matches, team, season):
    toss = overview(team, season)["toss_stats"]
    m = team_matches(matches, team, season)
    won_toss = m[m["toss_winner"] == team]
    assert (toss["tosses_won"], toss["elected_to_bat"], toss["elected_to_field"]) == (
        len(won_toss), int((won_toss["toss_decision"] == "bat").sum()), int((won_toss["toss_decision"] == "field").sum()))
    for key, subset in (("after_winning_toss", won_toss), ("chose_to_bat", won_toss[won_toss["toss_decision"] == "bat"]),
                        ("chose_to_field", won_toss[won_toss["toss_decision"] == "field"])):
        expected = results(subset, team)
        assert {k: toss[key][k] for k in expected} == expected, key


@pytest.mark.parametrize("team,season", [("Chennai Super Kings", None), ("Chennai Super Kings", 2024), ("Gujarat Titans", None)])
def test_league_toss_comparison_uses_the_same_seasons(matches, team, season):
    toss = overview(team, season)["toss_stats"]
    seasons = sorted(team_matches(matches, team, season)["season"].unique())
    league = matches[matches["season"].isin(seasons)]
    assert toss["league"]["seasons"] == [int(s) for s in seasons]
    won = league["final_winner"] == league["toss_winner"]
    denominator = len(league) - int((league["outcome_type"] == "no result").sum())
    expected = toss["league"]["after_winning_toss"]
    assert (expected["played"], expected["wins"], expected["win_pct"]) == (len(league), int(won.sum()), pct(won.sum(), denominator))
    assert "All teams, same seasons" in toss["league"]["label"]


def test_league_toss_comparison_recomputes_for_the_season_filter():
    all_seasons = overview("Chennai Super Kings")["toss_stats"]["league"]["after_winning_toss"]
    one_season = overview("Chennai Super Kings", 2024)["toss_stats"]["league"]["after_winning_toss"]
    assert one_season["played"] < all_seasons["played"]


# ------------------------------------------------------------------ sums across seasons, venues and opponents

SUMMED = ("played", "wins", "losses", "ties", "no_results", "super_over_wins", "super_over_losses")


@pytest.mark.parametrize("team", list(SLUGS))
def test_season_venue_and_opponent_rows_sum_to_all_time(team):
    data = overview(team)
    a = data["all_time"]
    venues = client.get(f"/api/teams/{SLUGS[team]}/venues", params={"min_matches": 1}).json()
    for label, rows in (("season", data["season_history"]), ("venue", venues["venues"]), ("opponent", data["opponents"])):
        for key in SUMMED:
            assert sum(r[key] for r in rows) == a[key], (label, key)
    for key in ("runs_scored", "runs_conceded", "wickets_lost", "wickets_taken"):
        assert sum(r[key] for r in data["season_history"]) == a[key], key
    assert venues["venues_shown"] == venues["venues_total"] and venues["matches_shown"] == a["played"]


@pytest.mark.parametrize("team", list(SLUGS))
def test_head_to_head_rows_across_all_opponents_sum_to_all_time(team):
    a = overview(team)["all_time"]
    totals = {"total_matches": 0, "team1_wins": 0, "team2_wins": 0, "no_results": 0}
    for other in client.get("/api/teams").json()["teams"]:
        if other["name"] == team:
            continue
        h = client.get("/api/teams/head-to-head", params={"team1": SLUGS[team], "team2": other["id"]}).json()
        for key in totals:
            totals[key] += h[key]
    assert (totals["total_matches"], totals["team1_wins"], totals["team2_wins"], totals["no_results"]) == (
        a["played"], a["wins"], a["losses"], a["no_results"])


@pytest.mark.parametrize("minimum", [1, 3, 5, 10])
def test_venue_minimum_matches_filter(matches, minimum):
    venues = client.get("/api/teams/chennai-super-kings/venues", params={"min_matches": minimum}).json()
    counts = team_matches(matches, "Chennai Super Kings")["venue_canonical"].value_counts()
    kept = counts[counts >= minimum]
    assert venues["min_matches"] == minimum and venues["venues_total"] == len(counts)
    assert venues["venues_shown"] == len(kept) == len(venues["venues"])
    assert venues["matches_shown"] == int(kept.sum())
    assert {v["venue"]: v["played"] for v in venues["venues"]} == kept.to_dict()
    overview_venues = overview("Chennai Super Kings")["venue_records"]
    assert all(v["played"] >= 3 for v in overview_venues)  # the overview list uses the default minimum of 3


# ------------------------------------------------------------------ head-to-head mirror

@pytest.mark.parametrize("a,b,season", [
    ("chennai-super-kings", "mumbai-indians", None), ("chennai-super-kings", "mumbai-indians", 2019),
    ("delhi-capitals", "punjab-kings", None), ("royal-challengers-bengaluru", "kolkata-knight-riders", None),
])
def test_head_to_head_mirrors(a, b, season):
    params = {"season": season} if season else {}
    ab = client.get("/api/teams/head-to-head", params={"team1": a, "team2": b, **params}).json()
    ba = client.get("/api/teams/head-to-head", params={"team1": b, "team2": a, **params}).json()
    assert ab["total_matches"] == ba["total_matches"] > 0
    for left, right in (("team1_wins", "team2_wins"), ("team1_super_over_wins", "team2_super_over_wins"),
                        ("team1_win_pct", "team2_win_pct"), ("team1_batting_first_wins", "team2_batting_first_wins"),
                        ("team1_chasing_wins", "team2_chasing_wins")):
        assert (ab[left], ab[right]) == (ba[right], ba[left]), left
    for key in ("ties_super_overs", "unresolved_ties", "no_results", "win_pct_denominator"):
        assert ab[key] == ba[key], key
    assert [m["match_id"] for m in ab["recent_meetings"]] == [m["match_id"] for m in ba["recent_meetings"]]


# ------------------------------------------------------------------ Super Over and no-result matches from raw JSON

@pytest.fixture(scope="module")
def raw_outcomes():
    out = {}
    for path in RAW.glob("*.json"):
        info = json.loads(path.read_text(encoding="utf-8"))["info"]
        out[int(path.stem)] = (int(str(info["dates"][0])[:4]), [franchise(t) for t in info["teams"]], info["outcome"])
    return out


@needs_raw
def test_super_over_and_no_result_matches_classified_for_both_teams(raw_outcomes):
    super_over = min(m for m, (_, _, o) in raw_outcomes.items() if o.get("result") == "tie" and "eliminator" in o)
    no_result = min(m for m, (_, _, o) in raw_outcomes.items() if o.get("result") == "no result")
    for match_id in (super_over, no_result):
        season, teams, outcome = raw_outcomes[match_id]
        slugs = [t["id"] for name in teams for t in client.get("/api/teams").json()["teams"] if t["name"] == name]
        for one, other in ((0, 1), (1, 0)):
            h = client.get("/api/teams/head-to-head", params={"team1": slugs[one], "team2": slugs[other], "season": season}).json()
            row = next(m for m in h["recent_meetings"] if m["match_id"] == match_id)
            if match_id == super_over:
                winner = franchise(outcome["eliminator"])
                assert (row["winner"], row["super_over"], row["result_text"]) == (winner, True, f"{winner} won (Super Over)")
                assert h["ties_super_overs"] >= 1
                won_by_team1 = teams[one] == winner
                assert h["team1_super_over_wins" if won_by_team1 else "team2_super_over_wins"] >= 1
            else:
                assert (row["winner"], row["super_over"], row["result_text"]) == (None, False, "No result")
                assert h["no_results"] >= 1 and h["win_pct_denominator"] == h["total_matches"] - h["no_results"]


# ------------------------------------------------------------------ franchise seasons

@needs_raw
def test_franchise_seasons_and_renamed_teams(raw_outcomes):
    teams = {t["name"]: t for t in client.get("/api/teams").json()["teams"]}
    assert min(teams["Gujarat Titans"]["active_seasons"]) == 2022
    assert client.get("/api/teams/gujarat-titans/overview", params={"season": 2021}).status_code == 404
    assert all(s["season"] >= 2022 for s in overview("Gujarat Titans")["season_history"])
    assert max(teams["Deccan Chargers"]["active_seasons"]) == 2012
    assert all(s["season"] <= 2012 for s in overview("Deccan Chargers")["season_history"])

    # Delhi Daredevils matches in the raw files are Delhi Capitals matches
    daredevils = {}
    for path in RAW.glob("*.json"):
        info = json.loads(path.read_text(encoding="utf-8"))["info"]
        if "Delhi Daredevils" in info["teams"]:
            season = int(str(info["dates"][0])[:4])
            daredevils[season] = daredevils.get(season, 0) + 1
    assert daredevils and set(daredevils) <= set(teams["Delhi Capitals"]["active_seasons"])
    for season, count in daredevils.items():
        assert overview("Delhi Capitals", season)["all_time"]["played"] == count, season
    # Deccan Chargers stays separate from Sunrisers Hyderabad
    assert not set(teams["Deccan Chargers"]["active_seasons"]) & set(teams["Sunrisers Hyderabad"]["active_seasons"])


def test_defunct_franchises_work_for_every_season_they_played():
    for team in client.get("/api/teams").json()["teams"]:
        if team["status"] != "Defunct":
            continue
        for season in team["active_seasons"]:
            data = client.get(f"/api/teams/{team['id']}/overview", params={"season": season}).json()
            assert data["coverage"]["seasons_in_scope"] == [season] and data["all_time"]["played"] > 0, (team["id"], season)


# ------------------------------------------------------------------ display codes

def test_no_internal_team_code_in_any_team_response():
    listed = client.get("/api/teams").json()
    bodies = [json.dumps(listed)]
    for team in listed["teams"]:
        assert re.fullmatch(r"[A-Z]{2,4}", team["short_name"]), team["short_name"]
        bodies.append(client.get(f"/api/teams/{team['id']}/overview").text)
        bodies.append(client.get(f"/api/teams/{team['id']}/venues", params={"min_matches": 1}).text)
    bodies.append(client.get("/api/teams/head-to-head", params={"team1": "deccan-chargers", "team2": "delhi-capitals"}).text)
    codes = {t["name"]: t["short_name"] for t in listed["teams"]}
    assert (codes["Deccan Chargers"], codes["Delhi Capitals"]) == ("DCH", "DC")
    assert len(set(codes.values())) == len(codes)
    assert not any("DC_OLD" in body or "_OLD" in body for body in bodies)


def test_team_404_messages_have_no_extra_quotes():
    detail = client.get("/api/teams/gujarat-titans/overview", params={"season": 2021}).json()["detail"]
    assert detail.startswith("Gujarat Titans did not play in the 2021 season")
    assert not detail.startswith(("'", '"'))
