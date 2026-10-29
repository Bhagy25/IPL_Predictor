"""Predictions from the Stage 3 deployment models and the official 2026 holdout evaluation.

Every probability comes from the Stage 3 inference functions, predict_wicket.forecast() and
forecast_future_batter.forecast(), called with the saved deployment artifacts. Nothing here builds
model features, refits or re-saves a model. Evaluation numbers are read from the Stage 3 Session 3
report and its per-example 2026 holdout forecasts. User inputs are neither logged nor stored.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from cricketlens import forecast_future_batter, predict_wicket
from cricketlens.fit_batter_models import calibration_table, metrics as batter_metrics
from cricketlens.fit_wicket_models import measure as wicket_measure, reliability as wicket_reliability
from cricketlens.wicket_training_data import phase_for_next_over
from cricketlens.api.services.canonical_data import FRANCHISE_METADATA, DerivedDataUnavailable, canonical_engine

ROOT = Path(__file__).resolve().parents[4]
MODEL_DIR = ROOT / "models"
DATA_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports" / "stage_03" / "session_03"

DEPLOYMENT_VERSION = "deployment_refit_2008_2026"
DEPLOYMENT_TRAIN_END = 2026
# Per model: the deployment artifact served here, the holdout artifact the 2026 evaluation used,
# and the artifact key holding the last training season (the two Stage 3 scripts name it differently).
MODELS: Dict[str, Dict[str, str]] = {
    "wicket": {
        "deployment": "wicket_deployment_through_2026.joblib",
        "holdout": "wicket_holdout_train_through_2025.joblib",
        "end_key": "training_end",
        "title": "Next-over wicket risk",
    },
    "batter": {
        "deployment": "batter_deployment_through_2026.joblib",
        "holdout": "batter_holdout_train_through_2025.joblib",
        "end_key": "train_end",
        "title": "Batter milestones (30+ / 50+)",
    },
}
RESULTS_JSON = "stage03_session03_final_results.json"
WICKET_HOLDOUT_CSV = Path("wicket") / "wicket_holdout_forecasts_2026.csv"
BATTER_HOLDOUT_CSV = Path("batter") / "batter_holdout_forecasts_2026.csv"
WICKET_CALIBRATION_CSV = Path("wicket") / "wicket_holdout_calibration_2026.csv"
BATTER_CALIBRATION_CSV = Path("batter") / "batter_holdout_calibration_2026.csv"
# Equal-width probability bins used by the Stage 3 calibration tables (reliability / calibration_table defaults)
WICKET_CALIBRATION_BINS = 10
BATTER_CALIBRATION_BINS = 8
METRIC_TOLERANCE = 1e-6

# The same eligibility rule forecast_future_batter.forecast() applies to a player's history
DLS_METHODS = {"D/L", "DLS", "D/L METHOD", "DLS METHOD"}
RECENT_INNINGS_SHOWN = 5

# Physically impossible inputs: an over has six legal balls (6 x 6 = 36 runs) plus an allowance for extras.
# These are deliberately loose bounds, not a precise rule; the 2008-2026 data never comes close to them.
MAX_RUNS_PER_OVER = 36
RUNS_EXTRAS_ALLOWANCE = 30
LAST_OVER_EXTRAS_ALLOWANCE = 20
# Input rules mirrored from predict_wicket.forecast(); the API adds team and venue membership
# because the models' encoders silently ignore an unknown category (handle_unknown="ignore").
WICKET_RULES = {
    "innings": [1, 2],
    "completed_overs": {"min": 1, "max": 19},
    "wickets": {"min": 0, "max": 9},
    "runs": {"min": 0, "max": f"{MAX_RUNS_PER_OVER} x completed overs + {RUNS_EXTRAS_ALLOWANCE}"},
    "last_over_runs": f"0 to the current runs, and at most {MAX_RUNS_PER_OVER + LAST_OVER_EXTRAS_ALLOWANCE}",
    "last_over_wickets": "0 to the current wickets",
}
# The deployment wicket model's eligible training rows (read only): observed ranges per checkpoint
WICKET_TRAINING_ROWS = "stage03_wicket_full_history_2008_2026.csv"
RANGE_FIELDS = {"runs": "Runs", "run_rate": "Run rate", "last_over_runs": "Last-over runs"}
# The stored run rate differs from runs / overs by float rounding (about 1e-15); boundaries count as seen
RANGE_TOLERANCE = 1e-9
EXTRAPOLATION_WARNING = ("These inputs are outside anything seen in {span} at this stage of an innings; the "
                         "estimate is an extrapolation.")
MANUAL_INPUT_NOTICE = "Manual input: these are the values you entered, not live match data."
BATTER_SCOPE_NOTE = ("Conditional on the player batting in the match; whether the player is selected in the "
                     "playing XI, or bats at all, is not predicted.")
HOLDOUT_LABEL = "2026 holdout replay — model trained through 2025"
HOLDOUT_STATEMENT = (
    "The 2026 holdout evaluates the holdout models trained on 2008–2025 data "
    "(wicket_holdout_train_through_2025.joblib and batter_holdout_train_through_2025.joblib), never the "
    "deployment models. The deployment models were refit through 2026 after that evaluation was saved, so "
    "they have no out-of-sample evaluation of their own."
)
HOLDOUT_ELIGIBILITY = {
    "wicket": "Every eligible 2026 next-over checkpoint: D/L-marked matches excluded; overs cut short are kept "
              "only when a wicket fell in them.",
    "batter": "Every eligible 2026 batting innings: D/L-marked and no-result matches excluded; form features use "
              "only innings from earlier dates.",
}


class ModelUnavailable(Exception):
    """A deployment artifact or a holdout report is missing or invalid (HTTP 503)."""


class PredictionInputError(Exception):
    """Inputs the Stage 3 function would reject or the model does not know (HTTP 422)."""

    def __init__(self, errors: List[Dict[str, Any]]):
        super().__init__("; ".join(e["msg"] for e in errors))
        self.errors = errors


class UnknownReplayMatch(KeyError):
    """No 2026 holdout forecast exists for this match (HTTP 404)."""


def _error(field: Optional[str], message: str) -> Dict[str, Any]:
    # Same shape as FastAPI's own request-validation errors, so clients read one format
    return {"loc": ["body", field] if field else ["body"], "msg": message, "type": "value_error"}


def as_percent(probability: float) -> float:
    """A probability as a percentage to one decimal, rounding halves up (0.23456 -> 23.5)."""
    return float((Decimal(repr(float(probability))) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _training_span(version: str, training_end: int) -> str:
    """'2008–2026' from the artifact's own version string, checked against its training end."""
    match = re.search(r"(\d{4})_(\d{4})$", version)
    if not match or int(match.group(2)) != training_end:
        raise ValueError(f"version '{version}' does not state a training span ending {training_end}")
    return f"{match.group(1)}–{match.group(2)}"


