"""The final models are the benchmark-selected models, and only they can be served.

Expected values come from the benchmark's saved files (selection.json, holdout_2026.json and the
per-example 2026 forecasts) and the modelling tables, with metrics recomputed here with sklearn.
"""
import json
import shutil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from cricketlens import final_models
from cricketlens.api.services.prediction_service import PredictionService
from cricketlens.hashing import file_sha256, table_sha256
from cricketlens.model_benchmark import TASKS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "model_benchmark"
FINAL = ROOT / "models" / "final"
SELECTION = json.loads((REPORT / "selection.json").read_text(encoding="utf-8"))
HOLDOUT = json.loads((REPORT / "holdout_2026.json").read_text(encoding="utf-8"))
SUMMARY = json.loads((REPORT / "final_models.json").read_text(encoding="utf-8"))
# The archived Stage 3 artifacts as committed before the final models were added; they must never change
ARCHIVED = {
    "batter_deployment_through_2026.joblib": "47b8bb25af7603ab7c6ed6815638df0ab98c5cffd0e7c4bfbc67547faca473a5",
    "batter_holdout_train_through_2025.joblib": "0dfcec75e159feee6a971547b672473c604401b33b2d13bd8ddcf038994fd7f1",
    "wicket_deployment_through_2026.joblib": "43d0b628f8ebe9f43d33bbba28ae1047a29f97814e06a0738f3e233c238f1ea5",
    "wicket_holdout_train_through_2025.joblib": "4861ee55e3757f1674cd5eebb2ca1da0aa38f8528b55ef8b3da598e270064483",
}

pytestmark = pytest.mark.skipif(not FINAL.is_dir(), reason="final model artifacts not available")


def _table(task):
    return pd.read_csv(DATA / task.path, parse_dates=["date"], dtype={"batter_id": str})


@pytest.mark.parametrize("task", TASKS, ids=[t.name for t in TASKS])
def test_holdout_artifact_reproduces_the_benchmark_forecasts(task):
    saved = joblib.load(FINAL / f"{task.name}_hgb_through_2025.joblib")
    rows = _table(task)
    test = rows[rows.season == 2026].sort_values(["date", *task.keys]).reset_index(drop=True)
    expected = pd.read_csv(REPORT / f"{task.name}_holdout_forecasts.csv", float_precision="round_trip",
                           dtype={"batter_id": str})
    assert test[task.keys].astype(str).equals(expected[task.keys].astype(str))
    p = saved["model"].predict_proba(test[saved["columns"]])
    columns = [f"p_class_{c}" for c in task.classes]
    assert np.max(np.abs(p - expected[columns].to_numpy())) <= 1e-12
    # The 2026 metrics, recomputed with sklearn, equal holdout_2026.json
    y, metrics = test[task.target].to_numpy(), HOLDOUT[task.name]["metrics"]
    if task.name == "wicket":
        assert brier_score_loss(y, p[:, 1]) == pytest.approx(metrics["brier"], abs=1e-12)
        assert roc_auc_score(y, p[:, 1]) == pytest.approx(metrics["roc_auc"], abs=1e-12)
    else:
        p30, p50 = p[:, 1] + p[:, 2], p[:, 2]
        assert (p50 <= p30).all()
        assert brier_score_loss(y >= 1, np.clip(p30, 0, 1)) == pytest.approx(metrics["brier_30"], abs=1e-12)
        assert brier_score_loss(y == 2, p50) == pytest.approx(metrics["brier_50"], abs=1e-12)
    assert log_loss(y, p, labels=list(task.classes)) == pytest.approx(metrics["log_loss"], abs=1e-12)
    assert len(test) == HOLDOUT[task.name]["evaluation_rows"]


