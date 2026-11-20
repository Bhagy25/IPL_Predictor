"""Verify the benchmark cohorts and the existing Stage 3 forecast artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from cricketlens.batter_training_data import build as build_batter
from cricketlens.fit_batter_models import metrics as batter_metrics
from cricketlens.fit_wicket_models import measure as wicket_metrics
from cricketlens.model_benchmark import TASKS, TUNING_YEARS, VALIDATION_YEARS, data_for, split, write_json
from cricketlens.pipeline import extract
from cricketlens.wicket_training_data import build as build_wicket


def compare_frames(expected, actual, key):
    pd.testing.assert_frame_equal(
        expected.sort_values(key).reset_index(drop=True),
        actual.loc[:, expected.columns].sort_values(key).reset_index(drop=True),
        check_dtype=False, rtol=1e-12, atol=1e-12,
    )


def check_wicket_state(cohort, deliveries):
    key = ["match_id", "innings"]
    totals = (deliveries.groupby([*key, "over_index"], as_index=False)
              .agg(legal=("legal_delivery", "sum"), runs=("runs_total", "sum"),
                   wickets=("team_wickets_on_ball", "sum"))
              .sort_values([*key, "over_index"]))
    totals[["runs_so_far", "wickets_so_far"]] = totals.groupby(key)[["runs", "wickets"]].cumsum()
    totals["legal_so_far"] = totals.groupby(key).legal.cumsum()
    observed = cohort.assign(over_index=cohort.completed_overs - 1)
    observed = observed.merge(totals, on=[*key, "over_index"], suffixes=("", "_over"), validate="one_to_one")
    future = totals.assign(over_index=totals.over_index - 1)
    observed = observed.merge(future[[*key, "over_index", "legal", "wickets"]],
                              on=[*key, "over_index"], suffixes=("", "_next"), validate="one_to_one")
    if len(cohort) != len(observed):
        raise ValueError("Checkpoint or next over missing from delivery data")
    expected_phase = np.select([observed.completed_overs <= 5, observed.completed_overs <= 14],
                               ["powerplay", "middle"], default="death")
    for actual, expected in [
        (observed.legal, 6), (observed.phase, expected_phase),
        (observed.runs, observed.runs_so_far), (observed.wickets, observed.wickets_so_far),
        (observed.run_rate, observed.runs_so_far / observed.completed_overs),
        (observed.last_over_runs, observed.runs_over), (observed.last_over_wickets, observed.wickets_over),
        (observed.next_over_legal_balls, observed.legal_next),
        (observed.wicket_next_over, (observed.wickets_next > 0).astype(int)),
    ]:
        if pd.api.types.is_float_dtype(actual):
            np.testing.assert_allclose(actual, expected, rtol=1e-12)
        else:
            np.testing.assert_array_equal(actual, expected)
    return {
        "delivery_verified_rows": len(observed),
        "checkpoint_legal_balls_differ_from_six_times_completed_overs":
            int(observed.legal_so_far.ne(6 * observed.completed_overs).sum()),
    }


def check_batter_history(cohort, original):
    key = ["match_id", "innings", "batter_id"]
    runs = cohort.merge(original[[*key, "runs", "balls_faced"]], on=key, validate="one_to_one")
    if len(runs) != len(cohort):
        raise ValueError("Batter innings missing from source data")
    np.testing.assert_array_equal(runs.actual_runs, runs.runs)
    np.testing.assert_array_equal(runs.milestone_class, np.digitize(runs.runs, [30, 50]))

    def stats(values, thresholds):
        if not len(values):
            return [0.0] * (1 + len(thresholds))
        return [values.mean(), *((values >= threshold).mean() for threshold in thresholds)]

    task = TASKS[1]
    for _, player in runs.sort_values(["date", *key]).groupby("batter_id"):
        days = player.date.to_numpy(dtype="datetime64[D]")
        scores = player.runs.to_numpy()
        opponents = player.bowling_team.to_numpy()
        venues = player.venue_canonical.to_numpy()
        expected = []
        # A left-side lookup excludes every match on the prediction date.
        for i, end in enumerate(days.searchsorted(days, side="left")):
            past = scores[:end]
            vs = past[opponents[:end] == opponents[i]]
            at = past[venues[:end] == venues[i]]
            gap = min(int((days[i] - days[end - 1]).astype(int)), 3650) if end else 3650
            expected.append([
                end, *stats(past, (30, 50)), *stats(past[-5:], (30, 50)), *stats(past[-10:], (30, 50)),
                len(vs), *stats(vs, (30,)), len(at), *stats(at, (30,)), gap,
            ])
        np.testing.assert_allclose(player[task.numeric], expected, rtol=1e-12, atol=1e-12)
    return {"strictly_prior_history_verified_rows": len(runs),
            "cohort_rows_with_zero_balls_faced": int(runs.balls_faced.eq(0).sum()),
            "cold_start_rows": int(runs.prior_innings.eq(0).sum()),
            "cold_start_rows_2026": int((runs.prior_innings.eq(0) & runs.season.eq(2026)).sum())}


def verify_legacy(root, wicket, batter):
    directory = root / "reports/stage_03/session_03"
    manifest = json.loads((directory / "stage03_session03_final_results.json").read_text(encoding="utf-8"))
    result = {}
    for task, data in zip(TASKS, (wicket, batter)):
        stems = f"{task.name}_holdout_forecasts_2026"
        forecasts = pd.read_csv(directory / task.name / f"{stems}.csv").sort_values(task.keys)
        test = data.loc[data.season == 2026].sort_values(task.keys)
        compare_frames(test[[*task.keys, task.target]], forecasts, task.keys)
        held = joblib.load(root / "models" / f"{task.name}_holdout_train_through_2025.joblib")
        deployed = joblib.load(root / "models" / f"{task.name}_deployment_through_2026.joblib")
        original = manifest[task.name]
        year_field = "training_end" if task.name == "wicket" else "train_end"
        for artifact, year in [(held, 2025), (deployed, 2026)]:
            if (artifact[year_field] != year or artifact["name"] != original["selected_name_from_2025_only"]
                    or artifact["columns"] != task.features):
                raise ValueError(f"Unexpected Stage 3 model metadata for {task.name}")
        p = held["model"].predict_proba(test[task.features])
        if task.name == "wicket":
            np.testing.assert_allclose(p[:, 1], forecasts.predicted_wicket_probability, atol=1e-12)
            measured = wicket_metrics(test[task.target], p[:, 1])
        else:
            np.testing.assert_allclose(p[:, 2], forecasts.probability_50_plus, atol=1e-12)
            np.testing.assert_allclose(p[:, 1:].sum(axis=1), forecasts.probability_30_plus, atol=1e-12)
            measured = batter_metrics(test[task.target], p)
        if measured != original["holdout_2026"]:
            raise ValueError(f"Archived scores differ for {task.name}")
        result[task.name] = {"holdout_artifact_train_end": held[year_field],
                             "deployment_artifact_train_end": deployed[year_field],
                             "deployment_estimator": type(deployed["model"].named_steps["model"]).__name__,
                             "archived_holdout_scores_reproduced": measured}
    return result


def audit(root, verify_raw):
    data_dir = root / "data/processed"
    base = {name: pd.read_csv(data_dir / f"{name}.csv") for name in (
        "matches", "innings", "overs", "batter_innings", "deliveries",
    )}
    raw_matches = list((root / "data/raw/ipl_json").glob("*.json"))
    if verify_raw:
        raw_tables = extract(root / "data/raw/ipl_json")
        raw_keys = {"matches": ["match_id"], "innings": ["match_id", "innings"],
                    "overs": ["match_id", "innings", "over_index"],
                    "batter_innings": ["match_id", "innings", "batter_id"],
                    "deliveries": ["match_id", "innings", "over_index", "delivery_index"]}
        for name, key in raw_keys.items():
            regenerated = pd.DataFrame(raw_tables[name]).replace("", np.nan)
            regenerated["match_id"] = regenerated.match_id.astype(base[name].match_id.dtype)
            compare_frames(base[name], regenerated, key)

    matches, overs, batters = (base[name] for name in ("matches", "overs", "batter_innings"))
    wicket, wicket_counts = build_wicket(overs, matches)
    batter, batter_counts = build_batter(batters, matches, max_development_season=2026, allow_2026=True)
    # The original batter builder reuses development-only counter names for the full history.
    batter_counts["source_rows"] = batter_counts.pop("all_rows_in_pre2026_raw")
    batter_counts["eligible_rows"] = batter_counts.pop("eligible_pre2026_batter_innings")
    del batter_counts["holdout"]
    results = {
        "archive": {"raw_json_files": len(raw_matches), "raw_base_tables_rebuilt_and_matched": verify_raw,
                    "counts": {name: len(table) for name, table in base.items()},
                    "date_min": matches.date.min(), "date_max": matches.date.max(),
                    "event": matches.event.unique().tolist(), "gender": matches.gender.unique().tolist(),
                    "match_missing": {k: int(v) for k, v in matches.isna().sum().items() if v},
                    "outcome_methods": matches.outcome_method.fillna("(blank)").value_counts().to_dict(),
                    "decided_by": matches.decided_by.value_counts().to_dict()},
        "wicket": {"builder_counts": wicket_counts,
                   "checks": check_wicket_state(wicket, base["deliveries"])},
        "batter": {"builder_counts": batter_counts, "checks": check_batter_history(batter, batters)},
    }
    for task, rebuilt in zip(TASKS, (wicket, batter)):
        data = data_for(task, data_dir)
        compare_frames(rebuilt.assign(date=pd.to_datetime(rebuilt.date)), data, task.keys)
        meta = data.merge(matches[["match_id", "date", "season", "decided_by", "outcome_method"]],
                          on="match_id", suffixes=("", "_match"), validate="many_to_one")
        np.testing.assert_array_equal(meta.date, pd.to_datetime(meta.date_match))
        np.testing.assert_array_equal(meta.season, meta.season_match)
        details = results[task.name]
        details["model_columns_missing"] = {k: int(v) for k, v in data[task.features].isna().sum().items() if v}
        details["matches"] = data.match_id.nunique()
        details["class_counts_by_split"] = {
            label: {str(k): int(v) for k, v in frame[task.target].value_counts().sort_index().items()}
            for label, frame in [
                ("pre2026", data[data.season < 2026]), ("2026", data[data.season == 2026]),
                ("all", data),
            ]
        }
        details["retained_match_outcomes"] = meta.decided_by.value_counts().to_dict()
        details["retained_outcome_methods"] = meta.outcome_method.fillna("(blank)").value_counts().to_dict()
        details["rows_with_unseen_categories"] = {}
        for year in (*TUNING_YEARS, *VALIDATION_YEARS, 2026):
            train, later = split(data, year)
            details["rows_with_unseen_categories"][str(year)] = {
                col: int((~later[col].isin(train[col])).sum()) for col in task.categorical
            }
    results["archived_stage03"] = verify_legacy(root, wicket, batter)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--verify-raw", action="store_true", help="Re-extract five base tables from Cricsheet JSON")
    parser.add_argument("--output", type=Path, default=Path("reports/model_benchmark/data_audit.json"))
    args = parser.parse_args()
    result = audit(args.root, args.verify_raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print(f"Verified source, cohorts and archived forecasts. Audit written to {args.output}.")


if __name__ == "__main__":
    main()
