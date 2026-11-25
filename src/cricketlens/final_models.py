"""Fit and save the final CricketLens forecast models from the frozen benchmark selection.

Both forecasts use the algorithm and settings that reports/model_benchmark/selection.json froze
(Histogram gradient boosting). The pipelines are built and fitted by cricketlens.model_benchmark
itself (its estimator(), fit() and split()), so the saved models are the benchmark's models, not a
re-typed copy. Two artifacts are saved per task:

* holdout: trained on every eligible row from 2008 to 2025. Its 2026 forecasts must reproduce the
  benchmark's saved holdout forecasts and metrics exactly; this run checks that and stops otherwise.
* final (deployment): trained on every eligible row from 2008 to 2026. The website serves it. It has
  no later season to be tested on yet.

The fitted steps are relabelled 'features' and 'model', the step names the Stage 3 inference
functions (predict_wicket.forecast, forecast_future_batter.forecast) and the API read. Relabelling
copies no estimator and changes no prediction. The run also records a class-prior reference for
2026 and a determinism check (two independent fits must give byte-identical probabilities).

    python -m cricketlens.final_models
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
from typing import Any, Dict

import joblib
import matplotlib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from cricketlens.model_benchmark import (
    SEED, TASKS, TEST_YEAR, data_for, fit, fold_info, probabilities, score, split, write_json,
)

ALGORITHM = "HistGradientBoostingClassifier"
BASELINE = "Class-prior baseline"
HOLDOUT_VERSION = "holdout_train_2008_2025"
# The version string the Stage 3 inference functions and the API accept for a model refitted through 2026
FINAL_VERSION = "deployment_refit_2008_2026"
RELEASE = "final"
# Exactness tolerance against the benchmark's saved forecasts and metrics
EXACT_TOLERANCE = 1e-12
ARTIFACTS = {
    "wicket": {"holdout": "wicket_hgb_through_2025.joblib", "final": "wicket_hgb_through_2026.joblib"},
    "batter": {"holdout": "batter_hgb_through_2025.joblib", "final": "batter_hgb_through_2026.joblib"},
}
TASK_DETAILS = {
    "wicket": {"outcome": "wicket_next_over", "horizon": "one upcoming over",
               "notice": "No automatic retraining, manual score/wickets input"},
    "batter": {"condition": "batter has recorded batting innings", "milestones": [30, 50]},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def library_versions() -> Dict[str, str]:
    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
            "scipy": scipy.__version__, "scikit-learn": sklearn.__version__, "joblib": joblib.__version__,
            "matplotlib": matplotlib.__version__}


def load_selection(selection_path: Path, data_dir: Path) -> Dict[str, Any]:
    """The frozen choices, checked against the current modelling tables and feature lists."""
    selection = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    for task in TASKS:
        choice = selection["tasks"][task.name]
        if choice["input_sha256"] != sha256(data_dir / task.path):
            raise ValueError(f"{task.path} differs from the table the benchmark selection was made on")
        if choice["features"] != task.features or choice["target"] != task.target:
            raise ValueError(f"Feature or target schema differs from the frozen selection for {task.name}")
        if choice["selected"] != "Histogram gradient boosting":
            raise ValueError(f"Unexpected frozen selection for {task.name}: {choice['selected']}")
    return selection


def fit_selected(task, choice, train):
    """Fit the frozen pipeline exactly as the benchmark does and relabel its two steps."""
    with threadpool_limits(limits=1):
        fitted, warnings = fit(task, choice["selected"], choice["params"], train)
    (_, features), (_, model) = fitted.steps
    if type(model).__name__ != ALGORITHM:
        raise ValueError(f"Expected {ALGORITHM}, got {type(model).__name__}")
    return Pipeline([("features", features), ("model", model)]), warnings


def predict(task, model, rows) -> np.ndarray:
    with threadpool_limits(limits=1):
        return probabilities(task, model, rows)


def artifact(task, choice, model, train, version, end_year, input_sha, warnings) -> Dict[str, Any]:
    info = fold_info(train, train, end_year)
    return {
        "model": model,
        "columns": list(task.features),
        "name": choice["selected"],
        "algorithm": ALGORITHM,
        "params": dict(choice["params"]),
        "estimator_params": dict(model.named_steps["model"].get_params()),
        "classes": [int(c) for c in model.classes_],
        "target": task.target,
        "version": version,
        "release": RELEASE,
        "seed": SEED,
        # Stage 3 wicket artifacts name the last season training_end, batter artifacts train_end
        "training_end": end_year,
        "train_end": end_year,
        "train_start": info["train_start"],
        "train_end_date": info["train_end"],
        "train_rows": int(info["train_rows"]),
        "train_matches": int(info["train_matches"]),
        "class_counts": {str(c): int((train[task.target] == c).sum()) for c in task.classes},
        "fit_warnings": list(warnings),
        "input_file": f"data/processed/{task.path}",
        "input_sha256": input_sha,
        "selection_file": "reports/model_benchmark/selection.json",
        "library_versions": library_versions(),
        **TASK_DETAILS[task.name],
    }


def holdout_proof(task, model, test, train_rows: int, benchmark_dir: Path,
                  holdout_report: Dict[str, Any]) -> Dict[str, Any]:
    """Holdout-artifact forecasts and scores on 2026 against the benchmark's saved ones."""
    saved = pd.read_csv(benchmark_dir / f"{task.name}_holdout_forecasts.csv", float_precision="round_trip",
                        dtype={"batter_id": str} if task.name == "batter" else None)
    p = predict(task, model, test)
    if not test[task.keys].astype(str).reset_index(drop=True).equals(saved[task.keys].astype(str)):
        raise ValueError(f"{task.name}: 2026 row keys differ from the benchmark forecasts")
    columns = [f"p_class_{c}" for c in task.classes]
    forecast_diff = float(np.max(np.abs(p - saved[columns].to_numpy())))
    official = holdout_report[task.name]
    metrics = score(task, test, p)
    metric_diff = max(abs(metrics[k] - official["metrics"][k]) for k in official["metrics"])
    y = test[task.target].to_numpy()
    matrix = confusion_matrix(y, p.argmax(axis=1), labels=task.classes).tolist()
    checks = {
        "rows": int(len(test)),
        "max_abs_forecast_difference": forecast_diff,
        "max_abs_metric_difference": float(metric_diff),
        "predicted_class_equal": bool(np.array_equal(p.argmax(axis=1), saved.predicted_class.to_numpy())),
        "confusion_matrix_equal": matrix == official["confusion_matrix"],
        "params_equal": all(model.named_steps["model"].get_params()[k] == v for k, v in official["params"].items()),
        "training_rows_equal": int(official["train_rows"]) == int(train_rows),
        "tolerance": EXACT_TOLERANCE,
    }
    if (forecast_diff > EXACT_TOLERANCE or metric_diff > EXACT_TOLERANCE
            or not all(v for k, v in checks.items() if k.endswith("_equal"))):
        raise ValueError(f"{task.name}: holdout artifact does not reproduce the benchmark holdout: {checks}")
    return checks


