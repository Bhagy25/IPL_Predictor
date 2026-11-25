"""The prediction methodology: benchmark, assumption evidence and the final models' 2026 test.

Read-only. Every number comes from reports/model_benchmark/ (selection.json, holdout_2026.json,
final_models.json, data_audit.json, the comparison, learning, paired-gap and calibration CSVs, and
assumptions/summary.json and tuning.csv), loaded once and cached. The fixed explanatory text describes how
each algorithm works and what it assumes; sentences that quote numbers are formatted from the files.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from cricketlens.api.settings import PROJECT_ROOT

REPORT_DIR = PROJECT_ROOT / "reports" / "model_benchmark"
TASKS = ("wicket", "batter")
SELECTED = "Histogram gradient boosting"
METRICS = ("brier", "log_loss", "accuracy", "balanced_accuracy", "macro_f1", "roc_auc", "average_precision")
CURVE_METRICS = ("brier", "log_loss", "accuracy", "balanced_accuracy")
TASK_TEXT = {
    "wicket": {
        "title": "Next-over wicket",
        "question": "After a completed over, will at least one team wicket fall in the next over?",
        "target": "1 if a wicket falls in the next over, otherwise 0",
        "output": "P(wicket in the next over)",
        "unit": "next-over checkpoints",
        "inputs": "Innings, completed overs, runs, wickets, run rate, last over's runs and wickets, batting and "
                  "bowling team, phase of the next over, venue: all known when the over ends.",
    },
    "batter": {
        "title": "Batter milestones",
        "question": "Before a match, will this batter score 30+ and 50+ runs, given that they bat?",
        "target": "Three classes: under 30, 30–49, 50+ runs",
        "output": "P(30+) = P(30–49) + P(50+); P(50+) = P(50+), so P(50+) never exceeds P(30+)",
        "unit": "batting innings",
        "inputs": "The batter's form from innings on earlier dates only (career, last 5 and last 10 innings, "
                  "record against the opponent and at the venue, days since the last innings), plus batting team, "
                  "opponent and venue.",
    },
}
WORKFLOW = [
    ("Data", "{matches:,} men's IPL matches ({first}–{last}) from Cricsheet ball-by-ball JSON."),
    ("Cleaning", "Legal balls, extras, super overs, D/L and no-result matches, franchise renames and venue "
                 "names standardised; every table verified against the raw files."),
    ("Feature construction", "Only what is known at prediction time: the score at the end of an over, or a "
                             "batter's innings on earlier dates."),
    ("Chronological splits", "Every model trains on earlier seasons and is scored on a later one; matches "
                             "never cross the split."),
    ("Tuning", "Three settings per algorithm, compared on 2018, 2019 and 2020."),
    ("Ranking", "Seven algorithms with their tuned settings, scored on each of 2021–2025."),
    ("Selection", "Lowest mean validation Brier score, log loss as tie-break: a rule fixed in advance."),
    ("2026 test", "The selected setting, trained on 2008–2025, scored once on 2026 (a retrospective test)."),
    ("Final refit", "The same setting refitted on all of 2008–2026."),
    ("Website", "The Prediction Arena serves the final models; this page shows the evidence."),
]
ALGORITHMS = {
    "Class-prior baseline": {
        "short": "Baseline",
        "how": "Gives every row the class shares seen in training. It uses no inputs and is the reference every "
               "other model must beat.",
        "formula": "p̂ₖ = nₖ / n",
        "assumptions": ["The share of each outcome stays the same from the training seasons to the next season."],
    },
    "Logistic regression": {
        "short": "Logistic",
        "how": "Adds up weighted inputs and turns the sum into a probability with the logistic (S-shaped) curve; "
               "a softmax version handles the three batter classes. An L2 penalty keeps the weights small.",
        "formula": "P(y=1|x) = 1 / (1 + e^−(β₀ + βᵀx))",
        "assumptions": ["The log-odds change in a straight line with each numeric input.",
                        "Inputs are not strongly collinear.",
                        "Observations are independent.",
                        "There are enough events per estimated weight."],
    },
    "Decision tree": {
        "short": "Tree",
        "how": "Splits the rows by one input at a time (for example, wickets ≥ 5) to make groups that are as "
               "pure as possible, and predicts each group's outcome shares.",
        "formula": "minimise Gini impurity G = 1 − Σₖ pₖ² at each split",
        "assumptions": ["No distributional assumption.",
                        "The pattern can be captured by a few axis-aligned thresholds.",
                        "A single tree is high-variance: small changes in the data change the tree."],
    },
    "Random forest": {
        "short": "Forest",
        "how": "Grows 160 trees, each on a bootstrap sample with a random subset of inputs at every split, and "
               "averages their probabilities.",
        "formula": "p̂(x) = (1/B) Σ_b T_b(x)",
        "assumptions": ["Averaging many decorrelated trees lowers variance without adding bias."],
    },
    "Histogram gradient boosting": {
        "short": "Boosting",
        "how": "Starts from the base rate and adds small trees one after another, each correcting the errors left "
               "so far, with a learning rate and an L2 penalty. Numeric inputs are grouped into at most 255 bins.",
        "formula": "F_M(x) = F₀ + Σₘ η·hₘ(x),  p = σ(F_M(x))",
        "assumptions": ["The signal is a sum of small interactions.",
                        "Binning the inputs loses little information.",
                        "The learning rate, iteration cap, leaf limit and penalty prevent overfitting."],
    },
    "Gaussian naive Bayes": {
        "short": "Naive Bayes",
        "how": "Combines the class shares with a bell-curve likelihood for each input, treating the inputs as "
               "independent within each class.",
        "formula": "P(y=k|x) ∝ πₖ Πⱼ N(xⱼ; μⱼₖ, σ²ⱼₖ)",
        "assumptions": ["Inputs are independent of each other within each class.",
                        "Each input follows a normal distribution within each class."],
    },
    "Multilayer perceptron": {
        "short": "Neural net",
        "how": "A small neural network: one or two hidden layers of ReLU units feed a probability output, fitted "
               "with the Adam optimiser and an L2 penalty.",
        "formula": "h = max(0, W₁x + b₁),  p = softmax(W₂h + b₂)",
        "assumptions": ["Inputs are standardised.",
                        "The optimiser reaches a good, seed-insensitive solution within the epoch budget.",
                        "There is enough data for the number of weights."],
    },
}
LIMITATIONS = [
    "Five validation seasons give a rough spread, not a confidence interval, and they share training history.",
    "Scoring and batter milestone rates have risen; a future season may differ again.",
    "The leading algorithms are statistically close; a different reasonable rule could pick the random forest.",
    "D/L-shortened innings and censored overs are excluded, so the forecasts describe ordinary innings.",
    "The batter forecast assumes the player bats; selection and batting position are not modelled.",
    "Debutants, new franchises and new venues rely on default values and the other inputs.",
    "2026 had been examined during development, so its score is a retrospective test; the models refitted "
    "through 2026 have no independent test season yet.",
]


class MethodologyUnavailable(Exception):
    """A benchmark or assumption file is missing (HTTP 503)."""


def _f(x: Any) -> float:
    return float(x)


class MethodologyService:
    def __init__(self, report_dir: Path = REPORT_DIR):
        self.report_dir = Path(report_dir)
        self._lock = threading.Lock()
        self._payload: Optional[Dict[str, Any]] = None

    def _json(self, name: str) -> Dict[str, Any]:
        path = self.report_dir / name
        if not path.is_file():
            raise MethodologyUnavailable(f"The model report {name} is not available.")
        return json.loads(path.read_text(encoding="utf-8"))

    def _csv(self, name: str) -> pd.DataFrame:
        path = self.report_dir / name
        if not path.is_file():
            raise MethodologyUnavailable(f"The model report {name} is not available.")
        return pd.read_csv(path, float_precision="round_trip")

    def get(self) -> Dict[str, Any]:
        with self._lock:
            if self._payload is None:
                self._payload = self._build()
            return self._payload

    # ------------------------------------------------------------------ building the payload

    def _build(self) -> Dict[str, Any]:
        selection, holdout = self._json("selection.json"), self._json("holdout_2026.json")
        final, audit = self._json("final_models.json"), self._json("data_audit.json")
        summary = self._json("assumptions/summary.json")
        tuning = self._csv("assumptions/tuning.csv")
        comparison = {t: self._csv(f"{t}_comparison.csv") for t in TASKS}
        learning = {t: self._csv(f"{t}_learning.csv") for t in TASKS}
        gaps = {t: self._csv(f"{t}_paired_brier_gaps.csv") for t in TASKS}
        calibration = {t: self._csv(f"{t}_holdout_calibration.csv") for t in TASKS}
        choice = selection["tasks"]["wicket"]
        if any(selection["tasks"][t]["selected"] != SELECTED for t in TASKS):
            raise MethodologyUnavailable("The frozen selection is not the model this page describes.")
        return {
            "decision": {
                "algorithm": SELECTED,
                "params": choice["params"],
                "fixed_settings": {"learning_rate": 0.06, "min_samples_leaf": 50, "early_stopping": False,
                                   "random_state": selection["seed"]},
                "rule": "Lowest mean validation Brier score over 2021–2025, log loss as tie-break, fixed before "
                        "the comparison.",
                "tuning_years": list(selection["tuning_years"]),
                "validation_years": list(selection["validation_years"]),
                "holdout_year": selection["holdout_year"],
            },
            "workflow": [{"step": i + 1, "title": t, "detail": d.format(
                matches=audit["archive"]["counts"]["matches"], first=audit["archive"]["date_min"][:4],
                last=audit["archive"]["date_max"][:4])} for i, (t, d) in enumerate(WORKFLOW)],
            "tasks": [self._task(t, holdout[t], final["tasks"][t], audit[t], summary["tasks"][t]) for t in TASKS],
            "data_assumptions": summary["verdicts"]["data"],
            "eligibility": summary["eligibility"],
            "algorithms": [self._algorithm(name, comparison, tuning, selection, summary, gaps)
                           for name in ALGORITHMS],
            "comparison": {t: self._comparison(comparison[t], selection["tasks"][t]) for t in TASKS},
            "learning_curves": {t: self._curves(learning[t]) for t in TASKS},
            "paired_gaps": {t: self._gaps(gaps[t]) for t in TASKS},
            "convergence": {t: self._convergence(summary["tasks"][t]["convergence"]) for t in TASKS},
            "holdout": {t: self._holdout(holdout[t], final["tasks"][t], calibration[t]) for t in TASKS},
            "final_models": {t: final["tasks"][t]["artifacts"] for t in TASKS},
            "limitations": LIMITATIONS,
            "sources": ["reports/model_benchmark/selection.json", "reports/model_benchmark/holdout_2026.json",
                        "reports/model_benchmark/final_models.json", "reports/model_benchmark/*_comparison.csv",
                        "reports/model_benchmark/*_learning.csv", "reports/model_benchmark/*_paired_brier_gaps.csv",
                        "reports/model_benchmark/*_holdout_calibration.csv",
                        "reports/model_benchmark/assumptions/summary.json", "docs/MODEL_METHODOLOGY.md"],
        }

    @staticmethod
    def _task(kind, test, fitted, audit, evidence) -> Dict[str, Any]:
        final = fitted["artifacts"]["final"]
        return {
            "kind": kind, **TASK_TEXT[kind],
            "rows": int(final["train_rows"]), "matches": int(final["train_matches"]),
            "test_rows": int(test["evaluation_rows"]), "test_matches": int(test["evaluation_matches"]),
            "class_shares": evidence["class_balance"]["class_shares"],
            "majority_class_accuracy": evidence["class_balance"]["majority_class_accuracy_mean"],
            "class_counts": {k: int(v) for k, v in audit["class_counts_by_split"]["all"].items()},
        }

    @staticmethod
    def _comparison(table: pd.DataFrame, choice: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows = []
        for rank, r in enumerate(table.itertuples(index=False), start=1):
            row = {"rank": rank, "model": str(r.model), "setting": int(r.setting),
                   "selected": str(r.model) == choice["selected"] and int(r.setting) == choice["selected_setting"]}
            for m in METRICS:
                row[f"{m}_mean"], row[f"{m}_std"] = _f(getattr(r, f"{m}_mean")), _f(getattr(r, f"{m}_std"))
            rows.append(row)
        return rows

    @staticmethod
    def _curves(learning: pd.DataFrame) -> List[Dict[str, Any]]:
        cols = [f"validation_{m}" for m in CURVE_METRICS] + ["train_brier"]
        grouped = learning.groupby(["model", "training_fraction"], sort=False)
        means, sds = grouped[cols + ["train_matches", "train_rows"]].mean(), grouped[cols].std()
        out = []
        for (model, fraction), row in means.iterrows():
            point = {"model": model, "training_fraction": _f(fraction), "train_matches": _f(row.train_matches),
                     "train_rows": _f(row.train_rows)}
            for c in cols:
                point[c] = _f(row[c])
                point[f"{c}_sd"] = _f(sds.loc[(model, fraction), c])
            out.append(point)
        return out

    @staticmethod
    def _gaps(table: pd.DataFrame) -> List[Dict[str, Any]]:
        return [{"year": int(r["year"]), "model": m, "gap": _f(r[m])}
                for _, r in table.iterrows() for m in table.columns if m not in ("year", SELECTED)]

    @staticmethod
    def _convergence(c: Dict[str, Any]) -> Dict[str, Any]:
        keep = ("leaders", "leader_brier_spread_by_fraction", "best_alternative_by_fraction", "selected_plateau",
                "paired_gaps_vs_selected", "accuracy_mean_by_model", "majority_class_accuracy_mean",
                "selected_mean_validation_brier", "runner_up", "runner_up_gap")
        return {k: c[k] for k in keep}

    @staticmethod
    def _holdout(test, fitted, calibration) -> Dict[str, Any]:
        bins = [{"event": str(r.event), "bin": int(r.bin), "lower": int(r.bin) / 10, "upper": (int(r.bin) + 1) / 10,
                 "rows": int(r.rows), "observed_rate": _f(r.observed_rate), "mean_probability": _f(r.mean_probability)}
                for r in calibration.itertuples(index=False)]
        return {"metrics": test["metrics"], "baseline_metrics": fitted["baseline_2026"]["metrics"],
                "confusion_matrix": test["confusion_matrix"],
                "class_counts": {k: int(v) for k, v in test["class_counts"].items()},
                "train_rows": int(test["train_rows"]), "train_matches": int(test["train_matches"]),
                "train_start": test["train_start"], "train_end": test["train_end"],
                "rows": int(test["evaluation_rows"]), "matches": int(test["evaluation_matches"]),
                "calibration": bins,
                "caveat": "2026 had been examined during development, so this is a retrospective chronological test. "
                          "The models refitted through 2026 have no independent test season yet."}

    def _algorithm(self, name, comparison, tuning, selection, summary, gaps) -> Dict[str, Any]:
        text = ALGORITHMS[name]
        grid, results, verdicts = {}, {}, {}
        for t in TASKS:
            chosen = selection["tasks"][t]["chosen_settings"][name]
            rows = tuning[(tuning.task == t) & (tuning.model == name)].sort_values("setting")
            grid[t] = [{"setting": int(r.setting), "params": json.loads(r.params), "chosen": int(r.setting) == chosen,
                        "tuning_brier_mean": _f(r.tuning_brier_mean),
                        "tuning_brier_sd": None if pd.isna(r.tuning_brier_sd) else _f(r.tuning_brier_sd)}
                       for r in rows.itertuples(index=False)]
            table = comparison[t].reset_index(drop=True)
            idx = int(table.index[table.model == name][0])
            row = table.loc[idx]
            results[t] = {"rank": idx + 1, **{f"{m}_mean": _f(row[f"{m}_mean"]) for m in METRICS},
                          **{f"{m}_std": _f(row[f"{m}_std"]) for m in METRICS}}
            if name != SELECTED:
                g = gaps[t][name]
                results[t]["paired_gap_mean"] = _f(g.mean())
                results[t]["paired_gap_sd"] = _f(g.std())
                results[t]["seasons_selected_better"] = int((g > 0).sum())
            verdicts[t] = summary["tasks"][t]["algorithms"][name]["verdict"]
        return {"name": name, "short": text["short"], "how_it_works": text["how"], "formula": text["formula"],
                "assumptions": text["assumptions"], "verdicts": verdicts,
                "evidence": self._evidence(name, summary), "grid": grid, "results": results,
                "selected": name == SELECTED, "decision": self._decision(name, results)}

    @staticmethod
    def _evidence(name: str, summary: Dict[str, Any]) -> List[str]:
        w, b = (summary["tasks"][t]["algorithms"][name]["evidence"] for t in TASKS)
        if name == "Class-prior baseline":
            hw, hb = w["homogeneity"]["wicket"], b["homogeneity"]["30+"]
            return [f"Wicket rate by season {hw['min_rate']:.1%}–{hw['max_rate']:.1%} (χ² test p = {hw['p_value']:.2f}): "
                    f"stable.",
                    f"Batter 30+ rate {hb['min_rate']:.1%} ({hb['min_season']}) to {hb['max_rate']:.1%} "
                    f"({hb['max_season']}) (p = {hb['p_value']:.1e}): not stable."]
        if name == "Logistic regression":
            return [f"Log-odds linearity rejected for {len(w['clearly_nonlinear_features'])} of {w['features_tested']} "
                    f"wicket and {len(b['clearly_nonlinear_features'])} of {b['features_tested']} batter numeric "
                    f"inputs (nested likelihood-ratio test).",
                    f"Largest variance inflation factor {w['max_vif']} ({w['max_vif_feature']}) and {b['max_vif']} "
                    f"({b['max_vif_feature']}); above 10 means serious collinearity.",
                    f"Events per weight {w['events_per_parameter']['events_per_parameter']} (wicket) and "
                    f"{b['events_per_parameter']['events_per_parameter']} (batter; below the usual 10).",
                    f"Tuning chose the strongest penalty, C = {w['chosen_setting']['C']}, for both tasks."]
        if name == "Decision tree":
            return [f"Tuning chose the shallowest tree (depth {w['chosen_setting']['max_depth']}, "
                    f"{w['chosen_setting']['min_samples_leaf']} rows per leaf) for both tasks.",
                    f"The random forest beat it in {w['seasons_forest_beats_tree']} of 5 wicket and "
                    f"{b['seasons_forest_beats_tree']} of 5 batter seasons."]
        if name == "Random forest":
            return [f"Beat the single tree in {w['seasons_forest_beats_tree']} of 5 wicket and "
                    f"{b['seasons_forest_beats_tree']} of 5 batter seasons (mean Brier gain "
                    f"{w['mean_brier_tree_minus_forest']:.5f} and {b['mean_brier_tree_minus_forest']:.5f})."]
        if name == SELECTED:
            return [f"{w['numeric_features_binned_losslessly']} of {w['numeric_features']} wicket and "
                    f"{b['numeric_features_binned_losslessly']} of {b['numeric_features']} batter numeric inputs fit in "
                    f"255 bins without loss.",
                    f"Train–validation Brier gap beyond the baseline's season drift: {w['excess_train_validation_gap']:.4f} "
                    f"(wicket) and {b['excess_train_validation_gap']:.4f} (batter).",
                    f"Validation Brier change from 75% to 100% of the history: "
                    f"{w['plateau']['change_75_to_100']:+.6f} (wicket) and {b['plateau']['change_75_to_100']:+.6f} (batter)."]
        if name == "Gaussian naive Bayes":
            cw, cb = w["calibration_2025"], b["calibration_2025"]
            return [f"{w['within_class_pairs_abs_corr_at_least_0.5']} wicket and "
                    f"{b['within_class_pairs_abs_corr_at_least_0.5']} batter within-class input pairs correlate at "
                    f"|r| ≥ 0.5, so the inputs are not independent.",
                    f"{w['one_hot_binary_columns']} and {b['one_hot_binary_columns']} one-hot columns are 0/1, never "
                    f"bell-shaped.",
                    f"2025 calibration error {cw['Gaussian naive Bayes']['expected_calibration_error']} (wicket) and "
                    f"{cb['Gaussian naive Bayes']['expected_calibration_error']} (batter 30+), against "
                    f"{cw[SELECTED]['expected_calibration_error']} and {cb[SELECTED]['expected_calibration_error']} "
                    f"for boosting."]
        if name == "Multilayer perceptron":
            capped = w["fits_stopped_by_epoch_cap"]["tuning"] + w["fits_stopped_by_epoch_cap"]["learning"]
            return [f"All {capped} perceptron fits per task stopped at the epoch cap before converging.",
                    f"Five seeds on the 2025 fold moved Brier by {w['seed_brier_range_2025']:.6f} (wicket) and "
                    f"{b['seed_brier_range_2025']:.6f} (batter); the gap to boosting is "
                    f"{w['gap_to_selected_mean_brier']:.6f} and {b['gap_to_selected_mean_brier']:.6f}.",
                    f"{w['weights_and_biases']:,} and {b['weights_and_biases']:,} weights for "
                    f"{w['training_rows_2008_2024']:,} and {b['training_rows_2008_2024']:,} training rows."]
        raise KeyError(name)

    @staticmethod
    def _decision(name: str, results: Dict[str, Dict[str, Any]]) -> str:
        w, b = results["wicket"], results["batter"]
        ranks = f"Ranked {w['rank']} (wicket) and {b['rank']} (batter) of 7 on mean validation Brier."
        if name == SELECTED:
            return (f"Selected. {ranks} Lowest mean Brier for both tasks under the rule fixed in advance, with a flat "
                    "learning curve and a small train–validation gap.")
        gap = (f"Boosting was better in {w['seasons_selected_better']} of 5 wicket and {b['seasons_selected_better']} "
               f"of 5 batter seasons (mean paired gap {w['paired_gap_mean']:.6f} and {b['paired_gap_mean']:.6f}).")
        reason = {
            "Class-prior baseline": "Not selected: it is the reference, with no ability to rank situations.",
            "Logistic regression": "Not selected: the effects are non-linear, which a straight-line log-odds model "
                                   "cannot represent.",
            "Decision tree": "Not selected: a shallow single tree is too coarse for well-calibrated probabilities.",
            "Random forest": "Not selected, but close: on this evidence it is statistically indistinguishable from "
                             "boosting, which the pre-specified rule ranks first.",
            "Gaussian naive Bayes": "Not selected: its independence and normality assumptions fail and its "
                                    "probabilities are badly calibrated, worse than the baseline.",
            "Multilayer perceptron": "Not selected: slightly higher mean Brier, unconverged optimisation, and "
                                     "seed sensitivity comparable to or larger than its gap to the leader.",
        }[name]
        return f"{reason} {ranks} {gap}"


methodology_service = MethodologyService()
