"""vercel.json stays within Vercel's schema limits and still bundles every file the API reads at runtime.

Vercel's schema (https://openapi.vercel.sh/vercel.json) caps a function's includeFiles and excludeFiles
at 256 characters each. The Python builder adds the includeFiles matches after applying excludeFiles,
so every runtime file must be matched by includeFiles.
"""
import json
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
FUNCTION = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))["functions"]["api/index.py"]
SCHEMA_MAX_LENGTH = 256

# Every data, model and report file the API opens (Part 12's bare-bundle run)
RUNTIME_FILES = [
    "data/derived/batting_appearances.csv",
    "data/derived/dismissals.csv",
    "data/derived/match_players.csv",
    "data/derived/match_replacements.csv",
    "data/derived/non_boundary_events.csv",
    "data/derived/people.csv",
    "data/processed/batter_innings.csv",
    "data/processed/deliveries.csv",
    "data/processed/innings.csv",
    "data/processed/matches.csv",
    "data/processed/stage03_wicket_full_history_2008_2026.csv",
    "models/batter_deployment_through_2026.joblib",
    "models/wicket_deployment_through_2026.joblib",
    *[f"reports/figures/stage_02/{name}.png" for name in (
        "01_season_scoring_trend", "02_first_innings_histogram", "03_score_boxplots_by_era",
        "04_scoring_rate_by_phase", "05_current_team_win_rates", "06_venue_first_innings_means",
        "07_next_over_event_frequency", "08_first_innings_correlation", "09_top_batters_recent",
        "10_batting_innings_scatter", "11_match_field_missingness", "12_full_vs_short_innings",
        "13_venue_season_centered", "14_paired_phase_differences", "15_phase_year_matched",
        "16_toss_decision_association", "17_city_missingness_by_venue", "18_match_outcomes",
        "19_win_rate_super_over_fix", "20_dl_innings_sensitivity")],
    "reports/stage_01/audit_summary.json",
    "reports/stage_01/missingness.csv",
    "reports/stage_01/raw_over_anomalies.csv",
    "reports/stage_02/session_01/first_innings_pearson_corr_2018_2025.csv",
    "reports/stage_02/session_01/first_innings_spearman_corr_2018_2025.csv",
    "reports/stage_02/session_01/innings_phase_patterns_2018_2025.csv",
    "reports/stage_02/session_01/match_field_missingness_pre2026.csv",
    "reports/stage_02/session_01/season_first_innings_trends.csv",
    "reports/stage_02/session_01/venues_min20_first_innings_2018_2025.csv",
    "reports/stage_02/session_02/toss_decision_match_result_crosstab_2018_2025.csv",
    "reports/stage_03/session_03/batter/batter_holdout_forecasts_2026.csv",
    "reports/stage_03/session_03/stage03_session03_final_results.json",
    "reports/stage_03/session_03/wicket/wicket_holdout_forecasts_2026.csv",
]


def _expand_braces(pattern):
    """Brace expansion as in minimatch, innermost group first: a{b,c{d,e}} -> ab, acd, ace."""
    match = re.search(r"\{([^{}]*)\}", pattern)
    if not match:
        return [pattern]
    return [expanded for alternative in match.group(1).split(",")
            for expanded in _expand_braces(pattern[:match.start()] + alternative + pattern[match.end():])]


def _matches(path, pattern):
    return any(PurePosixPath(path).full_match(p) for p in _expand_braces(pattern))


def test_globs_fit_the_schema_limit():
    for key in ("includeFiles", "excludeFiles"):
        assert len(FUNCTION[key]) <= SCHEMA_MAX_LENGTH, f"{key} is {len(FUNCTION[key])} characters"


def test_every_runtime_file_is_included():
    assert len(RUNTIME_FILES) == 46
    missing = [f for f in RUNTIME_FILES if not _matches(f, FUNCTION["includeFiles"])]
    assert missing == []


def test_unneeded_folders_stay_out():
    for path in ("data/raw/ipl_json/1082591.json", "notebooks/stage_02.ipynb", "docs/ROADMAP.md",
                 "tests/test_api.py", "web/src/App.tsx", "reports/IT462_report.pdf",
                 "data/processed/next_over_samples.csv", "models/batter_holdout_train_through_2025.joblib"):
        assert _matches(path, FUNCTION["excludeFiles"]), path
        assert not _matches(path, FUNCTION["includeFiles"]), path
