"""Canonical Full-History (2008-2026) IPL Analytics Engine.

Provides unified, verifiable historical statistics computed directly from
the complete processed delivery, match, and innings datasets.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Delivery key shared by deliveries.csv and the data/derived event tables
DELIVERY_KEY = ["match_id", "innings", "over_index", "delivery_index"]
DERIVED_BUILD_COMMAND = "python -m cricketlens.derived_events --raw data/raw/ipl_json --output data/derived"


ROLE_DEFINITION = (
    "Role derived from the IPL playing record. Bowls regularly: bowled in at least 50% of matches and at least "
    "12 legal balls per bowling innings. Bats regularly: batted in at least 50% of matches and faced at least "
    "8 balls per batting innings. Both: All-Rounder; only bowling: Bowler; only batting: Batter; neither: Bowler "
    "if legal balls bowled exceed balls faced, otherwise Batter."
)


def derive_role(matches: int, batting_innings: int, balls_faced: int, bowling_innings: int, legal_balls: int) -> str:
    """Classify a player from their record (see ROLE_DEFINITION); no player is special-cased."""
    matches = max(matches, 1)
    bowls_regularly = bowling_innings > 0 and bowling_innings / matches >= 0.5 and legal_balls / bowling_innings >= 12
    bats_regularly = batting_innings > 0 and batting_innings / matches >= 0.5 and balls_faced / batting_innings >= 8
    if bowls_regularly and bats_regularly:
        return "All-Rounder"
    if bowls_regularly:
        return "Bowler"
    if bats_regularly:
        return "Batter"
    return "Bowler" if legal_balls > balls_faced else "Batter"


# Why a profile value is null. A value that cannot be computed is never reported as 0.
STATE_DEFINITIONS = {
    "no_dismissals": "Never dismissed in these innings, so the batting average is undefined.",
    "no_balls_faced": "No ball faced in these innings (non-striker only), so the strike rate is undefined.",
    "no_wickets": "No bowler-credited wicket, so the bowling average and strike rate are undefined.",
    "no_legal_balls": "No legal ball bowled (only wides or no-balls), so the economy rate is undefined.",
    "not_recorded_in_source": "The raw Cricsheet match record does not contain this value.",
}

PROFILE_METRIC_DEFINITIONS = {
    "matches": "Match appearances: matches in which the player is in the official player list (info.players), "
               "including Impact Player and concussion substitutes who came in.",
    "teams": "Canonical franchise names; Cricsheet renames (e.g. Delhi Daredevils) are mapped to the current franchise.",
    "batting_innings": "One innings per ordinary innings in which the player was at the crease as striker or "
                       "non-striker, or was dismissed. Super overs are excluded from every statistic.",
    "not_outs": "Innings minus dismissals. Retired hurt and retired not out are not dismissals; retired out is.",
    "balls_faced": "Deliveries faced as striker, excluding wides; no-balls count.",
    "batting_average": "Runs / dismissals; null with state 'no_dismissals' when never dismissed.",
    "batting_strike_rate": "Runs per 100 balls faced; null with state 'no_balls_faced' when no ball was faced.",
    "highest_score": "Most runs in one innings; '*' marks not out (shown when that score was ever made not out).",
    "fours_sixes": "Boundaries off the bat; runs Cricsheet flags non_boundary (e.g. an all-run four) are excluded.",
    "ducks": "Innings dismissed for 0 runs, including dismissals without facing a ball (e.g. run out as non-striker). "
             "Retired hurt on 0 is not a duck.",
    "milestones": "Innings with at least 30, 50 or 100 runs; counts are cumulative (a 100 also counts as 50+ and 30+).",
    "bowling_innings": "Innings in which the player bowled at least one delivery, wides and no-balls included.",
    "legal_balls": "Deliveries that are neither wides nor no-balls.",
    "overs": "Cricket notation: completed six-ball overs, then remaining legal balls (22 balls = '3.4').",
    "runs_conceded": "Runs off the bat plus wide and no-ball extras; byes and leg byes are not charged to the bowler.",
    "wickets": "Bowler-credited dismissals: bowled, caught, caught and bowled, lbw, stumped, hit wicket. "
               "Run outs, retirements and obstructing the field are not credited.",
    "bowling_average": "Runs conceded / wickets; null with state 'no_wickets' when no wicket was taken.",
    "bowling_strike_rate": "Legal balls / wickets; null with state 'no_wickets' when no wicket was taken.",
    "economy": "Runs conceded per six legal balls; null with state 'no_legal_balls' when none was bowled.",
    "best_bowling": "Most wickets in one innings, ties broken by fewest runs conceded, as wickets/runs.",
    "hauls": "3w: exactly 3 wickets in an innings; 4w: exactly 4; 5w: 5 or more (counted only as 5w).",
    "splits": "Team: the player's franchise; opposition: the other franchise; venue: canonical venue name.",
    "appearance_state": "playing_xi: listed and not substituted; substituted_in: came in as an Impact Player or "
                        "concussion substitute; substituted_out: replaced during the match; substituted_in_and_out: both.",
    "result": "Result for the player's team: won, lost, tied (decided by a super over; super_over_winner names "
              "the winner) or no_result.",
    "season_filter": "When a season is given, every number is computed from that season's matches only.",
}


# Directory sorts that rank a rate: the innings that qualify a player, and whether higher is better
RATE_SORTS = {
    "batting_avg": ("batting", True),
    "strike_rate": ("batting", True),
    "bowling_avg": ("bowling", False),
    "economy": ("bowling", False),
}


def overs_notation(legal_balls: int) -> str:
    """Overs in cricket notation: completed six-ball overs, then remaining balls (22 -> '3.4')."""
    return f"{legal_balls // 6}.{legal_balls % 6}"


def _grouped(rows: pd.DataFrame, by: Optional[str]) -> Tuple[pd.DataFrame, str]:
    """The rows and grouping key; without a key every row falls in one career group."""
    return (rows, by) if by else (rows.assign(_career=0), "_career")


def batting_table(innings: pd.DataFrame, by: Optional[str] = None, label: Optional[str] = None) -> List[Dict[str, Any]]:
    """Batting figures from one row per batting innings, per value of `by` (or one career row)."""
    if innings.empty:
        return []
    rows, key = _grouped(innings, by)
    table = rows.groupby(key).agg(
        innings=("runs", "size"), runs=("runs", "sum"), balls_faced=("balls_faced", "sum"),
        dismissals=("dismissed", "sum"), fours=("fours", "sum"), sixes=("sixes", "sum"), ducks=("is_duck", "sum"),
        scores_30_plus=("reached_30", "sum"), scores_50_plus=("reached_50", "sum"), scores_100_plus=("is_100", "sum"),
    )
    # Highest score per group; a score made both out and not out is shown not out
    top = rows.sort_values(["runs", "dismissed"], ascending=[False, True]).drop_duplicates(key).set_index(key)
    table["hs_runs"] = top["runs"]
    table["hs_not_out"] = top["dismissed"] == 0
    records = []
    for group, r in zip(table.index, table.to_dict("records")):
        inns, runs, balls, outs = int(r["innings"]), int(r["runs"]), int(r["balls_faced"]), int(r["dismissals"])
        record = {
            "innings": inns, "runs": runs, "balls_faced": balls, "dismissals": outs, "not_outs": inns - outs,
            "average": round(runs / outs, 2) if outs else None,
            "average_state": None if outs else "no_dismissals",
            "strike_rate": round(runs / balls * 100, 2) if balls else None,
            "strike_rate_state": None if balls else "no_balls_faced",
            "highest_score": f"{int(r['hs_runs'])}{'*' if r['hs_not_out'] else ''}",
            "fours": int(r["fours"]), "sixes": int(r["sixes"]), "ducks": int(r["ducks"]),
            "scores_30_plus": int(r["scores_30_plus"]), "scores_50_plus": int(r["scores_50_plus"]),
            "scores_100_plus": int(r["scores_100_plus"]),
        }
        if label:
            record = {label: int(group) if label == "season" else group, **record}
        records.append(record)
    return records


def bowling_table(spells: pd.DataFrame, by: Optional[str] = None, label: Optional[str] = None) -> List[Dict[str, Any]]:
    """Bowling figures from one row per bowling innings, per value of `by` (or one career row)."""
    if spells.empty:
        return []
    rows, key = _grouped(spells, by)
    table = rows.groupby(key).agg(
        innings=("legal_balls", "size"), legal_balls=("legal_balls", "sum"), runs_conceded=("runs_conceded", "sum"),
        wickets=("wickets", "sum"), hauls_3=("is_3w", "sum"), hauls_4=("is_4w", "sum"), hauls_5=("is_5w", "sum"),
    )
    # Best figures: most wickets, then fewest runs conceded
    best = rows.sort_values(["wickets", "runs_conceded"], ascending=[False, True]).drop_duplicates(key).set_index(key)
    table["best"] = best["wickets"].astype(int).astype(str) + "/" + best["runs_conceded"].astype(int).astype(str)
    records = []
    for group, r in zip(table.index, table.to_dict("records")):
        balls, runs, wkts = int(r["legal_balls"]), int(r["runs_conceded"]), int(r["wickets"])
        record = {
            "innings": int(r["innings"]), "legal_deliveries": balls, "overs_bowled": overs_notation(balls),
            "runs_conceded": runs, "wickets": wkts,
            "bowling_average": round(runs / wkts, 2) if wkts else None,
            "bowling_average_state": None if wkts else "no_wickets",
            "bowling_strike_rate": round(balls / wkts, 2) if wkts else None,
            "bowling_strike_rate_state": None if wkts else "no_wickets",
            "economy_rate": round(runs / (balls / 6.0), 2) if balls else None,
            "economy_rate_state": None if balls else "no_legal_balls",
            "best_bowling": r["best"],
            "three_wicket_hauls": int(r["hauls_3"]), "four_wicket_hauls": int(r["hauls_4"]),
            "five_wicket_hauls": int(r["hauls_5"]),
        }
        if label:
            record = {label: int(group) if label == "season" else group, **record}
        records.append(record)
    return records


def _present(value: Any) -> bool:
    return value is not None and not (isinstance(value, float) and np.isnan(value))


# ---------------------------------------------------------------- team analysis

# Phases by Cricsheet's 0-based over_index
PHASES = [
    ("powerplay", "Powerplay (overs 1–6)", 0, 5),
    ("middle", "Middle (overs 7–16)", 6, 15),
    ("death", "Death (overs 17–20)", 16, 19),
]

TEAM_DEFINITIONS = {
    "won": "Won in regulation play, by D/L method, or by winning the Super Over after a tie.",
    "lost": "The opponent won in regulation play, by D/L method, or by winning the Super Over.",
    "super_over": "A tie decided by a Super Over counts as a win or a loss and is also reported separately as "
                  "'Tied → won/lost Super Over'.",
    "tied": "A tie with no Super Over result recorded: not a win or a loss, but part of the win percentage denominator.",
    "no_result": "Abandoned or no result: excluded from the win percentage and from batting-first/chasing records.",
    "win_pct": "Wins ÷ (matches − no results), to one decimal; win_pct_denominator is the divisor.",
    "innings_order": "Batting first or chasing from the regulation innings order (Super Over innings ignored); "
                     "no-result matches are excluded and counted in innings_order_no_results.",
    "runs_wickets": "Runs include extras. Team wickets come from team_wickets_on_ball: every dismissal except "
                    "retired hurt and retired not out. Super overs are excluded.",
    "phases": "Powerplay = overs 1–6 (over_index 0–5), middle = overs 7–16 (6–15), death = overs 17–20 (16–19).",
    "run_rate": "Runs ÷ (legal balls / 6).",
    "economy": "Runs conceded (extras included) ÷ (legal balls bowled / 6), overall and per phase.",
    "trends": "Season trends: runs per innings batted, run rate and economy for each season in the selection.",
    "league_toss": "League comparison: the results of every toss winner (all teams) in the same seasons as the "
                   "selection, with the same win percentage rule.",
    "toss": "Results after winning the toss use the same win percentage rule, overall and by decision.",
    "franchises": "Renamed franchises are one team: Delhi Daredevils → Delhi Capitals, Kings XI Punjab → Punjab "
                  "Kings, Royal Challengers Bangalore → Royal Challengers Bengaluru, Rising Pune Supergiants → "
                  "Rising Pune Supergiant. Deccan Chargers is a separate franchise from Sunrisers Hyderabad.",
    "venues": "Canonical venue names; the minimum-matches filter counts matches in the current selection.",
    "season_filter": "With a season selected, every number is computed from that season's matches only.",
}

TEAM_STATE_DEFINITIONS = {
    "no_decided_matches": "Every match in this selection was a no result, so there is no win percentage.",
    "no_legal_balls": "No legal ball in this selection, so the rate is undefined.",
}


def run_rate(runs: int, balls: int) -> Optional[float]:
    """Runs per six legal balls; None when no legal ball was bowled."""
    return round(runs / (balls / 6.0), 2) if balls else None


def percentage(part: int, whole: int) -> Optional[float]:
    """part / whole as a percentage to one decimal, rounding halves up exactly (9/16 = 56.25 -> 56.3)."""
    if not whole:
        return None
    return float((Decimal(int(part) * 100) / Decimal(int(whole))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def result_summary(rows: pd.DataFrame) -> Dict[str, Any]:
    """Results for one team over a set of its team-match rows (see TEAM_DEFINITIONS)."""
    counts = rows["result"].value_counts()
    won, lost, tied, no_result = (int(counts.get(k, 0)) for k in ("won", "lost", "tied", "no_result"))
    denominator = len(rows) - no_result
    return {
        "played": int(len(rows)),
        "wins": won,
        "losses": lost,
        "ties": tied,
        "no_results": no_result,
        "results_not_recorded": int(len(rows)) - won - lost - tied - no_result,
        "super_over_wins": int((rows["super_over"] == "won").sum()),
        "super_over_losses": int((rows["super_over"] == "lost").sum()),
        "win_pct": percentage(won, denominator),
        "win_pct_denominator": denominator,
        "win_pct_state": None if denominator else "no_decided_matches",
    }


def toss_record(toss_rows: pd.DataFrame) -> Dict[str, Any]:
    """Decisions and results of toss winners, from the toss winners' team-match rows (see TEAM_DEFINITIONS)."""
    bat, field = toss_rows[toss_rows["toss_decision"] == "bat"], toss_rows[toss_rows["toss_decision"] == "field"]
    return {
        "tosses_won": int(len(toss_rows)),
        "elected_to_bat": int(len(bat)),
        "elected_to_field": int(len(field)),
        "after_winning_toss": result_summary(toss_rows),
        "chose_to_bat": result_summary(bat),
        "chose_to_field": result_summary(field),
    }