def _categories(model: Any) -> Dict[str, List[str]]:
    """Category values each one-hot encoder in the saved pipeline was fitted on, keyed by column."""
    found: Dict[str, List[str]] = {}
    for _, transformer, columns in model.named_steps["features"].transformers_:
        encoder = transformer.steps[-1][1] if hasattr(transformer, "steps") else transformer
        if hasattr(encoder, "categories_"):
            for column, values in zip(columns, encoder.categories_):
                found[column] = [str(v) for v in values]
    return found


def _wicket_metrics(values: Dict[str, Any]) -> Dict[str, Any]:
    keys = ("model", "training_rows", "rows", "event_rate", "brier_score", "log_loss", "roc_auc")
    return {k: values[k] for k in keys if k in values}


def _batter_metrics(values: Dict[str, Any]) -> Dict[str, Any]:
    keys = ("model", "training_rows", "rows", "observed_30_rate", "observed_50_rate", "brier_30", "brier_50",
            "avg_milestone_brier", "multiclass_log_loss", "roc_auc_30", "roc_auc_50")
    return {k: values[k] for k in keys if k in values}


def _code(team: str) -> str:
    return FRANCHISE_METADATA.get(str(team), {}).get("short_name", str(team))


def _three_class(p30: np.ndarray, p50: np.ndarray) -> np.ndarray:
    """Class probabilities (<30, 30-49, 50+) back from the saved P(30+) and P(50+)."""
    return np.column_stack([1 - p30, p30 - p50, p50])


