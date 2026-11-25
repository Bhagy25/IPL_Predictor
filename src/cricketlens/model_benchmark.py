"""Chronological probability-model comparison for both CricketLens forecasts."""

from __future__ import annotations

import argparse
import json
import math
import platform
import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score, brier_score_loss,
    confusion_matrix, f1_score, log_loss, roc_auc_score,
)
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from threadpoolctl import threadpool_limits

from cricketlens.fit_batter_models import (
    CONTEXT_CAT, FORM_NUM, Y, make_forest, make_logistic as batter_logistic,
    positive_probability_three_class,
)
from cricketlens.fit_wicket_models import (
    ADDED_NUM, BASIC_CAT, BASIC_NUM, ENHANCED_CAT, TARGET, make_logistic as wicket_logistic,
)
from cricketlens.hashing import table_sha256

SEED = 42
TUNING_YEARS = (2018, 2019, 2020)
VALIDATION_YEARS = (2021, 2022, 2023, 2024, 2025)
TEST_YEAR = 2026
TRAIN_FRACTIONS = (0.10, 0.25, 0.50, 0.75, 1.00)
METRICS = ("brier", "log_loss", "accuracy", "balanced_accuracy", "macro_f1", "roc_auc", "average_precision")


@dataclass(frozen=True)
class Task:
    name: str
    target: str
    numeric: list[str]
    categorical: list[str]
    keys: list[str]
    classes: tuple[int, ...]
    deployed: str

    @property
    def features(self):
        return self.numeric + self.categorical

    @property
    def path(self):
        return f"stage03_{self.name}_full_history_2008_2026.csv"


TASKS = (
    Task("wicket", TARGET, BASIC_NUM + ADDED_NUM, BASIC_CAT + ENHANCED_CAT,
         ["match_id", "innings", "completed_overs"], (0, 1), "Logistic regression"),
    Task("batter", Y, FORM_NUM, CONTEXT_CAT,
         ["match_id", "innings", "batter_id"], (0, 1, 2), "Random forest"),
)


def search_space(task: Task):
    logistic_c = 1.0 if task.name == "wicket" else 0.25
    return {
        "Class-prior baseline": [{}],
        "Logistic regression": [{"C": c} for c in (logistic_c, 0.05, 4.0)],
        "Decision tree": [
            {"max_depth": 3, "min_samples_leaf": 100},
            {"max_depth": 5, "min_samples_leaf": 60},
            {"max_depth": 8, "min_samples_leaf": 40},
        ],
        "Random forest": [
            {"max_depth": 8, "min_samples_leaf": 30},
            {"max_depth": 5, "min_samples_leaf": 60},
            {"max_depth": 12, "min_samples_leaf": 15},
        ],
        "Histogram gradient boosting": [
            {"max_leaf_nodes": 7, "max_iter": 60, "l2_regularization": 2.0},
            {"max_leaf_nodes": 15, "max_iter": 100, "l2_regularization": 4.0},
            {"max_leaf_nodes": 31, "max_iter": 140, "l2_regularization": 8.0},
        ],
        "Gaussian naive Bayes": [{"var_smoothing": value} for value in (1e-3, 0.03, 0.20)],
        "Multilayer perceptron": [
            {"hidden_layer_sizes": (12,), "alpha": 0.1, "max_iter": 25},
            {"hidden_layer_sizes": (24,), "alpha": 1.0, "max_iter": 35},
            {"hidden_layer_sizes": (32, 12), "alpha": 2.0, "max_iter": 45},
        ],
    }


def estimator(task, name, params):
    if name == "Class-prior baseline":
        return DummyClassifier(strategy="prior")
    if name == "Logistic regression":
        factory = wicket_logistic if task.name == "wicket" else batter_logistic
        return factory(task.numeric, task.categorical).set_params(model__C=params["C"])
    if name == "Random forest":
        return make_forest(task.numeric, task.categorical).set_params(
            model__n_jobs=1, **{f"model__{key}": value for key, value in params.items()}
        )

    models = {
        "Decision tree": DecisionTreeClassifier(random_state=SEED),
        "Histogram gradient boosting": HistGradientBoostingClassifier(
            learning_rate=0.06, min_samples_leaf=50, early_stopping=False, random_state=SEED,
        ),
        "Gaussian naive Bayes": GaussianNB(),
        "Multilayer perceptron": MLPClassifier(
            solver="adam", early_stopping=False, n_iter_no_change=46, random_state=SEED,
        ),
    }
    numeric = SimpleImputer(strategy="median")
    if name in {"Gaussian naive Bayes", "Multilayer perceptron"}:
        numeric = make_pipeline(numeric, StandardScaler())
    features = ColumnTransformer([
        ("numeric", numeric, task.numeric),
        ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), task.categorical),
    ])
    return make_pipeline(features, models[name].set_params(**params))


