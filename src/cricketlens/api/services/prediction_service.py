"""Predictions from the Stage 3 deployment models.

Every probability comes from the Stage 3 inference functions, predict_wicket.forecast() and
forecast_future_batter.forecast(), called with the saved deployment artifacts. Nothing here builds
model features, refits or re-saves a model. User inputs are neither logged nor stored.
"""
from __future__ import annotations

import re
import threading
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd

from cricketlens import forecast_future_batter, predict_wicket
from cricketlens.wicket_training_data import phase_for_next_over
from cricketlens.api.services.canonical_data import FRANCHISE_METADATA, DerivedDataUnavailable, canonical_engine

ROOT = Path(__file__).resolve().parents[4]
MODEL_DIR = ROOT / "models"
DATA_DIR = ROOT / "data" / "processed"

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
# The same eligibility rule forecast_future_batter.forecast() applies to a player's history
DLS_METHODS = {"D/L", "DLS", "D/L METHOD", "DLS METHOD"}
RECENT_INNINGS_SHOWN = 5

# Input rules mirrored from predict_wicket.forecast(); the API adds team and venue membership
# because the models' encoders silently ignore an unknown category (handle_unknown="ignore").
WICKET_RULES = {
    "innings": [1, 2],
    "completed_overs": {"min": 1, "max": 19},
    "wickets": {"min": 0, "max": 9},
    "runs": {"min": 0},
    "last_over_runs": "0 to the current runs",
    "last_over_wickets": "0 to the current wickets",
}
MANUAL_INPUT_NOTICE = "Manual input: these are the values you entered, not live match data."
BATTER_SCOPE_NOTE = ("Conditional on the player batting in the match; whether the player is selected in the "
                     "playing XI, or bats at all, is not predicted.")


class ModelUnavailable(Exception):
    """A deployment artifact is missing or invalid (HTTP 503)."""


class PredictionInputError(Exception):
    """Inputs the Stage 3 function would reject or the model does not know (HTTP 422)."""

    def __init__(self, errors: List[Dict[str, Any]]):
        super().__init__("; ".join(e["msg"] for e in errors))
        self.errors = errors


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


class PredictionService:
    def __init__(self, model_dir: Path = MODEL_DIR, data_dir: Path = DATA_DIR):
        self.model_dir = Path(model_dir)
        self.data_dir = Path(data_dir)
        self._lock = threading.Lock()
        self._loaded = False
        self._status: Dict[str, Dict[str, Any]] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._options: Optional[Dict[str, Any]] = None
        self._history: Dict[str, pd.DataFrame] = {}

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

    def options(self) -> Dict[str, Any]:
        self.ensure_loaded()
        if not any(s["available"] for s in self._status.values()):
            raise ModelUnavailable("Neither deployment model could be loaded: "
                                   + " ".join(s["detail"] for s in self._status.values()))
        if self._options is None:
            allowed = self._allowed()
            matches = pd.read_csv(self.data_dir / "matches.csv")
            latest_season = int(matches.season.max())
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
                "archive_last_match_date": str(matches.date.max()),
                "wicket_rules": WICKET_RULES,
                "batters": self._batter_options(),
                "batter_date_rule": "The match date must be after the player's latest eligible innings "
                                    "(D/L-marked and no-result matches are not eligible).",
                "models_available": {k: s["available"] for k, s in self._status.items()},
            }
        return self._options

    def _batter_options(self) -> List[Dict[str, Any]]:
        try:
            directory = canonical_engine.list_players(page_size=100_000)["players"]
            names = {p["player_id"]: (p["name"], p["name_variants"]) for p in directory}
        except DerivedDataUnavailable:
            names = {}
        items = []
        for pid, rows in self._batter_history().items():
            last = rows.iloc[-1]
            name, variants = names.get(pid, (str(last.batter), []))
            items.append({
                "player_id": pid,
                "name": name,
                "name_variants": list(variants),
                "eligible_innings": int(len(rows)),
                "latest_innings_date": str(last.date),
                "latest_team": str(last.batting_team),
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
        if not 0 <= inputs["last_over_runs"] <= max(inputs["runs"], 0):
            errors.append(_error("last_over_runs", "Runs in the last over must be from 0 to the current runs."))
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
        if history is not None:
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
        name = next((b["name"] for b in self.options()["batters"] if b["player_id"] == pid), result["player_name"])
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


prediction_service = PredictionService()