def innings_order_record(rows: pd.DataFrame) -> Dict[str, Any]:
    """Results batting first and chasing; no-result matches are excluded and counted separately."""
    decided = rows[rows["result"] != "no_result"]
    return {
        "batting_first": result_summary(decided[decided["batted_first"]]),
        "chasing": result_summary(decided[~decided["batted_first"]]),
        "innings_order_no_results": int(len(rows) - len(decided)),
    }


def dismissal_breakdown(dismissals: pd.DataFrame) -> Dict[str, Any]:
    """Dismissal events by kind, most frequent first, with bowler-credited and team-wicket counts.

    Expects ordinary-innings rows of data/derived/dismissals.csv. Retired hurt is a dismissal event
    but not a team wicket; run outs, retirements and obstructing the field are not credited to the bowler.
    """
    total = int(len(dismissals))
    kinds = []
    for kind, g in dismissals.groupby("kind"):
        credited, wickets = int(g["bowler_credited"].sum()), int(g["counts_as_batting_dismissal"].sum())
        kinds.append({
            "kind": str(kind), "count": int(len(g)), "pct": percentage(len(g), total),
            "bowler_credited": credited, "not_bowler_credited": int(len(g)) - credited,
            "team_wickets": wickets,
        })
    kinds.sort(key=lambda k: (-k["count"], k["kind"]))
    credited = int(dismissals["bowler_credited"].sum())
    wickets = int(dismissals["counts_as_batting_dismissal"].sum())
    return {
        "kinds": kinds,
        "events": total,
        "bowler_credited": credited,
        "not_bowler_credited": total - credited,
        "team_wickets": wickets,
        "not_team_wickets": total - wickets,
    }


def outcome_breakdown(matches: pd.DataFrame) -> Dict[str, Any]:
    """How matches ended: decided in regulation (including D/L), decided by Super Over, or no result."""
    regulation = int((matches["decided_by"] == "regulation").sum())
    super_over = int(((matches["decided_by"] == "super_over") & matches["final_winner"].notna()).sum())
    no_result = int((matches["outcome_type"] == "no result").sum())
    total = int(len(matches))
    return {
        "matches": total,
        "decided": regulation + super_over,
        "decided_in_regulation": regulation,
        "decided_by_super_over": super_over,
        "no_result": no_result,
        "other_not_recorded": total - regulation - super_over - no_result,
        "dl_method": int((matches["outcome_method"] == "D/L").sum()),
    }


class DerivedDataUnavailable(RuntimeError):
    """Raised when bowling or boundary statistics are requested but data/derived is missing or inconsistent."""


# 15 Canonical Franchises
FRANCHISE_METADATA: Dict[str, Dict[str, Any]] = {
    "Chennai Super Kings": {
        "short_name": "CSK",
        "status": "Active",
        "titles": 5,
        "title_years": [2010, 2011, 2018, 2021, 2023],
        "primary_color": "#D9B15F",
        "slug": "chennai-super-kings",
    },
    "Mumbai Indians": {
        "short_name": "MI",
        "status": "Active",
        "titles": 5,
        "title_years": [2013, 2015, 2017, 2019, 2020],
        "primary_color": "#004BA0",
        "slug": "mumbai-indians",
    },
    "Kolkata Knight Riders": {
        "short_name": "KKR",
        "status": "Active",
        "titles": 3,
        "title_years": [2012, 2014, 2024],
        "primary_color": "#3A225D",
        "slug": "kolkata-knight-riders",
    },
    "Royal Challengers Bengaluru": {
        "short_name": "RCB",
        "status": "Active",
        "titles": 2,
        "title_years": [2025, 2026],
        "primary_color": "#EC1C24",
        "slug": "royal-challengers-bengaluru",
    },
    "Rajasthan Royals": {
        "short_name": "RR",
        "status": "Active",
        "titles": 1,
        "title_years": [2008],
        "primary_color": "#EA1A85",
        "slug": "rajasthan-royals",
    },
    "Sunrisers Hyderabad": {
        "short_name": "SRH",
        "status": "Active",
        "titles": 1,
        "title_years": [2016],
        "primary_color": "#F26522",
        "slug": "sunrisers-hyderabad",
    },
    "Gujarat Titans": {
        "short_name": "GT",
        "status": "Active",
        "titles": 1,
        "title_years": [2022],
        "primary_color": "#1C1C2B",
        "slug": "gujarat-titans",
    },
    "Delhi Capitals": {
        "short_name": "DC",
        "status": "Active",
        "titles": 0,
        "title_years": [],
        "primary_color": "#282968",
        "slug": "delhi-capitals",
    },
    "Lucknow Super Giants": {
        "short_name": "LSG",
        "status": "Active",
        "titles": 0,
        "title_years": [],
        "primary_color": "#A72056",
        "slug": "lucknow-super-giants",
    },
    "Punjab Kings": {
        "short_name": "PBKS",
        "status": "Active",
        "titles": 0,
        "title_years": [],
        "primary_color": "#DD1F2D",
        "slug": "punjab-kings",
    },
    # Defunct Franchises
    "Deccan Chargers": {
        # "DC" is Delhi Capitals; Deccan Chargers is shown as DCH
        "short_name": "DCH",
        "status": "Defunct",
        "titles": 1,
        "title_years": [2009],
        "primary_color": "#4A4D57",
        "slug": "deccan-chargers",
    },
    "Gujarat Lions": {
        "short_name": "GL",
        "status": "Defunct",
        "titles": 0,
        "title_years": [],
        "primary_color": "#E37424",
        "slug": "gujarat-lions",
    },
    "Rising Pune Supergiant": {
        "short_name": "RPS",
        "status": "Defunct",
        "titles": 0,
        "title_years": [],
        "primary_color": "#7B1B58",
        "slug": "rising-pune-supergiant",
    },
    "Pune Warriors": {
        "short_name": "PWI",
        "status": "Defunct",
        "titles": 0,
        "title_years": [],
        "primary_color": "#2F5597",
        "slug": "pune-warriors",
    },
    "Kochi Tuskers Kerala": {
        "short_name": "KTK",
        "status": "Defunct",
        "titles": 0,
        "title_years": [],
        "primary_color": "#6B2D82",
        "slug": "kochi-tuskers-kerala",
    },
}

