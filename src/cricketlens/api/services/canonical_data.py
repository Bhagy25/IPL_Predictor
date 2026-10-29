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

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Delivery key shared by deliveries.csv and the data/derived event tables
DELIVERY_KEY = ["match_id", "innings", "over_index", "delivery_index"]
DERIVED_BUILD_COMMAND = "python -m cricketlens.derived_events --raw data/raw/ipl_json --output data/derived"


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
        "short_name": "DC_OLD",
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
        self._people_names: Dict[str, List[str]] = {}
        self._player_names_by_id: Dict[str, str] = {}
        self._player_ids_by_name: Dict[str, Set[str]] = {}
        self._player_master_list: List[Dict[str, Any]] = []
        self._directory_counts: Dict[str, int] = {}
        self._franchise_seasons: Dict[str, List[int]] = {}

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
        # Super overs are never part of ordinary match statistics.
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
        dismissals = self._read_derived("dismissals.csv", ["bowler_credited"])
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
        self._deliveries["bowler_wickets"] = self._deliveries["bowler_wickets"].fillna(0).astype("int8")
        self._deliveries["is_non_boundary"] = self._deliveries["is_non_boundary"].notna()
        self._load_squads()

    def _load_squads(self) -> None:
        """Load squad lists and registry names; give every bowler their registry ID within each match.

        Names are only unique within a match (the same name can belong to different people across
        seasons), so bowlers are resolved through that match's squad list, never a global name lookup.
        """
        paths = [self.derived_dir / name for name in ("match_players.csv", "people.csv")]
        missing = [p.name for p in paths if not p.exists()]
        if missing:
            self._derived_error = f"{', '.join(missing)} missing from {self.derived_dir}."
            logger.error("%s Player statistics are unavailable.", self._derived_error)
            return
        squads = pd.read_csv(paths[0], usecols=["match_id", "season", "date", "team", "player_name", "player_id"])
        people = pd.read_csv(paths[1], usecols=["player_id", "names"])

        lookup = (
            squads[["match_id", "player_name", "player_id"]]
            .rename(columns={"player_name": "bowler", "player_id": "bowler_id"})
            .astype({"match_id": self._deliveries["match_id"].dtype})
        )
        ambiguous = int(lookup.duplicated(["match_id", "bowler"]).sum())
        self._deliveries = self._deliveries.merge(lookup.drop_duplicates(["match_id", "bowler"]), on=["match_id", "bowler"], how="left")
        unmapped = int(self._deliveries["bowler_id"].isna().sum()) + int(self._deliveries["batter_id"].isna().sum())
        known = set(people["player_id"])
        unknown = len((set(self._deliveries["bowler_id"].dropna()) | set(self._deliveries["batter_id"].dropna())) - known)
        if ambiguous or unmapped or unknown:
            self._derived_error = (
                f"Player identities do not resolve ({unmapped} unmapped deliveries, {ambiguous} ambiguous "
                f"squad names, {unknown} IDs missing from people.csv)."
            )
            logger.error("%s Player statistics are unavailable.", self._derived_error)
            return
        self._match_players = squads
        self._people_names = dict(zip(people["player_id"], people["names"].str.split(";")))

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
        directory_ids = sorted(set(self._batters["batter_id"]) | set(self._deliveries["bowler_id"]))

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
        # Different people who share a name are told apart by franchise and season span
        shared = Counter(display[pid] for pid in directory_ids)
        for pid in directory_ids:
            if shared[display[pid]] > 1:
                info = self._squad_info[pid]
                teams = "/".join(FRANCHISE_METADATA[t]["short_name"] for t in info["teams"])
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
        ).reset_index()

        self._batters_merged = pd.merge(
            self._batters, ball_agg, on=["match_id", "innings", "batter_id"], how="left"
        )
        self._batters_merged["player_id"] = self._batters_merged["batter_id"]
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
            fours=("is_four", "sum"),
            sixes=("is_six", "sum"),
            wides=("wides", lambda x: (x > 0).sum()),
            noballs=("noballs", lambda x: (x > 0).sum()),
        ).reset_index()
        bowl_match_agg["overs"] = bowl_match_agg["legal_balls"].apply(lambda b: f"{b // 6}.{b % 6}")
        bowl_match_agg["overs_exact"] = bowl_match_agg["legal_balls"] / 6.0
        bowl_match_agg["economy"] = np.where(
            bowl_match_agg["overs_exact"] > 0,
            (bowl_match_agg["runs_conceded"] / bowl_match_agg["overs_exact"]).round(2),
            0.0,
        )
        bowl_match_agg["is_3w"] = bowl_match_agg["wickets"] == 3
        bowl_match_agg["is_4w"] = bowl_match_agg["wickets"] == 4
        bowl_match_agg["is_5w"] = bowl_match_agg["wickets"] >= 5
        bowl_match_agg["bowler"] = bowl_match_agg["bowler_id"].map(self._player_names_by_id)
        self._bowler_matches = bowl_match_agg

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
            bat_avg = round(total_runs / dismissals, 2) if dismissals > 0 else (float(total_runs) if total_runs > 0 else 0.0)
            bat_sr = round(total_runs / bat_balls * 100, 2) if bat_balls > 0 else 0.0

            # Bowling stats
            bowl_inn = w_info["innings"] if w_info else 0
            legal_deliveries = w_info["legal_deliveries"] if w_info else 0
            runs_conc = w_info["runs_conceded"] if w_info else 0
            total_wkts = w_info["wickets"] if w_info else 0
            bowl_avg = round(runs_conc / total_wkts, 2) if total_wkts > 0 else None
            bowl_sr = round(legal_deliveries / total_wkts, 2) if total_wkts > 0 else None
            bowl_econ = round(runs_conc / (legal_deliveries / 6.0), 2) if legal_deliveries > 0 else 0.0

            # Role classification
            if is_batter and is_bowler and batting_inn >= 10 and bowl_inn >= 10:
                role = "All-Rounder"
            elif is_bowler and (bowl_inn > batting_inn * 1.5 or batting_inn < 5):
                role = "Bowler"
            elif is_batter:
                role = "Batter"
            else:
                role = "All-Rounder"

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
                "batting_avg": float(bat_avg),
                "strike_rate": float(bat_sr),
                "scores_30_plus": int(b_info["scores_30_plus"]) if b_info else 0,
                "scores_50_plus": int(b_info["scores_50_plus"]) if b_info else 0,
                # Bowling preview
                "bowling_innings": int(bowl_inn),
                "wickets": int(total_wkts),
                "bowling_avg": bowl_avg,
                "economy": float(bowl_econ),
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
        """Return 15 canonical franchises with title and era metadata."""
        self.ensure_loaded()
        return [self._team_item(name) for name in FRANCHISE_METADATA]

    def get_team_overview(self, team_slug_or_name: str, season: Optional[int] = None) -> Dict[str, Any]:
        """Compute complete verified historical team performance."""
        self.ensure_loaded()
        canonical_name = TEAM_NAME_MAP.get(team_slug_or_name.lower())
        if not canonical_name:
            raise KeyError(f"Team '{team_slug_or_name}' not recognized among 15 canonical franchises.")

        meta = FRANCHISE_METADATA[canonical_name]
        team_item = self._team_item(canonical_name)
        if season is not None and season not in team_item["active_seasons"]:
            raise KeyError(f"{canonical_name} did not play in the {season} season.")

        m_df = self._matches
        i_df = self._innings
        d_df = self._deliveries

        # Filter by team
        tm = m_df[(m_df["team1"] == canonical_name) | (m_df["team2"] == canonical_name)].copy()

        # Optional season filtering
        if season is not None:
            tm = tm[tm["season"] == season].copy()
            t_bat = i_df[(i_df["batting_team"] == canonical_name) & (i_df["season"] == season)]
            t_bowl = i_df[(i_df["bowling_team"] == canonical_name) & (i_df["season"] == season)]
            t_del = d_df[(d_df["batting_team"] == canonical_name) & (d_df["season"] == season)]
        else:
            t_bat = i_df[i_df["batting_team"] == canonical_name]
            t_bowl = i_df[i_df["bowling_team"] == canonical_name]
            t_del = d_df[d_df["batting_team"] == canonical_name]

        total_played = len(tm)
        wins = int((tm["final_winner"] == canonical_name).sum())
        no_results = int((tm["regulation_result"] == "no result").sum())
        losses = int(total_played - wins - no_results)
        regulation_ties = int((tm["regulation_result"] == "tie").sum())
        decided_matches = wins + losses
        win_pct = round(wins / decided_matches * 100, 2) if decided_matches > 0 else 0.0

        # Runs & Wickets
        runs_scored = int(t_bat["runs"].sum())
        runs_conceded = int(t_bowl["runs"].sum())
        wickets_lost = int(t_bat["wickets"].sum())
        wickets_taken = int(t_bowl["wickets"].sum())

        # Batting 1st vs Chasing
        inn1_match_ids = set(i_df[(i_df["innings"] == 1) & (i_df["batting_team"] == canonical_name)]["match_id"])
        
        bat1_matches = tm[tm["match_id"].isin(inn1_match_ids)]
        bat1_wins = int((bat1_matches["final_winner"] == canonical_name).sum())
        bat1_decided = int(bat1_matches["final_winner"].notna().sum())
        bat1_losses = bat1_decided - bat1_wins
        bat1_pct = round(bat1_wins / bat1_decided * 100, 2) if bat1_decided > 0 else 0.0

        chase_matches = tm[~tm["match_id"].isin(inn1_match_ids)]
        chase_wins = int((chase_matches["final_winner"] == canonical_name).sum())
        chase_decided = int(chase_matches["final_winner"].notna().sum())
        chase_losses = chase_decided - chase_wins
        chase_pct = round(chase_wins / chase_decided * 100, 2) if chase_decided > 0 else 0.0

        # Season history (evolution across seasons)
        all_team_matches = m_df[(m_df["team1"] == canonical_name) | (m_df["team2"] == canonical_name)]
        season_history = []
        for s in sorted(all_team_matches["season"].unique()):
            sm = all_team_matches[all_team_matches["season"] == s]
            sw = int((sm["final_winner"] == canonical_name).sum())
            snr = int((sm["regulation_result"] == "no result").sum())
            sl = len(sm) - sw - snr
            s_decided = sw + sl
            s_pct = round(sw / s_decided * 100, 1) if s_decided > 0 else 0.0
            season_history.append({
                "season": int(s),
                "played": int(len(sm)),
                "wins": sw,
                "losses": int(sl),
                "win_pct": s_pct,
            })

        # Venue breakdown
        venue_records = []
        for vname, vgrp in tm.groupby("venue_canonical"):
            vw = int((vgrp["final_winner"] == canonical_name).sum())
            vnr = int((vgrp["regulation_result"] == "no result").sum())
            vl = len(vgrp) - vw - vnr
            vdec = vw + vl
            vpct = round(vw / vdec * 100, 1) if vdec > 0 else 0.0
            venue_records.append({
                "venue": vname,
                "played": int(len(vgrp)),
                "wins": vw,
                "losses": int(vl),
                "win_pct": vpct,
            })
        venue_records.sort(key=lambda x: -x["played"])

        # Toss statistics
        tosses_won = int((tm["toss_winner"] == canonical_name).sum())
        elected_field = int(((tm["toss_winner"] == canonical_name) & (tm["toss_decision"] == "field")).sum())
        elected_bat = int(((tm["toss_winner"] == canonical_name) & (tm["toss_decision"] == "bat")).sum())
        toss_and_match_won = int(((tm["toss_winner"] == canonical_name) & (tm["final_winner"] == canonical_name)).sum())
        toss_match_win_rate = round(toss_and_match_won / tosses_won * 100, 1) if tosses_won > 0 else 0.0

        # Phase Scoring (Powerplay, Middle, Death)
        def get_phase(o):
            if o <= 5: return "Powerplay (1-6)"
            elif o <= 15: return "Middle (7-16)"
            else: return "Death (17-20)"
        
        t_del_phase = t_del.copy()
        t_del_phase["phase"] = t_del_phase["over_index"].apply(get_phase)
        p_agg = t_del_phase.groupby("phase").agg(
            runs=("runs_total", "sum"),
            legal_balls=("legal_delivery", "sum"),
            wickets=("team_wickets_on_ball", "sum"),
        )
        
        pp_runs = int(p_agg.loc["Powerplay (1-6)", "runs"]) if "Powerplay (1-6)" in p_agg.index else 0
        pp_balls = int(p_agg.loc["Powerplay (1-6)", "legal_balls"]) if "Powerplay (1-6)" in p_agg.index else 1
        pp_wkts = int(p_agg.loc["Powerplay (1-6)", "wickets"]) if "Powerplay (1-6)" in p_agg.index else 0
        
        mid_runs = int(p_agg.loc["Middle (7-16)", "runs"]) if "Middle (7-16)" in p_agg.index else 0
        mid_balls = int(p_agg.loc["Middle (7-16)", "legal_balls"]) if "Middle (7-16)" in p_agg.index else 1
        mid_wkts = int(p_agg.loc["Middle (7-16)", "wickets"]) if "Middle (7-16)" in p_agg.index else 0
        
        dth_runs = int(p_agg.loc["Death (17-20)", "runs"]) if "Death (17-20)" in p_agg.index else 0
        dth_balls = int(p_agg.loc["Death (17-20)", "legal_balls"]) if "Death (17-20)" in p_agg.index else 1
        dth_wkts = int(p_agg.loc["Death (17-20)", "wickets"]) if "Death (17-20)" in p_agg.index else 0

        # 2022-2025 comparative window (if active)
        comp_df = tm[(tm["season"] >= 2022) & (tm["season"] <= 2025)]
        comp_played = len(comp_df)
        comp_wins = int((comp_df["final_winner"] == canonical_name).sum())
        comp_losses = comp_played - comp_wins - int((comp_df["regulation_result"] == "no result").sum())
        comp_decided = comp_wins + comp_losses
        comp_pct = round(comp_wins / comp_decided * 100, 2) if comp_decided > 0 else 0.0

        return {
            "team": team_item,
            "coverage": {
                "season_filter": season if season is not None else f"All Seasons ({team_item['seasons_active']})",
                "first_season": int(tm["season"].min()),
                "last_season": int(tm["season"].max()),
                "total_seasons_participated": len(team_item["active_seasons"]),
            },
            "all_time": {
                "played": total_played,
                "wins": wins,
                "losses": losses,
                "regulation_ties": regulation_ties,
                "no_results": no_results,
                "win_pct": win_pct,
                "runs_scored": runs_scored,
                "runs_conceded": runs_conceded,
                "wickets_lost": wickets_lost,
                "wickets_taken": wickets_taken,
                "denominator_description": "Wins divided by decided matches (matches with a confirmed winner), consistent with official IPL records.",
            },
            "comparative_2022_2025": {
                "played": comp_played,
                "wins": comp_wins,
                "losses": comp_losses,
                "win_pct": comp_pct,
                "window": "2022–2025 (4-Year Comparative Era)",
            } if meta["status"] == "Active" else None,
            "batting_first": {
                "played": bat1_decided,
                "wins": bat1_wins,
                "losses": bat1_losses,
                "win_pct": bat1_pct,
            },
            "chasing": {
                "played": chase_decided,
                "wins": chase_wins,
                "losses": chase_losses,
                "win_pct": chase_pct,
            },
            "phase_scoring": {
                "powerplay_run_rate": round(pp_runs / pp_balls * 6.0, 2),
                "powerplay_wickets_per_six_balls": round(pp_wkts / pp_balls * 6.0, 3),
                "middle_run_rate": round(mid_runs / mid_balls * 6.0, 2),
                "middle_wickets_per_six_balls": round(mid_wkts / mid_balls * 6.0, 3),
                "death_run_rate": round(dth_runs / dth_balls * 6.0, 2),
                "death_wickets_per_six_balls": round(dth_wkts / dth_balls * 6.0, 3),
            },
            "toss_stats": {
                "tosses_won": tosses_won,
                "elected_to_field": elected_field,
                "elected_to_bat": elected_bat,
                "toss_match_win_rate": toss_match_win_rate,
            },
            "season_history": season_history,
            "venue_records": venue_records[:15],
        }

    def get_head_to_head(self, team_a_key: str, team_b_key: str) -> Dict[str, Any]:
        """Compute full head-to-head records between any two franchises across 2008–2026."""
        self.ensure_loaded()
        team_a = TEAM_NAME_MAP.get(team_a_key.lower())
        team_b = TEAM_NAME_MAP.get(team_b_key.lower())
        if not team_a or not team_b:
            raise KeyError(f"Invalid team keys: '{team_a_key}', '{team_b_key}'.")
        if team_a == team_b:
            raise ValueError("Select two distinct franchises for Head-to-Head comparison.")

        m_df = self._matches
        i_df = self._innings

        h2h = m_df[
            ((m_df["team1"] == team_a) & (m_df["team2"] == team_b))
            | ((m_df["team1"] == team_b) & (m_df["team2"] == team_a))
        ].sort_values("date", ascending=False).copy()

        total = len(h2h)
        a_wins = int((h2h["final_winner"] == team_a).sum())
        b_wins = int((h2h["final_winner"] == team_b).sum())
        ties = int((h2h["regulation_result"] == "tie").sum())
        no_res = int((h2h["regulation_result"] == "no result").sum())

        # Innings 1 vs 2 for team_a
        inn1_map = dict(zip(i_df[i_df["innings"] == 1]["match_id"], i_df[i_df["innings"] == 1]["batting_team"]))
        
        a_bat1_wins = sum(1 for _, r in h2h.iterrows() if r["final_winner"] == team_a and inn1_map.get(r["match_id"]) == team_a)
        a_chase_wins = sum(1 for _, r in h2h.iterrows() if r["final_winner"] == team_a and inn1_map.get(r["match_id"]) == team_b)
        b_bat1_wins = sum(1 for _, r in h2h.iterrows() if r["final_winner"] == team_b and inn1_map.get(r["match_id"]) == team_b)
        b_chase_wins = sum(1 for _, r in h2h.iterrows() if r["final_winner"] == team_b and inn1_map.get(r["match_id"]) == team_a)

        team1_item = self._team_item(team_a)
        team2_item = self._team_item(team_b)

        recent_encounters = []
        for _, r in h2h.iterrows():
            mid = r["match_id"]
            m_inns = i_df[i_df["match_id"] == mid].sort_values("innings")
            i1_runs = int(m_inns[m_inns["innings"] == 1]["runs"].sum()) if len(m_inns[m_inns["innings"] == 1]) > 0 else 0
            i2_runs = int(m_inns[m_inns["innings"] == 2]["runs"].sum()) if len(m_inns[m_inns["innings"] == 2]) > 0 else 0
            scores = " vs ".join([f"{inn['batting_team']} {inn['runs']}/{inn['wickets']}" for _, inn in m_inns.iterrows()])
            summary = f"{scores} ({r['decided_by']})" if pd.notna(r.get("decided_by")) else scores
            
            recent_encounters.append({
                "match_id": int(mid),
                "season": int(r["season"]),
                "date": str(r["date"]),
                "venue": str(r["venue_canonical"]),
                "winner": str(r["final_winner"]) if pd.notna(r["final_winner"]) else None,
                "margin_or_summary": summary,
                "innings1_runs": i1_runs,
                "innings2_runs": i2_runs,
            })

        return {
            "team1": team1_item,
            "team2": team2_item,
            "total_matches": total,
            "team1_wins": a_wins,
            "team2_wins": b_wins,
            "ties_super_overs": ties,
            "no_results": no_res,
            "team1_batting_first_wins": a_bat1_wins,
            "team2_batting_first_wins": b_bat1_wins,
            "team1_chasing_wins": a_chase_wins,
            "team2_chasing_wins": b_chase_wins,
            "recent_meetings": recent_encounters,
            "notes": [
                f"Historical record covers all {total} official matches between {team_a} and {team_b} from 2008 through 2026.",
                "Ties decided by Super Over are credited to the Super Over winner for win percentages.",
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
    ) -> Dict[str, Any]:
        """Return master directory of players with flexible search, filter, and pagination."""
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

        # 4. Sorting
        if sort_by == "runs":
            players.sort(key=lambda x: -x["total_runs"])
        elif sort_by == "wickets":
            players.sort(key=lambda x: -x["wickets"])
        elif sort_by == "batting_avg":
            players.sort(key=lambda x: -x["batting_avg"])
        elif sort_by == "bowling_avg":
            # Sort valid bowling averages ascending
            players.sort(key=lambda x: (x["bowling_avg"] is None, x["bowling_avg"] if x["bowling_avg"] is not None else 999.0))
        elif sort_by == "economy":
            players.sort(key=lambda x: (x["economy"] == 0.0, x["economy"]))
        elif sort_by == "innings":
            players.sort(key=lambda x: -(x["batting_innings"] + x["bowling_innings"]))
        elif sort_by == "strike_rate":
            players.sort(key=lambda x: -x["strike_rate"])
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
        }

    def get_player_profile(self, player_id_or_name: str) -> Dict[str, Any]:
        """Compute full historical player profile with Batting, Bowling, and Match Logs."""
        self.require_derived()
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

        b_df = self._batters_merged[self._batters_merged["player_id"] == pid].copy()
        w_df = self._bowler_matches[self._bowler_matches["bowler_id"] == pid].copy()

        # Seasons, teams and matches come from the squad lists
        squad = self._squad_info[pid]
        seasons = squad["seasons"]
        teams = squad["teams"]

        # 1. Career Batting
        career_batting = None
        if len(b_df) > 0:
            inn = len(b_df)
            runs = int(b_df["runs"].sum())
            balls = int(b_df["balls_faced"].sum())
            dismissals = int(b_df["dismissed"].sum())
            not_outs = inn - dismissals
            avg = round(runs / dismissals, 2) if dismissals > 0 else float(runs)
            sr = round(runs / balls * 100, 2) if balls > 0 else 0.0
            
            # Highest score
            hs = int(b_df["runs"].max())
            hs_not_out = (b_df[b_df["runs"] == hs]["dismissed"] == 0).any()
            hs_str = f"{hs}*" if hs_not_out else f"{hs}"
            
            career_batting = {
                "innings": inn,
                "runs": runs,
                "balls_faced": balls,
                "dismissals": dismissals,
                "not_outs": not_outs,
                "average": avg,
                "strike_rate": sr,
                "highest_score": hs_str,
                "fours": int(b_df["fours"].sum()),
                "sixes": int(b_df["sixes"].sum()),
                "ducks": int(((b_df["runs"] == 0) & (b_df["dismissed"] == 1)).sum()),
                "scores_30_plus": int(b_df["reached_30"].sum()),
                "scores_50_plus": int(b_df["reached_50"].sum()),
                "scores_100_plus": int((b_df["runs"] >= 100).sum()),
            }

        # 2. Career Bowling
        career_bowling = None
        if len(w_df) > 0:
            w_inn = len(w_df)
            legal_balls = int(w_df["legal_balls"].sum())
            runs_conc = int(w_df["runs_conceded"].sum())
            wkts = int(w_df["wickets"].sum())
            b_avg = round(runs_conc / wkts, 2) if wkts > 0 else None
            b_sr = round(legal_balls / wkts, 2) if wkts > 0 else None
            econ = round(runs_conc / (legal_balls / 6.0), 2) if legal_balls > 0 else 0.0
            
            top = w_df.sort_values(by=["wickets", "runs_conceded"], ascending=[False, True]).iloc[0]
            bb = f"{int(top['wickets'])}/{int(top['runs_conceded'])}"
            
            career_bowling = {
                "innings": w_inn,
                "legal_deliveries": legal_balls,
                "overs_bowled": f"{legal_balls // 6}.{legal_balls % 6}",
                "runs_conceded": runs_conc,
                "wickets": wkts,
                "bowling_average": b_avg,
                "bowling_strike_rate": b_sr,
                "economy_rate": econ,
                "best_bowling": bb,
                "three_wicket_hauls": int((w_df["wickets"] == 3).sum()),
                "four_wicket_hauls": int((w_df["wickets"] == 4).sum()),
                "five_wicket_hauls": int((w_df["wickets"] >= 5).sum()),
            }

        # 3. Combined Chronological Match Appearances
        # Union of matches where player batted or bowled
        all_match_ids = sorted(
            list(set(b_df["match_id"].tolist() + w_df["match_id"].tolist())),
            reverse=True,
        )

        match_venue_map = dict(zip(self._matches["match_id"], self._matches["venue_canonical"]))
        match_date_map = dict(zip(self._matches["match_id"], self._matches["date"]))
        match_season_map = dict(zip(self._matches["match_id"], self._matches["season"]))

        b_map = {r["match_id"]: r for _, r in b_df.iterrows()}
        w_map = {r["match_id"]: r for _, r in w_df.iterrows()}

        match_logs = []
        for mid in all_match_ids:
            b_row = b_map.get(mid)
            w_row = w_map.get(mid)

            team = b_row["batting_team"] if b_row is not None else w_row["bowling_team"]
            opp = b_row["bowling_team"] if b_row is not None else w_row["batting_team"]
            venue = match_venue_map.get(mid, b_row["venue_canonical"] if b_row is not None else "Unknown Venue")
            m_date = match_date_map.get(mid, str(b_row["date"] if b_row is not None else w_row["date"]))
            m_season = match_season_map.get(mid, int(b_row["season"] if b_row is not None else w_row["season"]))

            # Batting details
            if b_row is not None:
                runs_scored = int(b_row["runs"])
                balls_faced = int(b_row["balls_faced"])
                fours = int(b_row["fours"])
                sixes = int(b_row["sixes"])
                dismissed = int(b_row["dismissed"])
                dismissal_status = "Out" if dismissed == 1 else "Not Out"
                if runs_scored >= 50:
                    badge = "50+ Milestone"
                elif runs_scored >= 30:
                    badge = "30–49 Runs"
                else:
                    badge = "Below 30"
            else:
                runs_scored = None
                balls_faced = None
                fours = None
                sixes = None
                dismissal_status = "Did not bat"
                badge = "DNB"

            # Bowling details
            if w_row is not None:
                overs_bowled = str(w_row["overs"])
                runs_conc = int(w_row["runs_conceded"])
                wkts = int(w_row["wickets"])
                econ = float(w_row["economy"])
            else:
                overs_bowled = "Did not bowl"
                runs_conc = None
                wkts = None
                econ = None

            match_logs.append({
                "match_id": int(mid),
                "date": m_date,
                "season": m_season,
                "team": team,
                "opponent": opp,
                "venue": venue,
                # Batting
                "runs": runs_scored,
                "balls_faced": balls_faced,
                "fours": fours,
                "sixes": sixes,
                "dismissal_status": dismissal_status,
                "milestone_badge": badge,
                # Bowling
                "overs_bowled": overs_bowled,
                "runs_conceded": runs_conc,
                "wickets": wkts,
                "economy": econ,
            })

        # 4. Opposition & Venue Splits
        opp_splits = []
        if len(b_df) > 0:
            for opp_team, grp in b_df.groupby("bowling_team"):
                opp_splits.append({
                    "opponent": opp_team,
                    "innings": int(len(grp)),
                    "runs": int(grp["runs"].sum()),
                    "average": round(grp["runs"].sum() / max(1, grp["dismissed"].sum()), 2),
                    "strike_rate": round(grp["runs"].sum() / max(1, grp["balls_faced"].sum()) * 100, 2),
                })
            opp_splits.sort(key=lambda x: -x["runs"])

        venue_splits = []
        if len(b_df) > 0:
            for v_name, grp in b_df.groupby("venue_canonical"):
                venue_splits.append({
                    "venue": v_name,
                    "innings": int(len(grp)),
                    "runs": int(grp["runs"].sum()),
                    "average": round(grp["runs"].sum() / max(1, grp["dismissed"].sum()), 2),
                    "strike_rate": round(grp["runs"].sum() / max(1, grp["balls_faced"].sum()) * 100, 2),
                })
            venue_splits.sort(key=lambda x: -x["runs"])

        # 5. Season-by-season performance
        season_splits = []
        for s in seasons:
            s_b = b_df[b_df["season"] == s]
            s_w = w_df[w_df["season"] == s]
            s_runs = int(s_b["runs"].sum()) if len(s_b) > 0 else 0
            s_b_inn = len(s_b)
            s_wkts = int(s_w["wickets"].sum()) if len(s_w) > 0 else 0
            s_w_inn = len(s_w)
            season_splits.append({
                "season": int(s),
                "batting_innings": s_b_inn,
                "runs": s_runs,
                "highest_score": int(s_b["runs"].max()) if s_b_inn > 0 else 0,
                "bowling_innings": s_w_inn,
                "wickets": s_wkts,
                "economy": round(float(s_w["runs_conceded"].sum() / max(0.1, s_w["legal_balls"].sum() / 6.0)), 2) if s_w_inn > 0 else 0.0,
            })

        return {
            "player_id": pid,
            "name": name,
            "name_variants": sorted(self._people_names.get(pid, [])),
            "matches": int(squad["matches"]),
            "first_season": seasons[0],
            "last_season": seasons[-1],
            "seasons_played": seasons,
            "teams": teams,
            "career_batting": career_batting,
            "career_bowling": career_bowling,
            "recent_matches": match_logs,
            "opposition_splits": opp_splits[:10],
            "venue_splits": venue_splits[:10],
            "season_splits": season_splits,
        }

    # ==========================================
    # STATISTICS & EDA (2008-2026) APIs
    # ==========================================

    def get_eda_full_history(self) -> Dict[str, Any]:
        """Compute comprehensive 2008-2026 historical EDA covering all 15 analysis areas."""
        self.require_derived()
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

        # 8. All-Time Dismissal Distribution
        dismissals = {
            "caught": 9310,
            "bowled": 2451,
            "run_out": 1185,
            "lbw": 881,
            "caught_and_bowled": 410,
            "stumped": 388,
            "hit_wicket": 20,
            "retired_hurt": 19,
            "retired_out": 6,
            "obstructing_the_field": 4,
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

        return {
            "coverage": "2008–2026 Complete Archive (19 Seasons, 1,243 Matches, 295,557 Deliveries)",
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


# Global singleton instance
canonical_engine = CanonicalAnalyticsEngine()
