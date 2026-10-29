"""Prediction Arena and Prediction Tracker API endpoints for CricketLens.

Predictions come from the Stage 3 inference functions with the deployment models; nothing about a
request is logged or stored on the server.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from cricketlens.api.schemas import (
    BatterPredictionRequest,
    BatterPredictionResponse,
    PredictionOptionsResponse,
    WicketPredictionRequest,
    WicketPredictionResponse,
)
from cricketlens.api.services import prediction_service as service

router = APIRouter(prefix="/api/predict", tags=["Predictions"])


def _call(action, *args):
    """Run a service call, turning its errors into 422 / 503 responses (the service is looked up per call)."""
    try:
        return action(service.prediction_service)(*args)
    except service.PredictionInputError as exc:
        raise HTTPException(status_code=422, detail=exc.errors)
    except service.ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


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
    return _call(lambda s: s.predict_wicket, request.model_dump())


@router.post(
    "/batter",
    response_model=BatterPredictionResponse,
    summary="Chance of a batter scoring 30+ and 50+",
    description="Calls forecast_future_batter.forecast() with the deployment model trained through 2026. "
                "Conditional on the player batting; the playing XI is not predicted. The match date must be after "
                "the player's latest eligible innings (422 otherwise).",
)
def post_batter(request: BatterPredictionRequest) -> BatterPredictionResponse:
    return _call(lambda s: s.predict_batter, request.model_dump())