TEAM_NAME_MAP = {k.lower(): k for k in FRANCHISE_METADATA}
for name, meta in FRANCHISE_METADATA.items():
    TEAM_NAME_MAP[meta["short_name"].lower()] = name
    TEAM_NAME_MAP[meta["slug"].lower()] = name


def format_season_ranges(seasons: List[int]) -> str:
    """Compress sorted seasons into ranges, e.g. [2008, 2009, 2011] -> '2008–2009, 2011'."""
    ranges: List[List[int]] = []
    for s in seasons:
        if ranges and s == ranges[-1][1] + 1:
            ranges[-1][1] = s
        else:
            ranges.append([s, s])
    return ", ".join(f"{a}" if a == b else f"{a}–{b}" for a, b in ranges)


class CanonicalAnalyticsEngine:
    """In-memory full-history engine for CricketLens."""

    def __init__(self, data_dir: Optional[Path] = None, derived_dir: Optional[Path] = None):
        if data_dir is None:
            self.data_dir = Path(__file__).resolve().parents[4] / "data" / "processed"
        else:
            self.data_dir = Path(data_dir)
        self.derived_dir = Path(derived_dir) if derived_dir is not None else self.data_dir.parent / "derived"

        self._initialized = False
        self._derived_error: Optional[str] = None
        self._matches: pd.DataFrame = pd.DataFrame()
        self._deliveries: pd.DataFrame = pd.DataFrame()
        self._batters: pd.DataFrame = pd.DataFrame()
        self._innings: pd.DataFrame = pd.DataFrame()

        # Indexed structures (players are keyed by Cricsheet registry ID)
        self._match_players: pd.DataFrame = pd.DataFrame()
        self._batting_appearances: pd.DataFrame = pd.DataFrame()
        self._replacements: pd.DataFrame = pd.DataFrame()
        self._appearances: pd.DataFrame = pd.DataFrame()
        # Row positions per registry ID, so a profile reads only its own rows
        self._squad_rows: Dict[str, np.ndarray] = {}
        self._bat_rows: Dict[str, np.ndarray] = {}
        self._bowl_rows: Dict[str, np.ndarray] = {}
        self._appearance_rows: Dict[str, np.ndarray] = {}
        self._substitutions: Dict[Tuple[int, str], List[Dict[str, Any]]] = {}
        self._people_names: Dict[str, List[str]] = {}
        self._player_names_by_id: Dict[str, str] = {}
        self._player_ids_by_name: Dict[str, Set[str]] = {}
        self._player_master_list: List[Dict[str, Any]] = []
        self._directory_counts: Dict[str, int] = {}
        self._franchise_seasons: Dict[str, List[int]] = {}
        # One row per team per match (result, toss, innings order, runs, wickets, phase totals)
        self._team_rows: pd.DataFrame = pd.DataFrame()
        # Ordinary-innings dismissal events, and super-over rows of each derived table (reported as excluded)
        self._dismissals: pd.DataFrame = pd.DataFrame()
        self._super_over_events: Dict[str, pd.DataFrame] = {}
        self._eda_full_history: Optional[Dict[str, Any]] = None

    def ensure_loaded(self) -> None:
        if self._initialized:
            return

        p_matches = self.data_dir / "matches.csv"
        p_deliv = self.data_dir / "deliveries.csv"
        p_bat = self.data_dir / "batter_innings.csv"
        p_inn = self.data_dir / "innings.csv"

        if not (p_matches.exists() and p_deliv.exists() and p_bat.exists() and p_inn.exists()):
            raise FileNotFoundError(
                f"Missing processed datasets in {self.data_dir}. Ensure matches.csv, deliveries.csv, batter_innings.csv, and innings.csv are present."
            )

        deliv_dtypes = {
            "match_id": "int32",
            "season": "int16",
            "innings": "int8",
            "over_index": "int8",
            "delivery_index": "int8",
            "runs_batter": "int8",
            "runs_extras": "int8",
            "runs_total": "int8",
            "wides": "int8",
            "noballs": "int8",
            "byes": "int8",
            "legbyes": "int8",
            "legal_delivery": "int8",
            "team_wickets_on_ball": "int8",
            "innings_runs_after": "int16",
            "innings_wickets_after": "int8",
        }

        self._matches = pd.read_csv(p_matches)
        self._deliveries = pd.read_csv(p_deliv, dtype=deliv_dtypes)
        self._batters = pd.read_csv(p_bat)
        self._innings = pd.read_csv(p_inn)

        # Enrich deliveries with bowler runs conceded, legal ball, bowler wicket, boundaries
        # Bowler runs conceded = runs_batter + wides + noballs (excludes byes and legbyes!)
        self._deliveries["bowler_runs_conceded"] = (
            self._deliveries["runs_batter"] + self._deliveries["wides"] + self._deliveries["noballs"]
        )
        # Bowler wickets and non-boundary flags come from data/derived (built from the raw JSON)
        self._load_derived_events()
        # A four or six off the bat is a boundary unless Cricsheet flags it non_boundary (e.g. an all-run four)
        self._deliveries["is_four"] = (self._deliveries["runs_batter"] == 4) & ~self._deliveries["is_non_boundary"]
        self._deliveries["is_six"] = (self._deliveries["runs_batter"] == 6) & ~self._deliveries["is_non_boundary"]
        self._deliveries["is_dot"] = (self._deliveries["runs_batter"] == 0) & (self._deliveries["legal_delivery"] == 1)

        # Seasons each franchise actually played, from canonical team names in matches.csv
        appearances = pd.concat([
            self._matches[["season", "team1"]].rename(columns={"team1": "team"}),
            self._matches[["season", "team2"]].rename(columns={"team2": "team"}),
        ])
        seasons_by_team = appearances.groupby("team")["season"].unique()
        self._franchise_seasons = {
            name: sorted(int(s) for s in seasons_by_team.get(name, []))
            for name in FRANCHISE_METADATA
        }
        self._build_team_rows()

        # Build the player directory; without data/derived, player endpoints return 503 instead
        if not self._derived_error:
            self._build_player_index()
        self._initialized = True

    def _read_derived(self, name: str, columns: List[str]) -> Optional[pd.DataFrame]:
        """Read the ordinary-innings rows of a data/derived table; None if missing or not aligned."""
        path = self.derived_dir / name
        if not path.exists():
            self._derived_error = f"{name} is missing from {self.derived_dir}."
            return None
        table = pd.read_csv(path, usecols=DELIVERY_KEY + ["is_super_over", "bowler"] + columns)
        # Super overs are never part of ordinary match statistics; they are kept aside only to report the exclusion.
        self._super_over_events[name] = table[table["is_super_over"]].reset_index(drop=True)
        table = table[~table["is_super_over"]]
        joined = table.merge(
            self._deliveries[DELIVERY_KEY + ["bowler"]], on=DELIVERY_KEY,
            how="left", suffixes=("", "_delivery"), indicator=True,
        )
        matched = joined["_merge"] == "both"
        unmatched = int((~matched).sum())
        mismatched = int((joined.loc[matched, "bowler"] != joined.loc[matched, "bowler_delivery"]).sum())
        if unmatched or mismatched:
            self._derived_error = (
                f"{name} does not match deliveries.csv ({unmatched} unmatched rows, {mismatched} bowler mismatches)."
            )
            return None
        return table

    def _load_derived_events(self) -> None:
        """Attach bowler-credited wickets and non-boundary flags from data/derived to deliveries.

        The tables are rebuilt from the raw JSON by cricketlens.derived_events and joined on
        DELIVERY_KEY. If either is missing or does not line up with deliveries.csv, bowling and
        boundary statistics are marked unavailable instead of falling back to an estimate.
        """
        self._derived_error = None
        dismissals = self._read_derived(
            "dismissals.csv", ["bowler_credited", "kind", "batting_team", "counts_as_batting_dismissal"],
        )
        non_boundary = self._read_derived("non_boundary_events.csv", []) if dismissals is not None else None

        if self._derived_error:
            logger.error("%s Bowling and boundary statistics are unavailable.", self._derived_error)
            # Placeholders only: every endpoint serving these statistics returns 503 until this is fixed.
            self._deliveries["bowler_wickets"] = 0
            self._deliveries["is_non_boundary"] = False
            return

        key_types = {k: self._deliveries[k].dtype for k in DELIVERY_KEY}
        credited = (
            dismissals[dismissals["bowler_credited"]]
            .groupby(DELIVERY_KEY).size().rename("bowler_wickets").reset_index()
            .astype(key_types)
        )
        flagged = non_boundary[DELIVERY_KEY].drop_duplicates().assign(is_non_boundary=True).astype(key_types)
        self._deliveries = (
            self._deliveries
            .merge(credited, on=DELIVERY_KEY, how="left")
            .merge(flagged, on=DELIVERY_KEY, how="left")
        )
        # One row per ordinary-innings dismissal event (every kind, retirements included)
        self._dismissals = dismissals.drop(columns=["is_super_over", "bowler"]).reset_index(drop=True)
        self._deliveries["bowler_wickets"] = self._deliveries["bowler_wickets"].fillna(0).astype("int8")
        self._deliveries["is_non_boundary"] = self._deliveries["is_non_boundary"].notna()
        self._load_squads()

    def _load_squads(self) -> None:
        """Load squad lists and registry names; give every bowler their registry ID within each match.

        Names are only unique within a match (the same name can belong to different people across
        seasons), so bowlers are resolved through that match's squad list, never a global name lookup.
        """
        paths = [self.derived_dir / name for name in (
            "match_players.csv", "people.csv", "batting_appearances.csv", "match_replacements.csv",
        )]
        missing = [p.name for p in paths if not p.exists()]
        if missing:
            self._derived_error = f"{', '.join(missing)} missing from {self.derived_dir}."
            logger.error("%s Player statistics are unavailable.", self._derived_error)
            return
        squads = pd.read_csv(paths[0], usecols=["match_id", "season", "date", "team", "player_name", "player_id"])
        people = pd.read_csv(paths[1], usecols=["player_id", "names"])
        replacements = pd.read_csv(paths[3], usecols=[
            "match_id", "innings", "is_super_over", "team", "reason", "player_in", "player_in_id", "player_out", "player_out_id",
        ])
        # Every player at the crease (striker or non-striker) has a batting innings
        appearances = pd.read_csv(paths[2], usecols=[
            "match_id", "season", "date", "innings", "batting_team", "player_id", "balls_faced", "runs", "dismissed",
            "dismissal_kind",
        ]).merge(
            self._innings[["match_id", "innings", "bowling_team", "venue_canonical"]], on=["match_id", "innings"], how="left",
        )

        lookup = (
            squads[["match_id", "player_name", "player_id"]]
            .rename(columns={"player_name": "bowler", "player_id": "bowler_id"})
            .astype({"match_id": self._deliveries["match_id"].dtype})
        )
        ambiguous = int(lookup.duplicated(["match_id", "bowler"]).sum())
        self._deliveries = self._deliveries.merge(lookup.drop_duplicates(["match_id", "bowler"]), on=["match_id", "bowler"], how="left")
        unmapped = int(self._deliveries["bowler_id"].isna().sum()) + int(self._deliveries["batter_id"].isna().sum())
        known = set(people["player_id"])
        unknown = len((
            set(self._deliveries["bowler_id"].dropna()) | set(self._deliveries["batter_id"].dropna())
            | set(appearances["player_id"])
        ) - known)
        orphan_innings = int(appearances["bowling_team"].isna().sum())
        # Batting innings and both players of every substitution must be in that match's squad list
        listed = set(zip(squads["match_id"], squads["player_id"]))
        unlisted = sum(
            (m, p) not in listed for m, p in [
                *zip(appearances["match_id"], appearances["player_id"]),
                *zip(replacements["match_id"], replacements["player_in_id"]),
                *zip(replacements["match_id"], replacements["player_out_id"]),
            ]
        )
        if ambiguous or unmapped or unknown or orphan_innings or unlisted:
            self._derived_error = (
                f"Player identities do not resolve ({unmapped} unmapped deliveries, {ambiguous} ambiguous "
                f"squad names, {unknown} IDs missing from people.csv, {orphan_innings} appearances "
                f"without an innings in innings.csv, {unlisted} batting or substitution rows outside the squad lists)."
            )
            logger.error("%s Player statistics are unavailable.", self._derived_error)
            return
        self._match_players = squads
        self._people_names = dict(zip(people["player_id"], people["names"].str.split(";")))
        self._batting_appearances = appearances
        self._replacements = replacements

    def derived_status(self) -> Dict[str, Any]:
        """Availability of the data/derived tables used for bowling and boundary statistics."""
        self.ensure_loaded()
        if self._derived_error:
            return {"available": False, "detail": self._derived_error, "build_command": DERIVED_BUILD_COMMAND}
        return {"available": True, "detail": f"Loaded from {self.derived_dir}.", "build_command": DERIVED_BUILD_COMMAND}

    def require_derived(self) -> None:
        """Raise DerivedDataUnavailable when bowling or boundary statistics cannot be served."""
        self.ensure_loaded()
        if self._derived_error:
            raise DerivedDataUnavailable(
                f"Bowling and boundary statistics are unavailable: {self._derived_error} "
                f"Rebuild the derived tables with `{DERIVED_BUILD_COMMAND}` (see data/derived/README.md)."
            )

    def _build_player_index(self) -> None:
        """Build the player directory: one entry per Cricsheet registry ID who batted or bowled."""
        squads = self._match_players
        directory_ids = sorted(set(self._batting_appearances["player_id"]) | set(self._deliveries["bowler_id"]))

        # Squad appearances give matches, seasons and teams for every player
        squad_grp = squads.groupby("player_id").agg(
            matches=("match_id", "nunique"),
            seasons=("season", lambda s: sorted({int(x) for x in s})),
            teams=("team", lambda t: sorted(set(t))),
        )
        self._squad_info = squad_grp.to_dict(orient="index")

        # Display name: the most-used name variant, ties broken by the most recent match
        usage = (
            squads.groupby(["player_id", "player_name"])
            .agg(uses=("match_id", "count"), last_date=("date", "max")).reset_index()
            .sort_values(["player_id", "uses", "last_date"], ascending=[True, False, False])
        )
        display = usage.drop_duplicates("player_id").set_index("player_id")["player_name"].to_dict()
        # Different people who share a name are told apart by full franchise names and season span
        shared = Counter(display[pid] for pid in directory_ids)
        for pid in directory_ids:
            if shared[display[pid]] > 1:
                info = self._squad_info[pid]
                teams = " / ".join(info["teams"])
                first, last = info["seasons"][0], info["seasons"][-1]
                span = f"{first}" if first == last else f"{first}–{last}"
                display[pid] = f"{display[pid]} ({teams} {span})"
        self._player_names_by_id = {pid: display[pid] for pid in directory_ids}

        # Every listed name variant and the display name resolve to the registry ID
        self._player_ids_by_name = defaultdict(set)
        for pid in directory_ids:
            for name in {*self._people_names.get(pid, []), display[pid]}:
                self._player_ids_by_name[name.lower()].add(pid)

        # Aggregate batting metrics per batter
        # Pre-filter boundary balls before grouping for high performance
        boundary_deliv = self._deliveries[
            (self._deliveries["is_four"]) | (self._deliveries["is_six"]) | (self._deliveries["is_dot"])
        ]
        ball_agg = boundary_deliv.groupby(["match_id", "innings", "batter_id"]).agg(
            fours=("is_four", "sum"),
            sixes=("is_six", "sum"),
            dots=("is_dot", "sum"),
        ).reset_index().rename(columns={"batter_id": "player_id"})

        # One row per batting innings: every crease appearance, including non-striker-only ones
        self._batters_merged = pd.merge(
            self._batting_appearances, ball_agg, on=["match_id", "innings", "player_id"], how="left"
        )
        self._batters_merged["dismissed"] = self._batters_merged["dismissed"].astype(int)
        self._batters_merged["reached_30"] = (self._batters_merged["runs"] >= 30).astype(int)
        self._batters_merged["reached_50"] = (self._batters_merged["runs"] >= 50).astype(int)
        self._batters_merged["batter"] = self._batters_merged["player_id"].map(self._player_names_by_id)
        self._batters_merged["fours"] = self._batters_merged["fours"].fillna(0).astype(int)
        self._batters_merged["sixes"] = self._batters_merged["sixes"].fillna(0).astype(int)
        self._batters_merged["dots"] = self._batters_merged["dots"].fillna(0).astype(int)
        self._batters_merged["is_duck"] = (self._batters_merged["runs"] == 0) & (self._batters_merged["dismissed"] == 1)
        self._batters_merged["is_100"] = self._batters_merged["runs"] >= 100
        self._batters_merged["strike_rate"] = np.where(
            self._batters_merged["balls_faced"] > 0,
            (self._batters_merged["runs"] / self._batters_merged["balls_faced"] * 100).round(2),
            0.0,
        )

        # Batting career aggregations (vectorized)
        bat_grp = self._batters_merged.groupby("player_id").agg(
            innings=("match_id", "count"),
            runs=("runs", "sum"),
            balls_faced=("balls_faced", "sum"),
            dismissals=("dismissed", "sum"),
            fours=("fours", "sum"),
            sixes=("sixes", "sum"),
            ducks=("is_duck", "sum"),
            highest_score=("runs", "max"),
            scores_30_plus=("reached_30", "sum"),
            scores_50_plus=("reached_50", "sum"),
            scores_100_plus=("is_100", "sum"),
        )
        bat_dict = bat_grp.to_dict(orient="index")

        # Bowling per innings, keyed by the bowler's registry ID
        bowl_match_agg = self._deliveries.groupby(
            ["match_id", "date", "season", "innings", "bowling_team", "batting_team", "bowler_id"]
        ).agg(
            legal_balls=("legal_delivery", "sum"),
            runs_conceded=("bowler_runs_conceded", "sum"),
            wickets=("bowler_wickets", "sum"),
        ).reset_index()
        balls = bowl_match_agg["legal_balls"]
        bowl_match_agg["overs"] = (balls // 6).astype(str) + "." + (balls % 6).astype(str)
        bowl_match_agg["is_3w"] = bowl_match_agg["wickets"] == 3
        bowl_match_agg["is_4w"] = bowl_match_agg["wickets"] == 4
        bowl_match_agg["is_5w"] = bowl_match_agg["wickets"] >= 5
        bowl_match_agg["bowler"] = bowl_match_agg["bowler_id"].map(self._player_names_by_id)
        bowl_match_agg["venue_canonical"] = bowl_match_agg["match_id"].map(
            dict(zip(self._matches["match_id"], self._matches["venue_canonical"]))
        )
        self._bowler_matches = bowl_match_agg

        self._squad_rows = squads.groupby("player_id").indices
        self._bat_rows = self._batters_merged.groupby("player_id").indices
        self._bowl_rows = bowl_match_agg.groupby("bowler_id").indices
        self._build_appearance_log()

        # Bowling career aggregations (vectorized)
        bowl_grp = bowl_match_agg.groupby("bowler_id").agg(
            innings=("match_id", "count"),
            legal_deliveries=("legal_balls", "sum"),
            runs_conceded=("runs_conceded", "sum"),
            wickets=("wickets", "sum"),
            hauls_3=("is_3w", "sum"),
            hauls_4=("is_4w", "sum"),
            hauls_5=("is_5w", "sum"),
        )

        # Best bowling figures per bowler: most wickets, then fewest runs
        top_bowling = bowl_match_agg.sort_values(
            by=["wickets", "runs_conceded"], ascending=[False, True]
        ).drop_duplicates(subset=["bowler_id"], keep="first")
        best_bowling = dict(zip(top_bowling["bowler_id"], top_bowling["wickets"].astype(str) + "/" + top_bowling["runs_conceded"].astype(str)))

        bowl_dict = bowl_grp.to_dict(orient="index")

        # One directory entry per registry ID
        master_list = []
        for pid in directory_ids:
            b_info = bat_dict.get(pid)
            w_info = bowl_dict.get(pid)
            squad = self._squad_info[pid]

            is_batter = b_info is not None
            is_bowler = w_info is not None
            all_seasons = squad["seasons"]

            # Batting stats
            batting_inn = b_info["innings"] if b_info else 0
            total_runs = b_info["runs"] if b_info else 0
            dismissals = b_info["dismissals"] if b_info else 0
            bat_balls = b_info["balls_faced"] if b_info else 0
            # A rate with no denominator is undefined (null), never runs or 0
            bat_avg = round(total_runs / dismissals, 2) if dismissals > 0 else None
            bat_sr = round(total_runs / bat_balls * 100, 2) if bat_balls > 0 else None

            # Bowling stats
            bowl_inn = w_info["innings"] if w_info else 0
            legal_deliveries = w_info["legal_deliveries"] if w_info else 0
            runs_conc = w_info["runs_conceded"] if w_info else 0
            total_wkts = w_info["wickets"] if w_info else 0
            bowl_avg = round(runs_conc / total_wkts, 2) if total_wkts > 0 else None
            bowl_sr = round(legal_deliveries / total_wkts, 2) if total_wkts > 0 else None
            bowl_econ = round(runs_conc / (legal_deliveries / 6.0), 2) if legal_deliveries > 0 else None

            role = derive_role(int(squad["matches"]), int(batting_inn), int(bat_balls), int(bowl_inn), int(legal_deliveries))

            item = {
                "player_id": pid,
                "name": self._player_names_by_id[pid],
                "name_variants": sorted(self._people_names.get(pid, [])),
                "role": role,
                "is_batter": is_batter,
                "is_bowler": is_bowler,
                "matches": int(squad["matches"]),
                "first_season": all_seasons[0],
                "last_season": all_seasons[-1],
                "seasons_count": len(all_seasons),
                "seasons_played": all_seasons,
                "teams": squad["teams"],
                # Batting preview
                "batting_innings": int(batting_inn),
                "total_runs": int(total_runs),
                "batting_avg": bat_avg,
                "strike_rate": bat_sr,
                "scores_30_plus": int(b_info["scores_30_plus"]) if b_info else 0,
                "scores_50_plus": int(b_info["scores_50_plus"]) if b_info else 0,
                # Bowling preview
                "bowling_innings": int(bowl_inn),
                "wickets": int(total_wkts),
                "bowling_avg": bowl_avg,
                "economy": bowl_econ,
                "best_bowling": best_bowling.get(pid, "—"),
            }
            master_list.append(item)

        self._player_master_list = master_list
        self._directory_counts = {
            "all": len(master_list),
            "batters": sum(p["is_batter"] for p in master_list),
            "bowlers": sum(p["is_bowler"] for p in master_list),
            "all_rounders": sum(p["role"] == "All-Rounder" for p in master_list),
        }

    def _build_appearance_log(self) -> None:
        """One row per squad appearance with batting, bowling and the team's result, most recent first."""
        as_int = {"match_id": "int64"}
        matches = self._matches[[
            "match_id", "venue_canonical", "team1", "team2", "outcome_type", "winner", "super_over_winner",
            "outcome_method",
        ]].astype(as_int)
        log = self._match_players.astype(as_int).merge(matches, on="match_id", how="left", validate="many_to_one")
        log["opposition"] = np.where(log["team"] == log["team1"], log["team2"], log["team1"])

        batting = self._batters_merged[[
            "match_id", "player_id", "runs", "balls_faced", "fours", "sixes", "dismissed", "dismissal_kind",
        ]].astype(as_int).rename(columns=lambda c: c if c in ("match_id", "player_id") else f"bat_{c}")
        bowling = self._bowler_matches[[
            "match_id", "bowler_id", "legal_balls", "overs", "runs_conceded", "wickets",
        ]].astype(as_int).rename(columns={"bowler_id": "player_id"}).rename(
            columns=lambda c: c if c in ("match_id", "player_id") else f"bowl_{c}"
        )
        log = (
            log.merge(batting, on=["match_id", "player_id"], how="left", validate="one_to_one")
            .merge(bowling, on=["match_id", "player_id"], how="left", validate="one_to_one")
        )

        # Result for the player's team; an outcome type outside these is left unset
        won = log["outcome_type"] == "win"
        log["result"] = np.select(
            [won & (log["winner"] == log["team"]), won, log["outcome_type"] == "tie", log["outcome_type"] == "no result"],
            ["won", "lost", "tied", "no_result"],
            default="",
        )
        log = log.drop(columns=["team1", "team2"]).sort_values(
            ["player_id", "date", "match_id"], ascending=[True, False, False]
        ).reset_index(drop=True)
        self._appearances = log
        self._appearance_rows = log.groupby("player_id").indices

        # Each substitution gives the player who came in and the player replaced one entry each
        substitutions: Dict[Tuple[int, str], List[Dict[str, Any]]] = defaultdict(list)
        for r in self._replacements.to_dict("records"):
            for direction, pid, other, other_id in (
                ("in", r["player_in_id"], r["player_out"], r["player_out_id"]),
                ("out", r["player_out_id"], r["player_in"], r["player_in_id"]),
            ):
                substitutions[(int(r["match_id"]), pid)].append({
                    "direction": direction, "reason": r["reason"], "innings": int(r["innings"]),
                    "counterpart_id": other_id, "counterpart_name": other,
                })
        self._substitutions = dict(substitutions)

    # ==========================================
    # TEAM ANALYSIS APIs
    # ==========================================

    def _team_item(self, name: str) -> Dict[str, Any]:
        """Franchise metadata with participation seasons derived from match data."""
        meta = FRANCHISE_METADATA[name]
        seasons = self._franchise_seasons[name]
        return {
            "id": meta["slug"],
            "name": name,
            "short_name": meta["short_name"],
            "status": meta["status"],
            "seasons_active": format_season_ranges(seasons),
            "active_seasons": seasons,
            "titles": meta["titles"],
            "title_years": meta["title_years"],
            "primary_color": meta["primary_color"],
        }

    def list_teams(self) -> List[Dict[str, Any]]:
        """Return every canonical franchise with title and era metadata."""
        self.ensure_loaded()
        return [self._team_item(name) for name in FRANCHISE_METADATA]

    def _build_team_rows(self) -> None:
        """One row per team per match: result, Super Over, toss, innings order, runs, wickets and phase totals."""
        m = self._matches
        cols = [
            "match_id", "season", "date", "venue_canonical", "toss_winner", "toss_decision",
            "outcome_type", "final_winner", "decided_by", "outcome_method",
        ]
        t = pd.concat([
            m[cols].assign(team=m["team1"], opponent=m["team2"]),
            m[cols].assign(team=m["team2"], opponent=m["team1"]),
        ], ignore_index=True)
        has_winner = t["final_winner"].notna()
        t["result"] = np.select(
            [t["outcome_type"] == "no result", has_winner & (t["final_winner"] == t["team"]), has_winner,
             t["outcome_type"] == "tie"],
            ["no_result", "won", "lost", "tied"],
            default="not_recorded",
        )
        t["regulation_tie"] = t["outcome_type"] == "tie"
        t["super_over"] = np.where((t["decided_by"] == "super_over") & has_winner, t["result"], "")
        t["toss_won"] = t["toss_winner"] == t["team"]
        first = self._innings[self._innings["innings"] == 1].set_index("match_id")["batting_team"]
        t["batted_first"] = t["match_id"].map(first) == t["team"]

        # Innings totals as the batting side and as the fielding side
        counts: List[str] = []
        for team_col, names in (
            ("batting_team", ["runs_scored", "wickets_lost", "balls_faced"]),
            ("bowling_team", ["runs_conceded", "wickets_taken", "balls_bowled"]),
        ):
            agg = self._innings.groupby(["match_id", team_col])[["runs", "wickets", "legal_balls"]].sum()
            agg.columns = names
            agg.index.names = ["match_id", "team"]
            t = t.merge(agg.reset_index(), on=["match_id", "team"], how="left")
            counts += names

        t["innings_batted"] = t["runs_scored"].notna().astype("int64")
        t["innings_bowled"] = t["runs_conceded"].notna().astype("int64")

        # Phase totals as the batting side (bat_*) and as the fielding side (bowl_*)
        d = self._deliveries
        stats = d[["match_id", "batting_team", "bowling_team"]].assign(
            phase=np.select([d["over_index"] <= PHASES[0][3], d["over_index"] <= PHASES[1][3]],
                            [PHASES[0][0], PHASES[1][0]], PHASES[2][0]),
            runs=d["runs_total"].astype("int64"),
            balls=d["legal_delivery"].astype("int64"),
            wickets=d["team_wickets_on_ball"].astype("int64"),
        )
        for role, team_col in (("bat", "batting_team"), ("bowl", "bowling_team")):
            agg = stats.groupby(["match_id", team_col, "phase"])[["runs", "balls", "wickets"]].sum().unstack("phase", fill_value=0)
            agg.columns = [f"{role}_{phase}_{stat}" for stat, phase in agg.columns]
            agg.index.names = ["match_id", "team"]
            agg = agg.reset_index().astype({"match_id": "int64"})
            t = t.merge(agg, on=["match_id", "team"], how="left")
            counts += [c for c in agg.columns if c.startswith(f"{role}_")]

        # A team that never batted or bowled in a match (e.g. abandoned early) has zero totals
        t[counts] = t[counts].fillna(0).astype("int64")
        self._team_rows = t

    def _resolve_team(self, key: str) -> str:
        name = TEAM_NAME_MAP.get(key.lower())
        if not name:
            raise KeyError(f"Team '{key}' is not one of the {len(FRANCHISE_METADATA)} canonical franchises.")
        return name

    def _team_rows_for(self, name: str, season: Optional[int]) -> pd.DataFrame:
        """The franchise's team-match rows, optionally for one season it played."""
        if season is not None and season not in self._franchise_seasons[name]:
            played = format_season_ranges(self._franchise_seasons[name])
            raise KeyError(f"{name} did not play in the {season} season (seasons played: {played}).")
        rows = self._team_rows[self._team_rows["team"] == name]
        return rows if season is None else rows[rows["season"] == season]

    @staticmethod
    def _totals(rows: pd.DataFrame) -> Dict[str, Any]:
        """Runs, wickets and overall run rate / economy for a set of team-match rows."""
        sums = {k: int(rows[k].sum()) for k in (
            "runs_scored", "runs_conceded", "wickets_lost", "wickets_taken", "balls_faced", "balls_bowled",
            "innings_batted", "innings_bowled",
        )}
        return {
            **sums,
            "run_rate": run_rate(sums["runs_scored"], sums["balls_faced"]),
            "run_rate_state": None if sums["balls_faced"] else "no_legal_balls",
            "economy": run_rate(sums["runs_conceded"], sums["balls_bowled"]),
            "economy_state": None if sums["balls_bowled"] else "no_legal_balls",
            "runs_per_innings": round(sums["runs_scored"] / sums["innings_batted"], 2) if sums["innings_batted"] else None,
        }

    @staticmethod
    def _phase_records(rows: pd.DataFrame) -> List[Dict[str, Any]]:
        records = []
        for key, label, first_over, last_over in PHASES:
            runs, balls, wickets = (int(rows[f"bat_{key}_{s}"].sum()) for s in ("runs", "balls", "wickets"))
            conceded, bowled, taken = (int(rows[f"bowl_{key}_{s}"].sum()) for s in ("runs", "balls", "wickets"))
            records.append({
                "phase": key, "label": label, "overs": f"{first_over + 1}–{last_over + 1}",
                "batting_runs": runs, "batting_legal_balls": balls,
                "batting_run_rate": run_rate(runs, balls),
                "batting_run_rate_state": None if balls else "no_legal_balls",
                "wickets_lost": wickets,
                "wickets_lost_per_six": round(wickets / balls * 6, 3) if balls else None,
                "conceded_runs": conceded, "bowling_legal_balls": bowled,
                "economy": run_rate(conceded, bowled),
                "economy_state": None if bowled else "no_legal_balls",
                "wickets_taken": taken,
                "wickets_taken_per_six": round(taken / bowled * 6, 3) if bowled else None,
            })
        return records

    @staticmethod
    def _venue_records(rows: pd.DataFrame, min_matches: int) -> Tuple[List[Dict[str, Any]], int]:
        """Venues with at least min_matches matches in these rows, most matches first; and the venue total."""
        records = [{"venue": v, **result_summary(g)} for v, g in rows.groupby("venue_canonical")]
        shown = sorted((r for r in records if r["played"] >= min_matches), key=lambda r: (-r["played"], r["venue"]))
        return shown, len(records)

    def get_team_overview(self, team_slug_or_name: str, season: Optional[int] = None) -> Dict[str, Any]:
        """Franchise record for all seasons or one season; every number is recomputed for the selection."""
        self.ensure_loaded()
        name = self._resolve_team(team_slug_or_name)
        team_item = self._team_item(name)
        rows = self._team_rows_for(name, season)
        seasons = sorted(int(s) for s in rows["season"].unique())
        phases = self._phase_records(rows)
        venues, _ = self._venue_records(rows, 3)
        toss = rows[rows["toss_won"]]
        window = rows[(rows["season"] >= 2022) & (rows["season"] <= 2025)]
        # Every toss winner in the same seasons (one row per match), for comparison with this team
        league = self._team_rows[self._team_rows["toss_won"] & self._team_rows["season"].isin(seasons)]

        return {
            "team": team_item,
            "coverage": {
                "season_filter": season,
                "seasons_in_scope": seasons,
                "first_season": seasons[0],
                "last_season": seasons[-1],
                "total_seasons_participated": len(team_item["active_seasons"]),
            },
            "all_time": {
                **result_summary(rows),
                "regulation_ties": int(rows["regulation_tie"].sum()),
                **self._totals(rows),
                "denominator_description": TEAM_DEFINITIONS["win_pct"],
            },
            "comparative_2022_2025": {
                **result_summary(window), "window": "2022–2025 (4-Year Comparative Era)",
            } if season is None and len(window) else None,
            **innings_order_record(rows),
            "season_history": [
                {"season": int(s), **result_summary(g), "regulation_ties": int(g["regulation_tie"].sum()), **self._totals(g)}
                for s, g in rows.groupby("season")
            ],
            "venue_records": venues,
            "opponents": sorted(
                ({"opponent": o, "opponent_short_name": FRANCHISE_METADATA[o]["short_name"], **result_summary(g)}
                 for o, g in rows.groupby("opponent")),
                key=lambda r: (-r["played"], r["opponent"]),
            ),
            "phases": phases,
            "toss_stats": {
                **toss_record(toss),
                "toss_match_win_rate": result_summary(toss)["win_pct"],
                "league": {
                    "label": f"All teams, same seasons ({format_season_ranges(seasons)})",
                    "seasons": seasons,
                    **{k: v for k, v in toss_record(league).items() if k in ("after_winning_toss", "chose_to_bat", "chose_to_field")},
                },
            },
            "definitions": TEAM_DEFINITIONS,
            "state_definitions": TEAM_STATE_DEFINITIONS,
        }

    def get_team_venues(self, team_slug_or_name: str, season: Optional[int] = None, min_matches: int = 3) -> Dict[str, Any]:
        """Venue records for the selection, keeping venues with at least min_matches matches."""
        self.ensure_loaded()
        name = self._resolve_team(team_slug_or_name)
        rows = self._team_rows_for(name, season)
        venues, total = self._venue_records(rows, min_matches)
        return {
            "team": self._team_item(name),
            "season_filter": season,
            "min_matches": min_matches,
            "venues_total": total,
            "venues_shown": len(venues),
            "matches_shown": sum(v["played"] for v in venues),
            "venues": venues,
        }

    def get_head_to_head(self, team_a_key: str, team_b_key: str, season: Optional[int] = None) -> Dict[str, Any]:
        """Head-to-head record between two franchises, all seasons or one; B vs A mirrors A vs B."""
        self.ensure_loaded()
        team_a, team_b = self._resolve_team(team_a_key), self._resolve_team(team_b_key)
        if team_a == team_b:
            raise ValueError("Select two distinct franchises for Head-to-Head comparison.")
        rows = self._team_rows_for(team_a, season)
        self._team_rows_for(team_b, season)  # the opponent must also have played that season
        rows = rows[rows["opponent"] == team_b].sort_values(["date", "match_id"], ascending=False)
        mirror = rows.assign(result=rows["result"].replace({"won": "lost", "lost": "won"}),
                             super_over=rows["super_over"].replace({"won": "lost", "lost": "won"}))
        a, b = result_summary(rows), result_summary(mirror)
        won, lost = rows["result"] == "won", rows["result"] == "lost"

        scores = self._innings[self._innings["match_id"].isin(rows["match_id"])].sort_values("innings")
        scorecards = {
            mid: " vs ".join(f"{r.batting_team} {r.runs}/{r.wickets}" for r in grp.itertuples())
            for mid, grp in scores.groupby("match_id")
        }
        first_runs = scores[scores["innings"] == 1].set_index("match_id")["runs"].to_dict()
        second_runs = scores[scores["innings"] == 2].set_index("match_id")["runs"].to_dict()

        meetings = []
        for r in rows.itertuples():
            if r.result == "no_result":
                outcome = "No result"
            elif r.result == "tied":
                outcome = "Tied (no Super Over result recorded)"
            else:
                winner = team_a if r.result == "won" else team_b
                how = " (Super Over)" if r.super_over else f" ({r.outcome_method})" if pd.notna(r.outcome_method) else ""
                outcome = f"{winner} won{how}"
            meetings.append({
                "match_id": int(r.match_id),
                "season": int(r.season),
                "date": str(r.date),
                "venue": str(r.venue_canonical),
                "winner": str(r.final_winner) if pd.notna(r.final_winner) else None,
                "result_text": outcome,
                "super_over": bool(r.super_over),
                "margin_or_summary": f"{scorecards.get(r.match_id, 'No innings recorded')} · {outcome}",
                "innings1_runs": int(first_runs.get(r.match_id, 0)),
                "innings2_runs": int(second_runs.get(r.match_id, 0)),
            })

        span = format_season_ranges(sorted(int(s) for s in rows["season"].unique())) or "no seasons"
        return {
            "team1": self._team_item(team_a),
            "team2": self._team_item(team_b),
            "season_filter": season,
            "total_matches": a["played"],
            "team1_wins": a["wins"],
            "team2_wins": b["wins"],
            "ties_super_overs": int(rows["regulation_tie"].sum()),
            "unresolved_ties": a["ties"],
            "team1_super_over_wins": a["super_over_wins"],
            "team2_super_over_wins": b["super_over_wins"],
            "no_results": a["no_results"],
            "win_pct_denominator": a["win_pct_denominator"],
            "team1_win_pct": a["win_pct"],
            "team2_win_pct": b["win_pct"],
            "team1_batting_first_wins": int((won & rows["batted_first"]).sum()),
            "team2_batting_first_wins": int((lost & ~rows["batted_first"]).sum()),
            "team1_chasing_wins": int((won & ~rows["batted_first"]).sum()),
            "team2_chasing_wins": int((lost & rows["batted_first"]).sum()),
            "recent_meetings": meetings,
            "notes": [
                f"{a['played']} matches between {team_a} and {team_b} ({span}).",
                "A tie decided by a Super Over counts as a win for the Super Over winner and is also counted in ties_super_overs.",
            ],
        }

    # ==========================================
    # PLAYER EXPLORER APIs
    # ==========================================

    def list_players(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        tier: Optional[str] = None,
        sort_by: str = "runs",
        page: int = 1,
        page_size: int = 20,
        min_innings: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return master directory of players with flexible search, filter, and pagination.

        min_innings applies only to a rate sort (see RATE_SORTS): it keeps players with at least that
        many batting or bowling innings, so no player is ever removed when no rate is being ranked.
        """
        self.require_derived()
        players = list(self._player_master_list)

        # 1. Search filter: display name, any listed name variant, or registry ID
        if search:
            q = search.lower().strip()
            players = [
                p for p in players
                if q == p["player_id"].lower() or any(q in n.lower() for n in (p["name"], *p["name_variants"]))
            ]

        # 2. Role filter
        if role and role.lower() != "all":
            r_low = role.lower()
            if r_low == "batters" or r_low == "batter":
                players = [p for p in players if p["is_batter"]]
            elif r_low == "bowlers" or r_low == "bowler":
                players = [p for p in players if p["is_bowler"]]
            elif r_low == "all-rounders" or r_low == "all_rounder":
                players = [p for p in players if p["role"] == "All-Rounder"]

        # 3. Tier / Cohort filter
        if tier and tier.lower() != "all":
            t_low = tier.lower()
            if "leaderboard" in t_low or "min40" in t_low:
                players = [p for p in players if p["batting_innings"] >= 40]
            elif "veteran" in t_low or "60+" in t_low:
                players = [p for p in players if p["batting_innings"] >= 60 or p["bowling_innings"] >= 60]
            elif "experienced" in t_low or "31-60" in t_low:
                players = [p for p in players if (31 <= p["batting_innings"] <= 60) or (31 <= p["bowling_innings"] <= 60)]
            elif "regular" in t_low or "11-30" in t_low:
                players = [p for p in players if (11 <= p["batting_innings"] <= 30) or (11 <= p["bowling_innings"] <= 30)]
            elif "emerging" in t_low or "1-10" in t_low:
                players = [p for p in players if (1 <= p["batting_innings"] <= 10) or (1 <= p["bowling_innings"] <= 10)]

        # 4. Qualification for rate sorts, then sorting (an undefined rate always sorts last)
        qualification = None
        if sort_by in RATE_SORTS:
            innings_kind, higher_is_better = RATE_SORTS[sort_by]
            if min_innings:
                players = [p for p in players if p[f"{innings_kind}_innings"] >= min_innings]
                qualification = {"sort_by": sort_by, "min_innings": min_innings, "innings_kind": innings_kind}
            sign = -1 if higher_is_better else 1
            players.sort(key=lambda x: (x[sort_by] is None, sign * x[sort_by] if x[sort_by] is not None else 0))
        elif sort_by == "wickets":
            players.sort(key=lambda x: -x["wickets"])
        elif sort_by == "innings":
            players.sort(key=lambda x: -(x["batting_innings"] + x["bowling_innings"]))
        else:
            players.sort(key=lambda x: -x["total_runs"])

        total_count = len(players)
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        start_idx = (page - 1) * page_size
        paginated = players[start_idx : start_idx + page_size]

        return {
            "total_players": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "players": paginated,
            "directory_counts": dict(self._directory_counts),
            "qualification": qualification,
        }

    def _resolve_player(self, player_id_or_name: str) -> Tuple[str, str]:
        """Registry ID and display name for a player ID, or for a name variant that identifies one player."""
        pid = player_id_or_name.strip()
        name = self._player_names_by_id.get(pid)
        if not name:
            # Fall back to an exact name variant, but only when it identifies one player
            ids = self._player_ids_by_name.get(pid.lower(), set())
            if len(ids) > 1:
                raise KeyError(
                    f"'{player_id_or_name}' matches several players; use a player ID ({', '.join(sorted(ids))})."
                )
            if ids:
                pid = next(iter(ids))
                name = self._player_names_by_id[pid]
        if not name:
            raise KeyError(f"Player '{player_id_or_name}' not found in canonical IPL directory.")
        return pid, name

    def _player_rows(self, pid: str, season: Optional[int]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """The player's squad, batting-innings, bowling-innings and appearance-log rows, optionally for one season."""
        none = np.array([], dtype=int)
        frames = (
            self._match_players.iloc[self._squad_rows.get(pid, none)],
            self._batters_merged.iloc[self._bat_rows.get(pid, none)],
            self._bowler_matches.iloc[self._bowl_rows.get(pid, none)],
            self._appearances.iloc[self._appearance_rows.get(pid, none)],
        )
        if season is None:
            return frames
        return tuple(f[f["season"] == season] for f in frames)

    def _log_entry(self, r: Dict[str, Any]) -> Dict[str, Any]:
        """One appearance-log row in API shape; columns missing after the left joins become explicit states."""
        match_id, pid = int(r["match_id"]), r["player_id"]

        if _present(r["bat_runs"]):
            kind = r["bat_dismissal_kind"]
            batting = {
                "state": "batted", "runs": int(r["bat_runs"]), "balls_faced": int(r["bat_balls_faced"]),
                "fours": int(r["bat_fours"]), "sixes": int(r["bat_sixes"]), "dismissed": bool(r["bat_dismissed"]),
                "dismissal_kind": kind if _present(kind) else None,
            }
        else:
            batting = {"state": "did_not_bat"}

        if _present(r["bowl_legal_balls"]):
            balls, runs = int(r["bowl_legal_balls"]), int(r["bowl_runs_conceded"])
            bowling = {
                "state": "bowled", "legal_balls": balls, "overs": r["bowl_overs"],
                "runs_conceded": runs, "wickets": int(r["bowl_wickets"]),
                # Undefined for a spell of only wides or no-balls
                "economy": round(runs / (balls / 6.0), 2) if balls else None,
                "economy_state": None if balls else "no_legal_balls",
            }
        else:
            bowling = {"state": "did_not_bowl"}

        outcome = r["result"] or None
        result = {
            "outcome": outcome,
            "outcome_state": None if outcome else "not_recorded_in_source",
            "winner": r["winner"] if _present(r["winner"]) else None,
            "method": r["outcome_method"] if _present(r["outcome_method"]) else None,
        }
        if outcome == "tied":
            so_winner = r["super_over_winner"] if _present(r["super_over_winner"]) else None
            result["super_over_winner"] = so_winner
            if so_winner:
                result["super_over_outcome"] = "won" if so_winner == r["team"] else "lost"
            else:
                result["super_over_state"] = "not_recorded_in_source"

        substitutions = self._substitutions.get((match_id, pid), [])
        directions = {s["direction"] for s in substitutions}
        if not directions:
            appearance_state = "playing_xi"
        elif len(directions) == 2:
            appearance_state = "substituted_in_and_out"
        else:
            appearance_state = f"substituted_{directions.pop()}"

        return {
            "match_id": match_id, "date": r["date"], "season": int(r["season"]),
            "team": r["team"], "opposition": r["opposition"], "venue": r["venue_canonical"],
            "appearance_state": appearance_state, "substitutions": substitutions,
            "batting": batting, "bowling": bowling, "result": result,
        }

    def get_player_profile(self, player_id_or_name: str, season: Optional[int] = None) -> Dict[str, Any]:
        """Career profile (or one season's): summary, batting and bowling figures, season tables and splits."""
        self.require_derived()
        pid, name = self._resolve_player(player_id_or_name)
        squad, b_df, w_df, _ = self._player_rows(pid, season)
        if squad.empty:
            played = format_season_ranges(self._squad_info[pid]["seasons"])
            raise KeyError(f"{name} has no IPL match appearances in {season} (seasons played: {played}).")

        # 1. Career summary from the squad lists
        seasons = sorted(int(s) for s in squad["season"].unique())
        team_history = []
        for team, grp in squad.groupby("team"):
            team_seasons = sorted(int(s) for s in grp["season"].unique())
            team_history.append({
                "team": team,
                "short_name": FRANCHISE_METADATA.get(team, {}).get("short_name"),
                "seasons": team_seasons,
                "seasons_label": format_season_ranges(team_seasons),
                "matches": int(grp["match_id"].nunique()),
            })
        team_history.sort(key=lambda t: (t["seasons"][0], t["seasons"][-1], t["team"]))

        # 2. Batting: career, per season and splits (largest run totals first)
        career_batting = next(iter(batting_table(b_df)), None)
        batting_by_season = batting_table(b_df, "season", "season")
        batting_by_team = batting_table(b_df, "batting_team", "team")
        batting_by_opposition = batting_table(b_df, "bowling_team", "opposition")
        batting_by_venue = batting_table(b_df, "venue_canonical", "venue")
        for table, label in ((batting_by_team, "team"), (batting_by_opposition, "opposition"), (batting_by_venue, "venue")):
            table.sort(key=lambda r, label=label: (-r["runs"], r[label]))

        # 3. Bowling: career, per season and splits (most wickets, then fewest runs, first)
        career_bowling = next(iter(bowling_table(w_df)), None)
        bowling_by_season = bowling_table(w_df, "season", "season")
        bowling_by_opposition = bowling_table(w_df, "batting_team", "opposition")
        bowling_by_venue = bowling_table(w_df, "venue_canonical", "venue")
        for table, label in ((bowling_by_opposition, "opposition"), (bowling_by_venue, "venue")):
            table.sort(key=lambda r, label=label: (-r["wickets"], r["runs_conceded"], r[label]))

        return {
            "player_id": pid,
            "name": name,
            "name_variants": sorted(self._people_names.get(pid, [])),
            "season_filter": season,
            "coverage_period": f"{season} season only" if season is not None else "2008–2026 Complete History",
            "matches": int(squad["match_id"].nunique()),
            "first_season": seasons[0],
            "last_season": seasons[-1],
            "seasons_played": seasons,
            "seasons_count": len(seasons),
            "teams": sorted(set(squad["team"])),
            "team_history": team_history,
            "batting_state": "batted" if career_batting else "did_not_bat",
            "bowling_state": "bowled" if career_bowling else "did_not_bowl",
            "career_batting": career_batting,
            "career_bowling": career_bowling,
            "batting_by_season": batting_by_season,
            "batting_by_team": batting_by_team,
            "batting_by_opposition": batting_by_opposition,
            "batting_by_venue": batting_by_venue,
            "bowling_by_season": bowling_by_season,
            "bowling_by_opposition": bowling_by_opposition,
            "bowling_by_venue": bowling_by_venue,
            "metric_definitions": PROFILE_METRIC_DEFINITIONS,
            "state_definitions": STATE_DEFINITIONS,
        }

    def get_player_matches(
        self, player_id_or_name: str, season: Optional[int] = None, page: int = 1, page_size: int = 20,
    ) -> Dict[str, Any]:
        """Match-by-match log: one row per squad appearance, most recent first, paginated."""
        self.require_derived()
        pid, name = self._resolve_player(player_id_or_name)
        log = self._player_rows(pid, season)[3]
        total = len(log)
        start = (page - 1) * page_size
        return {
            "player_id": pid,
            "name": name,
            "season_filter": season,
            "total_count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)),
            "matches": [self._log_entry(r) for r in log.iloc[start:start + page_size].to_dict("records")],
        }

    # ==========================================
    # STATISTICS & EDA (2008-2026) APIs
    # ==========================================

    def get_eda_full_history(self) -> Dict[str, Any]:
        """Compute comprehensive 2008-2026 historical EDA covering all 15 analysis areas (computed once, then cached)."""
        self.require_derived()
        if self._eda_full_history is not None:
            return self._eda_full_history
        m_df = self._matches
        d_df = self._deliveries
        i_df = self._innings
        b_df = self._batters

        # 1. Season Scoring & Match Evolution
        s_m = m_df.groupby("season")["match_id"].count()
        s_r = d_df.groupby("season")["runs_total"].sum()
        s_w = d_df.groupby("season")["team_wickets_on_ball"].sum()
        s_b = d_df.groupby("season")["legal_delivery"].sum()

        season_evolution = []
        for s in sorted(s_m.index):
            season_evolution.append({
                "season": int(s),
                "matches": int(s_m.loc[s]),
                "runs": int(s_r.loc[s]),
                "wickets": int(s_w.loc[s]),
                "legal_balls": int(s_b.loc[s]),
                "run_rate": round(float(s_r.loc[s] / s_b.loc[s] * 6.0), 2),
            })

        # 2. First Innings Scoring Trends
        inn1 = i_df[i_df["innings"] == 1].copy()
        first_inn_trends = []
        for s, grp in inn1.groupby("season"):
            first_inn_trends.append({
                "season": int(s),
                "innings_count": int(len(grp)),
                "mean_runs": round(float(grp["runs"].mean()), 2),
                "median_runs": round(float(grp["runs"].median()), 1),
                "std_runs": round(float(grp["runs"].std()), 2),
                "min_runs": int(grp["runs"].min()),
                "max_runs": int(grp["runs"].max()),
            })

        # 3. Phase Scoring Evolution Across Eras
        def get_era(s):
            if s <= 2010: return "Inaugural Era (2008–2010)"
            elif s <= 2013: return "Expansion Era (2011–2013)"
            elif s <= 2017: return "Maturity Era (2014–2017)"
            elif s <= 2021: return "Pre-COVID Era (2018–2021)"
            else: return "Modern 10-Team Era (2022–2026)"

        def get_phase(o):
            if o <= 5: return "Powerplay (1-6)"
            elif o <= 15: return "Middle (7-16)"
            else: return "Death (17-20)"

        d_df_copy = d_df[["season", "over_index", "runs_total", "legal_delivery", "team_wickets_on_ball"]].copy()
        d_df_copy["era"] = d_df_copy["season"].apply(get_era)
        d_df_copy["phase"] = d_df_copy["over_index"].apply(get_phase)

        era_phase_patterns = []
        for (era, ph), grp in d_df_copy.groupby(["era", "phase"]):
            r = int(grp["runs_total"].sum())
            b = int(grp["legal_delivery"].sum())
            w = int(grp["team_wickets_on_ball"].sum())
            era_phase_patterns.append({
                "era": era,
                "phase": ph,
                "runs": r,
                "legal_balls": b,
                "wickets": w,
                "run_rate": round(r / b * 6.0, 2),
                "wickets_per_six_balls": round(w / b * 6.0, 3),
            })

        # 4. Boundaries Analysis (Fours & Sixes by Season)
        # is_four / is_six already exclude Cricsheet non-boundary runs
        d_df_b = d_df[["season", "is_four", "is_six", "runs_total"]]

        boundaries_by_season = []
        for s, grp in d_df_b.groupby("season"):
            f_cnt = int(grp["is_four"].sum())
            s_cnt = int(grp["is_six"].sum())
            b_runs = (f_cnt * 4) + (s_cnt * 6)
            tot_runs = int(grp["runs_total"].sum())
            boundaries_by_season.append({
                "season": int(s),
                "fours": f_cnt,
                "sixes": s_cnt,
                "boundary_runs": b_runs,
                "boundary_run_pct": round(b_runs / tot_runs * 100, 2),
            })

        # 5. Toss Decisions & Chasing Outcomes (All 1,243 Matches)
        toss_summary = []
        for s, grp in m_df.groupby("season"):
            decided = grp[grp["final_winner"].notna()]
            tw_won = (decided["toss_winner"] == decided["final_winner"]).sum()
            fld_choice = (grp["toss_decision"] == "field").sum()
            bat_choice = (grp["toss_decision"] == "bat").sum()
            
            # Chase win: winner == innings 2 batting team
            inn2_map = dict(zip(i_df[(i_df["innings"] == 2) & (i_df["season"] == s)]["match_id"], i_df[(i_df["innings"] == 2) & (i_df["season"] == s)]["batting_team"]))
            chase_w = sum(1 for mid, w in zip(decided["match_id"], decided["final_winner"]) if mid in inn2_map and inn2_map[mid] == w)
            
            toss_summary.append({
                "season": int(s),
                "matches": int(len(grp)),
                "decided_matches": int(len(decided)),
                "field_elected": int(fld_choice),
                "bat_elected": int(bat_choice),
                "toss_winner_match_win_pct": round(tw_won / len(decided) * 100, 1) if len(decided) > 0 else 0.0,
                "chasing_win_pct": round(chase_w / len(decided) * 100, 1) if len(decided) > 0 else 0.0,
            })

        # 6. Venue First-Innings Par Scoring (Min 10 Matches)
        venue_par = []
        for vname, grp in inn1.groupby("venue_canonical"):
            if len(grp) >= 10:
                venue_par.append({
                    "venue": vname,
                    "first_innings_count": int(len(grp)),
                    "mean_runs": round(float(grp["runs"].mean()), 2),
                    "median_runs": round(float(grp["runs"].median()), 1),
                    "min_runs": int(grp["runs"].min()),
                    "max_runs": int(grp["runs"].max()),
                })
        venue_par.sort(key=lambda x: -x["mean_runs"])

        # 7. Correlation Matrix (Runs, Wickets, Legal Balls, Boundaries, Season)
        inn1_corr = inn1[["match_id", "season", "runs", "wickets", "legal_balls"]].copy()
        inn1_boundaries = d_df[d_df["innings"] == 1].groupby("match_id").agg(
            fours=("is_four", "sum"),
            sixes=("is_six", "sum"),
        ).reset_index()
        inn1_corr = pd.merge(inn1_corr, inn1_boundaries, on="match_id", how="left").fillna(0)

        corr_vars = ["runs", "wickets", "legal_balls", "fours", "sixes", "season"]
        pearson_mat = inn1_corr[corr_vars].corr(method="pearson").round(3).to_dict()
        spearman_mat = inn1_corr[corr_vars].corr(method="spearman").round(3).to_dict()

        # 8. All-Time Dismissal Distribution (ordinary innings, from data/derived/dismissals.csv)
        dismissals = {
            k["kind"].replace(" ", "_"): k["count"] for k in dismissal_breakdown(self._dismissals)["kinds"]
        }

        # 9. Top All-Time Batters & Bowlers
        # Grouped by registry ID; the display name is one-to-one with the ID
        top_batters = self._batters_merged.groupby(["player_id", "batter"]).agg(
            runs=("runs", "sum"),
            innings=("match_id", "count"),
            fours=("fours", "sum"),
            sixes=("sixes", "sum"),
            scores_50=("reached_50", "sum"),
        ).sort_values("runs", ascending=False).head(10).reset_index().to_dict(orient="records")

        top_bowlers = self._bowler_matches.groupby(["bowler_id", "bowler"]).agg(
            wickets=("wickets", "sum"),
            innings=("match_id", "count"),
            legal_deliveries=("legal_balls", "sum"),
            runs_conceded=("runs_conceded", "sum"),
        ).reset_index().sort_values(
            ["wickets", "runs_conceded", "bowler"], ascending=[False, True, True]  # ties: fewer runs conceded first
        ).head(10).reset_index(drop=True)
        top_bowlers["economy"] = (top_bowlers["runs_conceded"] / (top_bowlers["legal_deliveries"] / 6.0)).round(2)
        top_bowlers_list = top_bowlers.to_dict(orient="records")

        seasons = sorted(int(s) for s in m_df["season"].unique())
        self._eda_full_history = {
            "coverage": (
                f"{format_season_ranges(seasons)} Complete Archive ({len(seasons)} Seasons, "
                f"{len(m_df):,} Matches, {len(d_df):,} Deliveries)"
            ),
            "season_evolution": season_evolution,
            "first_innings_trends": first_inn_trends,
            "era_phase_patterns": era_phase_patterns,
            "boundaries_by_season": boundaries_by_season,
            "toss_and_chasing": toss_summary,
            "venue_par": venue_par,
            "correlations": {
                "variables": corr_vars,
                "pearson": pearson_mat,
                "spearman": spearman_mat,
            },
            "dismissal_distribution": dismissals,
            "top_all_time_batters": top_batters,
            "top_all_time_bowlers": top_bowlers_list,
        }
        return self._eda_full_history


# Global singleton instance
canonical_engine = CanonicalAnalyticsEngine()
