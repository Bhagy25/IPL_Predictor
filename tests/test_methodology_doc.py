"""Key numbers quoted in docs/MODEL_METHODOLOGY.md equal the benchmark, final-model and assumption files.

Each expected string is formatted here from the files, the way the document prints it, and must appear in
the document verbatim.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "MODEL_METHODOLOGY.md").read_text(encoding="utf-8")
BENCH = ROOT / "reports" / "model_benchmark"
HOLDOUT = json.loads((BENCH / "holdout_2026.json").read_text(encoding="utf-8"))
FINAL = json.loads((BENCH / "final_models.json").read_text(encoding="utf-8"))
SELECTION = json.loads((BENCH / "selection.json").read_text(encoding="utf-8"))
SUMMARY = json.loads((BENCH / "assumptions" / "summary.json").read_text(encoding="utf-8"))
STAGE3 = json.loads((ROOT / "reports/stage_03/session_03/stage03_session03_final_results.json").read_text(encoding="utf-8"))


def pct(x):
    return f"{100 * x:.2f}%"


@pytest.mark.parametrize("task", ["wicket", "batter"])
def test_comparison_tables_equal_the_csv(task):
    table = pd.read_csv(BENCH / f"{task}_comparison.csv")
    for rank, r in enumerate(table.itertuples(index=False), start=1):
        name = f"**{r.model}**" if rank == 1 else r.model
        brier = f"{r.brier_mean:.5f} ± {r.brier_std:.5f}"
        brier = f"**{brier}**" if rank == 1 else brier
        row = (f"| {rank} | {name} | {brier} | {r.log_loss_mean:.5f} ± {r.log_loss_std:.5f} | "
               f"{pct(r.accuracy_mean)} ± {100 * r.accuracy_std:.2f} | "
               f"{pct(r.balanced_accuracy_mean)} ± {100 * r.balanced_accuracy_std:.2f} | "
               f"{r.macro_f1_mean:.4f} ± {r.macro_f1_std:.4f} | {r.roc_auc_mean:.4f} ± {r.roc_auc_std:.4f} | "
               f"{r.average_precision_mean:.4f} ± {r.average_precision_std:.4f} |")
        assert row in DOC, row


def test_selected_settings_and_rule():
    for task in ("wicket", "batter"):
        choice = SELECTION["tasks"][task]
        assert choice["selected"] == "Histogram gradient boosting"
        assert choice["params"] == {"max_leaf_nodes": 7, "max_iter": 60, "l2_regularization": 2.0}
    assert "`max_leaf_nodes=7`, `max_iter=60`, `l2_regularization=2.0`" in DOC


@pytest.mark.parametrize("task", ["wicket", "batter"])
def test_holdout_table_and_baseline(task):
    h = HOLDOUT[task]
    m = h["metrics"]
    label = "Next-over wicket" if task == "wicket" else "Batter milestones"
    row = (f"| {label} | {h['evaluation_rows']:,} ({h['evaluation_matches']}) | {m['brier']:.5f} | {m['log_loss']:.5f} | "
           f"{pct(m['accuracy'])} | {pct(m['balanced_accuracy'])} | {m['roc_auc']:.5f} | {m['average_precision']:.5f} |")
    assert row in DOC, row
    base = FINAL["tasks"][task]["baseline_2026"]["metrics"]["brier"]
    assert f"Brier {m['brier']:.5f} vs\n  {base:.5f}" in DOC or f"{m['brier']:.5f} vs {base:.5f}" in DOC
    rows = h["confusion_matrix"]
    for line in rows:
        assert "[" + ", ".join(f"{v:,}" for v in line) + "]" in DOC


def test_holdout_training_rows_and_calibration_numbers():
    w, b = HOLDOUT["wicket"], HOLDOUT["batter"]
    assert f"{w['train_rows']:,} wicket checkpoints from {w['train_matches']:,} matches" in DOC
    assert f"{b['train_rows']:,} batter innings from {b['train_matches']:,} matches" in DOC
    assert f"{w['class_counts']['1']} events ({pct(w['metrics']['observed_rate_wicket'])})" in DOC
    assert f"mean forecast of {pct(w['metrics']['mean_probability_wicket'])}" in DOC
    bm = b["metrics"]
    assert f"{pct(bm['observed_rate_30'])} reached 30" in DOC and f"{pct(bm['observed_rate_50'])} reached 50" in DOC
    assert f"{pct(bm['mean_probability_30'])} and {pct(bm['mean_probability_50'])}" in DOC
    assert f"Brier {STAGE3['wicket']['holdout_2026']['brier_score']}" in DOC
    assert f"Brier {STAGE3['batter']['holdout_2026']['avg_milestone_brier']}" in DOC


def test_learning_curve_and_paired_gaps():
    for task in ("wicket", "batter"):
        conv = SUMMARY["tasks"][task]["convergence"]
        curve = conv["selected_plateau"]["validation_brier_by_fraction"]
        label = "Wicket" if task == "wicket" else "Batter"
        assert f"| {label} | " + " | ".join(f"{curve[k]:.6f}" for k in ("0.1", "0.25", "0.5", "0.75", "1.0")) + " |" in DOC
        gaps = pd.read_csv(BENCH / f"{task}_paired_brier_gaps.csv")
        for model in ("Random forest", "Multilayer perceptron", "Logistic regression", "Decision tree",
                      "Class-prior baseline", "Gaussian naive Bayes"):
            g = gaps[model]
            assert f"{g.mean():.6f} ± {g.std():.6f} | {int((g > 0).sum())} of 5" in DOC, (task, model)
        learning = pd.read_csv(BENCH / f"{task}_learning.csv")
        matches = learning[learning.model == "Histogram gradient boosting"].groupby("training_fraction").train_matches.mean()
        assert f"{matches.iloc[0]:.0f} → {matches.iloc[-1]:.0f}" in DOC
        spread = conv["leader_brier_spread_by_fraction"]
        assert f"{spread['0.1']:.6f}" in DOC and f"{spread['1.0']:.6f}" in DOC


def test_assumption_verdicts_and_key_evidence():
    for row in SUMMARY["verdicts"]["algorithms"]:
        assert f"| {row['model']} | {row['wicket_verdict']} | {row['batter_verdict']} |" in DOC
    for row in SUMMARY["verdicts"]["data"]:
        assert f"| {row['assumption']} | {row['verdict']} |" in DOC
    w, b = SUMMARY["tasks"]["wicket"], SUMMARY["tasks"]["batter"]
    wl, bl = w["algorithms"]["Logistic regression"]["evidence"], b["algorithms"]["Logistic regression"]["evidence"]
    assert f"largest VIF {wl['max_vif']}" in DOC and f"{bl['max_vif']}" in DOC
    assert f"{wl['events_per_parameter']['events_per_parameter']}" in DOC
    assert f"{bl['events_per_parameter']['events_per_parameter']}" in DOC
    assert f"{len(wl['clearly_nonlinear_features'])} of {wl['features_tested']}" in DOC
    assert f"all {len(bl['clearly_nonlinear_features'])} batter" in DOC and bl["features_tested"] == 17
    nb_w, nb_b = (t["algorithms"]["Gaussian naive Bayes"]["evidence"] for t in (w, b))
    assert f"{nb_w['within_class_pairs_abs_corr_at_least_0.5']} wicket and {nb_b['within_class_pairs_abs_corr_at_least_0.5']} batter" in DOC
    assert f"{nb_w['calibration_2025']['Gaussian naive Bayes']['expected_calibration_error']}" in DOC
    assert f"{nb_b['calibration_2025']['Gaussian naive Bayes']['expected_calibration_error']}" in DOC
    mlp_w, mlp_b = (t["algorithms"]["Multilayer perceptron"]["evidence"] for t in (w, b))
    assert mlp_w["fits_stopped_by_epoch_cap"]["tuning"] + mlp_w["fits_stopped_by_epoch_cap"]["learning"] == 34
    assert f"{mlp_w['seed_brier_range_2025']:.6f}" in DOC and f"{mlp_b['seed_brier_range_2025']:.6f}" in DOC
    assert f"{mlp_w['weights_and_biases']:,}" in DOC and f"{mlp_b['weights_and_biases']:,}" in DOC
    hgb_w, hgb_b = (t["algorithms"]["Histogram gradient boosting"]["evidence"] for t in (w, b))
    for e in (hgb_w, hgb_b):
        assert f"{e['excess_train_validation_gap']:.6f}" in DOC and f"{e['train_validation_gap']:.6f}" in DOC
    assert f"{w['class_balance']['majority_class_accuracy_mean']:.2%}" in DOC
    assert f"{b['class_balance']['majority_class_accuracy_mean']:.2%}" in DOC


def test_eligibility_table_equals_the_counts():
    for row in SUMMARY["eligibility"]:
        if row["rule"] == "matches in the archive":
            continue
        assert f"| {row['count']:,} |" in DOC or f"**{row['count']:,}**" in DOC, row


def test_final_artifacts_reproduce_exactly():
    for task in ("wicket", "batter"):
        assert FINAL["tasks"][task]["holdout_reproduction"]["max_abs_forecast_difference"] == 0
    assert "maximum absolute difference 0" in DOC


def test_report_final_decision_numbers():
    report = (ROOT / "reports" / "REPORT_DRAFT.md").read_text(encoding="utf-8")
    section = report[report.index("### 8.9 Final model decision"):]
    assert "weak evidence for switching" not in report
    for task in ("wicket", "batter"):
        artifact = FINAL["tasks"][task]["artifacts"]["final"]
        assert f"{artifact['train_rows']:,}" in section
        plateau = SUMMARY["tasks"][task]["convergence"]["selected_plateau"]
        assert f"{plateau['change_50_to_75']:+.6f}".replace("-", "−") in section
        assert f"{plateau['change_75_to_100']:+.6f}".replace("-", "−") in section
        hgb = SUMMARY["tasks"][task]["algorithms"]["Histogram gradient boosting"]["evidence"]
        assert f"{hgb['excess_train_validation_gap']:.6f}" in section
        m, base = HOLDOUT[task]["metrics"]["brier"], FINAL["tasks"][task]["baseline_2026"]["metrics"]["brier"]
        assert f"{m:.5f} vs {base:.5f}" in section
        assert f"{SUMMARY['tasks'][task]['class_balance']['majority_class_accuracy_mean']:.2%}" in section
        gap = SUMMARY["tasks"][task]["convergence"]["paired_gaps_vs_selected"]["Random forest"]["mean"]
        assert f"{gap:.6f}".rstrip("0") in section
    assert STAGE3["wicket"]["holdout_2026"]["brier_score"] > HOLDOUT["wicket"]["metrics"]["brier"]
    assert STAGE3["batter"]["holdout_2026"]["avg_milestone_brier"] > HOLDOUT["batter"]["metrics"]["brier"]


def test_readme_model_tables():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    w, b = (pd.read_csv(BENCH / f"{t}_comparison.csv").set_index("model") for t in ("wicket", "batter"))
    for model in w.index:
        mark = "✓" if model == "Histogram gradient boosting" else ""
        row = (f"| {model} | {w.loc[model, 'brier_mean']:.5f} ± {w.loc[model, 'brier_std']:.5f} | "
               f"{b.loc[model, 'brier_mean']:.5f} ± {b.loc[model, 'brier_std']:.5f} | {mark} |")
        assert row.replace("|  |", "| |") in readme, row
    hw, hb = HOLDOUT["wicket"]["metrics"], HOLDOUT["batter"]["metrics"]
    bw, bb = (FINAL["tasks"][t]["baseline_2026"]["metrics"] for t in ("wicket", "batter"))
    assert f"| Brier score | {hw['brier']:.4f} | {bw['brier']:.4f} |" in readme
    assert f"| Log loss | {hw['log_loss']:.4f} | {bw['log_loss']:.4f} |" in readme
    assert f"| Brier 30+ | {hb['brier_30']:.4f} | {bb['brier_30']:.4f} |" in readme
    assert f"| Brier 50+ | {hb['brier_50']:.4f} | {bb['brier_50']:.4f} |" in readme
    assert f"| Log loss (3 classes) | {hb['log_loss']:.4f} | {bb['log_loss']:.4f} |" in readme
    assert f"| ROC AUC 30+ / 50+ | {hb['roc_auc_30']:.4f} / {hb['roc_auc_50']:.4f} |" in readme


def test_label_selection_unseen_rows_and_grid_edges_are_quoted():
    labels = SUMMARY["tasks"]["wicket"]["label_selection"]
    flat = " ".join(DOC.split())
    for doc in (DOC, (ROOT / "README.md").read_text(encoding="utf-8"),
                (ROOT / "reports" / "REPORT_DRAFT.md").read_text(encoding="utf-8")):
        doc = " ".join(doc.split())
        assert f"{pct(labels['eligible']['event_rate'])} on all" in doc or f"{pct(labels['eligible']['event_rate'])} against" in doc
        assert pct(labels["complete_overs_only"]["event_rate"]) in doc
        assert f"{pct(labels['late_second_innings_eligible']['event_rate'])} against {pct(labels['late_second_innings_complete_overs_only']['event_rate'])}" in doc
    edges = [e["at_edge"] for t in ("wicket", "batter") for e in SUMMARY["tasks"][t]["tuning_grid_edges"].values()]
    assert f"{sum(edges)} of the {len(edges)} chosen settings" in flat
    for task in ("wicket", "batter"):
        rows = SUMMARY["tasks"][task]["unseen_level_rows"]
        assert f"{task} 2021: {rows['2021']:,}, 2022: {rows['2022']:,}" in flat
    no_result = next(r["count"] for r in SUMMARY["eligibility"] if r["rule"] == "eligible rows from no-result matches (kept)")
    assert f"({no_result} wicket rows from no-result matches)" in flat
    assert "uninterrupted" not in DOC and "fixed before any 2026 score" not in DOC


def test_learning_curve_wording_matches_the_per_season_changes():
    w, b = (SUMMARY["tasks"][t]["convergence"]["selected_plateau"] for t in ("wicket", "batter"))
    batter_lower = sum(v < 0 for v in b["per_season_change_75_to_100"].values())
    wicket_lower = sum(v < 0 for v in w["per_season_change_75_to_100"].values())
    forest = SUMMARY["tasks"]["batter"]["convergence"]["paired_gaps_vs_selected"]["Random forest"]["mean"]
    assert batter_lower == 5 and abs(b["change_75_to_100"]) > forest
    assert f"lower in {wicket_lower} of 5 seasons from 75% to\n  100%" in DOC
    assert "negative in\n  all 5 seasons" in DOC


def test_readme_limitation_quotes_the_final_model():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    m = HOLDOUT["wicket"]["metrics"]
    base = FINAL["tasks"]["wicket"]["baseline_2026"]["metrics"]["brier"]
    assert f"(2026 Brier {m['brier']:.4f} vs {base:.4f}, ROC-AUC\n  {m['roc_auc']:.2f})" in readme
    assert "0.2005" not in readme