def data_for(task, data_dir):
    data = pd.read_csv(data_dir / task.path, parse_dates=["date"])
    required = set(task.keys + task.features + ["date", "season", task.target])
    if missing := required - set(data.columns):
        raise ValueError(f"Missing columns for {task.name}: {sorted(missing)}")
    if data[[*task.keys, "date", "season", task.target]].isna().any().any():
        raise ValueError(f"Missing match metadata or targets for {task.name}")
    if (data.duplicated(task.keys).any() or not data.date.dt.year.eq(data.season).all()
            or data.groupby("match_id")[["date", "season"]].nunique().ne(1).any().any()):
        raise ValueError(f"Inconsistent match keys, dates or seasons for {task.name}")
    if not set(data[task.target]).issubset(task.classes):
        raise ValueError(f"Unexpected class in {task.name}")
    return data.sort_values(["date", *task.keys]).reset_index(drop=True)


def split(data, year):
    train = data.loc[data.season < year]
    valid = data.loc[data.season == year]
    if (train.empty or valid.empty or train.date.max() >= valid.date.min()
            or set(train.match_id).intersection(valid.match_id)):
        raise ValueError(f"Invalid temporal or match split for {year}")
    return train, valid


def recent_matches(train, fraction):
    matches = train.drop_duplicates("match_id").sort_values(["date", "match_id"])
    cutoff = matches.date.iloc[-math.ceil(fraction * len(matches))]
    return train.loc[train.date >= cutoff]


def fit(task, name, params, train):
    if set(train[task.target]) != set(task.classes):
        raise ValueError(f"Training fold must contain all {task.name} classes")
    model = estimator(task, name, params)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(train[task.features], train[task.target])
    convergence = [str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)]
    for warning in caught:
        if not issubclass(warning.category, ConvergenceWarning):
            warnings.warn_explicit(str(warning.message), warning.category, warning.filename, warning.lineno)
    return model, convergence


def probabilities(task, model, data):
    proba = model.predict_proba(data[task.features])
    if (tuple(model.classes_) != task.classes or not np.isfinite(proba).all()
            or (proba < 0).any() or not np.allclose(proba.sum(axis=1), 1.0, rtol=0, atol=1e-12)):
        raise ValueError("Invalid predicted probability distribution")
    return proba


def event_probabilities(task, y, p):
    if task.name == "wicket":
        return [("wicket", y == 1, np.clip(p[:, 1], 0, 1))]
    p30, p50 = positive_probability_three_class(p)
    # Averaging tree probabilities can nudge an exact endpoint past 1 by roundoff.
    return [("30", y >= 1, np.clip(p30, 0, 1)), ("50", y == 2, np.clip(p50, 0, 1))]


def event_scores(task, y, p):
    metrics = {}
    for label, actual, predicted in event_probabilities(task, y, p):
        metrics[f"brier_{label}"] = brier_score_loss(actual, predicted)
        metrics[f"roc_auc_{label}"] = roc_auc_score(actual, predicted)
        metrics[f"average_precision_{label}"] = average_precision_score(actual, predicted)
        metrics[f"observed_rate_{label}"] = float(actual.mean())
        metrics[f"mean_probability_{label}"] = float(predicted.mean())
    return metrics


def score(task, data, p):
    y = data[task.target].to_numpy()
    pred = p.argmax(axis=1)
    events = event_scores(task, y, p)
    return {
        "brier": float(np.mean([v for k, v in events.items() if k.startswith("brier_")])),
        "log_loss": log_loss(y, p, labels=task.classes),
        "accuracy": accuracy_score(y, pred),
        "balanced_accuracy": balanced_accuracy_score(y, pred),
        "macro_f1": f1_score(y, pred, labels=task.classes, average="macro", zero_division=0),
        "roc_auc": float(np.mean([v for k, v in events.items() if k.startswith("roc_auc_")])),
        "average_precision": float(np.mean([v for k, v in events.items() if k.startswith("average_precision_")])),
        **events,
    }


def fold_info(train, valid, year):
    return {
        "year": year, "train_start": train.date.min().date().isoformat(),
        "train_end": train.date.max().date().isoformat(),
        "train_rows": len(train), "train_matches": train.match_id.nunique(),
        "evaluation_rows": len(valid), "evaluation_matches": valid.match_id.nunique(),
    }


