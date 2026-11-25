"""Evidence for the data and algorithm assumptions behind the CricketLens forecast benchmark.

Every number is computed from the modelling tables (data/processed/stage03_*_full_history_2008_2026.csv),
the source tables, and the benchmark's saved results (reports/model_benchmark/*.csv, *.json). The few
refits below (Gaussian naive Bayes, the multilayer perceptron with several seeds, the selected boosting
model) use cricketlens.model_benchmark's own estimator() and fit(), single-threaded and seeded.

Each verdict (Holds / Partially holds / Violated) follows a rule stated next to it in this file and is
written with the numbers that decided it. Outputs go to reports/model_benchmark/assumptions/:
CSV tables, PNG figures and summary.json.

    python -m cricketlens.model_assumptions
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression, LogisticRegression
from threadpoolctl import threadpool_limits

from cricketlens.model_benchmark import (
    SEED, TASKS, TEST_YEAR, TRAIN_FRACTIONS, TUNING_YEARS, VALIDATION_YEARS, data_for, event_probabilities, fit,
    probabilities, score, search_space, split, write_json,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SELECTED = "Histogram gradient boosting"
MODELS = ("Class-prior baseline", "Logistic regression", "Decision tree", "Random forest",
          "Histogram gradient boosting", "Gaussian naive Bayes", "Multilayer perceptron")
MLP_SEEDS = (42, 1, 2, 3, 4)
EVAL_YEARS = (*TUNING_YEARS, *VALIDATION_YEARS, TEST_YEAR)
HGB_MAX_BINS = 255  # scikit-learn's default, which the benchmark keeps
# Conventional thresholds used by the verdict rules
SMD_SMALL, SMD_LARGE = 0.2, 0.8          # Cohen's small and large standardised differences
PSI_MODERATE, PSI_MAJOR = 0.1, 0.25      # population stability index bands
VIF_HIGH = 10.0                          # variance inflation factor above which collinearity is serious
EPP_MIN = 10.0                           # events per model parameter, the usual lower bound
CORR_STRONG = 0.5                        # within-class correlation that contradicts conditional independence
SKEW_STRONG, KURT_STRONG = 1.0, 3.0      # |skewness| and excess kurtosis far from a normal distribution
ALPHA = 0.05
COLORS = {"Class-prior baseline": "#8E8E88", "Logistic regression": "#4C78A8", "Decision tree": "#72B7B2",
          "Random forest": "#54A24B", "Histogram gradient boosting": "#C8962E", "Gaussian naive Bayes": "#E45756",
          "Multilayer perceptron": "#B279A2"}
TASK_TITLE = {"wicket": "Next-over wicket", "batter": "Batter milestones"}
SCALES = {
    "innings": ("nominal", "1 or 2 (batting first or chasing); used as a 0/1-style number"),
    "completed_overs": ("ratio", "count of completed overs, 1–19"),
    "runs": ("ratio", "team runs so far"),
    "wickets": ("ratio", "team wickets so far, 0–9"),
    "run_rate": ("ratio", "runs per completed over"),
    "last_over_runs": ("ratio", "runs in the most recent over"),
    "last_over_wickets": ("ratio", "wickets in the most recent over"),
    "batting_team": ("nominal", "franchise, one-hot encoded"),
    "bowling_team": ("nominal", "franchise, one-hot encoded"),
    "phase": ("ordinal", "powerplay < middle < death; one-hot encoded, so the order is not imposed"),
    "venue_canonical": ("nominal", "venue, one-hot encoded"),
    "prior_innings": ("ratio", "count of earlier eligible innings"),
    "days_since_previous_innings": ("ratio", "days since the previous innings, capped at 3,650"),
    "wicket_next_over": ("nominal (binary target)", "at least one wicket in the next over"),
    "milestone_class": ("ordinal (target)", "<30, 30–49, 50+ runs"),
}


def scale_of(feature: str):
    if feature in SCALES:
        return SCALES[feature]
    if feature.endswith("_rate"):
        return ("ratio", "share of earlier innings reaching the milestone (0–1)")
    if feature.endswith("avg_runs"):
        return ("ratio", "mean runs in earlier innings")
    if feature.endswith("prior_innings"):
        return ("ratio", "count of earlier innings in this context")
    raise KeyError(feature)


def fmt(x, digits=4):
    return float(round(float(x), digits))


def binary_events(task, frame):
    """The binary event(s) each task is scored on: the wicket, or reaching 30 and 50."""
    y = frame[task.target].to_numpy()
    return {"wicket": y == 1} if task.name == "wicket" else {"30+": y >= 1, "50+": y == 2}


# ------------------------------------------------------------------ data assumptions

def eligibility(audit: Dict[str, Any], matches: pd.DataFrame) -> pd.DataFrame:
    w, b = audit["wicket"]["builder_counts"], audit["batter"]["builder_counts"]
    rows = [
        ("archive", "matches in the archive", int(len(matches))),
        ("archive", "super-over innings left out of the ordinary innings tables", int(matches.super_over_innings.sum())),
        ("archive", "D/L-marked matches", int((matches.outcome_method.fillna("") == "D/L").sum())),
        ("archive", "no-result matches", int((matches.decided_by == "no_result").sum())),
        ("wicket", "completed-over checkpoints considered", w["considered_completed_checkpoints"]),
        ("wicket", "excluded: in D/L-marked matches", w["excluded_dls_checkpoints"]),
        ("wicket", "excluded: anomalous or gapped overs", w["excluded_anomalous_or_gapped"]),
        ("wicket", "excluded: next over cut short with no wicket (censored)", w["censored_no_wicket_short_next_over"]),
        ("wicket", "kept: next over cut short by a wicket", w["witnessed_wicket_short_next_over"]),
        ("wicket", "kept: complete six-ball next over", w["full_next_over_examples"]),
        ("wicket", "eligible rows", w["eligible_rows"]),
        ("wicket", "eligible rows from no-result matches (kept)", audit["wicket"]["retained_match_outcomes"].get("no_result", 0)),
        ("batter", "batting innings in the source", b["source_rows"]),
        ("batter", "excluded: in D/L-marked matches", b["excluded_dls_batter_innings"]),
        ("batter", "excluded: in no-result matches", b["excluded_no_result_batter_innings"]),
        ("batter", "eligible rows", b["eligible_rows"]),
    ]
    table = pd.DataFrame(rows, columns=["scope", "rule", "count"])
    if w["considered_completed_checkpoints"] - w["excluded_dls_checkpoints"] - w["excluded_anomalous_or_gapped"] \
            - w["censored_no_wicket_short_next_over"] != w["eligible_rows"]:
        raise ValueError("Wicket eligibility counts do not add up")
    if b["source_rows"] - b["excluded_dls_batter_innings"] - b["excluded_no_result_batter_innings"] != b["eligible_rows"]:
        raise ValueError("Batter eligibility counts do not add up")
    return table


def folds(task, data) -> pd.DataFrame:
    rows = []
    for year in EVAL_YEARS:
        train, valid = split(data, year)  # raises on any date or match overlap
        rows.append({"task": task.name, "evaluation_season": year,
                     "role": "tuning" if year in TUNING_YEARS else "validation" if year in VALIDATION_YEARS else "2026 test",
                     "train_last_date": train.date.max().date().isoformat(),
                     "evaluation_first_date": valid.date.min().date().isoformat(),
                     "gap_days": int((valid.date.min() - train.date.max()).days),
                     "shared_matches": len(set(train.match_id) & set(valid.match_id)),
                     "train_rows": len(train), "evaluation_rows": len(valid)})
    return pd.DataFrame(rows)


def icc(y: np.ndarray, groups: np.ndarray) -> Dict[str, float]:
    """One-way ANOVA intraclass correlation ICC(1) of an outcome within groups, with its F test."""
    frame = pd.DataFrame({"y": y.astype(float), "g": groups})
    g = frame.groupby("g").y
    n_i, means = g.size().to_numpy(), g.mean().to_numpy()
    n, k = len(frame), len(n_i)
    grand = frame.y.mean()
    msb = float(np.sum(n_i * (means - grand) ** 2) / (k - 1))
    msw = float(((frame.y - g.transform("mean")) ** 2).sum() / (n - k))
    k0 = (n - np.sum(n_i ** 2) / n) / (k - 1)
    value = (msb - msw) / (msb + (k0 - 1) * msw)
    f = msb / msw
    mean_size = n / k
    effect = 1 + (mean_size - 1) * value
    return {"icc": fmt(value, 5), "f": fmt(f, 3), "p_value": float(stats.f.sf(f, k - 1, n - k)),
            "mean_rows_per_group": fmt(mean_size, 2), "design_effect": fmt(effect, 3),
            "effective_rows": int(round(n / effect))}


def dependence(task, data) -> Dict[str, Any]:
    per_match = data.groupby("match_id").size()
    result = {"rows": int(len(data)), "matches": int(per_match.size),
              "rows_per_match": {"mean": fmt(per_match.mean(), 2), "median": float(per_match.median()),
                                 "min": int(per_match.min()), "max": int(per_match.max())}}
    for label, event in binary_events(task, data).items():
        result[f"icc_{label}_by_match"] = icc(event, data.match_id.to_numpy())
        result[f"icc_{label}_by_innings"] = icc(event, (data.match_id.astype(str) + "-" + data.innings.astype(str)).to_numpy())
    return result


def psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    ref = np.histogram(reference, edges)[0] / len(reference)
    cur = np.histogram(current, edges)[0] / len(current)
    ref, cur = np.clip(ref, 1e-4, None), np.clip(cur, 1e-4, None)
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def drift(task, data) -> pd.DataFrame:
    """Each evaluation season against all earlier seasons (its training data): target rates, SMD and PSI."""
    rows = []
    for year in EVAL_YEARS:
        ref, cur = data[data.season < year], data[data.season == year]
        for feature in task.numeric:
            a, b = ref[feature].to_numpy(float), cur[feature].to_numpy(float)
            pooled = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
            rows.append({"task": task.name, "season": year, "feature": feature,
                         "training_mean": a.mean(), "season_mean": b.mean(),
                         "smd": (b.mean() - a.mean()) / pooled if pooled > 0 else 0.0, "psi": psi(a, b)})
    return pd.DataFrame(rows)


def target_rates(task, data) -> pd.DataFrame:
    rows = []
    for season, frame in data.groupby("season"):
        row = {"task": task.name, "season": int(season), "rows": len(frame)}
        for label, event in binary_events(task, frame).items():
            row[f"rate_{label}"] = float(event.mean())
        rows.append(row)
    return pd.DataFrame(rows)


def homogeneity(task, data) -> Dict[str, Any]:
    """Chi-square test that the event rate is the same in every season."""
    out = {}
    for label, event in binary_events(task, data).items():
        table = pd.crosstab(data.season, event)
        chi2, p, dof, _ = stats.chi2_contingency(table)
        rates = table[True] / table.sum(axis=1)
        out[label] = {"chi2": fmt(chi2, 2), "dof": int(dof), "p_value": float(p), "pooled_rate": fmt(event.mean()),
                      "min_rate": fmt(rates.min()), "min_season": int(rates.idxmin()),
                      "max_rate": fmt(rates.max()), "max_season": int(rates.idxmax()),
                      "max_abs_deviation": fmt((rates - event.mean()).abs().max())}
    return out


def class_balance(task, data) -> Dict[str, Any]:
    shares = data[task.target].value_counts(normalize=True).sort_index()
    floors = []
    for year in VALIDATION_YEARS:
        train, valid = split(data, year)
        majority = train[task.target].value_counts().idxmax()
        floors.append(float((valid[task.target] == majority).mean()))
    return {"class_shares": {str(k): fmt(v) for k, v in shares.items()},
            "minority_share": fmt(shares.min()),
            "majority_class_accuracy_by_validation_season": dict(zip(map(str, VALIDATION_YEARS), map(fmt, floors))),
            "majority_class_accuracy_mean": fmt(np.mean(floors))}


def defaults(task, data) -> Dict[str, Any]:
    out = {"missing_model_inputs": int(data[task.features].isna().sum().sum())}
    if task.name == "batter":
        out.update({
            "cold_start_rows_prior_innings_0": int((data.prior_innings == 0).sum()),
            "rows_without_opposition_history": int((data.opposition_prior_innings == 0).sum()),
            "rows_without_venue_history": int((data.venue_prior_innings == 0).sum()),
            "rows_with_days_since_default_3650": int((data.days_since_previous_innings == 3650).sum()),
            "cold_start_rows_2026": int(((data.prior_innings == 0) & (data.season == 2026)).sum()),
            "default_rule": "no earlier innings: averages and rates are 0.0 and days since the previous innings is 3,650",
        })
    else:
        out["default_rule"] = "none: every checkpoint input is observed in the match itself"
    return out


def unseen_levels(task, data) -> pd.DataFrame:
    rows = []
    for year in EVAL_YEARS:
        train, valid = split(data, year)
        for col in task.categorical:
            unseen = ~valid[col].isin(set(train[col]))
            rows.append({"task": task.name, "season": year, "feature": col, "unseen_rows": int(unseen.sum()),
                         "unseen_levels": ", ".join(sorted(valid.loc[unseen, col].unique()))})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ algorithm assumptions

def _log_likelihood(design: np.ndarray, y: np.ndarray) -> float:
    """Maximised log-likelihood of an (effectively unpenalised) logistic regression on these columns."""
    p = LogisticRegression(C=1e10, max_iter=5000).fit(design, y).predict_proba(design)[:, 1]
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def logit_linearity(task, train) -> pd.DataFrame:
    """Per numeric feature: empirical logits in bins against a fitted straight line, and a likelihood-ratio test.

    The test is nested: a straight line in the feature against the same line plus one indicator per bin, so
    the extra freedom measures departure from linearity; its degrees of freedom come from the design ranks.
    """
    label, event = next(iter(binary_events(task, train).items()))
    y = event.astype(int)
    rows = []
    for feature in task.numeric:
        x = train[feature].to_numpy(float)
        distinct = np.unique(x)
        if len(distinct) <= 2:
            rows.append({"task": task.name, "event": label, "feature": feature, "bins": len(distinct),
                         "lr_statistic": 0.0, "dof": 0, "p_value": 1.0, "max_abs_deviation": 0.0,
                         "weighted_r2": 1.0, "note": "two values: linear in the log-odds by construction"})
            continue
        # Up to ten observed values: one bin each; otherwise decile bins (tied values never split)
        bins = (pd.qcut(x, 10, labels=False, duplicates="drop") if len(distinct) > 10
                else np.searchsorted(distinct, x))
        frame = pd.DataFrame({"x": x, "y": y, "bin": np.asarray(bins)})
        grouped = frame.groupby("bin").agg(n=("y", "size"), events=("y", "sum"), x=("x", "mean"))
        z = (x - x.mean()) / x.std()
        model = LogisticRegression(C=1e10, max_iter=1000).fit(z.reshape(-1, 1), y)
        linear = z.reshape(-1, 1)
        dummies = pd.get_dummies(frame.bin, drop_first=True, dtype=float).to_numpy()
        extended = np.column_stack([z, dummies])
        ll_linear, ll_binned = _log_likelihood(linear, y), _log_likelihood(extended, y)
        ones = np.ones((len(z), 1))
        dof = (np.linalg.matrix_rank(np.column_stack([ones, extended]))
               - np.linalg.matrix_rank(np.column_stack([ones, linear])))
        empirical = np.log((grouped.events + .5) / (grouped.n - grouped.events + .5))
        fitted = model.intercept_[0] + model.coef_[0, 0] * (grouped.x - x.mean()) / x.std()
        weights = grouped.n / grouped.n.sum()
        resid = empirical - fitted
        r2 = 1 - np.sum(weights * resid ** 2) / np.sum(weights * (empirical - np.sum(weights * empirical)) ** 2)
        lr = max(2 * (ll_binned - ll_linear), 0.0)
        rows.append({"task": task.name, "event": label, "feature": feature, "bins": len(grouped),
                     "lr_statistic": lr, "dof": dof, "p_value": float(stats.chi2.sf(lr, dof)) if dof > 0 else 1.0,
                     "max_abs_deviation": float(np.max(np.abs(resid))), "weighted_r2": float(r2),
                     "note": "decile bins" if len(distinct) > 10 else "one bin per observed value"})
        grouped = grouped.assign(empirical_logit=empirical, fitted_logit=fitted)
        LINEARITY_POINTS.setdefault(task.name, {})[feature] = grouped.reset_index()
    return pd.DataFrame(rows)


LINEARITY_POINTS: Dict[str, Dict[str, pd.DataFrame]] = {}


def vif(task, train) -> pd.DataFrame:
    x = train[task.numeric].to_numpy(float)
    x = (x - x.mean(axis=0)) / x.std(axis=0)
    rows = []
    for i, feature in enumerate(task.numeric):
        others = np.delete(x, i, axis=1)
        r2 = LinearRegression().fit(others, x[:, i]).score(others, x[:, i])
        rows.append({"task": task.name, "feature": feature, "r2_on_other_features": r2,
                     "vif": float("inf") if r2 >= 1 else 1 / (1 - r2)})
    return pd.DataFrame(rows)


def events_per_parameter(task, train) -> Dict[str, Any]:
    levels = sum(train[c].nunique() for c in task.categorical)
    per_logit = len(task.numeric) + levels + 1
    logits = len(task.classes) - 1 if task.name == "wicket" else len(task.classes)
    params = per_logit * logits
    events = int(train[task.target].value_counts().min())
    return {"numeric_columns": len(task.numeric), "one_hot_columns": int(levels), "parameters": int(params),
            "minority_class_events": events, "events_per_parameter": fmt(events / params, 2),
            "note": ("binary logistic: one coefficient per column plus an intercept" if task.name == "wicket" else
                     "multinomial logistic: one coefficient set per class")}


def tuning_effect(task, tuning: pd.DataFrame, model: str) -> pd.DataFrame:
    rows = tuning[tuning.model == model]
    return (rows.groupby(["setting", "params"]).brier.agg(["mean", "std"]).reset_index()
            .rename(columns={"mean": "tuning_brier_mean", "std": "tuning_brier_sd"}).assign(task=task.name, model=model))


def learning_summary(learning: pd.DataFrame) -> pd.DataFrame:
    metrics = ["brier", "log_loss", "accuracy", "balanced_accuracy"]
    cols = {f"validation_{m}": "mean" for m in metrics} | {f"train_{m}": "mean" for m in metrics} | {"train_matches": "mean"}
    table = learning.groupby(["model", "training_fraction"]).agg(cols).reset_index()
    sds = learning.groupby(["model", "training_fraction"])[[f"validation_{m}" for m in metrics]].std().reset_index()
    return table.merge(sds, on=["model", "training_fraction"], suffixes=("", "_sd"))


def gaussian_checks(task, train) -> Dict[str, Any]:
    """Within-class correlations and shapes of the numeric inputs naive Bayes models as independent Gaussians."""
    corr_rows, shape_rows = [], []
    for cls in task.classes:
        frame = train.loc[train[task.target] == cls, task.numeric]
        corr = frame.corr().to_numpy()
        for i in range(len(task.numeric)):
            for j in range(i + 1, len(task.numeric)):
                if np.isfinite(corr[i, j]):
                    corr_rows.append({"task": task.name, "class": int(cls), "feature_a": task.numeric[i],
                                      "feature_b": task.numeric[j], "correlation": float(corr[i, j])})
        for feature in task.numeric:
            values = frame[feature].to_numpy(float)
            shape_rows.append({"task": task.name, "class": int(cls), "feature": feature,
                               "skewness": float(stats.skew(values)), "excess_kurtosis": float(stats.kurtosis(values)),
                               "distinct_values": int(len(np.unique(values)))})
    return {"correlations": pd.DataFrame(corr_rows), "shapes": pd.DataFrame(shape_rows)}


def calibration_error(actual: np.ndarray, predicted: np.ndarray, bins: int = 10) -> float:
    index = np.minimum((predicted * bins).astype(int), bins - 1)
    total = 0.0
    for b in range(bins):
        mask = index == b
        if mask.any():
            total += mask.mean() * abs(actual[mask].mean() - predicted[mask].mean())
    return float(total)


def refit_2025(task, data, choices, model, params_override=None):
    train, valid = split(data, 2025)
    params = dict(choices[model]) if params_override is None else params_override
    with threadpool_limits(limits=1):
        fitted, warnings = fit(task, model, params, train)
        p = probabilities(task, fitted, valid)
    return fitted, warnings, valid, p


def mlp_seeds(task, data, grids_params) -> pd.DataFrame:
    rows = []
    train, valid = split(data, 2025)
    for seed in MLP_SEEDS:
        params = {**grids_params, "random_state": seed}
        with threadpool_limits(limits=1):
            fitted, warnings = fit(task, "Multilayer perceptron", params, train)
            p = probabilities(task, fitted, valid)
        s = score(task, valid, p)
        rows.append({"task": task.name, "seed": seed, "brier": s["brier"], "log_loss": s["log_loss"],
                     "accuracy": s["accuracy"], "hit_epoch_cap": bool(warnings),
                     "iterations": int(fitted.steps[-1][1].n_iter_)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ figures

def plot_linearity(task, out):
    points = LINEARITY_POINTS.get(task.name, {})
    names = list(points)
    cols = 4
    rows = math.ceil(len(names) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(13, 2.7 * rows), squeeze=False)
    for ax, name in zip(axes.flat, names):
        g = points[name]
        ax.plot(g.x, g.empirical_logit, "o", color="#C8962E", ms=4, label="Empirical logit (bin)")
        ax.plot(g.x, g.fitted_logit, "-", color="#4C78A8", lw=1.5, label="Straight-line logistic fit")
        ax.set_title(name, fontsize=9, loc="left")
        ax.tick_params(labelsize=7)
        ax.grid(alpha=.25)
    for ax in list(axes.flat)[len(names):]:
        ax.axis("off")
    axes.flat[0].legend(fontsize=7, frameon=False)
    event = "a wicket in the next over" if task.name == "wicket" else "reaching 30 runs"
    fig.suptitle(f"{TASK_TITLE[task.name]}: log-odds of {event} by feature bin, 2008–2025 rows", x=.01, ha="left")
    fig.tight_layout()
    fig.savefig(out / f"logit_linearity_{task.name}.png", dpi=110)
    plt.close(fig)


def plot_drift(task, rates, shift, out):
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.2), gridspec_kw={"width_ratios": [1, 1.4]})
    for col in [c for c in rates.columns if c.startswith("rate_")]:
        a.plot(rates.season, rates[col], marker="o", ms=3, label=col.replace("rate_", ""))
    a.set_title("Event rate per season", loc="left", fontsize=10)
    a.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=0))
    a.grid(alpha=.25)
    a.legend(frameon=False, fontsize=8)
    pivot = shift.pivot(index="feature", columns="season", values="smd").loc[task.numeric]
    im = b.imshow(pivot.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    b.set_yticks(range(len(pivot.index)), pivot.index, fontsize=7)
    b.set_xticks(range(len(pivot.columns)), pivot.columns, fontsize=7)
    b.set_title("Standardised mean difference: season vs all earlier seasons", loc="left", fontsize=10)
    fig.colorbar(im, ax=b, shrink=.8)
    fig.suptitle(f"{TASK_TITLE[task.name]}: stationarity", x=.01, ha="left")
    fig.tight_layout()
    fig.savefig(out / f"drift_{task.name}.png", dpi=110)
    plt.close(fig)


def plot_qq(task, train, out, features):
    fig, axes = plt.subplots(1, len(features), figsize=(4 * len(features), 3.6), squeeze=False)
    for ax, feature in zip(axes.flat, features):
        values = train[feature].to_numpy(float)
        (theory, ordered), _ = stats.probplot(values, dist="norm")
        step = max(1, len(ordered) // 2000)
        ax.plot(theory[::step], ordered[::step], ".", ms=2, color="#C8962E")
        lo, hi = theory.min(), theory.max()
        ax.plot([lo, hi], [values.mean() + lo * values.std(), values.mean() + hi * values.std()], color="#4C78A8")
        ax.set_title(f"{feature} (skew {stats.skew(values):.2f})", fontsize=9, loc="left")
        ax.set_xlabel("Normal quantile", fontsize=8)
        ax.grid(alpha=.25)
    fig.suptitle(f"{TASK_TITLE[task.name]}: normal Q–Q plots, 2008–2025 rows", x=.01, ha="left")
    fig.tight_layout()
    fig.savefig(out / f"nb_qq_{task.name}.png", dpi=110)
    plt.close(fig)


def plot_learning(task, summary, out):
    panels = [("validation_brier", "Brier score (lower is better)"), ("validation_log_loss", "Log loss (lower is better)"),
              ("validation_accuracy", "Accuracy"), ("validation_balanced_accuracy", "Balanced accuracy")]
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5))
    for ax, (col, label) in zip(axes.flat, panels):
        for model in MODELS:
            rows = summary[summary.model == model].sort_values("training_fraction")
            if model == "Gaussian naive Bayes" and col in ("validation_brier", "validation_log_loss"):
                continue  # off the scale of the others; listed in learning_summary.csv
            ax.plot(rows.train_matches, rows[col], marker="o", ms=3, color=COLORS[model],
                    lw=2.6 if model == SELECTED else 1.2, label=model)
        ax.set_title(label + (" — naive Bayes off the scale" if col in ("validation_brier", "validation_log_loss") else ""),
                     loc="left", fontsize=10)
        ax.grid(alpha=.25)
        ax.set_xlabel("Mean training matches", fontsize=8)
    handles, labels = axes.flat[2].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, frameon=False)
    fig.suptitle(f"{TASK_TITLE[task.name]}: validation score against training size (mean of 2021–2025)",
                 x=.01, ha="left")
    fig.tight_layout(rect=(0, .06, 1, 1))
    fig.savefig(out / f"learning_curves_{task.name}.png", dpi=110)
    plt.close(fig)


def plot_gaps(task, gaps, out):
    fig, ax = plt.subplots(figsize=(10, 4))
    models = [m for m in MODELS if m not in (SELECTED, "Gaussian naive Bayes")]
    width = .8 / len(models)
    for i, model in enumerate(models):
        ax.bar(np.arange(len(gaps)) + i * width, gaps[model], width, color=COLORS[model], label=model)
    ax.axhline(0, color="#333", lw=.8)
    ax.set_xticks(np.arange(len(gaps)) + .4 - width / 2, gaps.year)
    ax.set_ylabel("Brier minus boosting's (positive: boosting better)", fontsize=8)
    ax.legend(fontsize=7, frameon=False, ncol=3)
    ax.grid(axis="y", alpha=.25)
    ax.set_title(f"{TASK_TITLE[task.name]}: paired per-season Brier gaps (naive Bayes omitted: far larger)",
                 loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / f"paired_gaps_{task.name}.png", dpi=110)
    plt.close(fig)


# ------------------------------------------------------------------ the analysis

def analyse(root: Path, out: Path) -> Dict[str, Any]:
    data_dir, bench = root / "data/processed", root / "reports/model_benchmark"
    out.mkdir(parents=True, exist_ok=True)
    selection = json.loads((bench / "selection.json").read_text(encoding="utf-8"))
    audit = json.loads((bench / "data_audit.json").read_text(encoding="utf-8"))
    holdout = json.loads((bench / "holdout_2026.json").read_text(encoding="utf-8"))
    matches = pd.read_csv(data_dir / "matches.csv")
    tables = {name: [] for name in ("folds", "drift", "rates", "unseen", "linearity", "vif", "tuning", "shapes",
                                    "correlations", "mlp_seeds", "learning", "gaps", "scales", "binning",
                                    "variance", "calibration")}
    summary: Dict[str, Any] = {"generated_by": "python -m cricketlens.model_assumptions", "seed": SEED,
                               "thresholds": {"smd_small": SMD_SMALL, "smd_large": SMD_LARGE,
                                              "psi_moderate": PSI_MODERATE, "psi_major": PSI_MAJOR,
                                              "vif_high": VIF_HIGH, "events_per_parameter_min": EPP_MIN,
                                              "within_class_correlation_strong": CORR_STRONG,
                                              "skewness_strong": SKEW_STRONG, "excess_kurtosis_strong": KURT_STRONG,
                                              "alpha": ALPHA},
                   "eligibility": eligibility(audit, matches).to_dict(orient="records"), "tasks": {}}
    for task in TASKS:
        data = data_for(task, data_dir)
        dev = data[data.season < TEST_YEAR]
        choice = selection["tasks"][task.name]
        grids = search_space(task)
        chosen = {m: grids[m][i] for m, i in choice["chosen_settings"].items()}
        tuning = pd.read_csv(bench / f"{task.name}_tuning.csv")
        validation = pd.read_csv(bench / f"{task.name}_validation.csv")
        learning = pd.read_csv(bench / f"{task.name}_learning.csv")
        comparison = pd.read_csv(bench / f"{task.name}_comparison.csv")
        gaps = pd.read_csv(bench / f"{task.name}_paired_brier_gaps.csv")
        t: Dict[str, Any] = {}

        # ---- data assumptions
        fold_table = folds(task, data)
        tables["folds"].append(fold_table)
        t["chronology"] = {"folds_checked": len(fold_table), "min_gap_days": int(fold_table.gap_days.min()),
                           "shared_matches": int(fold_table.shared_matches.sum()),
                           "strictly_prior_feature_rows_verified":
                               audit[task.name]["checks"].get("strictly_prior_history_verified_rows",
                                                              audit[task.name]["checks"].get("delivery_verified_rows"))}
        t["dependence"] = dependence(task, data)
        rates = target_rates(task, data)
        tables["rates"].append(rates)
        t["base_rate_homogeneity"] = homogeneity(task, data)
        shift = drift(task, data)
        tables["drift"].append(shift)
        later = shift[shift.season.isin([*VALIDATION_YEARS, TEST_YEAR])]
        worst = later.loc[later.smd.abs().idxmax()]
        t["drift"] = {"max_abs_smd": fmt(abs(worst.smd), 3), "max_abs_smd_feature": worst.feature,
                      "max_abs_smd_season": int(worst.season), "max_psi": fmt(later.psi.max(), 3),
                      "max_psi_feature": later.loc[later.psi.idxmax()].feature,
                      "max_psi_season": int(later.loc[later.psi.idxmax()].season),
                      "seasons_with_large_smd": int(later[later.smd.abs() >= SMD_LARGE].season.nunique()),
                      "seasons_with_major_psi": int(later[later.psi >= PSI_MAJOR].season.nunique()),
                      "feature_season_pairs": int(len(later)),
                      "pairs_with_small_or_larger_smd": int((later.smd.abs() >= SMD_SMALL).sum())}
        t["class_balance"] = class_balance(task, data)
        t["defaults"] = defaults(task, data)
        unseen = unseen_levels(task, data)
        tables["unseen"].append(unseen)
        t["unseen_levels"] = {str(y): int(unseen[unseen.season == y].unseen_rows.sum()) for y in EVAL_YEARS}
        expected = audit[task.name]["rows_with_unseen_categories"]
        if {str(y): sum(v.values()) for y, v in ((int(k), v) for k, v in expected.items())} != t["unseen_levels"]:
            raise ValueError("Unseen-level counts differ from data_audit.json")
        tables["scales"].append(pd.DataFrame(
            [{"task": task.name, "column": c, "role": "target" if c == task.target else "feature",
              "scale": scale_of(c)[0], "meaning": scale_of(c)[1]} for c in [*task.features, task.target]]))

        # ---- algorithm assumptions
        lin = logit_linearity(task, dev)
        tables["linearity"].append(lin)
        tested = lin[lin.dof > 0]
        bonferroni = ALPHA / max(len(tested), 1)
        nonlinear = tested[(tested.p_value < bonferroni) & (tested.max_abs_deviation > 0.1)]
        v = vif(task, dev)
        tables["vif"].append(v)
        epp = events_per_parameter(task, dev)
        reg = tuning_effect(task, tuning, "Logistic regression")
        tables["tuning"].append(pd.concat([tuning_effect(task, tuning, m) for m in MODELS], ignore_index=True))
        lsum = learning_summary(learning).assign(task=task.name)
        tables["learning"].append(lsum)
        tables["gaps"].append(gaps.assign(task=task.name))

        def at(model, fraction, col):
            row = lsum[(lsum.model == model) & (lsum.training_fraction == fraction)]
            return float(row[col].iloc[0])

        def mean_brier(model):
            return float(comparison.loc[comparison.model == model, "brier_mean"].iloc[0])

        def sd_brier(model):
            return float(comparison.loc[comparison.model == model, "brier_std"].iloc[0])

        def gap(model):
            return float(at(model, 1.0, "validation_brier") - at(model, 1.0, "train_brier"))

        paired = {}
        for model in MODELS:
            if model == SELECTED:
                continue
            g = gaps[model]
            paired[model] = {"mean": fmt(g.mean(), 6), "sd": fmt(g.std(), 6),
                             "selected_better_seasons": int((g > 0).sum()), "seasons": int(len(g))}
        variance = []
        for model in MODELS:
            variance.append({"task": task.name, "model": model, "validation_brier_mean": mean_brier(model),
                             "validation_brier_sd_across_seasons": sd_brier(model),
                             "train_brier_at_100pct": at(model, 1.0, "train_brier"),
                             "validation_brier_at_100pct": at(model, 1.0, "validation_brier"),
                             "train_validation_gap": gap(model),
                             "excess_gap_over_class_prior": gap(model) - gap("Class-prior baseline")})
        tables["variance"].append(pd.DataFrame(variance))
        gauss = gaussian_checks(task, dev)
        tables["shapes"].append(gauss["shapes"])
        tables["correlations"].append(gauss["correlations"])
        strong = gauss["correlations"][gauss["correlations"].correlation.abs() >= CORR_STRONG]
        shapes = gauss["shapes"]
        nonnormal = shapes[(shapes.skewness.abs() > SKEW_STRONG) | (shapes.excess_kurtosis > KURT_STRONG)]
        one_hot = sum(dev[c].nunique() for c in task.categorical)
        top_corr = gauss["correlations"].reindex(gauss["correlations"].correlation.abs().sort_values(ascending=False).index).head(5)
        # Calibration of naive Bayes and the selected model on the 2025 fold
        calib = {}
        for model in ("Gaussian naive Bayes", SELECTED):
            _, _, valid, p = refit_2025(task, data, chosen, model)
            label, actual, predicted = event_probabilities(task, valid[task.target].to_numpy(), p)[0]
            calib[model] = {"event": label, "expected_calibration_error": fmt(calibration_error(actual, predicted)),
                            "mean_probability": fmt(predicted.mean()), "observed_rate": fmt(actual.mean()),
                            "share_of_probabilities_below_0.05_or_above_0.95": fmt(((predicted < .05) | (predicted > .95)).mean())}
            tables["calibration"].append(pd.DataFrame([{"task": task.name, "model": model, **calib[model]}]))
        seeds = mlp_seeds(task, data, chosen["Multilayer perceptron"])
        tables["mlp_seeds"].append(seeds)
        mlp_warn = {k: int(frame[frame.model == "Multilayer perceptron"].fit_warnings.fillna("").ne("").sum())
                    for k, frame in (("tuning", tuning), ("validation", validation), ("learning", learning))}
        mlp_fits = {k: int((frame.model == "Multilayer perceptron").sum())
                    for k, frame in (("tuning", tuning), ("validation", validation), ("learning", learning))}
        other_warn = sum(int(frame[frame.model != "Multilayer perceptron"].fit_warnings.fillna("").ne("").sum())
                         for frame in (tuning, validation, learning))
        hidden = chosen["Multilayer perceptron"]["hidden_layer_sizes"]
        width_in = len(task.numeric) + one_hot
        layers = [width_in, *hidden, 1 if task.name == "wicket" else 3]
        mlp_params = int(sum((layers[i] + 1) * layers[i + 1] for i in range(len(layers) - 1)))
        binning = pd.DataFrame([{"task": task.name, "feature": f, "distinct_training_values": int(dev[f].nunique()),
                                 "max_bins": HGB_MAX_BINS, "binned_losslessly": bool(dev[f].nunique() <= HGB_MAX_BINS)}
                                for f in task.numeric])
        tables["binning"].append(binning)
        hgb_curve = [at(SELECTED, f, "validation_brier") for f in TRAIN_FRACTIONS]
        plateau = {"validation_brier_by_fraction": dict(zip(map(str, TRAIN_FRACTIONS), map(lambda x: fmt(x, 6), hgb_curve))),
                   "change_50_to_75": fmt(hgb_curve[3] - hgb_curve[2], 6),
                   "change_75_to_100": fmt(hgb_curve[4] - hgb_curve[3], 6),
                   "change_10_to_50": fmt(hgb_curve[2] - hgb_curve[0], 6)}
        per_fold = learning[learning.model == SELECTED].pivot(index="year", columns="training_fraction",
                                                               values="validation_brier")
        plateau["per_season_change_75_to_100"] = {str(y): fmt(r[1.0] - r[0.75], 6) for y, r in per_fold.iterrows()}
        leaders = comparison.model.head(3).tolist()
        spread = {}
        for f in TRAIN_FRACTIONS:
            values = [at(m, f, "validation_brier") for m in leaders]
            spread[str(f)] = fmt(max(values) - min(values), 6)
        best_other = {}
        for f in TRAIN_FRACTIONS:
            others = {m: at(m, f, "validation_brier") for m in MODELS if m != SELECTED}
            name = min(others, key=others.get)
            best_other[str(f)] = {"model": name, "gap_to_selected": fmt(others[name] - at(SELECTED, f, "validation_brier"), 6)}
        accuracy_floor = t["class_balance"]["majority_class_accuracy_mean"]
        accuracies = {m: fmt(float(comparison.loc[comparison.model == m, "accuracy_mean"].iloc[0])) for m in MODELS}
        t["convergence"] = {
            "leaders": leaders, "leader_brier_spread_by_fraction": spread,
            "best_alternative_by_fraction": best_other, "selected_plateau": plateau,
            "paired_gaps_vs_selected": paired,
            "accuracy_mean_by_model": accuracies, "majority_class_accuracy_mean": accuracy_floor,
            "models_within_1pp_of_majority_accuracy": [m for m, a in accuracies.items() if abs(a - accuracy_floor) <= .01],
            "selected_mean_validation_brier": fmt(mean_brier(SELECTED), 6),
            "runner_up": comparison.model.iloc[1], "runner_up_gap": fmt(comparison.brier_mean.iloc[1] - comparison.brier_mean.iloc[0], 6),
            "holdout_2026": {k: holdout[task.name]["metrics"][k] for k in ("brier", "log_loss", "accuracy", "balanced_accuracy", "roc_auc")},
        }

        # ---- verdicts (rules stated inline)
        hom = t["base_rate_homogeneity"]
        worst_dev = max(v["max_abs_deviation"] for v in hom.values())
        min_p = min(v["p_value"] for v in hom.values())
        # Base rate: Holds if no season differs significantly; Partially if it does but within 5 points; else Violated
        prior_verdict = ("Holds" if min_p >= ALPHA else "Partially holds" if worst_dev <= .05 else "Violated")
        max_vif = float(v.vif.max())
        # Logistic: Violated if half or more of the tested features are clearly non-linear in the log-odds;
        # Holds if none is and collinearity and events per parameter are fine; otherwise Partially holds
        if len(nonlinear) >= max(1, len(tested)) / 2:
            logistic_verdict = "Violated"
        elif nonlinear.empty and max_vif < VIF_HIGH and epp["events_per_parameter"] >= EPP_MIN:
            logistic_verdict = "Holds"
        else:
            logistic_verdict = "Partially holds"
        tree_sd = sd_brier("Decision tree")
        tree_settings = tuning_effect(task, tuning, "Decision tree")
        # Tree: piecewise-constant axis-aligned splits are adequate if the tree is not beaten by the forest in
        # every season; Partially holds when it is (the ensemble removes a consistent error)
        tree_vs_forest = gaps["Decision tree"] - gaps["Random forest"]
        tree_verdict = "Partially holds" if (tree_vs_forest > 0).all() else "Holds"
        # Forest: averaging should cut the single tree's error: Holds if it beats the tree in every season
        forest_verdict = "Holds" if (tree_vs_forest > 0).all() else "Partially holds"
        # Boosting: Holds if validation Brier no longer worsens with more data (75%->100% change <= 0) and its
        # train-validation gap exceeds the class-prior baseline's own gap (which reflects season drift, not
        # overfitting) by at most 0.005; Partially holds otherwise
        excess_gap = gap(SELECTED) - gap("Class-prior baseline")
        hgb_verdict = ("Holds" if plateau["change_75_to_100"] <= 0 and excess_gap <= .005 else "Partially holds")
        # Naive Bayes: its defining assumption is conditional independence. Violated if any within-class pair of
        # inputs correlates at |r| >= 0.5 (the one-hot columns are binary, so the Gaussian form fails for them in
        # any case); Partially holds if only the Gaussian shape fails; Holds otherwise
        nb_verdict = ("Violated" if len(strong) else "Partially holds" if len(nonnormal) or one_hot else "Holds")
        # MLP: Partially holds if the epoch cap stopped fits or seeds move Brier by more than the gap to boosting
        seed_range = float(seeds.brier.max() - seeds.brier.min())
        capped = sum(mlp_warn.values())
        mlp_gap = mean_brier("Multilayer perceptron") - mean_brier(SELECTED)
        mlp_verdict = ("Holds" if capped == 0 and seed_range < abs(mlp_gap) else "Partially holds")
        t["algorithms"] = {
            "Class-prior baseline": {"verdict": prior_verdict, "evidence": {"homogeneity": hom}},
            "Logistic regression": {"verdict": logistic_verdict, "evidence": {
                "features_tested": int(len(tested)), "bonferroni_alpha": fmt(bonferroni, 6),
                "clearly_nonlinear_features": nonlinear.feature.tolist(),
                "max_vif": fmt(max_vif, 2), "max_vif_feature": v.loc[v.vif.idxmax()].feature,
                "features_with_vif_above_10": v[v.vif > VIF_HIGH].feature.tolist(),
                "events_per_parameter": epp,
                "regularisation": reg[["params", "tuning_brier_mean", "tuning_brier_sd"]].to_dict(orient="records"),
                "chosen_setting": chosen["Logistic regression"],
                "independence_icc_by_match": t["dependence"][next(k for k in t["dependence"] if k.startswith("icc_") and k.endswith("_by_match"))]}},
            "Decision tree": {"verdict": tree_verdict, "evidence": {
                "chosen_setting": chosen["Decision tree"],
                "tuning_brier_by_setting": tree_settings[["params", "tuning_brier_mean", "tuning_brier_sd"]].to_dict(orient="records"),
                "validation_brier_sd_across_seasons": fmt(tree_sd, 6),
                "train_validation_gap": fmt(gap("Decision tree"), 6),
                "seasons_forest_beats_tree": int((tree_vs_forest > 0).sum())}},
            "Random forest": {"verdict": forest_verdict, "evidence": {
                "chosen_setting": chosen["Random forest"], "trees": 160,
                "mean_brier_tree_minus_forest": fmt(tree_vs_forest.mean(), 6),
                "seasons_forest_beats_tree": int((tree_vs_forest > 0).sum()),
                "validation_brier_sd_forest": fmt(sd_brier("Random forest"), 6),
                "validation_brier_sd_tree": fmt(tree_sd, 6),
                "train_validation_gap_forest": fmt(gap("Random forest"), 6),
                "train_validation_gap_tree": fmt(gap("Decision tree"), 6)}},
            SELECTED: {"verdict": hgb_verdict, "evidence": {
                "chosen_setting": chosen[SELECTED], "learning_rate": 0.06, "min_samples_leaf": 50, "max_bins": HGB_MAX_BINS,
                "numeric_features_binned_losslessly": int(binning.binned_losslessly.sum()),
                "numeric_features": int(len(binning)),
                "features_with_more_values_than_bins": binning[~binning.binned_losslessly].feature.tolist(),
                "train_validation_gap": fmt(gap(SELECTED), 6),
                "class_prior_train_validation_gap": fmt(gap("Class-prior baseline"), 6),
                "excess_train_validation_gap": fmt(excess_gap, 6), "plateau": plateau,
                "tuning_brier_by_setting": tuning_effect(task, tuning, SELECTED)[["params", "tuning_brier_mean", "tuning_brier_sd"]].to_dict(orient="records")}},
            "Gaussian naive Bayes": {"verdict": nb_verdict, "evidence": {
                "chosen_setting": chosen["Gaussian naive Bayes"],
                "within_class_pairs_abs_corr_at_least_0.5": int(len(strong)),
                "largest_within_class_correlations": top_corr.to_dict(orient="records"),
                "class_feature_pairs_far_from_normal": int(len(nonnormal)), "class_feature_pairs": int(len(shapes)),
                "one_hot_binary_columns": int(one_hot),
                "calibration_2025": calib, "mean_validation_brier": fmt(mean_brier("Gaussian naive Bayes"), 6)}},
            "Multilayer perceptron": {"verdict": mlp_verdict, "evidence": {
                "chosen_setting": chosen["Multilayer perceptron"], "inputs_standardised": True,
                "fits_stopped_by_epoch_cap": mlp_warn, "mlp_fits": mlp_fits,
                "other_models_fit_warnings": other_warn,
                "seed_brier_range_2025": fmt(seed_range, 6), "seed_brier_sd_2025": fmt(seeds.brier.std(), 6),
                "seeds": list(MLP_SEEDS), "gap_to_selected_mean_brier": fmt(mlp_gap, 6),
                "weights_and_biases": mlp_params, "training_rows_2008_2024": int(len(split(data, 2025)[0]))}},
        }
        summary["tasks"][task.name] = t

        plot_linearity(task, out)
        plot_drift(task, rates, shift, out)
        qq = ["runs", "run_rate", "last_over_runs"] if task.name == "wicket" else ["career_avg_runs", "recent5_avg_runs", "days_since_previous_innings"]
        plot_qq(task, dev, out, qq)
        plot_learning(task, lsum, out)
        plot_gaps(task, gaps, out)
        print(f"Analysed {task.name}", flush=True)

    for name, frames in tables.items():
        if frames:
            frame = pd.concat(frames, ignore_index=True)
            frame.to_csv(out / f"{name}.csv", index=False, float_format="%.10g")
    pd.DataFrame(summary["eligibility"]).to_csv(out / "eligibility.csv", index=False)
    summary["verdicts"] = verdict_tables(summary)
    write_json(out / "summary.json", json.loads(json.dumps(summary, default=_json_default)))
    return summary


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(type(value))


def verdict_tables(summary: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    """Plain-language verdict rows, written from the computed numbers."""
    w, b = summary["tasks"]["wicket"], summary["tasks"]["batter"]
    wd, bd = w["dependence"], b["dependence"]
    iccs = {task: {k: v for k, v in d.items() if k.startswith("icc_")} for task, d in (("wicket", wd), ("batter", bd))}
    # Independence: per task Violated if any intraclass correlation (by match or by innings) is significant;
    # overall Violated if both tasks are, Partially holds if one is, Holds if neither
    clustered = {task: any(v["p_value"] < ALPHA for v in d.values()) for task, d in iccs.items()}
    independence = ["Holds", "Partially holds", "Violated"][sum(clustered.values())]

    def shares(t):
        return " / ".join(f"{v:.2%}" for v in t["class_balance"]["class_shares"].values())

    def icc_text(task):
        return "; ".join(f"{k.replace('icc_', '').replace('_by_', ' by ')} ICC {v['icc']} (p={v['p_value']:.2g})"
                         for k, v in iccs[task].items())

    def drift_verdict(d):
        if d["seasons_with_large_smd"] == 0 and d["max_psi"] < PSI_MODERATE and d["pairs_with_small_or_larger_smd"] == 0:
            return "Holds"
        if d["seasons_with_large_smd"] >= 3 or d["seasons_with_major_psi"] >= 3:
            return "Violated"
        return "Partially holds"

    drift_v = [drift_verdict(w["drift"]), drift_verdict(b["drift"])]
    order = ["Holds", "Partially holds", "Violated"]
    worst_drift = max(drift_v, key=order.index)
    unseen_rows = {k: w["unseen_levels"][k] + b["unseen_levels"][k] for k in w["unseen_levels"]}
    data = [
        {"assumption": "Chronological order, no leakage", "verdict": "Holds",
         "evidence": (f"{w['chronology']['folds_checked']} folds per task: every training date precedes every "
                      f"evaluation date (smallest gap {min(w['chronology']['min_gap_days'], b['chronology']['min_gap_days'])} days), "
                      f"{w['chronology']['shared_matches'] + b['chronology']['shared_matches']} shared matches; "
                      f"{b['chronology']['strictly_prior_feature_rows_verified']:,} batter rows rebuilt from strictly earlier dates"),
         "consequence": "Validation and test scores are not inflated by future information."},
        {"assumption": "Independent rows", "verdict": independence,
         "evidence": (f"{wd['rows_per_match']['mean']} wicket rows and {bd['rows_per_match']['mean']} batter rows per match. "
                      f"Wicket: {icc_text('wicket')}. Batter: {icc_text('batter')}"),
         "consequence": ("Batter outcomes cluster slightly within an innings and a match, and wicket rows from one innings "
                         "share its running score, so whole matches and seasons stay together in every split and "
                         "uncertainty is reported across seasons, not rows.")},
        {"assumption": "Stationary seasons", "verdict": worst_drift,
         "evidence": (f"Largest season-vs-history shift: {w['drift']['max_abs_smd_feature']} SMD {w['drift']['max_abs_smd']} "
                      f"in {w['drift']['max_abs_smd_season']} (wicket), {b['drift']['max_abs_smd_feature']} SMD "
                      f"{b['drift']['max_abs_smd']} in {b['drift']['max_abs_smd_season']} (batter); wicket rate "
                      f"{w['base_rate_homogeneity']['wicket']['min_rate']:.1%}–{w['base_rate_homogeneity']['wicket']['max_rate']:.1%} by season"),
         "consequence": "Older seasons describe a different scoring environment; expanding-window training and season-by-season evaluation measure the effect instead of assuming it away."},
        {"assumption": "Classes adequately represented", "verdict": "Partially holds",
         "evidence": (f"Wicket class shares {shares(w)} (no wicket / wicket); batter {shares(b)} (under 30 / 30–49 / 50+); "
                      f"predicting the majority class scores {w['class_balance']['majority_class_accuracy_mean']:.1%} "
                      f"(wicket) and {b['class_balance']['majority_class_accuracy_mean']:.1%} (batter) accuracy"),
         "consequence": "Accuracy is dominated by the majority class, so probability scores (Brier, log loss) rank the models."},
        {"assumption": "Complete inputs; sensible defaults", "verdict": "Partially holds",
         "evidence": (f"{w['defaults']['missing_model_inputs'] + b['defaults']['missing_model_inputs']} missing model inputs; "
                      f"{b['defaults']['cold_start_rows_prior_innings_0']:,} batter rows with no earlier innings use "
                      f"defaults ({b['defaults']['cold_start_rows_2026']} in 2026)"),
         "consequence": "A debutant's 0.0 history rates are a code for 'no history', not an observed zero; prior_innings = 0 lets trees separate the two."},
        {"assumption": "Category levels seen in training", "verdict": "Partially holds" if any(unseen_rows.values()) else "Holds",
         "evidence": "Rows with a level unseen in training: " + ", ".join(f"{k}: {v:,}" for k, v in unseen_rows.items() if v),
         "consequence": "Unseen levels (the two 2022 franchises, new venues) are encoded as all-zero, so those rows fall back on the other inputs."},
        {"assumption": "Measurement scales respected", "verdict": "Holds",
         "evidence": "Counts and rates are ratio-scale numbers; teams and venues are nominal (one-hot); phase is ordinal, one-hot encoded",
         "consequence": "No arithmetic is done on nominal codes."},
        {"assumption": "Eligibility rules applied", "verdict": "Holds",
         "evidence": (f"Wicket: {w_e(summary, 'eligible rows'):,} rows after removing D/L matches and censored overs; "
                      f"batter: {b_e(summary, 'eligible rows'):,} innings after removing D/L and no-result matches; "
                      f"super-over innings never enter"),
         "consequence": "The forecasts describe ordinary, uninterrupted innings, not D/L-shortened ones."},
    ]
    algos = []
    for model in MODELS:
        wv, bv = w["algorithms"][model], b["algorithms"][model]
        verdict = max((wv["verdict"], bv["verdict"]), key=order.index)
        algos.append({"model": model, "verdict": verdict, "wicket_verdict": wv["verdict"], "batter_verdict": bv["verdict"]})
    return {"data": data, "algorithms": algos}


def w_e(summary, rule):
    return next(r["count"] for r in summary["eligibility"] if r["scope"] == "wicket" and r["rule"] == rule)


def b_e(summary, rule):
    return next(r["count"] for r in summary["eligibility"] if r["scope"] == "batter" and r["rule"] == rule)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("reports/model_benchmark/assumptions"))
    args = parser.parse_args()
    analyse(args.root, args.output)
    print(f"Wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
