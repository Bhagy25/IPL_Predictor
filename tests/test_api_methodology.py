"""GET /api/methodology returns exactly what the benchmark, final-model and assumption files contain.

Expected values are read or recomputed here from reports/model_benchmark with pandas, not the service.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cricketlens.api.app import app
from cricketlens.api.services.methodology_service import MethodologyService

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "reports" / "model_benchmark"
SELECTION = json.loads((BENCH / "selection.json").read_text(encoding="utf-8"))
HOLDOUT = json.loads((BENCH / "holdout_2026.json").read_text(encoding="utf-8"))
FINAL = json.loads((BENCH / "final_models.json").read_text(encoding="utf-8"))
SUMMARY = json.loads((BENCH / "assumptions" / "summary.json").read_text(encoding="utf-8"))
TASKS = ("wicket", "batter")
METRICS = ("brier", "log_loss", "accuracy", "balanced_accuracy", "macro_f1", "roc_auc", "average_precision")


@pytest.fixture(scope="module")
def body():
    r = client.get("/api/methodology")
    assert r.status_code == 200, r.text
    return r.json()


def test_decision_is_the_frozen_selection(body):
    for task in TASKS:
        assert SELECTION["tasks"][task]["selected"] == body["decision"]["algorithm"] == "Histogram gradient boosting"
        assert SELECTION["tasks"][task]["params"] == body["decision"]["params"]
    assert body["decision"]["validation_years"] == SELECTION["validation_years"]
    assert body["decision"]["tuning_years"] == SELECTION["tuning_years"]
    assert [s["step"] for s in body["workflow"]] == list(range(1, 11))
    matches = pd.read_csv(ROOT / "data" / "processed" / "matches.csv")
    assert body["workflow"][0]["detail"].startswith(
        f"{len(matches):,} men's IPL matches ({matches.date.min()[:4]}–{matches.date.max()[:4]})")


@pytest.mark.parametrize("task", TASKS)
def test_comparison_equals_the_csv(body, task):
    table = pd.read_csv(BENCH / f"{task}_comparison.csv", float_precision="round_trip")
    rows = body["comparison"][task]
    assert [r["model"] for r in rows] == table.model.tolist() and [r["rank"] for r in rows] == list(range(1, 8))
    for r, (_, expected) in zip(rows, table.iterrows()):
        for m in METRICS:
            assert r[f"{m}_mean"] == expected[f"{m}_mean"] and r[f"{m}_std"] == expected[f"{m}_std"]
    assert [r["model"] for r in rows if r["selected"]] == ["Histogram gradient boosting"]


@pytest.mark.parametrize("task", TASKS)
def test_learning_curves_equal_the_fold_means(body, task):
    learning = pd.read_csv(BENCH / f"{task}_learning.csv")
    points = body["learning_curves"][task]
    assert len(points) == 7 * 5
    for p in points:
        rows = learning[(learning.model == p["model"]) & (learning.training_fraction == p["training_fraction"])]
        assert len(rows) == 5
        assert p["train_matches"] == pytest.approx(rows.train_matches.mean(), abs=1e-9)
        for metric in ("brier", "log_loss", "accuracy", "balanced_accuracy"):
            assert p[f"validation_{metric}"] == pytest.approx(rows[f"validation_{metric}"].mean(), abs=1e-12)
            assert p[f"validation_{metric}_sd"] == pytest.approx(rows[f"validation_{metric}"].std(), abs=1e-12)
        assert p["train_brier"] == pytest.approx(rows.train_brier.mean(), abs=1e-12)


@pytest.mark.parametrize("task", TASKS)
def test_paired_gaps_equal_the_csv(body, task):
    gaps = pd.read_csv(BENCH / f"{task}_paired_brier_gaps.csv", float_precision="round_trip")
    api = {(g["year"], g["model"]): g["gap"] for g in body["paired_gaps"][task]}
    assert len(api) == 5 * 6
    for _, row in gaps.iterrows():
        for model in gaps.columns.drop(["year", "Histogram gradient boosting"]):
            assert api[(int(row.year), model)] == row[model]


@pytest.mark.parametrize("task", TASKS)
def test_holdout_metrics_calibration_and_confusion(body, task):
    h = body["holdout"][task]
    assert h["metrics"] == HOLDOUT[task]["metrics"] and h["confusion_matrix"] == HOLDOUT[task]["confusion_matrix"]
    assert h["baseline_metrics"] == FINAL["tasks"][task]["baseline_2026"]["metrics"]
    assert (h["rows"], h["matches"]) == (HOLDOUT[task]["evaluation_rows"], HOLDOUT[task]["evaluation_matches"])
    assert "retrospective" in h["caveat"] and "no independent test season" in h["caveat"]
    # The calibration bins equal the saved table and a recomputation from the per-row forecasts
    saved = pd.read_csv(BENCH / f"{task}_holdout_calibration.csv", float_precision="round_trip")
    assert [(b["event"], b["bin"], b["rows"]) for b in h["calibration"]] == list(
        zip(saved.event.astype(str), saved.bin, saved.rows))
    forecasts = pd.read_csv(BENCH / f"{task}_holdout_forecasts.csv")
    if task == "wicket":
        events = [("wicket", forecasts.wicket_next_over == 1, forecasts.p_class_1)]
    else:
        events = [("30", forecasts.milestone_class >= 1, forecasts.p_30), ("50", forecasts.milestone_class == 2, forecasts.p_50)]
    for label, actual, p in events:
        bins = np.minimum((p * 10).astype(int), 9)
        mine = pd.DataFrame({"bin": bins, "actual": actual, "p": p}).groupby("bin").agg(
            rows=("actual", "size"), observed=("actual", "mean"), mean_p=("p", "mean"))
        api = [b for b in h["calibration"] if b["event"] == label]
        assert [b["rows"] for b in api] == mine.rows.tolist()
        assert np.allclose([b["observed_rate"] for b in api], mine.observed, atol=1e-12)
        assert np.allclose([b["mean_probability"] for b in api], mine.mean_p, atol=1e-12)


def test_tasks_and_data_assumptions(body):
    for t in body["tasks"]:
        data = pd.read_csv(ROOT / "data" / "processed" / f"stage03_{t['kind']}_full_history_2008_2026.csv",
                           usecols=["match_id", "season"])
        assert t["rows"] == len(data) and t["matches"] == data.match_id.nunique()
        assert t["test_rows"] == int((data.season == 2026).sum())
        assert t["majority_class_accuracy"] == SUMMARY["tasks"][t["kind"]]["class_balance"]["majority_class_accuracy_mean"]
    assert body["data_assumptions"] == SUMMARY["verdicts"]["data"]
    assert body["eligibility"] == SUMMARY["eligibility"]


def test_algorithm_cards(body):
    names = [a["name"] for a in body["algorithms"]]
    assert names == ["Class-prior baseline", "Logistic regression", "Decision tree", "Random forest",
                     "Histogram gradient boosting", "Gaussian naive Bayes", "Multilayer perceptron"]
    tuning = pd.read_csv(BENCH / "assumptions" / "tuning.csv")
    for a in body["algorithms"]:
        assert a["selected"] == (a["name"] == "Histogram gradient boosting")
        assert a["how_it_works"] and a["formula"] and a["assumptions"] and a["evidence"] and a["decision"]
        for task in TASKS:
            assert a["verdicts"][task] == SUMMARY["tasks"][task]["algorithms"][a["name"]]["verdict"]
            chosen = SELECTION["tasks"][task]["chosen_settings"][a["name"]]
            assert [g["chosen"] for g in a["grid"][task]] == [g["setting"] == chosen for g in a["grid"][task]]
            rows = tuning[(tuning.task == task) & (tuning.model == a["name"])]
            assert [g["tuning_brier_mean"] for g in a["grid"][task]] == pytest.approx(rows.tuning_brier_mean.tolist())
            table = pd.read_csv(BENCH / f"{task}_comparison.csv")
            assert a["results"][task]["rank"] == table.model.tolist().index(a["name"]) + 1
            assert a["results"][task]["brier_mean"] == pytest.approx(
                table.set_index("model").loc[a["name"], "brier_mean"], abs=1e-15)
            if a["name"] != "Histogram gradient boosting":
                gaps = pd.read_csv(BENCH / f"{task}_paired_brier_gaps.csv")[a["name"]]
                assert a["results"][task]["seasons_selected_better"] == int((gaps > 0).sum())
                assert f"{a['results'][task]['paired_gap_mean']:.6f}" in a["decision"]
    tree = next(a for a in body["algorithms"] if a["name"] == "Decision tree")
    assert all(next(g for g in tree["grid"][t] if g["chosen"])["params"] == {"max_depth": 3, "min_samples_leaf": 100}
               for t in TASKS)  # the evidence sentence says "for both tasks"
    logistic = next(a for a in body["algorithms"] if a["name"] == "Logistic regression")
    assert all(next(g for g in logistic["grid"][t] if g["chosen"])["params"] == {"C": 0.05} for t in TASKS)


def test_missing_report_is_503(tmp_path, monkeypatch):
    service = MethodologyService(report_dir=tmp_path)
    monkeypatch.setattr("cricketlens.api.services.methodology_service.methodology_service", service)
    r = client.get("/api/methodology")
    assert r.status_code == 503 and str(tmp_path) not in r.text
