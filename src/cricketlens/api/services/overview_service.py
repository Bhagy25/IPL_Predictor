"""Data service for the IPL Overview homepage: KPIs, coverage, notices, charts and team records.

Every number is computed from the canonical match data (data/processed and data/derived) through the
shared engine, with the same definitions as Team Analysis and Statistics & EDA. Nothing is read from
reports/ and there are no fallback numbers: if the data cannot load, the endpoints fail and the page
shows its unavailable state.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from cricketlens.api.services.canonical_data import (
    CHAMPION_RULE,
    PLAYER_DIRECTORY_DEFINITION,
    TEAM_DEFINITIONS,
    CanonicalAnalyticsEngine,
    DerivedDataUnavailable,
    canonical_engine,
    format_season_ranges,
    outcome_breakdown,
    percentage,
    result_summary,
)
from cricketlens.api.schemas import (
    KPIMetricItem,
    CoverageMetadata,
    OverviewSummaryResponse,
    MatchesPerSeasonItem,
    ScoringTrendItem,
    MatchResultDistributionItem,
    ScoringDistributionBin,
    TeamRecordItem,
    OverviewChartsResponse,
)

FIRST_INNINGS_ELIGIBILITY = (
    "Completed first innings only: an innings counts when it was followed by a second innings, was bowled out "
    "(10 wickets) or used all 120 legal balls. First innings cut short when the match was abandoned (no result) "
    "are excluded. Shortened innings that were completed, such as rain-reduced or D/L matches, are included."
)

# First-innings score bins: [low, high) runs, label and description
SCORE_BINS: List[Tuple[Optional[int], Optional[int], str, str]] = [
    (None, 120, "< 120", "Extreme bowler-dominated or rain-shortened innings"),
    (120, 150, "120–149", "Below-average / defensive bowling surfaces"),
    (150, 180, "150–179", "Historical average par score span"),
    (180, 210, "180–209", "Above-average scoring / modern high-tempo batting"),
    (210, None, "210+", "Explosive / record scores"),
]

TEAM_RECORDS_WINDOW_RULE = (
    "Comparative window: from the first season in which every current franchise played, to the season before "
    "the latest one (the latest season is the Stage 3 holdout)."
)


def _count_label(n: int, singular: str, plural_form: str) -> str:
    return f"{n:,} {singular if n == 1 else plural_form}"


def first_innings_eligibility(engine: CanonicalAnalyticsEngine) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Completed first innings (see FIRST_INNINGS_ELIGIBILITY) and the excluded ones, from innings.csv."""
    innings = engine._innings
    first = innings[innings["innings"] == 1]
    followed = first["match_id"].isin(innings.loc[innings["innings"] == 2, "match_id"])
    completed = followed | (first["wickets"] >= 10) | (first["legal_balls"] >= 120)
    return first[completed], first[~completed]


