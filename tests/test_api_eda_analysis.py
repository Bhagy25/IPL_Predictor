"""Full-history Statistics & EDA checked against independent calculations.

Expected values are computed here from data/processed (matches, innings, deliveries), data/derived
(dismissals, batting appearances, non-boundary events, replacements, squads) and the raw Cricsheet
JSON. Nothing here reads the engine's tables or reuses its helpers.
"""
import json
import re
import time
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cricketlens.api.app import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
DERIVED = ROOT / "data" / "derived"
RAW = ROOT / "data" / "raw" / "ipl_json"
STAGE2 = ROOT / "reports" / "stage_02"

GT = "Gujarat Titans"
WANKHEDE = "Wankhede Stadium"
# (query, season range, team, venue): default, a season range, a team and a venue
SELECTIONS = [
    ({}, (2008, 2026), None, None),
    ({"season_from": 2008, "season_to": 2012}, (2008, 2012), None, None),
    ({"team": "gujarat-titans"}, (2008, 2026), GT, None),
    ({"venue": WANKHEDE}, (2008, 2026), None, WANKHEDE),
]
SELECTION_IDS = ["default", "2008-2012", "GT", "Wankhede"]

needs_raw = pytest.mark.skipif(not RAW.is_dir() or not any(RAW.glob("*.json")), reason="raw Cricsheet JSON not available")