class PredictionService:
    def __init__(self, model_dir: Path = MODEL_DIR, data_dir: Path = DATA_DIR, report_dir: Path = REPORT_DIR):
        self.model_dir = Path(model_dir)
        self.data_dir = Path(data_dir)
        self.report_dir = Path(report_dir)
        self._lock = threading.Lock()
        self._loaded = False
        self._status: Dict[str, Dict[str, Any]] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._options: Optional[Dict[str, Any]] = None
        self._history: Dict[str, pd.DataFrame] = {}
        self._ranges: Optional[pd.DataFrame] = None
        self._archive: Optional[Dict[str, Any]] = None
        self._replay: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------ deployment artifacts

    def ensure_loaded(self) -> None:
        """Validate both deployment artifacts once; a failure marks that model unavailable, never a fallback."""
        with self._lock:
            if self._loaded:
                return
            for kind in MODELS:
                try:
                    self._meta[kind] = self._validate_artifact(kind)
                    self._status[kind] = {"available": True, "detail": f"Loaded {MODELS[kind]['deployment']}."}
                except Exception as exc:
                    self._status[kind] = {"available": False,
                                          "detail": f"{MODELS[kind]['deployment']} could not be loaded: {exc}"}
            self._loaded = True

    def _validate_artifact(self, kind: str) -> Dict[str, Any]:
        spec = MODELS[kind]
        path = self.model_dir / spec["deployment"]
        if not path.is_file():
            raise FileNotFoundError(f"{path.name} is not in {self.model_dir}")
        saved = joblib.load(path)
        missing = {"model", "columns", "name", "version", spec["end_key"]} - set(saved)
        if missing:
            raise ValueError(f"missing keys {sorted(missing)}")
        if saved["version"] != DEPLOYMENT_VERSION or saved[spec["end_key"]] != DEPLOYMENT_TRAIN_END:
            raise ValueError(f"expected version {DEPLOYMENT_VERSION} trained through {DEPLOYMENT_TRAIN_END}, found "
                             f"{saved['version']} through {saved[spec['end_key']]}")
        categories = _categories(saved["model"])
        teams = set(categories.get("batting_team", [])) & set(categories.get("bowling_team", []))
        active = [name for name, meta in FRANCHISE_METADATA.items() if meta["status"] == "Active"]
        if unknown := [t for t in active if t not in teams]:
            raise ValueError(f"active franchises unknown to the model: {unknown}")
        return {
            "file": path.name,
            "name": saved["name"],
            "version": saved["version"],
            "training_end": int(saved[spec["end_key"]]),
            "training_span": _training_span(saved["version"], int(saved[spec["end_key"]])),
            "columns": list(saved["columns"]),
            "classes": [int(c) for c in saved["model"].named_steps["model"].classes_],
            "categories": categories,
            "condition": saved.get("condition"),
            "milestones": saved.get("milestones"),
            "horizon": saved.get("horizon"),
            "notice": saved.get("notice"),
        }

    def status(self) -> Dict[str, Dict[str, Any]]:
        self.ensure_loaded()
        return {kind: dict(value) for kind, value in self._status.items()}

    def _require(self, kind: str) -> Dict[str, Any]:
        self.ensure_loaded()
        if not self._status[kind]["available"]:
            raise ModelUnavailable(f"The {MODELS[kind]['title'].lower()} model is unavailable: "
                                   f"{self._status[kind]['detail']} No prediction can be made.")
        return self._meta[kind]

    # ------------------------------------------------------------------ options

    def _allowed(self) -> Dict[str, Any]:
        """Active franchises and venues known to every available model."""
        self.ensure_loaded()
        available = [self._meta[k] for k in MODELS if self._status[k]["available"]]
        active = [name for name, meta in FRANCHISE_METADATA.items() if meta["status"] == "Active"]
        venues: Optional[set] = None
        for meta in available:
            known = set(meta["categories"].get("venue_canonical", []))
            venues = known if venues is None else venues & known
        return {"teams": active, "venues": venues or set()}

    def _batter_history(self) -> Dict[str, pd.DataFrame]:
        """Each player's eligible innings, by the rule forecast_future_batter.forecast() applies."""
        if not self._history:
            bats = pd.read_csv(self.data_dir / "batter_innings.csv")
            matches = pd.read_csv(self.data_dir / "matches.csv")
            hist = bats.merge(matches[["match_id", "outcome_method", "outcome_type"]], on="match_id",
                              validate="many_to_one")
            dls = hist.outcome_method.fillna("").str.strip().str.upper().isin(DLS_METHODS)
            no_result = hist.outcome_type.fillna("").str.lower().str.contains("no result", regex=False)
            hist = hist.loc[~dls & ~no_result].copy()
            hist["batter_id"] = hist.batter_id.astype(str)
            hist = hist.sort_values(["date", "match_id", "innings"])
            self._history = {pid: rows for pid, rows in hist.groupby("batter_id", sort=False)}
        return self._history

    def _archive_extent(self) -> Dict[str, Any]:
        """Latest season and last match date of the archive, counted from matches.csv."""
        if self._archive is None:
            matches = pd.read_csv(self.data_dir / "matches.csv", usecols=["season", "date"])
            self._archive = {"latest_season": int(matches.season.max()), "last_match_date": str(matches.date.max())}
        return self._archive

    def _wicket_ranges(self) -> Optional[pd.DataFrame]:
        """Observed min and max of runs, run rate and last-over runs per completed-overs checkpoint."""
        if self._ranges is None:
            path = self.data_dir / WICKET_TRAINING_ROWS
            if not path.is_file():
                return None
            rows = pd.read_csv(path, usecols=["completed_overs", *RANGE_FIELDS])
            self._ranges = rows.groupby("completed_overs").agg(
                **{f"{f}_{stat}": (f, stat) for f in RANGE_FIELDS for stat in ("min", "max")})
        return self._ranges

    def input_range_check(self, inputs: Dict[str, Any], span: str) -> Dict[str, Any]:
        """Which inputs fall outside the training rows at this checkpoint; never changes the probability."""
        ranges = self._wicket_ranges()
        overs = inputs["completed_overs"]
        if ranges is None or overs not in ranges.index:
            return {"checked": False, "completed_overs": overs, "outside": [], "warning": None,
                    "source": f"data/processed/{WICKET_TRAINING_ROWS} (not available)"}
        row = ranges.loc[overs]
        values = {"runs": inputs["runs"], "run_rate": inputs["runs"] / overs, "last_over_runs": inputs["last_over_runs"]}
        outside = [
            {"field": f, "label": label, "value": round(float(values[f]), 2),
             "observed_min": round(float(row[f"{f}_min"]), 2), "observed_max": round(float(row[f"{f}_max"]), 2)}
            for f, label in RANGE_FIELDS.items()
            if not row[f"{f}_min"] - RANGE_TOLERANCE <= values[f] <= row[f"{f}_max"] + RANGE_TOLERANCE
        ]
        return {
            "checked": True,
            "completed_overs": overs,
            "outside": outside,
            "warning": EXTRAPOLATION_WARNING.format(span=span) if outside else None,
            "source": f"data/processed/{WICKET_TRAINING_ROWS} (the deployment model's eligible training rows)",
        }

    def options(self) -> Dict[str, Any]:
        self.ensure_loaded()
        if not any(s["available"] for s in self._status.values()):
            raise ModelUnavailable("Neither deployment model could be loaded: "
                                   + " ".join(s["detail"] for s in self._status.values()))
        if self._options is None:
            allowed = self._allowed()
            matches = pd.read_csv(self.data_dir / "matches.csv")
            latest_season = self._archive_extent()["latest_season"]
            per_venue = matches.groupby("venue_canonical").agg(matches=("match_id", "size"), last=("season", "max"))
            venues = [
                {"name": name, "matches": int(per_venue.loc[name, "matches"]) if name in per_venue.index else 0,
                 "last_season": int(per_venue.loc[name, "last"]) if name in per_venue.index else None,
                 "used_in_latest_season": bool(name in per_venue.index and per_venue.loc[name, "last"] == latest_season)}
                for name in sorted(allowed["venues"])
            ]
            teams = [{"name": n, "code": FRANCHISE_METADATA[n]["short_name"], "slug": FRANCHISE_METADATA[n]["slug"],
                      "primary_color": FRANCHISE_METADATA[n]["primary_color"]} for n in allowed["teams"]]
            self._options = {
                "teams": teams,
                "venues": venues,
                "latest_season": latest_season,
                "archive_last_match_date": self._archive_extent()["last_match_date"],
                "wicket_rules": WICKET_RULES,
                "batters": self._batter_options(),
                "batter_date_rule": f"The match date must be after the last match in the archive "
                                    f"({self._archive_extent()['last_match_date']}) and after the player's latest "
                                    "eligible innings (D/L-marked and no-result matches are not eligible).",
                "models_available": {k: s["available"] for k, s in self._status.items()},
            }
        return self._options

    def _batter_options(self) -> List[Dict[str, Any]]:
        latest_season = self._archive_extent()["latest_season"]
        try:
            directory = canonical_engine.list_players(page_size=100_000)["players"]
            # Last season in any match squad (playing XI or substitute), from the player directory
            names = {p["player_id"]: (p["name"], p["name_variants"], p["last_season"]) for p in directory}
        except DerivedDataUnavailable:
            names = {}
        items = []
        for pid, rows in self._batter_history().items():
            last = rows.iloc[-1]
            # Without the directory, fall back to the last season of a recorded batting innings
            name, variants, last_season = names.get(pid, (str(last.batter), [], int(last.season)))
            items.append({
                "player_id": pid,
                "name": name,
                "name_variants": list(variants),
                "eligible_innings": int(len(rows)),
                "latest_innings_date": str(last.date),
                "latest_team": str(last.batting_team),
                "last_season": int(last_season),
                "appeared_in_latest_season": int(last_season) == latest_season,
            })
        return sorted(items, key=lambda p: (-p["eligible_innings"], p["name"]))

    # ------------------------------------------------------------------ predictions

    def validate_wicket(self, inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        allowed = self._allowed()
        errors = []
        if inputs["innings"] not in (1, 2):
            errors.append(_error("innings", "Innings must be 1 or 2."))
        if not 1 <= inputs["completed_overs"] <= 19:
            errors.append(_error("completed_overs", "Completed overs must be from 1 to 19: the prediction is for "
                                                    "the next over, so at least one over must be complete and one "
                                                    "must remain."))
        if not 0 <= inputs["wickets"] <= 9:
            errors.append(_error("wickets", "Wickets must be from 0 to 9 (10 wickets ends the innings)."))
        if inputs["runs"] < 0:
            errors.append(_error("runs", "Runs cannot be negative."))
        runs_limit = MAX_RUNS_PER_OVER * inputs["completed_overs"] + RUNS_EXTRAS_ALLOWANCE
        if 1 <= inputs["completed_overs"] <= 19 and inputs["runs"] > runs_limit:
            errors.append(_error("runs", f"{inputs['runs']} runs after {inputs['completed_overs']} overs is not possible: "
                                         f"the limit is {MAX_RUNS_PER_OVER} per over plus {RUNS_EXTRAS_ALLOWANCE} for "
                                         f"extras ({runs_limit})."))
        if not 0 <= inputs["last_over_runs"] <= max(inputs["runs"], 0):
            errors.append(_error("last_over_runs", "Runs in the last over must be from 0 to the current runs."))
        elif inputs["last_over_runs"] > MAX_RUNS_PER_OVER + LAST_OVER_EXTRAS_ALLOWANCE:
            errors.append(_error("last_over_runs", f"{inputs['last_over_runs']} runs in one over is not possible: the "
                                                   f"limit is {MAX_RUNS_PER_OVER} plus {LAST_OVER_EXTRAS_ALLOWANCE} for "
                                                   f"extras ({MAX_RUNS_PER_OVER + LAST_OVER_EXTRAS_ALLOWANCE})."))
        if not 0 <= inputs["last_over_wickets"] <= max(inputs["wickets"], 0):
            errors.append(_error("last_over_wickets", "Wickets in the last over must be from 0 to the current "
                                                      "wickets."))
        errors += self._validate_context(inputs["batting_team"], inputs["bowling_team"], inputs["venue"],
                                         ("batting_team", "bowling_team"), allowed)
        return errors

    def _validate_context(self, team: str, opponent: str, venue: str, fields: tuple, allowed: Dict[str, Any]):
        errors = []
        for field, value in zip(fields, (team, opponent)):
            if value not in allowed["teams"]:
                errors.append(_error(field, f"'{value}' is not one of the active franchises the model accepts."))
        if team and team == opponent:
            errors.append(_error(fields[1], "The two teams must be different."))
        if venue not in allowed["venues"]:
            errors.append(_error("venue", f"'{venue}' is not a venue the model was trained on."))
        return errors

    def predict_wicket(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        meta = self._require("wicket")
        if errors := self.validate_wicket(inputs):
            raise PredictionInputError(errors)
        try:
            result = predict_wicket.forecast(self.model_dir / MODELS["wicket"]["deployment"], **inputs)
        except ValueError as exc:
            raise PredictionInputError([_error(None, str(exc))])
        except Exception as exc:
            raise ModelUnavailable(f"The wicket model could not be run: {exc}")
        return {
            **result,
            "probability_pct": as_percent(result["probability"]),
            "phase": phase_for_next_over(inputs["completed_overs"]),
            "inputs": dict(inputs),
            "model_file": meta["file"],
            "version": meta["version"],
            "training_span": meta["training_span"],
            "notice": MANUAL_INPUT_NOTICE,
            "function_notice": result["notice"],
            # Reported alongside the model's probability, which it never alters
            "input_range": self.input_range_check(inputs, meta["training_span"]),
        }

    def validate_batter(self, inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        errors = self._validate_context(inputs["batting_team"], inputs["opponent"], inputs["venue"],
                                        ("batting_team", "opponent"), self._allowed())
        history = self._batter_history().get(str(inputs["player_id"]).strip())
        if history is None:
            errors.append(_error("player_id", f"Unknown player ID '{inputs['player_id']}': no eligible batting "
                                              "innings are recorded for it."))
        try:
            when = date.fromisoformat(str(inputs["match_date"]))
        except ValueError:
            errors.append(_error("match_date", "Match date must be a valid date in YYYY-MM-DD form."))
            return errors
        archive_end = date.fromisoformat(self._archive_extent()["last_match_date"])
        if when <= archive_end:
            errors.append(_error("match_date", f"Match date must be after the last match in the data "
                                               f"({archive_end.isoformat()}): forecasts are for future matches."))
        elif history is not None:
            latest = date.fromisoformat(str(history.date.iloc[-1]))
            if when <= latest:
                errors.append(_error("match_date", f"Match date must be after this player's latest eligible innings "
                                                   f"on {latest.isoformat()}."))
        return errors

    def predict_batter(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        meta = self._require("batter")
        if errors := self.validate_batter(inputs):
            raise PredictionInputError(errors)
        pid = str(inputs["player_id"]).strip()
        try:
            result = forecast_future_batter.forecast(
                model_path=self.model_dir / MODELS["batter"]["deployment"],
                batters_path=self.data_dir / "batter_innings.csv",
                matches_path=self.data_dir / "matches.csv",
                batter_id=pid, opponent=inputs["opponent"], venue=inputs["venue"],
                batting_team=inputs["batting_team"], match_date=inputs["match_date"])
        except ValueError as exc:
            raise PredictionInputError([_error(None, str(exc))])
        except Exception as exc:
            raise ModelUnavailable(f"The batter model could not be run: {exc}")
        if not result["chance_50_plus"] <= result["chance_30_plus"]:
            raise RuntimeError("Milestone probabilities out of order: P(50+) exceeds P(30+)")
        history = self._batter_history()[pid]
        recent = history.iloc[::-1].head(RECENT_INNINGS_SHOWN)
        option = next((b for b in self.options()["batters"] if b["player_id"] == pid), None)
        name = option["name"] if option else result["player_name"]
        active = bool(option and option["appeared_in_latest_season"])
        return {
            **result,
            "player_name": name,
            "source_name": result["player_name"],
            "chance_30_plus_pct": as_percent(result["chance_30_plus"]),
            "chance_50_plus_pct": as_percent(result["chance_50_plus"]),
            "model": meta["name"],
            "model_file": meta["file"],
            "training_span": meta["training_span"],
            "scope": BATTER_SCOPE_NOTE,
            "appeared_in_latest_season": active,
            "return_note": None if active else (
                f"This player has no {self._archive_extent()['latest_season']} appearance; the forecast assumes "
                "they play again."),
            "function_scope": result["scope"],
            "notice": MANUAL_INPUT_NOTICE,
            "form_context": {
                "prior_eligible_innings": result["prior_eligible_innings"],
                "latest_innings_date": str(history.date.iloc[-1]),
                "recent_innings": [
                    {"date": str(r.date), "runs": int(r.runs), "batting_team": str(r.batting_team),
                     "opponent": str(r.bowling_team), "venue": str(r.venue_canonical)}
                    for r in recent.itertuples(index=False)
                ],
                "definition": "Eligible innings exclude D/L-marked and no-result matches, as in the model's "
                              "training data; all of them are before the match date.",
            },
        }

    # ------------------------------------------------------------------ evaluation report and holdout replay

    def _report(self) -> Dict[str, Any]:
        path = self.report_dir / RESULTS_JSON
        if not path.is_file():
            raise ModelUnavailable(f"The Stage 3 evaluation report {RESULTS_JSON} is not in {self.report_dir}.")
        return json.loads(path.read_text(encoding="utf-8"))

    def models(self) -> Dict[str, Any]:
        self.ensure_loaded()
        report = self._report()
        items = []
        for kind, spec in MODELS.items():
            section = report[kind]
            convert = _wicket_metrics if kind == "wicket" else _batter_metrics
            meta = self._meta.get(kind, {})
            items.append({
                "kind": kind,
                "title": spec["title"],
                "available": self._status[kind]["available"],
                "status_detail": self._status[kind]["detail"],
                "deployment_file": spec["deployment"],
                "holdout_file": spec["holdout"],
                "name": meta.get("name"),
                "version": meta.get("version"),
                "training_end": meta.get("training_end"),
                "training_span": meta.get("training_span"),
                "features": meta.get("columns", []),
                "classes": meta.get("classes", []),
                "condition": meta.get("condition"),
                "selected_name": section["selected_name_from_2025_only"],
                "selection_metric": section["selection_metric"],
                "validation_2025": [convert(c) for c in section["candidate_validation_2025"]],
                "validation_2025_constant": convert(section["constant_validation_2025"]),
                "holdout_2026": convert(section["holdout_2026"]),
                "holdout_2026_constant": convert(section["holdout_constant"]),
                "rows": {
                    "train_2008_2024": section["train_2008_2024"],
                    "validate_2025": section["validate_2025"],
                    "refit_2008_2025_for_holdout": section["refit_2008_2025_for_holdout"],
                    "test_2026_rows": section["test_2026_rows"],
                    "test_2026_matches": section["test_2026_matches"],
                    "final_refit_2008_2026": section["final_refit_2008_2026"],
                },
                "exclusions": section.get("exclusions"),
                "notes": [v for v in (section.get("limitation"), section.get("assumption")) if v],
            })
        return {
            "models": items,
            "holdout_statement": HOLDOUT_STATEMENT,
            "caveats": report.get("important_caveats", []),
            "source": f"reports/stage_03/session_03/{RESULTS_JSON}",
            "report_created_utc": report.get("created_utc"),
        }

    def _load_replay(self) -> Dict[str, Any]:
        if self._replay is None:
            paths = [self.report_dir / p for p in (WICKET_HOLDOUT_CSV, BATTER_HOLDOUT_CSV)]
            if missing := [p.name for p in paths if not p.is_file()]:
                raise ModelUnavailable(f"The 2026 holdout forecasts are missing: {missing}.")
            # round_trip: probabilities are read back exactly as the Stage 3 run wrote them
            wicket = pd.read_csv(paths[0], float_precision="round_trip")
            batter = pd.read_csv(paths[1], dtype={"batter_id": str}, float_precision="round_trip")
            innings = pd.read_csv(self.data_dir / "innings.csv", usecols=["match_id", "innings", "batting_team"])
            matches = pd.read_csv(self.data_dir / "matches.csv",
                                  usecols=["match_id", "date", "team1", "team2", "venue_canonical", "final_winner"])
            self._replay = {
                "wicket": wicket.merge(innings, on=["match_id", "innings"], how="left", validate="many_to_one"),
                "batter": batter.merge(innings, on=["match_id", "innings"], how="left", validate="many_to_one"),
                "matches": matches.set_index("match_id"),
            }
        return self._replay

    def _wicket_summary(self, rows: pd.DataFrame) -> Dict[str, Any]:
        y, p = rows.wicket_next_over.to_numpy(int), rows.predicted_wicket_probability.to_numpy(float)
        bins = wicket_reliability(y, p, bins=WICKET_CALIBRATION_BINS)
        return {
            **_wicket_metrics(wicket_measure(y, p)),
            "calibration": [
                {"bin": int(b.bin), "lower": int(b.bin) / WICKET_CALIBRATION_BINS,
                 "upper": (int(b.bin) + 1) / WICKET_CALIBRATION_BINS, "n": int(b.n),
                 "avg_predicted": float(b.avg_predicted), "observed_rate": float(b.observed_frequency)}
                for b in bins.itertuples(index=False)
            ],
        }

    def _batter_summary(self, rows: pd.DataFrame) -> Dict[str, Any]:
        p30, p50 = rows.probability_30_plus.to_numpy(float), rows.probability_50_plus.to_numpy(float)
        y = rows.milestone_class.to_numpy(int)
        calibration = []
        for label, events, probs in (("30+", y >= 1, p30), ("50+", y == 2, p50)):
            for b in calibration_table(events, probs, label, bins=BATTER_CALIBRATION_BINS).itertuples(index=False):
                calibration.append({"milestone": label, "bin": int(b.bin), "lower": int(b.bin) / BATTER_CALIBRATION_BINS,
                                    "upper": (int(b.bin) + 1) / BATTER_CALIBRATION_BINS, "n": int(b.n),
                                    "avg_predicted": float(b.predicted), "observed_rate": float(b.actual_rate)})
        return {**_batter_metrics(batter_metrics(y, _three_class(p30, p50))), "calibration": calibration}

    @staticmethod
    def _check(computed: Dict[str, Any], official: Dict[str, Any]) -> Dict[str, Any]:
        keys = [k for k in official if k in computed and isinstance(official[k], (int, float))]
        mismatched = [k for k in keys if abs(float(computed[k]) - float(official[k])) > METRIC_TOLERANCE]
        return {"matches_official": not mismatched, "compared": keys, "mismatched": mismatched,
                "tolerance": METRIC_TOLERANCE}

    def replay_index(self) -> Dict[str, Any]:
        replay, report = self._load_replay(), self._report()
        wicket, batter, matches = replay["wicket"], replay["batter"], replay["matches"]
        ids = sorted(set(wicket.match_id) | set(batter.match_id), key=lambda m: (str(matches.loc[m, "date"]), m))
        w_counts, b_counts = wicket.groupby("match_id").size(), batter.groupby("match_id").size()
        items = [{
            "match_id": int(m), "date": str(matches.loc[m, "date"]), "team1": str(matches.loc[m, "team1"]),
            "team2": str(matches.loc[m, "team2"]), "team1_code": _code(matches.loc[m, "team1"]),
            "team2_code": _code(matches.loc[m, "team2"]), "venue": str(matches.loc[m, "venue_canonical"]),
            "winner": None if pd.isna(matches.loc[m, "final_winner"]) else str(matches.loc[m, "final_winner"]),
            "wicket_checkpoints": int(w_counts.get(m, 0)), "batter_forecasts": int(b_counts.get(m, 0)),
        } for m in ids]
        wicket_summary, batter_summary = self._wicket_summary(wicket), self._batter_summary(batter)
        official_w = _wicket_metrics(report["wicket"]["holdout_2026"])
        official_b = _batter_metrics(report["batter"]["holdout_2026"])
        return {
            "label": HOLDOUT_LABEL,
            "statement": HOLDOUT_STATEMENT,
            "matches": items,
            "wicket": {
                "computed": wicket_summary, "official": official_w,
                "official_constant": _wicket_metrics(report["wicket"]["holdout_constant"]),
                "check": self._check(wicket_summary, official_w), "matches_count": int(wicket.match_id.nunique()),
                "eligibility": HOLDOUT_ELIGIBILITY["wicket"],
            },
            "batter": {
                "computed": batter_summary, "official": official_b,
                "official_constant": _batter_metrics(report["batter"]["holdout_constant"]),
                "check": self._check(batter_summary, official_b), "matches_count": int(batter.match_id.nunique()),
                "eligibility": HOLDOUT_ELIGIBILITY["batter"],
            },
            "sources": [f"reports/stage_03/session_03/{p.as_posix()}" for p in
                        (WICKET_HOLDOUT_CSV, BATTER_HOLDOUT_CSV, WICKET_CALIBRATION_CSV, BATTER_CALIBRATION_CSV)]
                       + [f"reports/stage_03/session_03/{RESULTS_JSON}"],
        }

    def replay_match(self, match_id: int) -> Dict[str, Any]:
        replay = self._load_replay()
        wicket = replay["wicket"][replay["wicket"].match_id == match_id].sort_values(["innings", "completed_overs"])
        batter = replay["batter"][replay["batter"].match_id == match_id]
        if wicket.empty and batter.empty:
            raise UnknownReplayMatch(f"Match {match_id} has no 2026 holdout forecasts.")
        info = replay["matches"].loc[match_id]
        return {
            "label": HOLDOUT_LABEL,
            "match_id": int(match_id),
            "date": str(info.date),
            "team1": str(info.team1),
            "team2": str(info.team2),
            "venue": str(info.venue_canonical),
            "winner": None if pd.isna(info.final_winner) else str(info.final_winner),
            "batters": [{
                "innings": int(r.innings), "batting_team": str(r.batting_team), "batter_id": str(r.batter_id),
                "batter": str(r.batter), "prior_innings": int(r.prior_innings),
                "probability_30_plus": float(r.probability_30_plus), "probability_50_plus": float(r.probability_50_plus),
                "actual_runs": int(r.actual_runs), "actual_30_plus": bool(r.actual_30_plus),
                "actual_50_plus": bool(r.actual_50_plus),
            } for r in batter.itertuples(index=False)],
            "wickets": [{
                "innings": int(r.innings), "batting_team": str(r.batting_team), "completed_overs": int(r.completed_overs),
                "next_over": int(r.completed_overs) + 1, "phase": str(r.phase),
                "predicted_probability": float(r.predicted_wicket_probability),
                "wicket_fell": bool(r.wicket_next_over),
            } for r in wicket.itertuples(index=False)],
            "wicket_summary": _wicket_metrics(wicket_measure(wicket.wicket_next_over.to_numpy(int),
                                                            wicket.predicted_wicket_probability.to_numpy(float)))
            if not wicket.empty else None,
            "batter_summary": _batter_metrics(batter_metrics(
                batter.milestone_class.to_numpy(int),
                _three_class(batter.probability_30_plus.to_numpy(float), batter.probability_50_plus.to_numpy(float))))
            if not batter.empty else None,
        }


prediction_service = PredictionService()
