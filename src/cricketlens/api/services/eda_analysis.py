"""Filterable full-history Statistics & EDA, computed from the canonical engine.

Every area is recomputed server-side for the selected season range, team and venue. Each one
reports the filters it supports (and a note for any active filter it does not), the seasons
actually present in its data, its sample size, definitions, units and data source. A selection
with no matches returns an explanation instead of zeros.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from cricketlens.api.services.canonical_data import (
    FRANCHISE_METADATA,
    PHASES,
    TEAM_DEFINITIONS,
    CanonicalAnalyticsEngine,
    batting_table,
    bowling_table,
    canonical_engine,
    dismissal_breakdown,
    format_season_ranges,
    innings_order_record,
    outcome_breakdown,
    percentage,
    result_summary,
    run_rate,
    toss_record,
)
from cricketlens.api.settings import PROJECT_ROOT

REPO_ROOT = PROJECT_ROOT

# Correlations are never reported for fewer innings than this
CORRELATION_MIN_N = 30
PLAYER_COMPARISON_MIN, PLAYER_COMPARISON_MAX = 2, 4
LEADERBOARD_SIZE = 10

FILTER_LABELS = {"season": "season range", "team": "team", "venue": "venue"}

SOURCE_MATCHES = "Computed from Cricsheet match records: data/processed/matches.csv and innings.csv."
SOURCE_BALLS = ("Computed from Cricsheet ball-by-ball data: data/processed/deliveries.csv "
                "(ordinary innings; super overs excluded).")
SOURCE_TEAM_ROWS = ("Computed from Cricsheet match and ball-by-ball data (data/processed/matches.csv, innings.csv, "
                    "deliveries.csv) with the same team-match rows and definitions as Team Analysis.")
SOURCE_BATTING = ("Computed from Cricsheet ball-by-ball data: data/derived/batting_appearances.csv and "
                  "data/processed/deliveries.csv.")
SOURCE_BOWLING = ("Computed from Cricsheet ball-by-ball data: data/processed/deliveries.csv with bowler-credited "
                  "wickets from data/derived/dismissals.csv.")
SOURCE_DISMISSALS = "Computed from Cricsheet ball-by-ball data: data/derived/dismissals.csv (built from the raw JSON)."
SOURCE_ANOMALIES = ("Computed from Cricsheet data: data/processed/matches.csv, innings.csv, deliveries.csv and "
                    "data/derived/match_replacements.csv.")
SOURCE_STAGE1 = ("Static Stage 1 audit: reports/stage_01/audit_summary.json, missingness.csv and "
                 "raw_over_anomalies.csv (not recomputed).")

SUPERS_ALL = ("season", "team", "venue")

AREAS: Dict[str, Dict[str, Any]] = {
    "matches_runs": {
        "title": "Matches and runs by season",
        "supports": SUPERS_ALL,
        "units": "Matches; runs; runs per over (runs per 6 legal balls)",
        "source": SOURCE_BALLS,
        "definitions": {
            "matches": "Matches in the selection, including no results.",
            "runs": "Runs including extras in ordinary innings. With a team selected: the team's batting only.",
            "deliveries": "Every recorded ball, wides and no-balls included; legal balls exclude wides and no-balls.",
            "wickets": "Team wickets: every dismissal except retired hurt and retired not out.",
        },
    },
    "scoring_trends": {
        "title": "Scoring trends by season",
        "supports": SUPERS_ALL,
        "units": "Runs per innings; runs per over",
        "source": SOURCE_MATCHES,
        "definitions": {
            "runs_per_innings": "Total runs ÷ ordinary innings batted (shortened and all-out innings included).",
            "run_rate": "Runs ÷ (legal balls / 6).",
            "first_second": "Mean total of first innings and of second innings separately.",
            "team": "With a team selected: only that team's batting innings.",
        },
    },
    "batting_distribution": {
        "title": "Batting performance distributions",
        "supports": SUPERS_ALL,
        "units": "Runs per innings; strike rate (runs per 100 balls)",
        "source": SOURCE_BATTING,
        "definitions": {
            "innings": "One batting innings per player at the crease (striker or non-striker) or dismissed.",
            "strike_rate": "Runs per 100 balls faced (wides excluded); only innings with at least the minimum "
                           "balls faced are in the strike-rate distribution.",
            "average": "Runs ÷ dismissals; retired hurt is not a dismissal.",
            "team": "With a team selected: that team's batters.",
            "leaderboard": f"Top {LEADERBOARD_SIZE} run scorers in the selection, by registry ID.",
        },
    },
    "bowling": {
        "title": "Bowling wickets and economy",
        "supports": SUPERS_ALL,
        "units": "Wickets; economy (runs conceded per over)",
        "source": SOURCE_BOWLING,
        "definitions": {
            "wickets": "Bowler-credited dismissals: bowled, caught, caught and bowled, lbw, stumped, hit wicket.",
            "economy": "Runs conceded (off the bat plus wides and no-balls) ÷ (legal balls / 6). Only bowling "
                       "innings with at least the minimum legal balls are in the economy distribution.",
            "team": "With a team selected: that team's bowlers.",
            "leaderboard": f"Top {LEADERBOARD_SIZE} wicket takers, ties broken by fewer runs conceded.",
        },
    },
    "phases": {
        "title": "Powerplay, middle and death overs by season",
        "supports": SUPERS_ALL,
        "units": "Runs per over; wickets per over",
        "source": SOURCE_TEAM_ROWS,
        "definitions": {
            "phases": TEAM_DEFINITIONS["phases"],
            "run_rate": TEAM_DEFINITIONS["run_rate"],
            "economy": TEAM_DEFINITIONS["economy"],
            "team": "With a team selected: the team's batting run rate and the economy of its bowling in each phase.",
        },
    },
    "team_comparison": {
        "title": "Team-level historical comparison",
        "supports": ("season", "venue"),
        "unsupported": {"team": "every franchise is compared; the selected team is highlighted."},
        "units": "Win % (wins ÷ (matches − no results)); runs per over",
        "source": SOURCE_TEAM_ROWS,
        "definitions": {
            "won_lost": TEAM_DEFINITIONS["won"] + " " + TEAM_DEFINITIONS["lost"],
            "tied": TEAM_DEFINITIONS["tied"],
            "win_pct": TEAM_DEFINITIONS["win_pct"],
            "run_rate": "Batting runs ÷ (legal balls faced / 6); economy: runs conceded ÷ (legal balls bowled / 6).",
            "franchises": TEAM_DEFINITIONS["franchises"],
        },
    },
    "venues": {
        "title": "Venue analysis",
        "supports": ("season", "team"),
        "unsupported": {"venue": "every venue is compared; the selected venue is highlighted."},
        "units": "Matches; first-innings runs; runs per over; win %",
        "source": SOURCE_TEAM_ROWS,
        "definitions": {
            "venues": TEAM_DEFINITIONS["venues"],
            "first_innings": "Mean and median first-innings total in the selected matches at the venue.",
            "run_rate": "All ordinary-innings runs at the venue ÷ (legal balls / 6).",
            "result": "Without a team: results of the side batting first. With a team: that team's results "
                      "(the Team Analysis venue record). " + TEAM_DEFINITIONS["win_pct"],
        },
    },
    "toss": {
        "title": "Toss decisions and match outcomes",
        "supports": SUPERS_ALL,
        "units": "Tosses; win % of the toss winner",
        "source": SOURCE_TEAM_ROWS,
        "definitions": {
            "toss": TEAM_DEFINITIONS["toss"],
            "league": TEAM_DEFINITIONS["league_toss"],
            "win_pct": TEAM_DEFINITIONS["win_pct"],
            "team": "With a team selected: the tosses that team won (the Team Analysis toss record).",
        },
    },
    "innings_order": {
        "title": "Batting first vs chasing",
        "supports": SUPERS_ALL,
        "units": "Win % (wins ÷ decided matches)",
        "source": SOURCE_TEAM_ROWS,
        "definitions": {
            "innings_order": TEAM_DEFINITIONS["innings_order"],
            "decided": "Decided matches: decided in regulation (including D/L) or by a Super Over. "
                       "No-result matches are excluded.",
            "team": "With a team selected: that team's results batting first and chasing (as on Team Analysis).",
        },
    },
    "innings_scores": {
        "title": "Innings-score distributions",
        "supports": SUPERS_ALL,
        "units": "Runs per innings",
        "source": SOURCE_MATCHES,
        "definitions": {
            "innings": "Ordinary first and second innings as recorded, including shortened, all-out and D/L innings.",
            "quartiles": "Q1, median and Q3 use linear interpolation.",
            "full_innings": "Full innings: 120 legal balls.",
            "team": "With a team selected: that team's batting innings.",
        },
    },
    "dismissals": {
        "title": "Dismissal types",
        "supports": SUPERS_ALL,
        "units": "Dismissal events",
        "source": SOURCE_DISMISSALS,
        "definitions": {
            "events": "Every dismissal event in ordinary innings, retirements included. Super overs are excluded "
                      "and counted separately.",
            "bowler_credited": "Bowled, caught, caught and bowled, lbw, stumped and hit wicket are credited to the "
                               "bowler; run out, retired hurt, retired out and obstructing the field are not.",
            "team_wickets": "Every event except retired hurt (and retired not out) is a team wicket.",
            "team": "With a team selected: dismissals of that team's batters.",
        },
    },
    "boundaries": {
        "title": "Boundaries and scoring patterns",
        "supports": SUPERS_ALL,
        "units": "Fours, sixes; % of runs; % of legal balls",
        "source": SOURCE_BALLS,
        "definitions": {
            "boundaries": "Fours and sixes off the bat; runs Cricsheet flags non_boundary (e.g. an all-run four) "
                          "are not boundaries.",
            "boundary_run_pct": "(4 × fours + 6 × sixes) ÷ all runs including extras.",
            "dot_ball_pct": "Legal balls from which no run of any kind was scored ÷ legal balls.",
            "team": "With a team selected: that team's batting.",
        },
    },
    "anomalies": {
        "title": "Cricket-specific anomalies and data quality",
        "supports": SUPERS_ALL,
        "units": "Matches, deliveries and substitutions",
        "source": SOURCE_ANOMALIES,
        "definitions": {
            "super_over": "Matches tied in regulation and decided by a Super Over.",
            "dl": "Matches whose result was decided by the D/L method.",
            "no_result": "Matches with no result (abandoned or not completed).",
            "penalty_runs": "Deliveries with penalty runs: extras not explained by wides, no-balls, byes or leg byes.",
            "substitutions": "Impact Player and concussion substitutions recorded in the match data "
                             "(data/derived/match_replacements.csv).",
            "missing_city": "Matches whose city field is missing in the source.",
            "team": "With a team selected: that team's matches; penalty runs awarded while it batted; its substitutions.",
        },
    },
    "correlations": {
        "title": "Correlations (first innings)",
        "supports": SUPERS_ALL,
        "units": "Correlation coefficient (−1 to 1)",
        "source": SOURCE_BALLS,
        "definitions": {
            "sample": "One observation per first innings in the selection (shortened innings included).",
            "pearson": "Pearson: linear correlation.",
            "spearman": "Spearman: rank (monotonic) correlation.",
            "minimum": f"No coefficient is shown for fewer than {CORRELATION_MIN_N} innings.",
            "team": "With a team selected: that team's first innings.",
        },
    },
    "player_comparison": {
        "title": "Player comparison",
        "supports": ("season",),
        "unsupported": {
            "team": "career figures within the season range cover every team the player played for.",
            "venue": "career figures within the season range cover every venue.",
        },
        "units": "Runs, wickets, averages, strike rates, economy",
        "source": SOURCE_BATTING + " " + SOURCE_BOWLING,
        "definitions": {
            "players": "Players are chosen by Cricsheet registry ID.",
            "batting": "Same definitions as Player Explorer: innings at the crease, average = runs ÷ dismissals.",
            "bowling": "Wickets are bowler-credited; economy = runs conceded ÷ (legal balls / 6).",
        },
    },
}

CORRELATION_VARIABLES = [
    ("total_runs", "Total runs"),
    ("wickets_lost", "Wickets lost"),
    ("legal_balls", "Legal balls"),
    ("powerplay_runs", "Powerplay runs"),
    ("middle_runs", "Middle-overs runs"),
    ("death_runs", "Death-overs runs"),
    ("fours", "Fours"),
    ("sixes", "Sixes"),
]

RUNS_BINS = [(0, 0, "0"), (1, 9, "1–9"), (10, 19, "10–19"), (20, 29, "20–29"), (30, 49, "30–49"),
             (50, 99, "50–99"), (100, None, "100+")]
STRIKE_RATE_BINS = [(0, 50, "Under 50"), (50, 100, "50–99"), (100, 150, "100–149"), (150, 200, "150–199"),
                    (200, 250, "200–249"), (250, None, "250+")]
ECONOMY_BINS = [(0, 6, "Under 6"), (6, 8, "6–7.99"), (8, 10, "8–9.99"), (10, 12, "10–11.99"), (12, None, "12+")]
SCORE_BINS = [(None, 100, "Under 100")] + [(lo, lo + 20, f"{lo}–{lo + 19}") for lo in range(100, 260, 20)] + [
    (260, None, "260+")]


class FilterError(ValueError):
    """An invalid filter value (returned as HTTP 422)."""


@dataclass(frozen=True)
class EDAFilters:
    season_from: int
    season_to: int
    team: Optional[str] = None
    venue: Optional[str] = None
    venue_min_matches: int = 1
    bat_min_balls: int = 1
    bowl_min_balls: int = 1


def available_seasons(engine: CanonicalAnalyticsEngine) -> List[int]:
    return sorted(int(s) for s in engine._matches["season"].unique())


def resolve_filters(
    engine: CanonicalAnalyticsEngine,
    season_from: Optional[int] = None,
    season_to: Optional[int] = None,
    team: Optional[str] = None,
    venue: Optional[str] = None,
    venue_min_matches: int = 1,
    bat_min_balls: int = 1,
    bowl_min_balls: int = 1,
) -> EDAFilters:
    """Validate query values against the data; defaults cover every season in the archive."""
    engine.ensure_loaded()
    seasons = available_seasons(engine)
    first, last = seasons[0], seasons[-1]
    season_from = first if season_from is None else season_from
    season_to = last if season_to is None else season_to
    for name, value in (("season_from", season_from), ("season_to", season_to)):
        if not first <= value <= last:
            raise FilterError(f"{name}={value} is outside the available seasons {first}–{last}.")
    if season_from > season_to:
        raise FilterError(f"season_from ({season_from}) is after season_to ({season_to}).")

    team_name = None
    if team:
        try:
            team_name = engine._resolve_team(team)
        except KeyError as exc:
            raise FilterError(exc.args[0]) from None

    venue_name = None
    if venue:
        venues = {v.lower(): v for v in engine._matches["venue_canonical"].unique()}
        venue_name = venues.get(venue.strip().lower())
        if venue_name is None:
            raise FilterError(f"Venue '{venue}' is not one of the {len(venues)} canonical venues.")
    return EDAFilters(season_from, season_to, team_name, venue_name, venue_min_matches, bat_min_balls, bowl_min_balls)


def filter_options(engine: CanonicalAnalyticsEngine) -> Dict[str, Any]:
    """Seasons, franchises and venues the filter bar offers, with the seasons each one appears in."""
    engine.ensure_loaded()
    m = engine._matches
    venues = [
        {"name": v, "matches": int(len(g)), "seasons_label": format_season_ranges(sorted(int(s) for s in g["season"].unique()))}
        for v, g in m.groupby("venue_canonical")
    ]
    venues.sort(key=lambda v: (-v["matches"], v["name"]))
    teams = [
        {"id": t["id"], "name": t["name"], "short_name": t["short_name"], "status": t["status"],
         "seasons_label": t["seasons_active"]}
        for t in engine.list_teams() if t["active_seasons"]
    ]
    return {"seasons": available_seasons(engine), "teams": teams, "venues": venues,
            "correlation_min_n": CORRELATION_MIN_N, "areas": {k: {"title": a["title"], "supports": list(a["supports"])}
                                                              for k, a in AREAS.items()}}


# ---------------------------------------------------------------- shared helpers

def _select_matches(engine: CanonicalAnalyticsEngine, f: EDAFilters, supports: Sequence[str]) -> pd.DataFrame:
    """Matches in the selection, applying only the filters the area supports."""
    m = engine._matches
    mask = m["season"].between(f.season_from, f.season_to)
    if f.team and "team" in supports:
        mask &= (m["team1"] == f.team) | (m["team2"] == f.team)
    if f.venue and "venue" in supports:
        mask &= m["venue_canonical"] == f.venue
    return m[mask]


def _team(f: EDAFilters, supports: Sequence[str]) -> Optional[str]:
    return f.team if "team" in supports else None


def _selection_text(engine: CanonicalAnalyticsEngine, f: EDAFilters, supports: Sequence[str]) -> str:
    span = f"{f.season_from}" if f.season_from == f.season_to else f"{f.season_from}–{f.season_to}"
    parts = []
    team = _team(f, supports)
    if team:
        parts.append(f"{team} (played {format_season_ranges(engine._franchise_seasons[team])})")
    if f.venue and "venue" in supports:
        hosted = engine._matches.loc[engine._matches["venue_canonical"] == f.venue, "season"].unique()
        parts.append(f"{f.venue} (hosted IPL matches in {format_season_ranges(sorted(int(s) for s in hosted))})")
    who = " at ".join(parts) if parts else "the archive"
    return f"No matches for {who} in {span}."


def _area(
    area_id: str,
    engine: CanonicalAnalyticsEngine,
    f: EDAFilters,
    seasons: Sequence[int],
    sample: List[Dict[str, Any]],
    data: Optional[Dict[str, Any]],
    empty_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """An area with its filter support, actual coverage, sample size, definitions, units and source."""
    spec = AREAS[area_id]
    supports = spec["supports"]
    active = ["season"] + [k for k in ("team", "venue") if getattr(f, k)]
    seasons = sorted(int(s) for s in seasons)
    return {
        "id": area_id,
        "title": spec["title"],
        "supported_filters": list(supports),
        "applied_filters": [k for k in active if k in supports],
        "unaffected_by": [
            {"filter": k, "note": f"Not affected by the {FILTER_LABELS[k]} filter: {spec['unsupported'][k]}"}
            for k in active if k not in supports
        ],
        "coverage": {
            "seasons": seasons,
            "first_season": seasons[0],
            "last_season": seasons[-1],
            "label": format_season_ranges(seasons),
        } if seasons else None,
        "sample": sample,
        "definitions": spec["definitions"],
        "units": spec["units"],
        "source": spec["source"],
        "state": "empty" if data is None else "ok",
        "empty_reason": empty_reason if data is None else None,
        "data": data,
    }


def _empty(area_id: str, engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    """An area with no data: explains the selection instead of reporting zeros."""
    supports = AREAS[area_id]["supports"]
    matches = len(_select_matches(engine, f, supports))
    reason = (_selection_text(engine, f, supports) if not matches else
              f"The {matches} match{'es' if matches != 1 else ''} in this selection have no records for this analysis.")
    return _area(area_id, engine, f, [], [], None, reason)


def _histogram(values: pd.Series, bins: List[Tuple[Optional[float], Optional[float], str]], inclusive: bool) -> List[Dict[str, Any]]:
    """Counts per bin; `inclusive` bins are closed integer ranges, otherwise [low, high)."""
    total = int(len(values))
    out = []
    for low, high, label in bins:
        mask = pd.Series(True, index=values.index)
        if low is not None:
            mask &= values >= low
        if high is not None:
            mask &= (values <= high) if inclusive else (values < high)
        n = int(mask.sum())
        out.append({"bin": label, "count": n, "pct": percentage(n, total)})
    return out


def _describe(values: pd.Series) -> Dict[str, Any]:
    if values.empty:
        return {"n": 0, "mean": None, "median": None, "q1": None, "q3": None, "min": None, "max": None}
    return {
        "n": int(len(values)),
        "mean": round(float(values.mean()), 2),
        "median": round(float(values.median()), 1),
        "q1": round(float(values.quantile(0.25)), 1),
        "q3": round(float(values.quantile(0.75)), 1),
        "min": int(values.min()),
        "max": int(values.max()),
    }


def _deliveries(engine: CanonicalAnalyticsEngine, matches: pd.DataFrame, batting_team: Optional[str]) -> pd.DataFrame:
    d = engine._deliveries
    mask = d["match_id"].isin(matches["match_id"])
    if batting_team:
        mask &= d["batting_team"] == batting_team
    return d[mask]


def _team_rows(engine: CanonicalAnalyticsEngine, matches: pd.DataFrame, team: Optional[str]) -> pd.DataFrame:
    rows = engine._team_rows[engine._team_rows["match_id"].isin(matches["match_id"])]
    return rows[rows["team"] == team] if team else rows


_INNINGS_STATS: Dict[int, pd.DataFrame] = {}


def _innings_stats(engine: CanonicalAnalyticsEngine) -> pd.DataFrame:
    """One row per ordinary innings: totals, phase runs and boundaries (built once per engine)."""
    key = id(engine)
    if key not in _INNINGS_STATS:
        d = engine._deliveries
        phase = np.select([d["over_index"] <= PHASES[0][3], d["over_index"] <= PHASES[1][3]],
                          [PHASES[0][0], PHASES[1][0]], PHASES[2][0])
        runs = d["runs_total"].astype("int64")
        frame = pd.DataFrame({
            "match_id": d["match_id"].astype("int64"), "innings": d["innings"], "batting_team": d["batting_team"],
            "total_runs": runs, "wickets_lost": d["team_wickets_on_ball"].astype("int64"),
            "legal_balls": d["legal_delivery"].astype("int64"),
            "powerplay_runs": np.where(phase == PHASES[0][0], runs, 0),
            "middle_runs": np.where(phase == PHASES[1][0], runs, 0),
            "death_runs": np.where(phase == PHASES[2][0], runs, 0),
            "fours": d["is_four"].astype("int64"), "sixes": d["is_six"].astype("int64"),
        })
        stats = frame.groupby(["match_id", "innings", "batting_team"], as_index=False).sum()
        _INNINGS_STATS[key] = stats.merge(
            engine._matches[["match_id", "season"]].astype({"match_id": "int64"}), on="match_id", how="left",
            validate="many_to_one",
        )
    return _INNINGS_STATS[key]


# ---------------------------------------------------------------- the 15 areas

def area_matches_runs(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["matches_runs"]["supports"]
    m = _select_matches(engine, f, supports)
    if m.empty:
        return _empty("matches_runs", engine, f)
    d = _deliveries(engine, m, _team(f, supports))
    agg = d.groupby("season").agg(
        runs=("runs_total", "sum"), deliveries=("runs_total", "size"),
        legal_balls=("legal_delivery", "sum"), wickets=("team_wickets_on_ball", "sum"),
    )
    by_season = []
    for season, g in m.groupby("season"):
        r = agg.loc[season] if season in agg.index else pd.Series(0, index=agg.columns)
        runs, balls = int(r["runs"]), int(r["legal_balls"])
        by_season.append({
            "season": int(season), "matches": int(len(g)), "runs": runs, "deliveries": int(r["deliveries"]),
            "legal_balls": balls, "wickets": int(r["wickets"]),
            "run_rate": run_rate(runs, balls), "run_rate_state": None if balls else "no_legal_balls",
        })
    totals = {k: sum(s[k] for s in by_season) for k in ("matches", "runs", "deliveries", "legal_balls", "wickets")}
    totals["run_rate"] = run_rate(totals["runs"], totals["legal_balls"])
    return _area("matches_runs", engine, f, m["season"].unique(), [
        {"label": "matches", "value": totals["matches"]}, {"label": "deliveries", "value": totals["deliveries"]},
    ], {"by_season": by_season, "totals": totals})


def area_scoring_trends(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["scoring_trends"]["supports"]
    m = _select_matches(engine, f, supports)
    inn = engine._innings[engine._innings["match_id"].isin(m["match_id"])]
    team = _team(f, supports)
    if team:
        inn = inn[inn["batting_team"] == team]
    if inn.empty:
        return _empty("scoring_trends", engine, f)
    by_season = []
    for season, g in inn.groupby("season"):
        runs, balls = int(g["runs"].sum()), int(g["legal_balls"].sum())
        first, second = g[g["innings"] == 1]["runs"], g[g["innings"] == 2]["runs"]
        by_season.append({
            "season": int(season), "innings": int(len(g)), "runs": runs, "legal_balls": balls,
            "runs_per_innings": round(runs / len(g), 2), "run_rate": run_rate(runs, balls),
            "first_innings": int(len(first)),
            "first_innings_mean": round(float(first.mean()), 2) if len(first) else None,
            "second_innings": int(len(second)),
            "second_innings_mean": round(float(second.mean()), 2) if len(second) else None,
        })
    runs, balls = int(inn["runs"].sum()), int(inn["legal_balls"].sum())
    return _area("scoring_trends", engine, f, inn["season"].unique(), [{"label": "innings", "value": int(len(inn))}], {
        "by_season": by_season,
        "totals": {"innings": int(len(inn)), "runs": runs, "legal_balls": balls,
                   "runs_per_innings": round(runs / len(inn), 2), "run_rate": run_rate(runs, balls)},
    })


def _named(engine: CanonicalAnalyticsEngine, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"name": engine._player_names_by_id.get(r["player_id"], r["player_id"]), **r} for r in records]


def area_batting(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["batting_distribution"]["supports"]
    m = _select_matches(engine, f, supports)
    b = engine._batters_merged
    b = b[b["match_id"].isin(m["match_id"])]
    team = _team(f, supports)
    if team:
        b = b[b["batting_team"] == team]
    if b.empty:
        return _empty("batting_distribution", engine, f)
    eligible = b[b["balls_faced"] >= f.bat_min_balls]
    innings_sr = eligible["runs"] / eligible["balls_faced"] * 100
    summary = batting_table(b)[0]
    leaders = batting_table(b, "player_id", "player_id")
    leaders = sorted(_named(engine, leaders), key=lambda r: (-r["runs"], r["name"]))[:LEADERBOARD_SIZE]
    return _area("batting_distribution", engine, f, b["season"].unique(), [
        {"label": "batting innings", "value": int(len(b))},
        {"label": f"innings with at least {f.bat_min_balls} ball{'s' if f.bat_min_balls != 1 else ''} faced",
         "value": int(len(eligible))},
    ], {
        "summary": {**summary, "mean_runs": round(float(b["runs"].mean()), 2), "median_runs": float(b["runs"].median())},
        "runs_histogram": _histogram(b["runs"], RUNS_BINS, inclusive=True),
        "strike_rate_min_balls": f.bat_min_balls,
        "strike_rate_innings": int(len(eligible)),
        "strike_rate_median": round(float(innings_sr.median()), 2) if len(eligible) else None,
        "strike_rate_histogram": _histogram(innings_sr, STRIKE_RATE_BINS, inclusive=False) if len(eligible) else [],
        "leaders": leaders,
    })


def area_bowling(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["bowling"]["supports"]
    m = _select_matches(engine, f, supports)
    w = engine._bowler_matches
    w = w[w["match_id"].isin(m["match_id"])]
    team = _team(f, supports)
    if team:
        w = w[w["bowling_team"] == team]
    if w.empty:
        return _empty("bowling", engine, f)
    eligible = w[w["legal_balls"] >= f.bowl_min_balls]
    innings_econ = eligible["runs_conceded"] / (eligible["legal_balls"] / 6.0)
    leaders = bowling_table(w, "bowler_id", "player_id")
    leaders = sorted(_named(engine, leaders), key=lambda r: (-r["wickets"], r["runs_conceded"], r["name"]))
    return _area("bowling", engine, f, w["season"].unique(), [
        {"label": "bowling innings", "value": int(len(w))},
        {"label": f"innings with at least {f.bowl_min_balls} legal ball{'s' if f.bowl_min_balls != 1 else ''}",
         "value": int(len(eligible))},
    ], {
        "summary": bowling_table(w)[0],
        "economy_min_balls": f.bowl_min_balls,
        "economy_innings": int(len(eligible)),
        "economy_median": round(float(innings_econ.median()), 2) if len(eligible) else None,
        "economy_histogram": _histogram(innings_econ, ECONOMY_BINS, inclusive=False) if len(eligible) else [],
        "leaders": leaders[:LEADERBOARD_SIZE],
    })


def area_phases(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["phases"]["supports"]
    m = _select_matches(engine, f, supports)
    rows = _team_rows(engine, m, _team(f, supports))
    if rows.empty:
        return _empty("phases", engine, f)
    phase_records = engine._phase_records
    overall = phase_records(rows)
    return _area("phases", engine, f, rows["season"].unique(), [
        {"label": "legal balls", "value": sum(p["batting_legal_balls"] for p in overall)},
        {"label": "matches", "value": int(rows["match_id"].nunique())},
    ], {
        "team_view": bool(_team(f, supports)),
        "overall": overall,
        "by_season": [{"season": int(s), "phases": phase_records(g)} for s, g in rows.groupby("season")],
    })


def area_team_comparison(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["team_comparison"]["supports"]
    m = _select_matches(engine, f, supports)
    rows = _team_rows(engine, m, None)
    if rows.empty:
        return _empty("team_comparison", engine, f)
    teams = []
    for name, g in rows.groupby("team"):
        meta = FRANCHISE_METADATA[name]
        totals = engine._totals(g)
        teams.append({
            "team": name, "id": meta["slug"], "short_name": meta["short_name"], "status": meta["status"],
            "seasons_label": format_season_ranges(sorted(int(s) for s in g["season"].unique())),
            **result_summary(g),
            "run_rate": totals["run_rate"], "economy": totals["economy"], "runs_per_innings": totals["runs_per_innings"],
            "selected": name == f.team,
        })
    teams.sort(key=lambda t: (t["win_pct"] is None, -(t["win_pct"] or 0), -t["played"], t["team"]))
    return _area("team_comparison", engine, f, rows["season"].unique(), [
        {"label": "matches", "value": int(len(m))}, {"label": "franchises", "value": len(teams)},
    ], {"teams": teams})


def area_venues(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["venues"]["supports"]
    m = _select_matches(engine, f, supports)
    team = _team(f, supports)
    rows = _team_rows(engine, m, team)
    if rows.empty:
        return _empty("venues", engine, f)
    inn = engine._innings[engine._innings["match_id"].isin(m["match_id"])]
    inn_by_venue = dict(tuple(inn.groupby("venue_canonical")))
    records = []
    for venue, g in rows.groupby("venue_canonical"):
        vi = inn_by_venue.get(venue, inn.iloc[0:0])
        first = vi[vi["innings"] == 1]["runs"]
        runs, balls = int(vi["runs"].sum()), int(vi["legal_balls"].sum())
        result_rows = g if team else g[g["batted_first"]]
        records.append({
            "venue": venue, "matches": int(g["match_id"].nunique()),
            "first_innings": int(len(first)),
            "first_innings_mean": round(float(first.mean()), 2) if len(first) else None,
            "first_innings_median": float(first.median()) if len(first) else None,
            "run_rate": run_rate(runs, balls),
            "result_label": f"{team} result" if team else "Batting-first result",
            "result": result_summary(result_rows),
            "selected": venue == f.venue,
        })
    shown = sorted((r for r in records if r["matches"] >= f.venue_min_matches),
                   key=lambda r: (-r["matches"], r["venue"]))
    return _area("venues", engine, f, rows["season"].unique(), [
        {"label": "matches", "value": int(rows["match_id"].nunique())},
        {"label": f"venues with at least {f.venue_min_matches} match{'es' if f.venue_min_matches != 1 else ''}",
         "value": len(shown)},
    ], {
        "min_matches": f.venue_min_matches,
        "venues_total": len(records),
        "venues_shown": len(shown),
        "matches_shown": sum(r["matches"] for r in shown),
        "venues": shown,
    })


def area_toss(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["toss"]["supports"]
    m = _select_matches(engine, f, supports)
    rows = _team_rows(engine, m, _team(f, supports))
    toss = rows[rows["toss_won"]]
    if toss.empty:
        return _empty("toss", engine, f)
    return _area("toss", engine, f, toss["season"].unique(), [{"label": "tosses", "value": int(len(toss))}], {
        "team_view": bool(_team(f, supports)),
        "overall": toss_record(toss),
        "by_season": [{"season": int(s), **toss_record(g)} for s, g in toss.groupby("season")],
    })


def area_innings_order(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["innings_order"]["supports"]
    m = _select_matches(engine, f, supports)
    rows = _team_rows(engine, m, _team(f, supports))
    if rows.empty:
        return _empty("innings_order", engine, f)
    outcomes = outcome_breakdown(m)
    return _area("innings_order", engine, f, rows["season"].unique(), [
        {"label": "decided matches", "value": outcomes["decided"]},
        {"label": "no results excluded", "value": outcomes["no_result"]},
    ], {
        "team_view": bool(_team(f, supports)),
        "outcomes": outcomes,
        "overall": innings_order_record(rows),
        "by_season": [{"season": int(s), **innings_order_record(g)} for s, g in rows.groupby("season")],
    })


def area_innings_scores(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["innings_scores"]["supports"]
    m = _select_matches(engine, f, supports)
    inn = engine._innings[engine._innings["match_id"].isin(m["match_id"])]
    team = _team(f, supports)
    if team:
        inn = inn[inn["batting_team"] == team]
    if inn.empty:
        return _empty("innings_scores", engine, f)
    by_innings = []
    for number in (1, 2):
        g = inn[inn["innings"] == number]
        by_innings.append({
            "innings": number, **_describe(g["runs"]),
            "full_innings": int((g["legal_balls"] == 120).sum()),
            "histogram": _histogram(g["runs"], SCORE_BINS, inclusive=False) if len(g) else [],
        })
    return _area("innings_scores", engine, f, inn["season"].unique(), [
        {"label": "first innings", "value": by_innings[0]["n"]},
        {"label": "second innings", "value": by_innings[1]["n"]},
    ], {"by_innings": by_innings})


def _dismissal_rows(table: pd.DataFrame, m: pd.DataFrame, team: Optional[str]) -> pd.DataFrame:
    rows = table[table["match_id"].isin(m["match_id"])]
    return rows[rows["batting_team"] == team] if team else rows


def area_dismissals(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["dismissals"]["supports"]
    m = _select_matches(engine, f, supports)
    team = _team(f, supports)
    rows = _dismissal_rows(engine._dismissals, m, team)
    if rows.empty:
        return _empty("dismissals", engine, f)
    super_over = _dismissal_rows(engine._super_over_events.get("dismissals.csv", engine._dismissals.iloc[0:0]), m, team)
    seasons = m.loc[m["match_id"].isin(rows["match_id"]), "season"].unique()
    breakdown = dismissal_breakdown(rows)
    return _area("dismissals", engine, f, seasons, [{"label": "dismissal events", "value": breakdown["events"]}], {
        **breakdown,
        "team_wickets_from_deliveries": int(_deliveries(engine, m, team)["team_wickets_on_ball"].sum()),
        "super_over_events_excluded": int(len(super_over)),
    })


def area_boundaries(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["boundaries"]["supports"]
    m = _select_matches(engine, f, supports)
    d = _deliveries(engine, m, _team(f, supports))
    if d.empty:
        return _empty("boundaries", engine, f)

    def record(g: pd.DataFrame) -> Dict[str, Any]:
        fours, sixes = int(g["is_four"].sum()), int(g["is_six"].sum())
        runs, balls = int(g["runs_total"].sum()), int(g["legal_delivery"].sum())
        dots = int(((g["legal_delivery"] == 1) & (g["runs_total"] == 0)).sum())
        boundary_runs = 4 * fours + 6 * sixes
        return {
            "fours": fours, "sixes": sixes, "boundary_runs": boundary_runs, "runs": runs, "legal_balls": balls,
            "dot_balls": dots, "boundary_run_pct": percentage(boundary_runs, runs),
            "dot_ball_pct": percentage(dots, balls),
            "balls_per_boundary": round(balls / (fours + sixes), 2) if fours + sixes else None,
        }

    return _area("boundaries", engine, f, d["season"].unique(), [
        {"label": "deliveries", "value": int(len(d))}, {"label": "legal balls", "value": int(d["legal_delivery"].sum())},
    ], {"totals": record(d), "by_season": [{"season": int(s), **record(g)} for s, g in d.groupby("season")]})


_STAGE1_AUDIT: Dict[str, Any] = {}


def stage1_audit() -> Dict[str, Any]:
    """The static Stage 1 screening and missingness outputs, read once and labelled with their own coverage."""
    if not _STAGE1_AUDIT:
        base = REPO_ROOT / "reports" / "stage_01"
        audit = json.loads((base / "audit_summary.json").read_text(encoding="utf-8"))
        seasons = audit["coverage"]["seasons"]
        _STAGE1_AUDIT.update({
            "label": "Static Stage 1 audit — not affected by filters",
            "coverage": f"{format_season_ranges(seasons)} ({audit['counts']['matches']:,} matches)",
            "source": SOURCE_STAGE1,
            "screening_issue_counts": audit.get("screening_issue_counts", {}),
            "missingness": pd.read_csv(base / "missingness.csv").to_dict("records"),
            "raw_over_anomalies": pd.read_csv(base / "raw_over_anomalies.csv").to_dict("records"),
        })
    return _STAGE1_AUDIT


def _match_list(m: pd.DataFrame) -> List[Dict[str, Any]]:
    return [{
        "match_id": int(r.match_id), "date": str(r.date), "season": int(r.season),
        "teams": f"{r.team1} v {r.team2}", "venue": str(r.venue_canonical),
        "winner": str(r.final_winner) if pd.notna(r.final_winner) else None,
    } for r in m.sort_values(["date", "match_id"]).itertuples()]


def area_anomalies(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["anomalies"]["supports"]
    m = _select_matches(engine, f, supports)
    if m.empty:
        return _empty("anomalies", engine, f)
    team = _team(f, supports)
    d = _deliveries(engine, m, team)
    penalty = d["runs_extras"] - d["wides"] - d["noballs"] - d["byes"] - d["legbyes"]
    subs = engine._replacements[engine._replacements["match_id"].isin(m["match_id"])]
    if team:
        subs = subs[subs["team"] == team]
    innings_per_match = engine._innings[engine._innings["match_id"].isin(m["match_id"])].groupby("match_id").size()
    super_over = m[m["decided_by"] == "super_over"]
    dl = m[m["outcome_method"] == "D/L"]
    no_result = m[m["outcome_type"] == "no result"]
    return _area("anomalies", engine, f, m["season"].unique(), [{"label": "matches", "value": int(len(m))}], {
        "outcomes": outcome_breakdown(m),
        "super_over_matches": int(len(super_over)),
        "dl_matches": int(len(dl)),
        "no_results": int(len(no_result)),
        "penalty_run_deliveries": int((penalty > 0).sum()),
        "penalty_runs": int(penalty[penalty > 0].sum()),
        "substitutions": int(len(subs)),
        "substitutions_by_reason": {str(k): int(v) for k, v in subs["reason"].value_counts().sort_index().items()},
        "substitutions_in_super_overs": int(subs["is_super_over"].sum()),
        "missing_city_matches": int(m["city"].isna().sum()),
        "matches_without_two_innings": int((m["match_id"].map(innings_per_match).fillna(0) < 2).sum()),
        "lists": {
            "super_over": _match_list(super_over),
            "dl": _match_list(dl),
            "no_result": _match_list(no_result),
        },
        "stage1_audit": stage1_audit(),
    })


def _coefficients(frame: pd.DataFrame, method: str) -> Dict[str, Dict[str, Optional[float]]]:
    corr = frame.corr(method=method)
    return {a: {b: (None if pd.isna(v) else round(float(v), 3)) for b, v in corr[a].items()} for a in corr.columns}


def area_correlations(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    supports = AREAS["correlations"]["supports"]
    m = _select_matches(engine, f, supports)
    stats = _innings_stats(engine)
    first = stats[(stats["innings"] == 1) & stats["match_id"].isin(m["match_id"])]
    team = _team(f, supports)
    if team:
        first = first[first["batting_team"] == team]
    if first.empty:
        return _empty("correlations", engine, f)
    n = int(len(first))
    keys = [k for k, _ in CORRELATION_VARIABLES]
    sufficient = n >= CORRELATION_MIN_N
    pearson = _coefficients(first[keys], "pearson") if sufficient else None
    spearman = _coefficients(first[keys], "spearman") if sufficient else None
    pairs = [
        {"x": k, "y": "total_runs", "pearson": pearson[k]["total_runs"] if pearson else None,
         "spearman": spearman[k]["total_runs"] if spearman else None}
        for k in keys if k != "total_runs"
    ]
    return _area("correlations", engine, f, first["season"].unique(), [{"label": "first innings", "value": n}], {
        "n": n,
        "min_n": CORRELATION_MIN_N,
        "state": "ok" if sufficient else "insufficient_sample",
        "explanation": None if sufficient else (
            f"Only {n} first innings in this selection; coefficients are shown from {CORRELATION_MIN_N} innings."),
        "variables": [{"key": k, "label": label} for k, label in CORRELATION_VARIABLES],
        "pearson": pearson,
        "spearman": spearman,
        "pairs_with_total": pairs,
    })


AREA_FUNCTIONS = {
    "matches_runs": area_matches_runs,
    "scoring_trends": area_scoring_trends,
    "batting_distribution": area_batting,
    "bowling": area_bowling,
    "phases": area_phases,
    "team_comparison": area_team_comparison,
    "venues": area_venues,
    "toss": area_toss,
    "innings_order": area_innings_order,
    "innings_scores": area_innings_scores,
    "dismissals": area_dismissals,
    "boundaries": area_boundaries,
    "anomalies": area_anomalies,
    "correlations": area_correlations,
}


def _filters_echo(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    team = engine._team_item(f.team) if f.team else None
    parts = [f"{f.season_from}" if f.season_from == f.season_to else f"{f.season_from}–{f.season_to}"]
    if team:
        parts.append(team["name"])
    if f.venue:
        parts.append(f.venue)
    return {
        "season_from": f.season_from, "season_to": f.season_to,
        "team": {"id": team["id"], "name": team["name"], "short_name": team["short_name"],
                 "seasons_label": team["seasons_active"]} if team else None,
        "venue": f.venue,
        "venue_min_matches": f.venue_min_matches,
        "bat_min_balls": f.bat_min_balls,
        "bowl_min_balls": f.bowl_min_balls,
        "label": " · ".join(parts),
    }


@lru_cache(maxsize=256)
def _cached_analysis(f: EDAFilters) -> Dict[str, Any]:
    engine = canonical_engine
    return {
        "filters": _filters_echo(engine, f),
        "areas": {area_id: fn(engine, f) for area_id, fn in AREA_FUNCTIONS.items()},
    }


def get_analysis(engine: CanonicalAnalyticsEngine, f: EDAFilters) -> Dict[str, Any]:
    """All full-history areas for one filter combination (cached per combination for the shared engine)."""
    engine.require_derived()
    if engine is canonical_engine:
        return _cached_analysis(f)
    return {"filters": _filters_echo(engine, f), "areas": {k: fn(engine, f) for k, fn in AREA_FUNCTIONS.items()}}


def get_player_comparison(engine: CanonicalAnalyticsEngine, player_ids: Sequence[str], f: EDAFilters) -> Dict[str, Any]:
    """Career batting and bowling of 2–4 players within the season range, using the Player Explorer tables."""
    engine.require_derived()
    ids = [p.strip() for p in player_ids if p.strip()]
    if not PLAYER_COMPARISON_MIN <= len(ids) <= PLAYER_COMPARISON_MAX or len(set(ids)) != len(ids):
        raise FilterError(
            f"Choose {PLAYER_COMPARISON_MIN} to {PLAYER_COMPARISON_MAX} different players by registry ID.")
    players = []
    all_seasons: set = set()
    for pid in ids:
        if pid not in engine._player_names_by_id:
            raise FilterError(f"Player ID '{pid}' is not in the player directory.")
        squad, bat, bowl, _ = engine._player_rows(pid, None)
        in_range = lambda frame: frame[frame["season"].between(f.season_from, f.season_to)]  # noqa: E731
        squad, bat, bowl = in_range(squad), in_range(bat), in_range(bowl)
        seasons = sorted(int(s) for s in squad["season"].unique())
        all_seasons.update(seasons)
        played = format_season_ranges(engine._squad_info[pid]["seasons"])
        players.append({
            "player_id": pid,
            "name": engine._player_names_by_id[pid],
            "seasons_played": played,
            "state": "ok" if seasons else "empty",
            "empty_reason": None if seasons else (
                f"{engine._player_names_by_id[pid]} played in {played}; no matches in "
                f"{f.season_from}–{f.season_to}."),
            "coverage": format_season_ranges(seasons) or None,
            "matches": int(squad["match_id"].nunique()),
            "batting": next(iter(batting_table(bat)), None),
            "bowling": next(iter(bowling_table(bowl)), None),
            "batting_by_season": batting_table(bat, "season", "season"),
            "bowling_by_season": bowling_table(bowl, "season", "season"),
        })
    sample = [{"label": "matches", "value": sum(p["matches"] for p in players)}]
    data = {"players": players} if all_seasons else None
    area = _area("player_comparison", engine, f, all_seasons, sample, data,
                 "None of these players played in the selected seasons.")
    return {"filters": _filters_echo(engine, f), "area": area}
