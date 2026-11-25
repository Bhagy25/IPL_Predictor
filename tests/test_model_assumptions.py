"""The assumption evidence in reports/model_benchmark/assumptions agrees with the data and the benchmark files.

Each check recomputes a number from the modelling tables or the benchmark CSVs here, independently of
cricketlens.model_assumptions, and compares it with summary.json or the evidence CSVs.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
BENCH = ROOT / "reports" / "model_benchmark"
OUT = BENCH / "assumptions"
SUMMARY = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
TABLES = {"wicket": ("stage03_wicket_full_history_2008_2026.csv", "wicket_next_over"),
          "batter": ("stage03_batter_full_history_2008_2026.csv", "milestone_class")}
MODELS = ["Class-prior baseline", "Logistic regression", "Decision tree", "Random forest",
          "Histogram gradient boosting", "Gaussian naive Bayes", "Multilayer perceptron"]


@pytest.fixture(scope="module", params=["wicket", "batter"])
def task(request):
    name, target = TABLES[request.param]
    return request.param, pd.read_csv(DATA / name, parse_dates=["date"]), target


def test_folds_are_chronological_and_disjoint(task):
    kind, data, _ = task
    folds = pd.read_csv(OUT / "folds.csv").query("task == @kind")
    assert folds.evaluation_season.tolist() == [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
    for year in folds.evaluation_season:
        train, valid = data[data.season < year], data[data.season == year]
        assert train.date.max() < valid.date.min()
        assert not set(train.match_id) & set(valid.match_id)
    assert (folds.shared_matches == 0).all() and (folds.gap_days > 0).all()


def test_class_balance_and_majority_floor(task):
    kind, data, target = task
    balance = SUMMARY["tasks"][kind]["class_balance"]
    shares = data[target].value_counts(normalize=True).sort_index()
    assert balance["class_shares"] == {str(k): round(v, 4) for k, v in shares.items()}
    floors = []
    for year in range(2021, 2026):
        train, valid = data[data.season < year], data[data.season == year]
        floors.append((valid[target] == train[target].mode()[0]).mean())
    assert balance["majority_class_accuracy_mean"] == pytest.approx(np.mean(floors), abs=5e-5)


def test_unseen_levels_equal_the_data_audit(task):
    kind, _, _ = task
    audit = json.loads((BENCH / "data_audit.json").read_text(encoding="utf-8"))[kind]["rows_with_unseen_categories"]
    assert SUMMARY["tasks"][kind]["unseen_levels"] == {k: sum(v.values()) for k, v in audit.items()}


def test_season_rates_and_drift(task):
    kind, data, target = task
    rates = pd.read_csv(OUT / "rates.csv").query("task == @kind").set_index("season")
    column = "rate_wicket" if kind == "wicket" else "rate_30+"
    event = data[target] == 1 if kind == "wicket" else data[target] >= 1
    assert np.allclose(rates[column], event.groupby(data.season).mean().loc[rates.index], atol=1e-12)
    drift = pd.read_csv(OUT / "drift.csv").query("task == @kind")
    row = drift.loc[drift.smd.abs().idxmax()]
    ref, cur = data[data.season < row.season][row.feature], data[data.season == row.season][row.feature]
    smd = (cur.mean() - ref.mean()) / np.sqrt((cur.var() + ref.var()) / 2)
    assert row.smd == pytest.approx(smd, rel=1e-9)


def test_mlp_epoch_cap_counts_equal_the_benchmark_logs(task):
    kind, _, _ = task
    evidence = SUMMARY["tasks"][kind]["algorithms"]["Multilayer perceptron"]["evidence"]
    for stage in ("tuning", "validation", "learning"):
        frame = pd.read_csv(BENCH / f"{kind}_{stage}.csv")
        mlp = frame[frame.model == "Multilayer perceptron"]
        assert evidence["fits_stopped_by_epoch_cap"][stage] == int(mlp.fit_warnings.notna().sum())
        assert evidence["mlp_fits"][stage] == len(mlp)
        assert frame[frame.model != "Multilayer perceptron"].fit_warnings.isna().all()
    seeds = pd.read_csv(OUT / "mlp_seeds.csv").query("task == @kind")
    assert len(seeds) >= 3 and evidence["seed_brier_range_2025"] == pytest.approx(np.ptp(seeds.brier), abs=1e-6)


def test_convergence_numbers_equal_the_learning_and_gap_tables(task):
    kind, _, _ = task
    conv = SUMMARY["tasks"][kind]["convergence"]
    learning = pd.read_csv(BENCH / f"{kind}_learning.csv")
    hgb = learning[learning.model == "Histogram gradient boosting"].groupby("training_fraction").validation_brier.mean()
    assert conv["selected_plateau"]["change_75_to_100"] == pytest.approx(hgb[1.0] - hgb[0.75], abs=1e-6)
    assert conv["selected_plateau"]["change_50_to_75"] == pytest.approx(hgb[0.75] - hgb[0.5], abs=1e-6)
    gaps = pd.read_csv(BENCH / f"{kind}_paired_brier_gaps.csv")
    for model, entry in conv["paired_gaps_vs_selected"].items():
        assert entry["mean"] == pytest.approx(gaps[model].mean(), abs=1e-6)
        assert entry["selected_better_seasons"] == int((gaps[model] > 0).sum())
    comparison = pd.read_csv(BENCH / f"{kind}_comparison.csv")
    assert conv["leaders"] == comparison.model.head(3).tolist()
    assert conv["runner_up_gap"] == pytest.approx(comparison.brier_mean[1] - comparison.brier_mean[0], abs=1e-6)


def test_every_algorithm_and_data_assumption_has_a_verdict():
    allowed = {"Holds", "Partially holds", "Violated"}
    algos = SUMMARY["verdicts"]["algorithms"]
    assert [a["model"] for a in algos] == MODELS
    assert all({a["verdict"], a["wicket_verdict"], a["batter_verdict"]} <= allowed for a in algos)
    assert len(SUMMARY["verdicts"]["data"]) == 8
    assert all(d["verdict"] in allowed and d["evidence"] and d["consequence"] for d in SUMMARY["verdicts"]["data"])


def test_eligibility_counts_add_up():
    rows = {(r["scope"], r["rule"]): r["count"] for r in SUMMARY["eligibility"]}
    matches = pd.read_csv(DATA / "matches.csv")
    assert rows[("archive", "matches in the archive")] == len(matches) == 1243
    assert rows[("archive", "D/L-marked matches")] == (matches.outcome_method == "D/L").sum()
    assert rows[("wicket", "eligible rows")] == len(pd.read_csv(DATA / TABLES["wicket"][0], usecols=["match_id"]))
    assert rows[("batter", "eligible rows")] == len(pd.read_csv(DATA / TABLES["batter"][0], usecols=["match_id"]))