class OverviewService:
    def __init__(self, engine: Optional[CanonicalAnalyticsEngine] = None):
        self.engine = engine or canonical_engine
        self._summary_cache: Optional[OverviewSummaryResponse] = None
        self._charts_cache: Optional[OverviewChartsResponse] = None

    # ---------------------------------------------------------------- KPIs

    def _players_metric(self) -> Tuple[KPIMetricItem, bool]:
        """Player KPI from the same directory as Player Explorer; an unavailable directory is shown as such."""
        try:
            players = self.engine.player_directory_counts()["all"]
        except DerivedDataUnavailable:
            return KPIMetricItem(
                id="players", label="Players", value="—", numeric_value=None,
                statusText="Player data unavailable", iconName="User", description=PLAYER_DIRECTORY_DEFINITION,
            ), False
        return KPIMetricItem(
            id="players", label="Players", value=f"{players:,}", numeric_value=float(players),
            statusText="Batted or bowled", iconName="User", description=PLAYER_DIRECTORY_DEFINITION,
        ), True

    def _retired_hurt(self) -> Optional[int]:
        """Ordinary-innings retired-hurt events from data/derived/dismissals.csv; None when unavailable."""
        if self.engine.derived_status()["available"]:
            return int((self.engine._dismissals["kind"] == "retired hurt").sum())
        return None

    def _reconciled_matches(self) -> int:
        """Matches whose innings totals (runs, wickets, legal balls) equal the sums of their deliveries."""
        e = self.engine
        balls = e._deliveries.groupby(["match_id", "innings"]).agg(
            runs=("runs_total", "sum"), wickets=("team_wickets_on_ball", "sum"), legal_balls=("legal_delivery", "sum"),
        ).reset_index().astype({"match_id": "int64", "innings": "int64"})
        joined = e._innings[["match_id", "innings", "runs", "wickets", "legal_balls"]].astype(
            {"match_id": "int64", "innings": "int64"}
        ).merge(balls, on=["match_id", "innings"], how="left", suffixes=("", "_balls"))
        ok = (
            (joined["runs"] == joined["runs_balls"]) & (joined["wickets"] == joined["wickets_balls"])
            & (joined["legal_balls"] == joined["legal_balls_balls"])
        )
        bad = set(joined.loc[~ok, "match_id"])
        return int((~e._matches["match_id"].isin(bad)).sum())

    def _build_summary(self) -> Tuple[OverviewSummaryResponse, bool]:
        e = self.engine
        e.ensure_loaded()
        m, d = e._matches, e._deliveries
        seasons = sorted(int(s) for s in m["season"].unique())
        first, last = seasons[0], seasons[-1]
        span = format_season_ranges(seasons)
        complete = seasons == list(range(first, last + 1))
        matches = int(len(m))
        no_results = outcome_breakdown(m)["no_result"]
        deliveries = int(len(d))
        legal = int(d["legal_delivery"].sum())
        wides, noballs = int((d["wides"] > 0).sum()), int((d["noballs"] > 0).sum())
        runs = int(d["runs_total"].sum())
        wickets = int(d["team_wickets_on_ball"].sum())
        franchises = sorted(set(m["team1"]) | set(m["team2"]))
        latest = m[m["season"] == last]
        active = len(set(latest["team1"]) | set(latest["team2"]))
        venues = int(m["venue_canonical"].nunique())
        raw_venues = int(m["venue"].nunique())
        verified = percentage(self._reconciled_matches(), matches)
        retired_hurt = self._retired_hurt()
        so_matches = int((m["super_over_innings"] > 0).sum())
        so_innings = int(m["super_over_innings"].sum())
        players, players_ok = self._players_metric()

        metrics = [
            KPIMetricItem(
                id="seasons", label="Seasons covered", value=f"{len(seasons)}", numeric_value=float(len(seasons)),
                statusText=f"{span} complete" if complete else span, iconName="Trophy",
                description=f"All {len(seasons)} men's Indian Premier League tournament editions"
                            + ("." if complete else f" in the archive ({span})."),
            ),
            KPIMetricItem(
                id="matches", label="Matches analyzed", value=f"{matches:,}", numeric_value=float(matches),
                statusText=f"{verified:g}% verified", iconName="Eye",
                description=f"{matches:,} matches in the canonical Cricsheet archive, including "
                            f"{_count_label(no_results, 'no result', 'no results')}; {verified:g}% have innings totals "
                            "that reconcile with their ball-by-ball data.",
            ),
            KPIMetricItem(
                id="deliveries", label="Recorded deliveries", value=f"{deliveries:,}", numeric_value=float(deliveries),
                statusText=f"{legal:,} legal balls", iconName="Activity",
                description=f"{deliveries:,} ball events including {wides:,} wides and {noballs:,} no-balls; "
                            f"{legal:,} legal deliveries.",
            ),
            KPIMetricItem(
                id="teams", label="Teams", value=f"{len(franchises)}", numeric_value=float(len(franchises)),
                statusText=f"{active} active franchises", iconName="Shield",
                description=f"{active} active franchises (those that played in {last}) and {len(franchises) - active} "
                            "historical defunct teams with name renames consolidated.",
            ),
            players,
            KPIMetricItem(
                id="venues", label="Venues", value=f"{venues}", numeric_value=float(venues),
                statusText=f"{venues} canonical grounds", iconName="MapPin",
                description=f"{venues} canonical stadiums across India and overseas, normalized from {raw_venues} raw "
                            "naming strings.",
            ),
            KPIMetricItem(
                id="runs", label="Total runs", value=f"{runs:,}", numeric_value=float(runs),
                statusText="Ordinary innings", iconName="TrendingUp",
                description="Total team runs scored across all regular match innings (Super Overs excluded).",
            ),
            KPIMetricItem(
                id="wickets", label="Total wickets", value=f"{wickets:,}", numeric_value=float(wickets),
                statusText="Team wickets", iconName="Target",
                description="Total batting-team wickets lost; "
                            + (f"excludes {retired_hurt} recorded retired-hurt events." if retired_hurt is not None
                               else "retired-hurt events are excluded (count unavailable: derived tables missing)."),
            ),
        ]

        coverage = CoverageMetadata(
            first_match_date=str(m["date"].min()),
            last_match_date=str(m["date"].max()),
            seasons_count=len(seasons),
            seasons_span=span,
            total_matches=matches,
            gender="male",
            competition="Indian Premier League",
        )

        notices = [
            f"Recorded deliveries distinguish {deliveries:,} ball events from {legal:,} legal deliveries "
            "(wides and no-balls are illegal).",
            f"Total runs ({runs:,}) include extras and represent team totals from ordinary innings.",
            f"Wickets ({wickets:,}) represent batting-team losses; "
            + (f"{retired_hurt} retired hurt events are excluded per MCC law." if retired_hurt is not None
               else "retired hurt events are excluded per MCC law."),
            f"Super Over deliveries ({so_innings} innings across {so_matches} tied games) are excluded from ordinary "
            "innings aggregates.",
            "Franchise renames are standardized (Delhi Capitals, Punjab Kings, Royal Challengers Bengaluru). "
            "Discontinued clubs remain distinct.",
            f"IPL {last}, the latest season, was reserved as an unseen holdout for Stage 3 machine learning evaluation.",
        ]
        complete_summary = players_ok and retired_hurt is not None
        return OverviewSummaryResponse(metrics=metrics, coverage=coverage, notices=notices), complete_summary

    # ---------------------------------------------------------------- charts

    def _team_records(self) -> Tuple[List[TeamRecordItem], Dict[str, Any]]:
        """Records of the current franchises over the comparative window (see TEAM_RECORDS_WINDOW_RULE)."""
        e = self.engine
        m = e._matches
        last = int(m["season"].max())
        current = sorted(set(m.loc[m["season"] == last, "team1"]) | set(m.loc[m["season"] == last, "team2"]))
        start = max(e._franchise_seasons[t][0] for t in current)
        end = last - 1
        rows = e._team_rows[e._team_rows["season"].between(start, end)]
        champions = e.season_champions()
        records = []
        for team in current:
            r = result_summary(rows[rows["team"] == team])
            years = [c["season"] for c in champions if c["champion"] == team]
            records.append(TeamRecordItem(
                team=team,
                played=r["played"],
                wins=r["wins"],
                losses=r["losses"],
                tied_no_result=r["played"] - r["wins"] - r["losses"],
                win_pct=r["win_pct"],
                titles=len(years),
                title_years=years,
                status="Active",
            ))
        records.sort(key=lambda t: (t.win_pct is None, -(t.win_pct or 0), -t.played, t.team))
        window = {
            "first_season": start,
            "last_season": end,
            "label": f"{start}–{end}",
            "rule": TEAM_RECORDS_WINDOW_RULE,
            "win_pct_definition": TEAM_DEFINITIONS["win_pct"],
            "franchises": len(current),
        }
        return records, window

    def _build_charts(self) -> OverviewChartsResponse:
        e = self.engine
        e.ensure_loaded()
        m, inn, d = e._matches, e._innings, e._deliveries
        first_all = inn[inn["innings"] == 1]

        # Matches and scoring by season (scoring: every recorded first innings, as on Statistics & EDA)
        runs_by_season = d.groupby("season")["runs_total"].sum()
        matches_per_season, scoring_trends = [], []
        for season, g in m.groupby("season"):
            fi = first_all[first_all["season"] == season]["runs"]
            matches_per_season.append(MatchesPerSeasonItem(
                season=int(season), matches=int(len(g)), teams=len(set(g["team1"]) | set(g["team2"])),
            ))
            scoring_trends.append(ScoringTrendItem(
                season=int(season),
                avg_first_innings_runs=round(float(fi.mean()), 1),
                median_first_innings_runs=round(float(fi.median()), 1),
                total_runs=int(runs_by_season.get(season, 0)),
            ))
        means = pd.Series({t.season: t.avg_first_innings_runs for t in scoring_trends})
        exact_means = first_all.groupby("season")["runs"].mean()
        slope = float(np.polyfit(exact_means.index.to_numpy(dtype=float), exact_means.to_numpy(), 1)[0])
        peak = int(means.idxmax())
        trend = {
            "first_innings": int(len(first_all)),
            "overall_mean": round(float(first_all["runs"].mean()), 1),
            "slope_runs_per_season": round(slope, 2),
            "seasons_label": format_season_ranges([int(s) for s in exact_means.index]),
            "peak_season": peak,
            "peak_mean": float(means[peak]),
            "definition": "Mean and median of every recorded first innings per season; the trend is an ordinary "
                          "least-squares line through the season means (observational, not causal).",
        }

        # Results: the shared Team Analysis / EDA outcome breakdown
        oc = outcome_breakdown(m)
        result_distribution = [
            MatchResultDistributionItem(
                category="Regulation Win", count=oc["decided_in_regulation"],
                percentage=round(100 * oc["decided_in_regulation"] / oc["matches"], 2),
                description=f"Decided in regulation by runs or wickets, including {oc['dl_method']} by the D/L method",
            ),
            MatchResultDistributionItem(
                category="Tie (Super Over)", count=oc["decided_by_super_over"],
                percentage=round(100 * oc["decided_by_super_over"] / oc["matches"], 2),
                description="Tied in regulation; settled by one-over eliminator",
            ),
            MatchResultDistributionItem(
                category="No Result", count=oc["no_result"],
                percentage=round(100 * oc["no_result"] / oc["matches"], 2),
                description="Abandoned or rain interruption without reaching DLS minimum",
            ),
        ]
        if oc["other_not_recorded"]:
            result_distribution.append(MatchResultDistributionItem(
                category="Not recorded", count=oc["other_not_recorded"],
                percentage=round(100 * oc["other_not_recorded"] / oc["matches"], 2),
                description="No result type recorded in the source",
            ))
        outcomes = {**oc, "decided_pct": percentage(oc["decided"], oc["matches"])}

        # First-innings score distribution over completed first innings
        eligible, excluded = first_innings_eligibility(e)
        runs = eligible["runs"]
        n = int(len(runs))
        median, top = float(runs.median()), int(runs.max())
        scoring_distribution = []
        for low, high, span, text in SCORE_BINS:
            mask = pd.Series(True, index=runs.index)
            if low is not None:
                mask &= runs >= low
            if high is not None:
                mask &= runs < high
            count = int(mask.sum())
            in_bin = lambda v, low=low, high=high: (low is None or v >= low) and (high is None or v < high)  # noqa: E731
            notes = [f"median {median:g}"] * in_bin(median) + [f"max {top}"] * in_bin(top)
            scoring_distribution.append(ScoringDistributionBin(
                span=span, count=count, percentage=percentage(count, n) or 0.0,
                description=text + (f" ({', '.join(notes)})" if notes else ""),
            ))
        modal = max(scoring_distribution, key=lambda b: b.count)
        scoring_summary = {
            "n": n,
            "first_innings_recorded": int(len(first_all)),
            "eligibility_rule": FIRST_INNINGS_ELIGIBILITY,
            "excluded": [
                {
                    "match_id": int(r.match_id), "date": str(r.date),
                    "season": int(r.season), "batting_team": str(r.batting_team), "runs": int(r.runs),
                    "wickets": int(r.wickets), "legal_balls": int(r.legal_balls),
                    "reason": "No result: abandoned during the first innings, which was not completed",
                }
                for r in excluded.sort_values(["date", "match_id"]).itertuples()
            ],
            "mean": round(float(runs.mean()), 1),
            "median": median,
            "q1": float(runs.quantile(0.25)),
            "q3": float(runs.quantile(0.75)),
            "min": int(runs.min()),
            "max": top,
            "modal_span": modal.span,
            "modal_pct": modal.percentage,
        }

        team_records, window = self._team_records()
        return OverviewChartsResponse(
            matches_per_season=matches_per_season,
            scoring_trends=scoring_trends,
            scoring_trend=trend,
            result_distribution=result_distribution,
            outcomes=outcomes,
            scoring_distribution=scoring_distribution,
            scoring_summary=scoring_summary,
            team_records=team_records,
            team_records_window=window,
            champions=e.season_champions(),
            champion_rule=CHAMPION_RULE,
        )

    # ---------------------------------------------------------------- API

    def get_summary(self) -> OverviewSummaryResponse:
        """The 8 KPI cards, coverage and notices, computed from the match data."""
        if self._summary_cache is None:
            summary, complete = self._build_summary()
            if not complete:
                return summary  # rebuilt on the next request once the derived tables are available
            self._summary_cache = summary
        return self._summary_cache

    def get_charts(self) -> OverviewChartsResponse:
        """The chart datasets, champions and team records, computed from the match data."""
        if self._charts_cache is None:
            self._charts_cache = self._build_charts()
        return self._charts_cache


# Global singleton instance
overview_service = OverviewService()