@pytest.mark.parametrize("task", TASKS, ids=[t.name for t in TASKS])
def test_artifacts_carry_the_frozen_selection(task):
    choice, rows = SELECTION["tasks"][task.name], _table(task)
    for kind, end, train in (("2025", 2025, rows[rows.season < 2026]), ("2026", 2026, rows)):
        saved = joblib.load(FINAL / f"{task.name}_hgb_through_{kind}.joblib")
        estimator = saved["model"].named_steps["model"]
        assert type(estimator).__name__ == "HistGradientBoostingClassifier"
        assert saved["name"] == choice["selected"] == "Histogram gradient boosting"
        assert saved["params"] == choice["params"]
        assert all(estimator.get_params()[k] == v for k, v in choice["params"].items())
        # The fixed settings the benchmark gives every boosting candidate
        assert (estimator.learning_rate, estimator.min_samples_leaf, estimator.early_stopping,
                estimator.random_state) == (0.06, 50, False, 42)
        assert saved["columns"] == choice["features"] and saved["target"] == choice["target"]
        assert saved["classes"] == list(task.classes) == [int(c) for c in estimator.classes_]
        assert saved["training_end"] == saved["train_end"] == end and saved["release"] == "final"
        assert saved["train_rows"] == len(train) and saved["train_matches"] == train.match_id.nunique()
        assert saved["train_start"] == "2008-04-18"
        assert saved["train_end_date"] == train.date.max().date().isoformat()
        assert saved["input_sha256"] == choice["input_sha256"] == table_sha256(DATA / task.path)
        assert saved["version"] == ("deployment_refit_2008_2026" if end == 2026 else "holdout_train_2008_2025")


def test_summary_file_describes_the_artifacts_on_disk():
    for name, task in SUMMARY["tasks"].items():
        for entry in task["artifacts"].values():
            assert file_sha256(ROOT / entry["file"]) == entry["sha256"]
        assert task["holdout_reproduction"]["max_abs_forecast_difference"] == 0
        assert task["determinism"]["holdout_refit_identical"] and task["determinism"]["final_refit_identical"]
        assert task["params"] == SELECTION["tasks"][name]["params"]


def test_a_fresh_fit_through_the_benchmark_code_equals_the_saved_holdout_model():
    task = TASKS[0]
    rows = _table(task).sort_values(["date", *task.keys]).reset_index(drop=True)
    train = rows[rows.season < 2026]
    model, _ = final_models.fit_selected(task, SELECTION["tasks"][task.name], train)
    saved = joblib.load(FINAL / "wicket_hgb_through_2025.joblib")["model"]
    assert model.predict_proba(rows[task.features]).tobytes() == saved.predict_proba(rows[task.features]).tobytes()


def test_archived_stage3_artifacts_are_unchanged():
    assert {p.name: file_sha256(p) for p in sorted((ROOT / "models").glob("*.joblib"))} == ARCHIVED


# ------------------------------------------------------------------ the API serves only the final models

def _service_with(tmp_path, kind, artifact):
    for name in ("wicket_hgb_through_2026.joblib", "batter_hgb_through_2026.joblib"):
        shutil.copy(FINAL / name, tmp_path / name)
    joblib.dump(artifact, tmp_path / f"{kind}_hgb_through_2026.joblib")
    service = PredictionService(model_dir=tmp_path)
    return service.status()


def test_an_archived_stage3_model_is_refused(tmp_path):
    archived = joblib.load(ROOT / "models" / "wicket_deployment_through_2026.joblib")
    status = _service_with(tmp_path, "wicket", archived)
    assert status["wicket"]["available"] is False and "final-release" in status["wicket"]["detail"]
    assert status["batter"]["available"] is True


def test_other_settings_are_refused(tmp_path):
    saved = joblib.load(FINAL / "batter_hgb_through_2026.joblib")
    saved["model"].named_steps["model"].set_params(max_leaf_nodes=15)
    status = _service_with(tmp_path, "batter", saved)
    assert status["batter"]["available"] is False and "frozen selection" in status["batter"]["detail"]


def test_relabelled_settings_are_refused(tmp_path):
    saved = joblib.load(FINAL / "wicket_hgb_through_2026.joblib")
    status = _service_with(tmp_path, "wicket", dict(saved, params={**saved["params"], "max_iter": 140}))
    assert status["wicket"]["available"] is False and "frozen selection" in status["wicket"]["detail"]
