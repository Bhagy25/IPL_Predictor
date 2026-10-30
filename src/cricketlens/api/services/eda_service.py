"""Statistics and EDA Lab Service for CricketLens.

Provides access to the 20 Stage 2 analytical figures, correlation matrices,
phase scoring patterns, venue scoring distributions, and missingness audits.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional
import pandas as pd

from cricketlens.api.settings import PROJECT_ROOT
from cricketlens.api.schemas import (
    EDAFigureItem,
    EDACatalogResponse,
    EDACorrelationMatrix,
    EDAPhaseStats,
    EDASummaryResponse,
)

# Systematic catalog of the 20 Stage 2 analytical figures
FIGURE_CATALOG_DATA: List[Dict[str, Any]] = [
    {
        "id": "01_season_scoring_trend",
        "figure_num": 1,
        "title": "Season First-Innings Mean Scoring Trend (2008–2025)",
        "category": "Scoring Trends",
        "description": "Annual first-innings team scoring averages fitted with an unweighted ordinary least-squares regression line across 18 tournament editions (2008–2025).",
        "figure_url": "/figures/stage_02/01_season_scoring_trend.png",
        "coverage_span": "2008–2025",
        "sample_size": "1,169 first innings",
        "key_findings": [
            "Statistically significant secular upward trend: +1.71 runs per season (R² = 0.663, p < 0.001).",
            "Scoring rose from ~150–161 runs (2008–2009) to over 188 runs in the 2024–2025 era.",
            "Observational linear regression is descriptive; does not imply causal progression.",
        ],
        "source_file": "season_first_innings_trends.csv",
    },
    {
        "id": "02_first_innings_histogram",
        "figure_num": 2,
        "title": "First-Innings Runs Distribution & Outliers",
        "category": "Historical Distributions",
        "description": "Histogram of all recorded 2018–2025 first innings (shortened innings included) in 10-run bins, with the median marked. Tukey bounds from the same sample: IQR = 44 runs, 1.5×IQR bounds = [89, 265].",
        "figure_url": "/figures/stage_02/02_first_innings_histogram.png",
        "coverage_span": "2018–2025",
        "sample_size": "533 first innings",
        "key_findings": [
            "Mean first-innings score is 175.8 runs; median is 175 runs.",
            "Interquartile Range (IQR) spans 155 to 199 runs (middle 50% of innings).",
            "11 Tukey outliers detected outside [89, 265] (maximum 287).",
        ],
        "source_file": "numeric_descriptive_summary.csv",
    },
    {
        "id": "03_score_boxplots_by_era",
        "figure_num": 3,
        "title": "First-Innings Scores Across Tournament Eras",
        "category": "Historical Distributions",
        "description": "Comparative boxplots of first-innings totals in four season groups: 2008–2012, 2013–2017, 2018–2021 and 2022–2025.",
        "figure_url": "/figures/stage_02/03_score_boxplots_by_era.png",
        "coverage_span": "2008–2025",
        "sample_size": "1,169 first innings",
        "key_findings": [
            "The 2022–2025 group exhibits a substantial upward shift in both median and upper quartile.",
            "Variance increased noticeably in 2024–2025 following high-tempo tactical batting changes.",
            "Lower quartiles remained relatively anchored around 150 runs even in high-scoring seasons.",
        ],
        "source_file": "season_first_innings_trends.csv",
    },
    {
        "id": "04_scoring_rate_by_phase",
        "figure_num": 4,
        "title": "Scoring Rate by Match Phase (Powerplay, Middle, Death)",
        "category": "Innings and Over Phases",
        "description": "Average runs and wickets lost per 6 legal balls partitioned across standardized phases: Powerplay (overs 1–6), Middle overs (overs 7–16), and Death overs (overs 17–20).",
        "figure_url": "/figures/stage_02/04_scoring_rate_by_phase.png",
        "coverage_span": "2018–2025",
        "sample_size": "533 first innings (63,960+ deliveries)",
        "key_findings": [
            "Powerplay scoring rate: 8.49 runs per 6 legal balls (0.22 wickets per over).",
            "Middle overs scoring rate: 8.32 runs per 6 legal balls (0.25 wickets per over).",
            "Death overs scoring rate surges to 10.73 runs per 6 legal balls accompanied by high dismissal risk (0.51 wickets per over).",
        ],
        "source_file": "innings_phase_patterns_2018_2025.csv",
    },
    {
        "id": "05_current_team_win_rates",
        "figure_num": 5,
        "title": "2022–2025 Active Franchise Win Rates (Decided Matches)",
        "category": "Match Outcomes and Toss",
        "description": "Ranked win rates for the 10 active franchises across the 2022–2025 comparative window, with Super Over victories credited to winners.",
        "figure_url": "/figures/stage_02/05_current_team_win_rates.png",
        "coverage_span": "2022–2025",
        "sample_size": "289 decided matches",
        "key_findings": [
            "Gujarat Titans leads the 4-year comparative window at 61.67% win rate (37 wins / 60 matches).",
            "Royal Challengers Bengaluru ranks second at 56.67% win rate (34 wins / 60 matches).",
            "Win rate denominator is strictly decided matches; abandoned and unplayed games excluded.",
        ],
        "source_file": "current_teams_win_rates_2022_2025.csv",
    },
    {
        "id": "06_venue_first_innings_means",
        "figure_num": 6,
        "title": "Venue First-Innings Scoring Means (Min 20 Matches)",
        "category": "Venue Analysis",
        "description": "Bar chart ranking canonical grounds hosting at least 20 first innings during the 2018–2025 period, plotting mean and median first-innings scores.",
        "figure_url": "/figures/stage_02/06_venue_first_innings_means.png",
        "coverage_span": "2018–2025",
        "sample_size": "13 qualifying canonical grounds",
        "key_findings": [
            "Eden Gardens boasts the highest first-innings mean (191.3 runs, median 188.0).",
            "Arun Jaitley Stadium (188.2 runs) and Narendra Modi Stadium (186.6 runs) follow closely.",
            "MA Chidambaram Stadium (Chepauk) exhibits defensive surface dynamics (mean 161.5 runs, median 160.0).",
        ],
        "source_file": "venues_min20_first_innings_2018_2025.csv",
    },
    {
        "id": "07_next_over_event_frequency",
        "figure_num": 7,
        "title": "Over-by-Over Wicket Event Frequency",
        "category": "Batting and Bowling",
        "description": "Observed empirical probability of at least one wicket falling in the subsequent over, evaluated at each completed-over checkpoint (overs 1–19).",
        "figure_url": "/figures/stage_02/07_next_over_event_frequency.png",
        "coverage_span": "2018–2025",
        "sample_size": "19,290 eligible checkpoint windows",
        "key_findings": [
            "Overall tournament wicket-next-over frequency is 27.85%.",
            "Wicket hazard rises steeply in the death overs (overs 17–19), exceeding 40% as batters hit out.",
            "Early overs (overs 1–3) show lower dismissal frequencies (~20–22%) as openers assess conditions.",
        ],
        "source_file": "next_over_historical_rates_2018_2025.csv",
    },
    {
        "id": "08_first_innings_correlation",
        "figure_num": 8,
        "title": "First-Innings Correlation Heatmaps (Pearson & Spearman)",
        "category": "Correlation Analysis",
        "description": "Correlation heatmaps examining linear (Pearson) and monotonic (Spearman) relationships between first-innings runs, wickets lost, legal deliveries, and season year.",
        "figure_url": "/figures/stage_02/08_first_innings_correlation.png",
        "coverage_span": "2018–2025",
        "sample_size": "533 first innings",
        "key_findings": [
            "Wickets lost exhibits a strong negative correlation with final score (Pearson r = -0.612, Spearman rho = -0.598).",
            "Legal balls bowled correlates positively (r = +0.285); prematurely shortened innings suppress totals.",
            "Season year shows a moderate positive trend (r = +0.241), confirming progressive scoring inflation.",
        ],
        "source_file": "first_innings_pearson_corr_2018_2025.csv",
    },
    {
        "id": "09_top_batters_recent",
        "figure_num": 9,
        "title": "Top Batters Milestone Rates & Runs (2018–2025 Leaderboard)",
        "category": "Batting and Bowling",
        "description": "Leaderboard analysis of the top IPL batters with >= 40 innings appearances (2018–2025), comparing total runs scored, 30+ milestone rates, and 50+ milestone rates.",
        "figure_url": "/figures/stage_02/09_top_batters_recent.png",
        "coverage_span": "2018–2025",
        "sample_size": "69 qualifying batters (8,123 appearances)",
        "key_findings": [
            "KL Rahul leads overall scoring in this cohort (4,497 runs, 55.2% 30+ rate, 39.1% 50+ rate).",
            "Virat Kohli ranks second (4,243 runs, 53.4% 30+ rate, 31.4% 50+ rate).",
            "Milestone rates are strictly conditional on observed batting appearances, not squad selections.",
        ],
        "source_file": "batters_min40_appearances_2018_2025.csv",
    },
    {
        "id": "10_batting_innings_scatter",
        "figure_num": 10,
        "title": "Batter Runs vs Balls Faced Scatter",
        "category": "Batting and Bowling",
        "description": "Scatter plot of runs against balls faced for every recorded 2018–2025 batting appearance.",
        "figure_url": "/figures/stage_02/10_batting_innings_scatter.png",
        "coverage_span": "2018–2025",
        "sample_size": "8,123 batting appearances",
        "key_findings": [
            "Runs rise roughly in proportion to balls faced; the spread widens for longer innings.",
            "Most appearances end within 20 balls faced.",
            "Each point is one batting appearance, not a player aggregate.",
        ],
        "source_file": "batters_min40_appearances_2018_2025.csv",
    },
    {
        "id": "11_match_field_missingness",
        "figure_num": 11,
        "title": "Match-Level Feature Missingness Audit",
        "category": "Data Quality and Missingness",
        "description": "Bar plot documenting data completeness across all 1,169 pre-2026 matches in the canonical Cricsheet extraction.",
        "figure_url": "/figures/stage_02/11_match_field_missingness.png",
        "coverage_span": "2008–2025",
        "sample_size": "1,169 matches",
        "key_findings": [
            "Key identifiers (match_id, season, date, teams, balls, runs) have 0% missingness (100% complete).",
            "City field is missing in 51 matches (4.36%) due to historical UAE fixtures without city tags.",
            "Missingness is systematic (concentrated in Dubai and Sharjah) and preserved rather than imputed.",
        ],
        "source_file": "match_field_missingness_pre2026.csv",
    },
    {
        "id": "12_full_vs_short_innings",
        "figure_num": 12,
        "title": "Full (120-Ball) vs Shortened First-Innings Comparison",
        "category": "Historical Distributions",
        "description": "Kernel density distributions comparing complete 120-legal-ball innings against prematurely concluded innings (all-out or weather-reduced).",
        "figure_url": "/figures/stage_02/12_full_vs_short_innings.png",
        "coverage_span": "2018–2025",
        "sample_size": "501 full innings vs 32 shortened innings",
        "key_findings": [
            "Full 120-ball innings average 178.88 runs (median 177.0).",
            "Shortened / all-out innings average 127.50 runs (median 130.5).",
            "Separating completed innings is essential to avoid distorting venue par scores.",
        ],
        "source_file": "first_innings_full_vs_short_2018_2025.csv",
    },
    {
        "id": "13_venue_season_centered",
        "figure_num": 13,
        "title": "Season-Centered Venue Scoring Deviations",
        "category": "Venue Analysis",
        "description": "Diverging bar chart showing venue scoring deviations after subtracting annual tournament scoring means, isolating ground character from era inflation.",
        "figure_url": "/figures/stage_02/13_venue_season_centered.png",
        "coverage_span": "2018–2025",
        "sample_size": "12 canonical grounds with full innings",
        "key_findings": [
            "Eden Gardens exhibits an era-adjusted scoring premium of +10.34 runs above annual par.",
            "Ekana Stadium (Lucknow) exhibits a severe defensive deviation of -14.32 runs below annual par.",
            "Season-centering correctly prevents early-era venues from being unfairly penalized as low-scoring.",
        ],
        "source_file": "venues_full_20_season_adjusted_2018_2025.csv",
    },
    {
        "id": "14_paired_phase_differences",
        "figure_num": 14,
        "title": "Paired Within-Innings Phase Differences",
        "category": "Innings and Over Phases",
        "description": "Distribution of within-innings paired differences (Death overs run rate minus Powerplay run rate for the same batting innings).",
        "figure_url": "/figures/stage_02/14_paired_phase_differences.png",
        "coverage_span": "2018–2025",
        "sample_size": "937 paired innings (min 12 death balls)",
        "key_findings": [
            "Mean paired acceleration is +2.26 runs per 6 balls from Powerplay to Death (95% CI: [2.02, 2.51]).",
            "Match-clustered paired t-statistic = 18.68 (p < 1e-60), confirming consistent acceleration.",
            "In ~21% of innings, heavy wicket loss caused death rates to collapse below Powerplay levels.",
        ],
        "source_file": "paired_powerplay_death_per_innings_2018_2025.csv",
    },
    {
        "id": "15_phase_year_matched",
        "figure_num": 15,
        "title": "Phase Run Rates Across Tournament Years",
        "category": "Innings and Over Phases",
        "description": "Multi-line tracking comparing Powerplay, Middle, and Death overs run rates year-by-year from 2018 through 2025.",
        "figure_url": "/figures/stage_02/15_phase_year_matched.png",
        "coverage_span": "2018–2025",
        "sample_size": "533 first innings",
        "key_findings": [
            "Death overs scoring maintained a persistent 2.0–2.5 rpo advantage over earlier phases.",
            "Powerplay scoring jumped sharply in 2024–2025 (surpassing 9.0 rpo for the first time).",
            "Middle overs run rates remained relatively stable across the 8-year span (~8.0–8.5 rpo).",
        ],
        "source_file": "paired_phase_by_season_2018_2025.csv",
    },
    {
        "id": "16_toss_decision_association",
        "figure_num": 16,
        "title": "Toss Decision vs Match Result Association",
        "category": "Match Outcomes and Toss",
        "description": "Mosaic plot and win-rate comparison evaluating whether electing to field or bat confers an observational match outcome advantage.",
        "figure_url": "/figures/stage_02/16_toss_decision_association.png",
        "coverage_span": "2018–2025",
        "sample_size": "528 decided matches",
        "key_findings": [
            "Teams electing to field won 210 of 398 matches (52.76% win rate).",
            "Teams electing to bat won 62 of 130 matches (47.69% win rate).",
            "Difference is not statistically significant (Fisher's exact test p = 0.363); toss advantage is modest.",
        ],
        "source_file": "toss_decision_match_result_crosstab_2018_2025.csv",
    },
    {
        "id": "17_city_missingness_by_venue",
        "figure_num": 17,
        "title": "Missing City Field Analysis by Venue",
        "category": "Data Quality and Missingness",
        "description": "Breakdown showing that all 51 missing city cases in pre-2026 data are localized to two overseas venues in the UAE.",
        "figure_url": "/figures/stage_02/17_city_missingness_by_venue.png",
        "coverage_span": "2008–2025",
        "sample_size": "51 missing cases",
        "key_findings": [
            "Dubai International Cricket Stadium accounts for 33 missing city instances (2014 & 2020 editions).",
            "Sharjah Cricket Stadium accounts for 18 missing city instances.",
            "Documented as a Cricsheet source format artifact; venues are physically unambiguously known.",
        ],
        "source_file": "missing_city_by_venue_pre2026.csv",
    },
    {
        "id": "18_match_outcomes",
        "figure_num": 18,
        "title": "Tournament Match Outcome Classification (2008–2025)",
        "category": "Match Outcomes and Toss",
        "description": "Partition of all 1,169 development matches into Regulation Wins (1,146 / 98.0%), Super Over Ties (15 / 1.3%), and No Results (8 / 0.7%).",
        "figure_url": "/figures/stage_02/18_match_outcomes.png",
        "coverage_span": "2008–2025",
        "sample_size": "1,169 matches",
        "key_findings": [
            "98.03% of historical matches were decided in ordinary regulation overs.",
            "15 regulation ties were decided by Super Over eliminators (including 1 double Super Over).",
            "8 matches were abandoned without reaching the Duckworth-Lewis minimum requirement.",
        ],
        "source_file": "match_outcomes_2008_2025.csv",
    },
    {
        "id": "19_win_rate_super_over_fix",
        "figure_num": 19,
        "title": "Impact of Super Over Correction on Franchise Win Rates",
        "category": "Match Outcomes and Toss",
        "description": "Comparison showing franchise win rates before and after correctly crediting Super Over victories, resolving previous pipeline discrepancies.",
        "figure_url": "/figures/stage_02/19_win_rate_super_over_fix.png",
        "coverage_span": "2022–2025",
        "sample_size": "289 decided matches",
        "key_findings": [
            "Correcting Super Over attribution adjusted Delhi Capitals' win rate from 46.30% to 47.27% (+0.98%).",
            "Rajasthan Royals' win rate adjusted from 50.85% to 50.00% (-0.85%) after accounting for decided games.",
            "All-time records now uniformly reflect true tournament winner declarations.",
        ],
        "source_file": "team_wins_before_after_super_over_fix_2022_2025.csv",
    },
    {
        "id": "20_dl_innings_sensitivity",
        "figure_num": 20,
        "title": "Duckworth-Lewis Rain Interruption Sensitivity Analysis",
        "category": "Historical Distributions",
        "description": "Sensitivity analysis quantifying the impact of D/L rain-interrupted first innings on aggregate scoring statistics.",
        "figure_url": "/figures/stage_02/20_dl_innings_sensitivity.png",
        "coverage_span": "2018–2025",
        "sample_size": "533 first innings (6 D/L matches)",
        "key_findings": [
            "Only 6 first innings in 2018–2025 were impacted by rain revisions (1.1% of sample).",
            "Excluding D/L matches shifts the sample mean by only +0.12 runs (175.80 to 175.92).",
            "Confirms that uncorrected descriptive averages are robust against rain truncation distortions.",
        ],
        "source_file": "first_innings_by_d_l_and_length_2018_2025.csv",
    },
]


# Where each figure's season coverage comes from: the generating code (src/cricketlens/stage02_*.py)
# and the source file or figure title. Every Stage 2 figure excludes the 2026 holdout season.
FIGURE_COVERAGE_EVIDENCE: Dict[str, str] = {
    "01_season_scoring_trend": "season_first_innings_trends.csv has one row per season, 2008–2025 (18 rows).",
    "02_first_innings_histogram": "stage02_eda.py plots first_recent (season >= 2018); figure title 'First-innings totals: 2018-2025'; numeric_descriptive_summary.csv scope recent_2018_2025 (n = 533).",
    "03_score_boxplots_by_era": "stage02_eda.py plots all 2008–2025 first innings in groups 2008-12, 2013-17, 2018-21, 2022-25.",
    "04_scoring_rate_by_phase": "innings_phase_patterns_2018_2025.csv, from deliveries with season >= 2018.",
    "05_current_team_win_rates": "current_teams_win_rates_2022_2025.csv, from matches with 2022 <= season <= 2025.",
    "06_venue_first_innings_means": "venues_min20_first_innings_2018_2025.csv, from first innings with season >= 2018.",
    "07_next_over_event_frequency": "next_over_historical_rates_2018_2025.csv, from checkpoints with season >= 2018.",
    "08_first_innings_correlation": "first_innings_pearson_corr_2018_2025.csv, from first innings with season >= 2018.",
    "09_top_batters_recent": "batters_min40_appearances_2018_2025.csv, from batting appearances with season >= 2018.",
    "10_batting_innings_scatter": "stage02_eda.py plots recent_b (season >= 2018); figure title 'Batter runs vs balls faced, 2018-2025'.",
    "11_match_field_missingness": "match_field_missingness_pre2026.csv: total_records = 1,169 matches (2008–2025).",
    "12_full_vs_short_innings": "first_innings_full_vs_short_2018_2025.csv, from first innings with season >= 2018.",
    "13_venue_season_centered": "venues_full_20_season_adjusted_2018_2025.csv, from 120-ball first innings with season >= 2018.",
    "14_paired_phase_differences": "paired_powerplay_death_per_innings_2018_2025.csv: seasons 2018–2025 (937 innings).",
    "15_phase_year_matched": "paired_phase_by_season_2018_2025.csv: one row per season, 2018–2025.",
    "16_toss_decision_association": "toss_decision_match_result_crosstab_2018_2025.csv, from matches with season >= 2018.",
    "17_city_missingness_by_venue": "missing_city_by_venue_pre2026.csv, from all 2008–2025 matches.",
    "18_match_outcomes": "match_outcomes_2008_2025.csv: 1,169 matches (2008–2025).",
    "19_win_rate_super_over_fix": "team_wins_before_after_super_over_fix_2022_2025.csv, from matches with season >= 2022.",
    "20_dl_innings_sensitivity": "first_innings_by_d_l_and_length_2018_2025.csv, from first innings with season >= 2018.",
}

STATIC_FIGURE_NOTE = "Static research figure — not affected by filters"


class EDAService:
    """Service providing cataloged Stage 2 figures and raw analytical tables."""

    def __init__(self) -> None:
        self._summary_data: Optional[EDASummaryResponse] = None

    def get_catalog(self) -> EDACatalogResponse:
        """Return all 20 cataloged figures with categories."""
        figures = [
            EDAFigureItem(**f, coverage_evidence=FIGURE_COVERAGE_EVIDENCE[f["id"]], static_note=STATIC_FIGURE_NOTE)
            for f in FIGURE_CATALOG_DATA
        ]
        categories = list(dict.fromkeys(f["category"] for f in FIGURE_CATALOG_DATA))
        return EDACatalogResponse(
            categories=categories,
            figures=figures,
            total_figures=len(figures),
        )

    def get_summary(self) -> EDASummaryResponse:
        """Return raw statistical data tables backing the Stage 2 figures."""
        if self._summary_data is not None:
            return self._summary_data

        base_dir = PROJECT_ROOT
        s1_dir = base_dir / "reports" / "stage_02" / "session_01"
        s2_dir = base_dir / "reports" / "stage_02" / "session_02"

        # 1. Scoring trends
        scoring_trends = []
        st_path = s1_dir / "season_first_innings_trends.csv"
        if st_path.exists():
            df_st = pd.read_csv(st_path)
            scoring_trends = df_st.to_dict(orient="records")

        # 2. Phase patterns
        phase_patterns = []
        ph_path = s1_dir / "innings_phase_patterns_2018_2025.csv"
        if ph_path.exists():
            df_ph = pd.read_csv(ph_path)
            for _, r in df_ph.iterrows():
                phase_patterns.append(
                    EDAPhaseStats(
                        phase=str(r["phase"]),
                        total_runs=int(r["total_runs"]),
                        legal_balls=int(r["legal_balls"]),
                        team_wickets=int(r["team_wickets"]),
                        runs_per_six_legal_balls=round(float(r["runs_per_six_legal_balls"]), 2),
                        wickets_per_six_legal_balls=round(float(r["wickets_per_six_legal_balls"]), 3),
                    )
                )

        # 3. Correlations
        p_path = s1_dir / "first_innings_pearson_corr_2018_2025.csv"
        s_path = s1_dir / "first_innings_spearman_corr_2018_2025.csv"
        pearson_dict = {}
        spearman_dict = {}
        vars_list = ["runs", "wickets", "legal_balls", "season"]
        if p_path.exists():
            df_p = pd.read_csv(p_path, index_col=0)
            pearson_dict = {col: {k: round(float(v), 3) for k, v in df_p[col].items()} for col in df_p.columns}
        if s_path.exists():
            df_s = pd.read_csv(s_path, index_col=0)
            spearman_dict = {col: {k: round(float(v), 3) for k, v in df_s[col].items()} for col in df_s.columns}

        correlations = EDACorrelationMatrix(
            variables=vars_list,
            pearson=pearson_dict,
            spearman=spearman_dict,
            sample_size=533,
            notes="Evaluated among 2018–2025 first innings. Demonstrates strong negative association between wickets lost and runs.",
        )

        # 4. Toss crosstab
        toss_crosstab = []
        toss_path = s2_dir / "toss_decision_match_result_crosstab_2018_2025.csv"
        if toss_path.exists():
            df_toss = pd.read_csv(toss_path)
            toss_crosstab = df_toss.to_dict(orient="records")

        # 5. Venue means
        venue_means = []
        ven_path = s1_dir / "venues_min20_first_innings_2018_2025.csv"
        if ven_path.exists():
            df_ven = pd.read_csv(ven_path)
            venue_means = df_ven.to_dict(orient="records")

        # 6. Missingness audit
        missingness = []
        miss_path = s1_dir / "match_field_missingness_pre2026.csv"
        if miss_path.exists():
            df_miss = pd.read_csv(miss_path)
            missingness = df_miss.to_dict(orient="records")

        notices = [
            "All figures and summary statistics are derived strictly from pre-2026 development data.",
            "IPL 2026 was strictly isolated as an unseen holdout to prevent data leakage.",
            "Statistical associations are observational and descriptive; they do not imply causal mechanisms.",
            "Venue and phase comparisons include all recorded first innings (full, shortened, and all-out).",
        ]

        self._summary_data = EDASummaryResponse(
            scoring_trends=scoring_trends,
            phase_patterns=phase_patterns,
            correlations=correlations,
            toss_crosstab=toss_crosstab,
            venue_means=venue_means,
            missingness_audit=missingness,
            notices=notices,
        )
        return self._summary_data


eda_service = EDAService()
