"""Prediction Arena and Prediction Tracker API endpoints for CricketLens.

Predictions come from the Stage 3 inference functions with the deployment models; nothing about a
request is logged or stored on the server.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from cricketlens.api.schemas import (
    BatterPredictionRequest,
    BatterPredictionResponse,
    HoldoutReplayMatchResponse,
    HoldoutReplayResponse,
    PredictionModelsResponse,
    PredictionOptionsResponse,
    WicketPredictionRequest,
    WicketPredictionResponse,
)
from cricketlens.api.services import prediction_service as service

router = APIRouter(prefix="/api/predict", tags=["Predictions"])
logger = logging.getLogger(__name__)


def _call(action, *args):
    """Run a service call, turning its errors into 422 / 404 / 503 responses (the service is looked up per call)."""
    try:
        return action(service.prediction_service)(*args)
    except service.PredictionInputError as exc:
        raise HTTPException(status_code=422, detail=exc.errors)
    except service.UnknownReplayMatch as exc:
        raise HTTPException(status_code=404, detail=exc.args[0])
    except service.ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


def _predict(action, request):
    """_call for a prediction: any other failure is logged with its traceback and returned as a generic 500."""
    try:
        return _call(action, request.model_dump())
    except HTTPException:
        raise
    except Exception:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=service.PREDICTION_FAILED)


@router.get(
    "/options",
    response_model=PredictionOptionsResponse,
    summary="Inputs the deployment models accept",
    description="The 10 active franchises and the venues known to the models (canonical names, exactly as trained), "
                "the wicket input rules, and every player with eligible batting history with name variants and the "
                "date a batter forecast must follow.",
)
def get_options() -> PredictionOptionsResponse:
    return _call(lambda s: s.options)


@router.post(
    "/wicket",
    response_model=WicketPredictionResponse,
    summary="Chance of at least one wicket in the next over",
    description="Calls predict_wicket.forecast() with the deployment model trained through 2026. Inputs are checked "
                "with the function's own rules plus team and venue membership (422 lists every problem). "
                "Manual input, not live data.",
)
def post_wicket(request: WicketPredictionRequest) -> WicketPredictionResponse:
    return _predict(lambda s: s.predict_wicket, request)


@router.post(
    "/batter",
    response_model=BatterPredictionResponse,
    summary="Chance of a batter scoring 30+ and 50+",
    description="Calls forecast_future_batter.forecast() with the deployment model trained through 2026. "
                "Conditional on the player batting; the playing XI is not predicted. The match date must be after "
                "the player's latest eligible innings (422 otherwise).",
)
def post_batter(request: BatterPredictionRequest) -> BatterPredictionResponse:
    return _predict(lambda s: s.predict_batter, request)


@router.get(
    "/models",
    response_model=PredictionModelsResponse,
    summary="Model metadata and the official Stage 3 evaluation",
    description="Deployment model metadata with the 2025 validation and 2026 holdout numbers read from "
                "stage03_session03_final_results.json. The 2026 holdout scores the holdout model trained through "
                "2025, not the deployment model.",
)
def get_models() -> PredictionModelsResponse:
    return _call(lambda s: s.models)


@router.get(
    "/holdout-replay",
    response_model=HoldoutReplayResponse,
    summary="2026 holdout replay: matches and season summary",
    description="Matches in the saved 2026 holdout forecasts (holdout model trained through 2025) with Brier, log "
                "loss, ROC AUC and calibration bins recomputed from the CSVs and compared with the official report.",
)
def get_holdout_replay() -> HoldoutReplayResponse:
    return _call(lambda s: s.replay_index)


@router.get(
    "/holdout-replay/{match_id}",
    response_model=HoldoutReplayMatchResponse,
    summary="2026 holdout replay for one match",
    description="Each eligible batter's 30+/50+ forecast against actual runs, and each next-over wicket forecast "
                "against what happened, from the saved holdout forecasts.",
)
def get_holdout_replay_match(match_id: int) -> HoldoutReplayMatchResponse:
    return _call(lambda s: s.replay_match, match_id)