def pct(part, whole):
    """One-decimal percentage with halves rounded up; None without a denominator."""
    if not whole:
        return None
    return float((Decimal(int(part) * 100) / Decimal(int(whole))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def rate(runs, balls):
    return round(int(runs) / (int(balls) / 6.0), 2) if balls else None


def analysis(**params):
    res = client.get("/api/eda/analysis", params=params)
    assert res.status_code == 200, res.text
    return res.json()["areas"]


# ---------------------------------------------------------------- independent data

@pytest.fixture(scope="module")
def m():
    return pd.read_csv(DATA / "matches.csv")


@pytest.fixture(scope="module")
def inn():
    return pd.read_csv(DATA / "innings.csv")


@pytest.fixture(scope="module")
def d():
    return pd.read_csv(DATA / "deliveries.csv", usecols=[
        "match_id", "season", "innings", "batting_team", "bowling_team", "over_index", "delivery_index", "bowler",
        "runs_batter", "runs_extras", "runs_total", "wides", "noballs", "byes", "legbyes", "legal_delivery",
        "team_wickets_on_ball",
    ])


@pytest.fixture(scope="module")
def dis():
    return pd.read_csv(DERIVED / "dismissals.csv")


@pytest.fixture(scope="module")
def bat():
    return pd.read_csv(DERIVED / "batting_appearances.csv")


def select(m, seasons, team, venue):
    """Matches in a season range, involving a team, at a venue."""
    rows = m[m["season"].between(*seasons)]
    if team:
        rows = rows[(rows["team1"] == team) | (rows["team2"] == team)]
    if venue:
        rows = rows[rows["venue_canonical"] == venue]
    return rows


def batting_side(frame, sel, team):
    rows = frame[frame["match_id"].isin(sel["match_id"])]
    return rows[rows["batting_team"] == team] if team else rows


def label(seasons):
    """Compressed season ranges, written independently: [2008, 2009, 2011] -> '2008–2009, 2011'."""
    out, start = [], None
    for i, s in enumerate(seasons):
        if start is None:
            start = s
        if i == len(seasons) - 1 or seasons[i + 1] != s + 1:
            out.append(f"{start}" if start == s else f"{start}–{s}")
            start = None
    return ", ".join(out)


# ---------------------------------------------------------------- 1. matches and runs

@pytest.mark.parametrize("query,seasons,team,venue", SELECTIONS, ids=SELECTION_IDS)
def test_matches_and_runs(m, d, query, seasons, team, venue):
    area = analysis(**query)["matches_runs"]
    sel = select(m, seasons, team, venue)
    balls = batting_side(d, sel, team)
    data = area["data"]
    assert [(r["season"], r["matches"]) for r in data["by_season"]] == list(sel.groupby("season").size().items())
    by_runs = balls.groupby("season")["runs_total"].sum()
    assert [(r["season"], r["runs"]) for r in data["by_season"]] == [(s, int(by_runs.get(s, 0))) for s in sorted(sel["season"].unique())]
    t = data["totals"]
    assert (t["matches"], t["runs"], t["deliveries"], t["legal_balls"], t["wickets"]) == (
        len(sel), balls["runs_total"].sum(), len(balls), balls["legal_delivery"].sum(), balls["team_wickets_on_ball"].sum())
    assert t["run_rate"] == rate(balls["runs_total"].sum(), balls["legal_delivery"].sum())
    assert area["coverage"]["label"] == label(sorted(int(s) for s in sel["season"].unique()))


def test_matches_by_season_sum_to_archive_and_cover_2008_and_2026(m):
    data = analysis()["matches_runs"]
    assert sum(r["matches"] for r in data["data"]["by_season"]) == len(m) == 1243
    assert data["coverage"]["first_season"] == 2008 and data["coverage"]["last_season"] == 2026


def test_gt_coverage_starts_in_2022(m):
    area = analysis(team="gujarat-titans")["matches_runs"]
    first = int(m[(m["team1"] == GT) | (m["team2"] == GT)]["season"].min())
    assert area["coverage"]["first_season"] == first == 2022


# ---------------------------------------------------------------- 2. scoring trends

@pytest.mark.parametrize("query,seasons,team,venue", SELECTIONS, ids=SELECTION_IDS)
def test_scoring_trends(m, inn, query, seasons, team, venue):
    data = analysis(**query)["scoring_trends"]["data"]
    rows = batting_side(inn, select(m, seasons, team, venue), team)
    for r in data["by_season"]:
        g = rows[rows["season"] == r["season"]]
        first = g[g["innings"] == 1]["runs"]
        assert r["innings"] == len(g)
        assert r["runs_per_innings"] == round(g["runs"].sum() / len(g), 2)
        assert r["first_innings_mean"] == (round(float(first.mean()), 2) if len(first) else None)
    assert data["totals"]["innings"] == len(rows)


# ---------------------------------------------------------------- 3. batting distributions

@pytest.mark.parametrize("query,seasons,team,venue", SELECTIONS, ids=SELECTION_IDS)
def test_batting_distribution(m, bat, query, seasons, team, venue):
    data = analysis(**query)["batting_distribution"]["data"]
    rows = batting_side(bat, select(m, seasons, team, venue), team)
    assert data["summary"]["innings"] == len(rows) == sum(b["count"] for b in data["runs_histogram"])
    assert data["summary"]["runs"] == rows["runs"].sum()
    assert data["runs_histogram"][0] == {"bin": "0", "count": int((rows["runs"] == 0).sum()), "pct": pct((rows["runs"] == 0).sum(), len(rows))}
    assert data["runs_histogram"][-1]["count"] == (rows["runs"] >= 100).sum()
    assert data["strike_rate_innings"] == (rows["balls_faced"] >= 1).sum() == sum(b["count"] for b in data["strike_rate_histogram"])
    top = rows.groupby("player_id")["runs"].sum().sort_values(ascending=False)
    assert (data["leaders"][0]["player_id"], data["leaders"][0]["runs"]) == (top.index[0], top.iloc[0])


def test_strike_rate_minimum_balls_control(bat):
    data = analysis(bat_min_balls=10)["batting_distribution"]["data"]
    assert data["strike_rate_min_balls"] == 10
    assert data["strike_rate_innings"] == (bat["balls_faced"] >= 10).sum()
    assert data["summary"]["innings"] == len(bat)  # the control changes only the strike-rate distribution


# ---------------------------------------------------------------- 4. bowling

def test_bowling_leaderboard_and_innings(m, d, dis):
    data = analysis()["bowling"]["data"]
    ordinary = dis[~dis["is_super_over"] & dis["bowler_credited"]]
    top = ordinary.groupby("bowler_id").size().sort_values(ascending=False)
    assert (data["leaders"][0]["player_id"], data["leaders"][0]["wickets"]) == (top.index[0], top.iloc[0])
    assert data["summary"]["wickets"] == len(ordinary)
    spells = d.groupby(["match_id", "innings", "bowler"])["legal_delivery"].sum()
    assert data["summary"]["innings"] == len(spells)
    assert data["economy_innings"] == (spells >= 1).sum()
    assert analysis(bowl_min_balls=12)["bowling"]["data"]["economy_innings"] == (spells >= 12).sum()


def test_bowling_team_filter_uses_that_teams_bowlers(m, dis):
    data = analysis(team="gujarat-titans", season_from=2022, season_to=2022)["bowling"]["data"]
    sel = select(m, (2022, 2022), GT, None)
    credited = dis[~dis["is_super_over"] & dis["bowler_credited"] & dis["match_id"].isin(sel["match_id"]) & (dis["bowling_team"] == GT)]
    assert data["summary"]["wickets"] == len(credited)


# ---------------------------------------------------------------- 5. phases

def phase_of(over):
    return np.select([over <= 5, over <= 15], ["powerplay", "middle"], "death")


@pytest.mark.parametrize("query,seasons,team,venue", SELECTIONS, ids=SELECTION_IDS)
def test_phases_by_season(m, d, query, seasons, team, venue):
    data = analysis(**query)["phases"]["data"]
    balls = batting_side(d, select(m, seasons, team, venue), team).assign(phase=lambda x: phase_of(x["over_index"]))
    agg = balls.groupby(["season", "phase"])[["runs_total", "legal_delivery", "team_wickets_on_ball"]].sum()
    assert [s["season"] for s in data["by_season"]] == sorted(int(s) for s in balls["season"].unique())
    for s in data["by_season"]:
        for p in s["phases"]:
            r = agg.loc[(s["season"], p["phase"])]
            assert (p["batting_runs"], p["batting_legal_balls"], p["wickets_lost"]) == tuple(int(v) for v in r)
            assert p["batting_run_rate"] == rate(r["runs_total"], r["legal_delivery"])
    if team:
        conceded = d[d["match_id"].isin(select(m, seasons, team, venue)["match_id"]) & (d["bowling_team"] == team)]
        pp = conceded[conceded["over_index"] <= 5]
        assert data["overall"][0]["economy"] == rate(pp["runs_total"].sum(), pp["legal_delivery"].sum())


# ---------------------------------------------------------------- 6. team comparison

def team_record(m, team):
    rows = m[(m["team1"] == team) | (m["team2"] == team)]
    nr = (rows["outcome_type"] == "no result").sum()
    wins = (rows["final_winner"] == team).sum()
    return len(rows), wins, pct(wins, len(rows) - nr)


def test_team_comparison(m):
    teams = {t["team"]: t for t in analysis()["team_comparison"]["data"]["teams"]}
    assert len(teams) == len(set(m["team1"]) | set(m["team2"]))
    for name in ("Chennai Super Kings", GT, "Kochi Tuskers Kerala"):
        played, wins, win_pct = team_record(m, name)
        assert (teams[name]["played"], teams[name]["wins"], teams[name]["win_pct"]) == (played, wins, win_pct)
    assert teams["Chennai Super Kings"]["win_pct"] == 55.8


def test_team_filter_note_on_team_comparison_and_data_unchanged():
    base = analysis()["team_comparison"]
    with_team = analysis(team="gujarat-titans")["team_comparison"]
    assert [n["filter"] for n in with_team["unaffected_by"]] == ["team"]
    assert with_team["unaffected_by"][0]["note"].startswith("Not affected by the team filter")
    strip = lambda rows: [{k: v for k, v in r.items() if k != "selected"} for r in rows]  # noqa: E731
    assert strip(with_team["data"]["teams"]) == strip(base["data"]["teams"])
    assert [t["team"] for t in with_team["data"]["teams"] if t["selected"]] == [GT]
    assert base["unaffected_by"] == []


# ---------------------------------------------------------------- 7. player comparison

KOHLI, ROHIT, WARNER = "ba607b88", "740742ef", "dcce6f09"


def test_player_comparison(bat):
    res = client.get("/api/eda/player-comparison", params={"players": f"{KOHLI},{ROHIT},{WARNER}"})
    assert res.status_code == 200
    players = {p["player_id"]: p for p in res.json()["area"]["data"]["players"]}
    for pid in (KOHLI, ROHIT, WARNER):
        rows = bat[bat["player_id"] == pid]
        assert players[pid]["batting"]["runs"] == rows["runs"].sum()
        assert players[pid]["batting"]["innings"] == len(rows)
    ranged = client.get("/api/eda/player-comparison", params={
        "players": f"{KOHLI},{WARNER}", "season_from": 2018, "season_to": 2026}).json()["area"]
    warner = next(p for p in ranged["data"]["players"] if p["player_id"] == WARNER)
    rows = bat[(bat["player_id"] == WARNER) & bat["season"].between(2018, 2026)]
    assert warner["batting"]["runs"] == rows["runs"].sum()
    assert warner["coverage"] == label(sorted(int(s) for s in rows["season"].unique()))


def test_player_comparison_validation_and_unsupported_filters():
    assert client.get("/api/eda/player-comparison", params={"players": KOHLI}).status_code == 422
    assert client.get("/api/eda/player-comparison", params={"players": f"{KOHLI},nobody00"}).status_code == 422
    res = client.get("/api/eda/player-comparison", params={"players": f"{KOHLI},{ROHIT}", "team": "gujarat-titans"}).json()
    assert [n["filter"] for n in res["area"]["unaffected_by"]] == ["team"]


# ---------------------------------------------------------------- 8. venues

def test_venues(m, inn):
    data = analysis()["venues"]["data"]
    assert data["venues_total"] == m["venue_canonical"].nunique() == data["venues_shown"]
    venues = {v["venue"]: v for v in data["venues"]}
    w = m[m["venue_canonical"] == WANKHEDE]
    first = inn[(inn["innings"] == 1) & inn["match_id"].isin(w["match_id"])]
    batted_first_won = (w.merge(first[["match_id", "batting_team"]], on="match_id")
                        .pipe(lambda x: (x["final_winner"] == x["batting_team"]).sum()))
    decided = (w["outcome_type"] != "no result").sum()
    assert venues[WANKHEDE]["matches"] == len(w)
    assert venues[WANKHEDE]["first_innings_mean"] == round(float(first["runs"].mean()), 2)
    assert venues[WANKHEDE]["result"]["win_pct"] == pct(batted_first_won, decided)


def test_venue_minimum_control(m):
    data = analysis(venue_min_matches=10)["venues"]["data"]
    counts = m["venue_canonical"].value_counts()
    assert data["venues_shown"] == (counts >= 10).sum()
    assert data["matches_shown"] == counts[counts >= 10].sum()


def test_venue_filter_note_on_venue_analysis_and_data_unchanged():
    base = analysis()["venues"]
    with_venue = analysis(venue=WANKHEDE)["venues"]
    assert [n["filter"] for n in with_venue["unaffected_by"]] == ["venue"]
    strip = lambda rows: [{k: v for k, v in r.items() if k != "selected"} for r in rows]  # noqa: E731
    assert strip(with_venue["data"]["venues"]) == strip(base["data"]["venues"])
    assert [v["venue"] for v in with_venue["data"]["venues"] if v["selected"]] == [WANKHEDE]


def test_venues_with_team_match_team_analysis():
    eda = analysis(team="chennai-super-kings")["venues"]["data"]["venues"]
    team = client.get("/api/teams/chennai-super-kings/venues", params={"min_matches": 1}).json()["venues"]
    assert {v["venue"]: v["result"]["win_pct"] for v in eda} == {v["venue"]: v["win_pct"] for v in team}


# ---------------------------------------------------------------- 9. toss

@pytest.mark.parametrize("query,seasons,team,venue", SELECTIONS, ids=SELECTION_IDS)
def test_toss(m, query, seasons, team, venue):
    data = analysis(**query)["toss"]["data"]["overall"]
    sel = select(m, seasons, team, venue)
    tosses = sel[sel["toss_winner"] == team] if team else sel
    nr = (tosses["outcome_type"] == "no result").sum()
    wins = (tosses["toss_winner"] == tosses["final_winner"]).sum()
    assert data["tosses_won"] == len(tosses)
    assert data["elected_to_field"] == (tosses["toss_decision"] == "field").sum()
    assert data["after_winning_toss"]["wins"] == wins
    assert data["after_winning_toss"]["win_pct_denominator"] == len(tosses) - nr
    assert data["after_winning_toss"]["win_pct"] == pct(wins, len(tosses) - nr)


def test_toss_with_team_matches_team_analysis():
    eda = analysis(team="chennai-super-kings")["toss"]["data"]["overall"]
    team = client.get("/api/teams/chennai-super-kings/overview").json()["toss_stats"]
    for k in ("after_winning_toss", "chose_to_bat", "chose_to_field"):
        assert eda[k] == team[k]


# ---------------------------------------------------------------- 10. batting first vs chasing

@pytest.mark.parametrize("query,seasons,team,venue", SELECTIONS, ids=SELECTION_IDS)
def test_batting_first_and_chasing(m, inn, query, seasons, team, venue):
    data = analysis(**query)["innings_order"]["data"]
    sel = select(m, seasons, team, venue)
    first = inn[inn["innings"] == 1].set_index("match_id")["batting_team"]
    decided = sel[sel["final_winner"].notna()].assign(first=lambda x: x["match_id"].map(first))
    if team:
        bat_first = decided[decided["first"] == team]
        chase = decided[decided["first"] != team]
        bf_wins, ch_wins = (bat_first["final_winner"] == team).sum(), (chase["final_winner"] == team).sum()
    else:
        bat_first = chase = decided
        bf_wins = (decided["final_winner"] == decided["first"]).sum()
        ch_wins = len(decided) - bf_wins
    assert (data["overall"]["batting_first"]["wins"], data["overall"]["batting_first"]["win_pct_denominator"]) == (bf_wins, len(bat_first))
    assert data["overall"]["chasing"]["wins"] == ch_wins
    assert data["overall"]["batting_first"]["win_pct"] == pct(bf_wins, len(bat_first))


def test_outcome_breakdown_reconciles_to_archive(m):
    oc = analysis()["innings_order"]["data"]["outcomes"]
    assert oc["decided"] == m["final_winner"].notna().sum() == 1234
    assert oc["decided_in_regulation"] == (m["decided_by"] == "regulation").sum()
    assert oc["decided_by_super_over"] == (m["decided_by"] == "super_over").sum()
    assert oc["no_result"] == (m["outcome_type"] == "no result").sum()
    assert oc["decided_in_regulation"] + oc["decided_by_super_over"] + oc["no_result"] == oc["matches"] == len(m) == 1243


def test_innings_order_with_team_matches_team_analysis():
    eda = analysis(team="chennai-super-kings")["innings_order"]["data"]["overall"]
    team = client.get("/api/teams/chennai-super-kings/overview").json()
    assert eda["batting_first"] == team["batting_first"] and eda["chasing"] == team["chasing"]


# ---------------------------------------------------------------- 11. innings scores

@pytest.mark.parametrize("query,seasons,team,venue", SELECTIONS, ids=SELECTION_IDS)
def test_innings_score_distributions(m, inn, query, seasons, team, venue):
    data = analysis(**query)["innings_scores"]["data"]["by_innings"]
    rows = batting_side(inn, select(m, seasons, team, venue), team)
    for d_ in data:
        runs = rows[rows["innings"] == d_["innings"]]["runs"]
        assert d_["n"] == len(runs) == sum(b["count"] for b in d_["histogram"])
        assert (d_["mean"], d_["median"], d_["max"]) == (round(float(runs.mean()), 2), round(float(runs.median()), 1), runs.max())
        assert d_["full_innings"] == (rows[rows["innings"] == d_["innings"]]["legal_balls"] == 120).sum()


# ---------------------------------------------------------------- 12. dismissals

@pytest.mark.parametrize("query,seasons,team,venue", SELECTIONS, ids=SELECTION_IDS)
def test_dismissal_types(m, d, dis, query, seasons, team, venue):
    data = analysis(**query)["dismissals"]["data"]
    sel = select(m, seasons, team, venue)
    rows = batting_side(dis, sel, team)
    ordinary, super_over = rows[~rows["is_super_over"]], rows[rows["is_super_over"]]
    assert {k["kind"]: k["count"] for k in data["kinds"]} == ordinary["kind"].value_counts().to_dict()
    assert data["events"] == len(ordinary) == sum(k["count"] for k in data["kinds"])
    assert data["bowler_credited"] == ordinary["bowler_credited"].sum()
    assert data["team_wickets"] == (ordinary["kind"] != "retired hurt").sum()
    assert data["team_wickets_from_deliveries"] == batting_side(d, sel, team)["team_wickets_on_ball"].sum()
    assert data["super_over_events_excluded"] == len(super_over)


def test_dismissals_reconcile_with_archive_totals(dis):
    data = analysis()["dismissals"]["data"]
    assert data["events"] == (~dis["is_super_over"]).sum() == 14674
    assert data["team_wickets"] == data["team_wickets_from_deliveries"] == 14655
    assert {k["kind"]: k["count"] for k in data["kinds"]}["retired hurt"] == 19
    assert data["super_over_events_excluded"] == dis["is_super_over"].sum() > 0


def test_dismissal_kinds_are_computed(dis):
    # Replaces the /api/eda/full-history dismissal_distribution check
    kinds = {k["kind"]: k["count"] for k in analysis()["dismissals"]["data"]["kinds"]}
    assert kinds == dis[~dis["is_super_over"]]["kind"].value_counts().to_dict()


# ---------------------------------------------------------------- 13. boundaries

@pytest.fixture(scope="module")
def non_boundary():
    nb = pd.read_csv(DERIVED / "non_boundary_events.csv")
    return set(zip(nb["match_id"], nb["innings"], nb["over_index"], nb["delivery_index"]))


@pytest.mark.parametrize("query,seasons,team,venue", SELECTIONS, ids=SELECTION_IDS)
def test_boundaries_and_dot_balls(m, d, non_boundary, query, seasons, team, venue):
    data = analysis(**query)["boundaries"]["data"]["totals"]
    balls = batting_side(d, select(m, seasons, team, venue), team)
    flagged = pd.Series([k in non_boundary for k in zip(balls["match_id"], balls["innings"], balls["over_index"], balls["delivery_index"])], index=balls.index)
    fours = ((balls["runs_batter"] == 4) & ~flagged).sum()
    sixes = ((balls["runs_batter"] == 6) & ~flagged).sum()
    dots = ((balls["legal_delivery"] == 1) & (balls["runs_total"] == 0)).sum()
    assert (data["fours"], data["sixes"], data["dot_balls"]) == (fours, sixes, dots)
    assert data["boundary_run_pct"] == pct(4 * fours + 6 * sixes, balls["runs_total"].sum())
    assert data["dot_ball_pct"] == pct(dots, balls["legal_delivery"].sum())


# ---------------------------------------------------------------- 14. anomalies

@pytest.fixture(scope="module")
def raw_penalties():
    """Penalty-run deliveries in ordinary innings, read from the raw JSON: {(match_id, batting_team): runs}."""
    found = []
    for path in RAW.glob("*.json"):
        match = json.loads(path.read_text(encoding="utf-8"))
        for innings in match["innings"]:
            if innings.get("super_over"):
                continue
            for over in innings.get("overs", []):
                for ball in over["deliveries"]:
                    runs = ball.get("extras", {}).get("penalty")
                    if runs:
                        found.append((int(path.stem), innings["team"], runs))
    return found


@needs_raw
def test_anomalies_default(m, raw_penalties):
    data = analysis()["anomalies"]["data"]
    reps = pd.read_csv(DERIVED / "match_replacements.csv")
    assert data["super_over_matches"] == (m["decided_by"] == "super_over").sum() == 16
    assert data["dl_matches"] == (m["outcome_method"] == "D/L").sum()
    assert data["no_results"] == (m["outcome_type"] == "no result").sum()
    assert data["penalty_run_deliveries"] == len(raw_penalties)
    assert data["penalty_runs"] == sum(r for _, _, r in raw_penalties)
    assert data["substitutions"] == len(reps)
    assert data["substitutions_by_reason"] == reps["reason"].value_counts().sort_index().to_dict()
    assert data["missing_city_matches"] == m["city"].isna().sum()
    assert len(data["lists"]["super_over"]) == data["super_over_matches"]
    assert data["stage1_audit"]["label"].startswith("Static Stage 1 audit")


@pytest.mark.parametrize("query,seasons,team,venue", SELECTIONS[1:], ids=SELECTION_IDS[1:])
def test_anomalies_filtered(m, query, seasons, team, venue):
    data = analysis(**query)["anomalies"]["data"]
    sel = select(m, seasons, team, venue)
    reps = pd.read_csv(DERIVED / "match_replacements.csv")
    reps = reps[reps["match_id"].isin(sel["match_id"])]
    if team:
        reps = reps[reps["team"] == team]
    assert data["super_over_matches"] == (sel["decided_by"] == "super_over").sum()
    assert data["no_results"] == (sel["outcome_type"] == "no result").sum()
    assert data["substitutions"] == len(reps)
    assert data["outcomes"]["matches"] == len(sel)


# ---------------------------------------------------------------- 15. correlations

def first_innings_table(m, d, sel, team):
    balls = batting_side(d, sel, team)
    balls = balls[balls["innings"] == 1].assign(phase=lambda x: phase_of(x["over_index"]))
    total = balls.groupby("match_id")["runs_total"].sum()
    pp = balls[balls["phase"] == "powerplay"].groupby("match_id")["runs_total"].sum().reindex(total.index, fill_value=0)
    return total, pp


def test_correlations_default(m, d):
    data = analysis()["correlations"]["data"]
    total, pp = first_innings_table(m, d, m, None)
    assert data["n"] == len(total)
    pair = next(p for p in data["pairs_with_total"] if p["x"] == "powerplay_runs")
    assert pair["pearson"] == round(float(np.corrcoef(pp, total)[0, 1]), 3)
    assert pair["spearman"] == round(float(pd.Series(pp).rank().corr(pd.Series(total).rank())), 3)


def test_correlation_minimum_n_rule(m, d):
    small = analysis(team="gujarat-titans", season_from=2022, season_to=2022)["correlations"]
    total, _ = first_innings_table(m, d, select(m, (2022, 2022), GT, None), GT)
    assert small["data"]["n"] == len(total) < small["data"]["min_n"] == 30
    assert small["data"]["state"] == "insufficient_sample"
    assert small["data"]["pearson"] is None and small["data"]["spearman"] is None
    assert all(p["pearson"] is None and p["spearman"] is None for p in small["data"]["pairs_with_total"])
    assert str(len(total)) in small["data"]["explanation"]
    big = analysis(team="gujarat-titans")["correlations"]["data"]
    assert big["n"] >= 30 and big["state"] == "ok" and big["pearson"] is not None


# ---------------------------------------------------------------- filters, empty selections, metadata

def test_every_area_declares_metadata():
    areas = analysis()
    assert len(areas) == 14  # plus the player comparison endpoint: 15 areas
    for a in areas.values():
        assert a["supported_filters"] and a["definitions"] and a["units"] and a["source"]
        assert a["coverage"]["first_season"] == 2008 and a["coverage"]["last_season"] == 2026
        assert a["sample"] and all(s["value"] > 0 for s in a["sample"])


def test_empty_combination_explains_instead_of_zeros():
    areas = analysis(team="gujarat-titans", season_from=2008, season_to=2012)
    for area_id, a in areas.items():
        if area_id == "team_comparison":  # does not support the team filter
            assert a["state"] == "ok"
            continue
        assert a["state"] == "empty" and a["data"] is None and a["coverage"] is None, area_id
        assert "Gujarat Titans" in a["empty_reason"] and "2022–2026" in a["empty_reason"]


@pytest.mark.parametrize("params", [
    {"season_from": 2007}, {"season_to": 2027}, {"season_from": 2012, "season_to": 2010},
    {"team": "not-a-team"}, {"venue": "Nowhere Oval"}, {"season_from": "abc"}, {"venue_min_matches": 0},
])
def test_invalid_filters_return_422(params):
    assert client.get("/api/eda/analysis", params=params).status_code == 422


def test_filter_options_cover_archive(m):
    opts = client.get("/api/eda/filters").json()
    assert opts["seasons"] == sorted(int(s) for s in m["season"].unique())
    assert len(opts["venues"]) == m["venue_canonical"].nunique()
    assert {t["name"] for t in opts["teams"]} == set(m["team1"]) | set(m["team2"])


def test_warm_responses_are_fast():
    analysis(season_from=2015, season_to=2020)
    for path in ("/api/eda/analysis?season_from=2015&season_to=2020", "/api/eda/analysis"):
        client.get(path)
        start = time.perf_counter()
        assert client.get(path).status_code == 200
        assert time.perf_counter() - start < 0.3, path


# ---------------------------------------------------------------- homepage player KPI

def test_homepage_player_kpi_is_the_directory_total(m, d, bat):
    metrics = {k["id"]: k for k in client.get("/api/overview/summary").json()["metrics"]}
    directory = client.get("/api/players", params={"page_size": 1}).json()["directory_counts"]["all"]
    squads = pd.read_csv(DERIVED / "match_players.csv")
    bowled = squads.merge(d[["match_id", "bowler"]].drop_duplicates(), left_on=["match_id", "player_name"], right_on=["match_id", "bowler"])
    expected = len(set(bat["player_id"]) | set(bowled["player_id"]))
    assert metrics["players"]["numeric_value"] == directory == expected
    assert metrics["players"]["value"] == f"{expected:,}" and metrics["players"]["label"] == "Players"
    assert "batted" in metrics["players"]["description"] and "bowled" in metrics["players"]["description"]
    # The other KPIs still match the archive
    assert metrics["matches"]["numeric_value"] == len(m)
    assert metrics["deliveries"]["numeric_value"] == len(d)
    assert metrics["runs"]["numeric_value"] == d["runs_total"].sum()
    assert metrics["wickets"]["numeric_value"] == d["team_wickets_on_ball"].sum()


# ---------------------------------------------------------------- Focused Studies (Stage 2 figures)

def expected_coverage(fig, m):
    """Coverage from the figure's source file: its season column, its name, or the matching summary scope."""
    path = next(STAGE2.glob(f"session_0*/{fig['source_file']}"))
    table = pd.read_csv(path)
    if "season" in table.columns and table["season"].min() >= 2000:
        return f"{table['season'].min()}–{table['season'].max()}"
    years = re.search(r"_(\d{4})_(\d{4})\.csv$", fig["source_file"])
    if years:
        return f"{years.group(1)}–{years.group(2)}"
    if "pre2026" in fig["source_file"]:
        dev = m[m["season"] < 2026]["season"]
        return f"{dev.min()}–{dev.max()}"
    # numeric_descriptive_summary.csv: the first-innings scope whose count is the figure's sample
    n = int(re.sub(r"\D", "", fig["sample_size"].split()[0]))
    scope = table[(table["variable"] == "first_innings_runs") & (table["count"] == n)]["scope"].iloc[0]
    a, b = re.findall(r"\d{4}", scope)
    return f"{a}–{b}"


def test_focused_studies_figures_served_with_verified_coverage(m):
    catalog = client.get("/api/eda/catalog").json()
    assert catalog["total_figures"] == len(catalog["figures"]) == 20
    for fig in catalog["figures"]:
        res = client.get(f"/api/eda/figures/{fig['id']}.png")
        assert res.status_code == 200 and res.headers["content-type"] == "image/png", fig["id"]
        assert fig["coverage_span"] == expected_coverage(fig, m), fig["id"]
        assert fig["coverage_evidence"] and fig["static_note"] == "Static research figure — not affected by filters"
    spans = [f["coverage_span"] for f in catalog["figures"]]
    assert spans.count("2008–2025") == 5 and "2026" not in " ".join(spans)
