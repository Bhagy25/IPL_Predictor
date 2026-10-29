"""IPL Overview homepage checked against independent calculations.

Expected values are computed here from data/processed (matches, innings, deliveries), data/derived
(dismissals) and the raw Cricsheet JSON; nothing reads the engine's tables. A guard test fails when a
hard-coded statistic is reintroduced into the homepage service or components.
"""
from __future__ import annotations

import ast
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cricketlens.api.app import app
from cricketlens.api.services.overview_service import overview_service
from cricketlens.pipeline import franchise

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
DERIVED = ROOT / "data" / "derived"
RAW = ROOT / "data" / "raw" / "ipl_json"

needs_raw = pytest.mark.skipif(not RAW.is_dir() or not any(RAW.glob("*.json")), reason="raw Cricsheet JSON not available")


def pct(part, whole):
    """One-decimal percentage with halves rounded up; None without a denominator."""
    if not whole:
        return None
    return float((Decimal(int(part) * 100) / Decimal(int(whole))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def span(seasons):
    """Compressed season ranges, written independently: [2008, 2009, 2011] -> '2008–2009, 2011'."""
    out, start = [], None
    for i, s in enumerate(seasons):
        start = s if start is None else start
        if i == len(seasons) - 1 or seasons[i + 1] != s + 1:
            out.append(f"{start}" if start == s else f"{start}–{s}")
            start = None
    return ", ".join(out)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def m():
    return pd.read_csv(DATA / "matches.csv")


@pytest.fixture(scope="module")
def inn():
    return pd.read_csv(DATA / "innings.csv")


@pytest.fixture(scope="module")
def d():
    return pd.read_csv(DATA / "deliveries.csv", usecols=[
        "match_id", "season", "innings", "runs_total", "legal_delivery", "wides", "noballs", "team_wickets_on_ball",
    ])


@pytest.fixture(scope="module")
def summary(client):
    res = client.get("/api/overview/summary")
    assert res.status_code == 200
    return res.json()


@pytest.fixture(scope="module")
def charts(client):
    res = client.get("/api/overview/charts")
    assert res.status_code == 200
    return res.json()


def test_health_check_endpoint(client):
    data = client.get("/api/health").json()
    assert data["status"] == "healthy"
    assert data["service"] == "CricketLens Analytical Backend"


def test_health_archive_counts_come_from_data(client, m):
    data = client.get("/api/health").json()
    assert data["archive_matches"] == len(m)
    assert data["archive"] == {
        "matches": len(m),
        "seasons": m["season"].nunique(),
        "first_season": int(m["season"].min()),
        "last_season": int(m["season"].max()),
        "first_match_date": m["date"].min(),
        "last_match_date": m["date"].max(),
    }
    # Guard: no number is typed into the health response
    source = (ROOT / "src" / "cricketlens" / "api" / "app.py").read_text(encoding="utf-8")
    health = source[source.index("async def health_check"):]
    assert not re.search(r"archive_matches\s*=\s*\d", health)
    assert not re.search(r"\b(1243|1,243|2008|2026)\b", health)


# ---------------------------------------------------------------- KPIs, coverage, notices

def test_kpi_values(summary, m, d, client):
    k = {x["id"]: x for x in summary["metrics"]}
    assert list(k) == ["seasons", "matches", "deliveries", "teams", "players", "venues", "runs", "wickets"]
    expected = {
        "seasons": m["season"].nunique(),
        "matches": len(m),
        "deliveries": len(d),
        "teams": len(set(m["team1"]) | set(m["team2"])),
        "players": client.get("/api/players", params={"page_size": 1}).json()["directory_counts"]["all"],
        "venues": m["venue_canonical"].nunique(),
        "runs": d["runs_total"].sum(),
        "wickets": d["team_wickets_on_ball"].sum(),
    }
    for key, value in expected.items():
        assert k[key]["numeric_value"] == value, key
        assert k[key]["value"] == f"{value:,}", key


def test_kpi_status_and_descriptions(summary, m, inn, d):
    k = {x["id"]: x for x in summary["metrics"]}
    seasons = sorted(m["season"].unique())
    assert k["seasons"]["statusText"] == f"{seasons[0]}–{seasons[-1]} complete"
    assert seasons == list(range(seasons[0], seasons[-1] + 1))
    assert k["seasons"]["description"] == f"All {len(seasons)} men's Indian Premier League tournament editions."

    # Matches whose innings totals equal the sums of their deliveries
    sums = d.groupby(["match_id", "innings"]).agg(runs=("runs_total", "sum"), wickets=("team_wickets_on_ball", "sum"), legal_balls=("legal_delivery", "sum"))
    joined = inn.set_index(["match_id", "innings"])[["runs", "wickets", "legal_balls"]].join(sums, rsuffix="_d")
    bad = joined[(joined["runs"] != joined["runs_d"]) | (joined["wickets"] != joined["wickets_d"]) | (joined["legal_balls"] != joined["legal_balls_d"])]
    verified = pct(len(m) - bad.index.get_level_values(0).nunique(), len(m))
    assert k["matches"]["statusText"] == f"{verified:g}% verified"
    nr = (m["outcome_type"] == "no result").sum()
    assert f"including {nr} no results" in k["matches"]["description"]

    legal = d["legal_delivery"].sum()
    assert k["deliveries"]["statusText"] == f"{legal:,} legal balls"
    assert k["deliveries"]["description"] == (
        f"{len(d):,} ball events including {(d['wides'] > 0).sum():,} wides and {(d['noballs'] > 0).sum():,} no-balls; "
        f"{legal:,} legal deliveries.")

    last = m["season"].max()
    active = len(set(m.loc[m["season"] == last, "team1"]) | set(m.loc[m["season"] == last, "team2"]))
    total = len(set(m["team1"]) | set(m["team2"]))
    assert k["teams"]["statusText"] == f"{active} active franchises"
    assert f"{active} active franchises (those that played in {last}) and {total - active} historical defunct" in k["teams"]["description"]

    venues, raw = m["venue_canonical"].nunique(), m["venue"].nunique()
    assert k["venues"]["statusText"] == f"{venues} canonical grounds"
    assert f"normalized from {raw} raw naming strings" in k["venues"]["description"]

    dis = pd.read_csv(DERIVED / "dismissals.csv", usecols=["is_super_over", "kind"])
    hurt = ((~dis["is_super_over"]) & (dis["kind"] == "retired hurt")).sum()
    assert f"excludes {hurt} recorded retired-hurt events" in k["wickets"]["description"]
    assert "registry IDs who batted" in k["players"]["description"]


def test_coverage_dates(summary, m):
    c = summary["coverage"]
    assert (c["first_match_date"], c["last_match_date"]) == (m["date"].min(), m["date"].max())
    assert c["total_matches"] == len(m)
    assert c["seasons_count"] == m["season"].nunique()
    assert c["seasons_span"] == span(sorted(m["season"].unique()))


def test_notices(summary, m, d):
    n = summary["notices"]
    dis = pd.read_csv(DERIVED / "dismissals.csv", usecols=["is_super_over", "kind"])
    hurt = ((~dis["is_super_over"]) & (dis["kind"] == "retired hurt")).sum()
    assert f"distinguish {len(d):,} ball events from {d['legal_delivery'].sum():,} legal deliveries" in n[0]
    assert f"Total runs ({d['runs_total'].sum():,})" in n[1]
    assert f"Wickets ({d['team_wickets_on_ball'].sum():,})" in n[2] and f"{hurt} retired hurt events" in n[2]
    assert f"({m['super_over_innings'].sum()} innings across {(m['super_over_innings'] > 0).sum()} tied games)" in n[3]
    assert f"IPL {m['season'].max()}, the latest season" in n[5]


# ---------------------------------------------------------------- champions

@pytest.fixture(scope="module")
def raw_finals():
    """{season: canonical winner} of every match recorded with event stage 'Final' in the raw JSON."""
    finals = {}
    for path in RAW.glob("*.json"):
        info = json.loads(path.read_text(encoding="utf-8"))["info"]
        if info.get("event", {}).get("stage") == "Final":
            season = int(str(info["season"])[-4:]) if "/" not in str(info["season"]) else int(info["dates"][0][:4])
            assert season not in finals, f"two finals in {season}"
            finals[season] = franchise(info["outcome"]["winner"])
    return finals


@needs_raw
def test_champions_are_the_winners_of_each_final(charts, raw_finals, m):
    champions = charts["champions"]
    assert len(champions) == m["season"].nunique() == len(raw_finals) == 19
    assert {c["season"]: c["champion"] for c in champions} == raw_finals
    # The final is also each season's last match by date
    last = m.sort_values(["date", "match_id"]).groupby("season").tail(1).set_index("season")["final_winner"].to_dict()
    assert last == raw_finals


@needs_raw
def test_title_counts(charts, client, raw_finals):
    counts = pd.Series(raw_finals).value_counts().to_dict()
    assert counts == {
        "Mumbai Indians": 5, "Chennai Super Kings": 5, "Kolkata Knight Riders": 3, "Royal Challengers Bengaluru": 2,
        "Rajasthan Royals": 1, "Deccan Chargers": 1, "Sunrisers Hyderabad": 1, "Gujarat Titans": 1,
    }
    records = {t["team"]: t for t in charts["team_records"]}
    teams = {t["name"]: t for t in client.get("/api/teams").json()["teams"]}
    for team, t in teams.items():
        years = sorted(s for s, w in raw_finals.items() if w == team)
        assert (t["titles"], t["title_years"]) == (len(years), years), team
        if team in records:
            assert (records[team]["titles"], records[team]["title_years"]) == (len(years), years), team


# ---------------------------------------------------------------- charts

def test_matches_and_scoring_by_season(charts, m, inn, d):
    first = inn[inn["innings"] == 1]
    for row in charts["matches_per_season"]:
        g = m[m["season"] == row["season"]]
        assert (row["matches"], row["teams"]) == (len(g), len(set(g["team1"]) | set(g["team2"])))
    assert sum(r["matches"] for r in charts["matches_per_season"]) == len(m)
    for row in charts["scoring_trends"]:
        runs = first[first["season"] == row["season"]]["runs"]
        assert row["avg_first_innings_runs"] == round(runs.mean(), 1)
        assert row["median_first_innings_runs"] == round(runs.median(), 1)
        assert row["total_runs"] == d[d["season"] == row["season"]]["runs_total"].sum()
    means = first.groupby("season")["runs"].mean()
    t = charts["scoring_trend"]
    assert t["overall_mean"] == round(first["runs"].mean(), 1)
    assert t["slope_runs_per_season"] == round(float(np.polyfit(means.index, means.values, 1)[0]), 2)
    assert t["peak_season"] == means.round(1).idxmax()


def test_result_distribution_matches_team_and_eda_definitions(charts, client, m):
    r = {x["category"]: x["count"] for x in charts["result_distribution"]}
    assert r["Regulation Win"] == (m["decided_by"] == "regulation").sum()
    assert r["Tie (Super Over)"] == ((m["decided_by"] == "super_over") & m["final_winner"].notna()).sum()
    assert r["No Result"] == (m["outcome_type"] == "no result").sum()
    assert sum(r.values()) == len(m) == 1243
    eda = client.get("/api/eda/analysis").json()["areas"]["innings_order"]["data"]["outcomes"]
    oc = charts["outcomes"]
    assert {k: oc[k] for k in eda} == eda
    assert oc["decided_pct"] == pct(m["final_winner"].notna().sum(), len(m))
    assert f"including {(m['outcome_method'] == 'D/L').sum()} by the D/L method" in charts["result_distribution"][0]["description"]


@pytest.fixture(scope="module")
def first_innings(d):
    """First innings from deliveries.csv with the completed-innings rule applied independently."""
    per = d.groupby(["match_id", "innings"]).agg(runs=("runs_total", "sum"), balls=("legal_delivery", "sum"), wickets=("team_wickets_on_ball", "sum")).reset_index()
    first = per[per["innings"] == 1].copy()
    first["completed"] = first["match_id"].isin(per.loc[per["innings"] == 2, "match_id"]) | (first["wickets"] >= 10) | (first["balls"] >= 120)
    return first


def test_score_histogram_eligibility(charts, first_innings, m):
    s = charts["scoring_summary"]
    eligible = first_innings[first_innings["completed"]]
    excluded = first_innings[~first_innings["completed"]]
    assert s["first_innings_recorded"] == len(first_innings) == len(m)
    assert s["n"] == len(eligible) == sum(b["count"] for b in charts["scoring_distribution"])
    assert sorted(e["match_id"] for e in s["excluded"]) == sorted(excluded["match_id"])
    # Every excluded innings belongs to a no-result match without a second innings
    nr = set(m.loc[m["outcome_type"] == "no result", "match_id"])
    assert set(excluded["match_id"]) <= nr
    runs = eligible["runs"]
    edges = [(None, 120), (120, 150), (150, 180), (180, 210), (210, None)]
    counts = [int(runs.between(lo if lo is not None else -1, (hi - 1) if hi is not None else 10_000).sum()) for lo, hi in edges]
    assert [b["count"] for b in charts["scoring_distribution"]] == counts
    assert [b["percentage"] for b in charts["scoring_distribution"]] == [pct(c, len(runs)) for c in counts]
    assert (s["q1"], s["q3"], s["min"], s["max"]) == (runs.quantile(0.25), runs.quantile(0.75), runs.min(), runs.max())
    assert "6 matches abandoned" not in json.dumps(charts)


def test_team_records_window_and_values(charts, m):
    w = charts["team_records_window"]
    last = m["season"].max()
    current = set(m.loc[m["season"] == last, "team1"]) | set(m.loc[m["season"] == last, "team2"])
    start = max(m[(m["team1"] == t) | (m["team2"] == t)]["season"].min() for t in current)
    # Descriptive records include the latest season (only model evaluation holds it out)
    assert (w["first_season"], w["last_season"], w["franchises"]) == (start, last, len(current))
    assert w["label"] == f"{start}–{last}"
    window = m[m["season"].between(start, last)]
    records = {t["team"]: t for t in charts["team_records"]}
    assert set(records) == current
    for team in current:
        rows = window[(window["team1"] == team) | (window["team2"] == team)]
        nr = (rows["outcome_type"] == "no result").sum()
        wins = (rows["final_winner"] == team).sum()
        losses = (rows["final_winner"].notna() & (rows["final_winner"] != team)).sum()
        r = records[team]
        assert (r["played"], r["wins"], r["losses"], r["tied_no_result"]) == (len(rows), wins, losses, len(rows) - wins - losses)
        assert r["win_pct"] == pct(wins, len(rows) - nr)


def test_service_caching():
    overview_service._summary_cache = None
    overview_service._charts_cache = None
    assert overview_service.get_summary() is overview_service.get_summary()
    assert overview_service.get_charts() is overview_service.get_charts()


# ---------------------------------------------------------------- guard against hard-coded statistics

HOMEPAGE_PY = [ROOT / "src/cricketlens/api/services/overview_service.py", ROOT / "src/cricketlens/api/routes_overview.py"]
HOMEPAGE_TSX = [ROOT / "web/src/pages/IPLOverviewPage.tsx", ROOT / "web/src/components/KPICards.tsx",
                ROOT / "web/src/components/PerspectiveCharts.tsx", ROOT / "web/src/components/TeamRecordsTable.tsx"]
NOUNS = (r"match(?:es)?|seasons?|runs?|innings|teams?|franchises?|wins?|ties?|NR|titles?|deliver(?:y|ies)|balls?|"
         r"wickets?|venues?|grounds?|players?|batters?|editions?|games?|events?")
SUSPICIOUS = [
    re.compile(r"\b(19|20)\d\d\b"),                       # a year
    re.compile(r"\b\d{1,3}(,\d{3})+\b"),                  # 1,243
    re.compile(r"\b\d+(\.\d+)?%"),                        # 98.0%
    re.compile(r"\b\d+\.\d+\b"),                          # 168.6
    re.compile(r"\b\d+\s*[–-]\s*\d+\b"),                  # 147–188
    re.compile(r"\b\d{3,}\b"),                            # 736
    # 76 matches, 10-team, 5 defunct teams (an ordinal such as "1st Innings" is a label, not a count)
    re.compile(rf"\b\d+(?![A-Za-z\d])\s*(?:-\s*)?(?:[A-Za-z]+\s+){{0,2}}(?:{NOUNS})\b", re.I),
]
# Genuine constants of the game and of the documented rules, and infrastructure text
ALLOWED = {"120 legal balls", "10 wickets", "127.0.0.1:8000", "Port 8000"}


def suspicious(text):
    for phrase in ALLOWED:
        text = text.replace(phrase, " ")
    return [hit.group(0) for pattern in SUSPICIOUS for hit in pattern.finditer(text)]


def python_strings(path):
    """User-facing string pieces of a module: string constants and f-string text, without docstrings and
    without the score-bin labels (the bin edges are the documented histogram design)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr) \
                and isinstance(node.body[0].value, ast.Constant):
            skip.add(id(node.body[0].value))
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == "SCORE_BINS" for t in targets):
                skip.update(id(n) for n in ast.walk(node))
    return [(n.lineno, n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip]


def tsx_text(path):
    """JSX text and string literals of a component, without comments, imports, class names and styles."""
    src = path.read_text(encoding="utf-8")
    src = re.sub(r"\{/\*.*?\*/\}|/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"(?m)//.*$", " ", src)
    src = re.sub(r"(?m)^import .*$", " ", src)
    src = re.sub(r'className=(\{`[^`]*`\}|"[^"]*")', " ", src)
    src = re.sub(r"\b(width|height|stroke|fill|strokeDasharray|key|offset)=\"[^\"]*\"", " ", src)
    src = re.sub(r"#[0-9A-Fa-f]{3,8}\b", " ", src)
    src = re.sub(r"\$\{[^}]*\}", " ", src)
    pieces = re.findall(r">([^<>{}]+)<", src) + re.findall(r"'([^'\n]*)'|\"([^\"\n]*)\"|`([^`]*)`", src)
    return [p if isinstance(p, str) else " ".join(x for x in p if x) for p in pieces]


@pytest.mark.parametrize("path", HOMEPAGE_PY, ids=lambda p: p.name)
def test_no_hard_coded_statistics_in_service(path):
    hits = [(line, text, suspicious(text)) for line, text in python_strings(path) if suspicious(text)]
    assert hits == [], hits


@pytest.mark.parametrize("path", HOMEPAGE_TSX, ids=lambda p: p.name)
def test_no_hard_coded_statistics_in_components(path):
    hits = [(text.strip()[:80], suspicious(text)) for text in tsx_text(path) if suspicious(text)]
    assert hits == [], hits


def test_guard_catches_a_reintroduced_statistic():
    assert suspicious("736 unique batters")
    assert suspicious("1,243 matches · 19 seasons (2008–2026)")
    assert suspicious("98.0% Decided") and suspicious("IQR: 147–188 runs") and suspicious("10-team expansion")
    assert not suspicious("Completed first innings: bowled out (10 wickets) or all 120 legal balls")