def run(data_dir: Path, model_dir: Path, benchmark_dir: Path, output: Path) -> Dict[str, Any]:
    selection = load_selection(benchmark_dir / "selection.json", data_dir)
    holdout_report = json.loads((benchmark_dir / "holdout_2026.json").read_text(encoding="utf-8"))
    model_dir.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {
        "description": "Final models refitted from the frozen benchmark selection (Histogram gradient boosting).",
        "selection_file": "reports/model_benchmark/selection.json",
        "holdout_file": "reports/model_benchmark/holdout_2026.json",
        "seed": SEED, "holdout_year": TEST_YEAR, "versions": library_versions(), "tasks": {},
    }
    for task in TASKS:
        choice = selection["tasks"][task.name]
        data = data_for(task, data_dir)
        input_sha = choice["input_sha256"]
        train, test = split(data, TEST_YEAR)
        names = ARTIFACTS[task.name]

        held, held_warnings = fit_selected(task, choice, train)
        held_again, _ = fit_selected(task, choice, train)
        final, final_warnings = fit_selected(task, choice, data)
        final_again, _ = fit_selected(task, choice, data)
        determinism = {
            "holdout_refit_identical": predict(task, held, data).tobytes() == predict(task, held_again, data).tobytes(),
            "final_refit_identical": predict(task, final, data).tobytes() == predict(task, final_again, data).tobytes(),
            "rows_compared": int(len(data)),
        }
        if not all(v for k, v in determinism.items() if k.endswith("identical")):
            raise ValueError(f"{task.name}: refitting gave different probabilities: {determinism}")

        paths = {kind: model_dir / names[kind] for kind in ("holdout", "final")}
        joblib.dump(artifact(task, choice, held, train, HOLDOUT_VERSION, TEST_YEAR - 1, input_sha, held_warnings),
                    paths["holdout"])
        joblib.dump(artifact(task, choice, final, data, FINAL_VERSION, TEST_YEAR, input_sha, final_warnings),
                    paths["final"])
        # The proof runs on the artifact as saved on disk, not the in-memory model
        proof = holdout_proof(task, joblib.load(paths["holdout"])["model"], test, len(train), benchmark_dir,
                              holdout_report)

        with threadpool_limits(limits=1):
            prior, _ = fit(task, BASELINE, {}, train)
        baseline = score(task, test, probabilities(task, prior, test))
        report["tasks"][task.name] = {
            "algorithm": choice["selected"], "estimator": ALGORITHM, "params": choice["params"],
            "features": task.features, "target": task.target, "classes": list(task.classes),
            "artifacts": {
                kind: {"file": f"models/final/{names[kind]}", "sha256": sha256(paths[kind]),
                       "version": HOLDOUT_VERSION if kind == "holdout" else FINAL_VERSION,
                       **fold_info(frame, frame, TEST_YEAR - 1 if kind == "holdout" else TEST_YEAR)}
                for kind, frame in (("holdout", train), ("final", data))
            },
            "holdout_reproduction": proof,
            "determinism": determinism,
            "class_rates": {
                "through_2025": {str(c): float((train[task.target] == c).mean()) for c in task.classes},
                "through_2026": {str(c): float((data[task.target] == c).mean()) for c in task.classes},
            },
            "baseline_2026": {"model": BASELINE, "train_rows": int(len(train)), "metrics": baseline},
        }
        for entry in report["tasks"][task.name]["artifacts"].values():
            for key in ("year", "evaluation_rows", "evaluation_matches"):
                entry.pop(key)
        print(f"{task.name}: saved {names['holdout']} and {names['final']}; max |forecast difference| "
              f"{proof['max_abs_forecast_difference']:.3g}; refits identical", flush=True)
    write_json(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data", type=Path, default=Path("data/processed"))
    parser.add_argument("--models", type=Path, default=Path("models/final"))
    parser.add_argument("--benchmark", type=Path, default=Path("reports/model_benchmark"))
    parser.add_argument("--output", type=Path, default=Path("reports/model_benchmark/final_models.json"))
    args = parser.parse_args()
    run(args.data, args.models, args.benchmark, args.output)
    print(f"Wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