def tune(task, dev, grids):
    rows, choices = [], {}
    for name, grid in grids.items():
        trials = []
        for index, params in enumerate(grid):
            for year in TUNING_YEARS:
                train, valid = split(dev, year)
                model, convergence = fit(task, name, params, train)
                scores = score(task, valid, probabilities(task, model, valid))
                trials.append({"model": name, "setting": index, "params": json.dumps(params),
                               **fold_info(train, valid, year), "fit_warnings": " | ".join(convergence), **scores})
        trial_frame = pd.DataFrame(trials)
        ranking = trial_frame.groupby("setting")[["brier", "log_loss"]].mean().reset_index()
        best = int(ranking.sort_values(["brier", "log_loss", "setting"]).iloc[0].setting)
        choices[name] = best
        rows.extend(trials)
        print(f"  Tuned {name}", flush=True)
    return pd.DataFrame(rows), choices


def compare(task, dev, grids, choices):
    validation, learning, incumbent = [], [], []
    for name, index in choices.items():
        for year in VALIDATION_YEARS:
            full, valid = split(dev, year)
            for fraction in TRAIN_FRACTIONS:
                train = recent_matches(full, fraction)
                model, convergence = fit(task, name, grids[name][index], train)
                valid_scores = score(task, valid, probabilities(task, model, valid))
                train_scores = score(task, train, probabilities(task, model, train))
                row = {"model": name, "setting": index, "training_fraction": fraction,
                       **fold_info(train, valid, year), "fit_warnings": " | ".join(convergence)}
                learning.append({**row, **{f"train_{k}": v for k, v in train_scores.items()},
                                 **{f"validation_{k}": v for k, v in valid_scores.items()}})
                if fraction == 1.0:
                    validation.append({**row, **valid_scores})
                    if name == task.deployed:
                        if index == 0:
                            incumbent.append({**row, **valid_scores})
                        else:
                            original, original_warnings = fit(task, name, grids[name][0], train)
                            observed = score(task, valid, probabilities(task, original, valid))
                            incumbent.append({**row, "setting": 0,
                                              "fit_warnings": " | ".join(original_warnings), **observed})
        print(f"  Evaluated {name}", flush=True)
    return pd.DataFrame(validation), pd.DataFrame(learning), pd.DataFrame(incumbent)


def combined_scores(validation):
    summary = validation.groupby(["model", "setting"])[list(METRICS)].agg(["mean", "std"])
    summary.columns = [f"{metric}_{stat}" for metric, stat in summary.columns]
    return summary.reset_index().sort_values(["brier_mean", "log_loss_mean", "model"]).reset_index(drop=True)


def plot_learning(task, learning, output):
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    for metric, label, percent in [
        ("accuracy", "Accuracy", True), ("balanced_accuracy", "Balanced accuracy", True),
        ("brier", "Brier score", False),
    ]:
        panels = list(learning.groupby("model", sort=False))
        fig, axes = plt.subplots(2, 4, figsize=(13.2, 6.3), sharex=True, sharey=True)
        for ax, (name, data) in zip(axes.flat, panels):
            grouped = data.groupby("training_fraction")
            x = grouped.train_matches.mean()
            for key, color, caption in [("train", "#007e86", "Training"), ("validation", "#9c410c", "Validation")]:
                values = grouped[f"{key}_{metric}"]
                mean, sd = values.mean(), values.std()
                ax.plot(x, mean, marker="o", markersize=4, label=caption, color=color)
                ax.fill_between(x, mean - sd, mean + sd, alpha=.13, color=color, linewidth=0)
            ax.set_title(name, loc="left", fontsize=10, fontweight="bold")
            ax.grid(axis="y", alpha=.28)
            if percent:
                ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        axes.flat[-1].axis("off")
        handles, labels = axes.flat[0].get_legend_handles_labels()
        axes.flat[-1].legend(handles, labels, loc="center left", frameon=False,
                             title="Mean ± 1 SD across five folds")
        task_title = "Next-over wicket" if task.name == "wicket" else "Batter milestones"
        fig.suptitle(f"{task_title} | {label} learning curves", x=.08, ha="left", fontsize=17)
        fig.supxlabel("Mean number of training matches")
        fig.supylabel(label + (" (%)" if percent else " (lower is better)"))
        fig.text(.08, .90, "Cricsheet IPL • validation seasons 2021–2025 • same validation season at every size within a fold",
                 fontsize=9)
        fig.tight_layout(rect=(.03, .055, 1, .89))
        fig.savefig(output / f"{task.name}_{metric}_learning.png", dpi=170, bbox_inches="tight")
        plt.close(fig)


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def development(task, data, out, fingerprint):
    dev = data.loc[data.season < TEST_YEAR]
    grids = search_space(task)
    tuning, choices = tune(task, dev, grids)
    validation, learning, incumbent = compare(task, dev, grids, choices)
    summary = combined_scores(validation)
    best = summary.iloc[0]
    model = str(best.model)
    pairs = validation.pivot(index="year", columns="model", values="brier")
    for name, frame in {"tuning": tuning, "validation": validation,
                        "learning": learning, "incumbent": incumbent}.items():
        frame.to_csv(out / f"{task.name}_{name}.csv", index=False)
    summary.to_csv(out / f"{task.name}_comparison.csv", index=False)
    pairs.sub(pairs[model], axis=0).to_csv(out / f"{task.name}_paired_brier_gaps.csv")
    plot_learning(task, learning, out)
    return {"selected": model, "selected_setting": int(best.setting),
            "params": grids[model][choices[model]], "target": task.target, "features": task.features,
            "chosen_settings": choices, "input_sha256": fingerprint}


def holdout(task, data, choice, out):
    name, params = choice["selected"], choice["params"]
    train, test = split(data, TEST_YEAR)
    model, convergence = fit(task, name, params, train)
    p = probabilities(task, model, test)
    result = score(task, test, p)
    y = test[task.target].to_numpy()
    forecasts = test[[*task.keys, "date", task.target]].copy()
    for i in task.classes:
        forecasts[f"p_class_{i}"] = p[:, i]
    events = event_probabilities(task, y, p)
    if task.name == "batter":
        for event, _, predicted in events:
            forecasts[f"p_{event}"] = predicted
    forecasts["predicted_class"] = p.argmax(axis=1)
    forecasts.to_csv(out / f"{task.name}_holdout_forecasts.csv", index=False)
    calibration = []
    for event, actual, predicted in events:
        bins = pd.cut(predicted, np.linspace(0, 1, 11), labels=False, include_lowest=True)
        table = pd.DataFrame({"bin": bins, "actual": actual, "predicted": predicted})
        table = table.groupby("bin").agg(rows=("actual", "size"), observed_rate=("actual", "mean"),
                                         mean_probability=("predicted", "mean")).reset_index()
        table["event"] = event
        calibration.append(table)
    pd.concat(calibration).to_csv(out / f"{task.name}_holdout_calibration.csv", index=False)
    return {"model": name, "params": params, **fold_info(train, test, TEST_YEAR),
            "fit_warnings": convergence, "class_counts": {str(i): int((y == i).sum()) for i in task.classes},
            "confusion_matrix": confusion_matrix(y, p.argmax(axis=1), labels=task.classes).tolist(),
            "metrics": result}


def experiment_manifest():
    return {"seed": SEED, "tuning_years": TUNING_YEARS, "validation_years": VALIDATION_YEARS,
            "holdout_year": TEST_YEAR, "training_fractions": TRAIN_FRACTIONS,
            "versions": {"python": platform.python_version(), "numpy": np.__version__,
                         "pandas": pd.__version__, "scipy": scipy.__version__,
                         "scikit-learn": sklearn.__version__, "matplotlib": matplotlib.__version__},
            "tasks": {}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, default=Path("reports/model_benchmark"))
    parser.add_argument("--phase", choices=("all", "development", "holdout"), default="all")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    selection_path = args.output / "selection.json"
    tables = {task.name: data_for(task, args.data) for task in TASKS}
    fingerprints = {
        task.name: table_sha256(args.data / task.path) for task in TASKS
    }
    with threadpool_limits(limits=1):
        if args.phase in {"all", "development"}:
            manifest = experiment_manifest()
            for task in TASKS:
                print(f"Comparing {task.name} candidates", flush=True)
                manifest["tasks"][task.name] = development(
                    task, tables[task.name], args.output, fingerprints[task.name],
                )
            write_json(selection_path, manifest)
        if args.phase in {"all", "holdout"}:
            choices = json.loads(selection_path.read_text(encoding="utf-8"))["tasks"]
            for task in TASKS:
                choice = choices[task.name]
                if choice["input_sha256"] != fingerprints[task.name] or choice["features"] != task.features:
                    raise ValueError(f"Holdout input or feature schema differs from frozen selection for {task.name}")
            result = {task.name: holdout(task, tables[task.name], choices[task.name], args.output) for task in TASKS}
            write_json(args.output / "holdout_2026.json", result)
            print(json.dumps({name: entry["model"] for name, entry in result.items()}), flush=True)


if __name__ == "__main__":
    main()
