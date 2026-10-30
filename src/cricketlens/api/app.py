"""FastAPI Application entry point for CricketLens."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cricketlens.api import __version__
from cricketlens.api.schemas import HealthCheckResponse
from cricketlens.api.routes_overview import router as overview_router
from cricketlens.api.routes_teams import router as teams_router
from cricketlens.api.routes_players import router as players_router
from cricketlens.api.routes_eda import router as eda_router
from cricketlens.api.routes_predict import router as predict_router
from cricketlens.api.services.canonical_data import canonical_engine
from cricketlens.api.services import prediction_service
from cricketlens.api.settings import cors_allow_origins


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Validate the deployment model artifacts once; a failure is reported by /api/health and returns 503
    prediction_service.prediction_service.ensure_loaded()
    yield


app = FastAPI(
    title="CricketLens Analytical API",
    description="Statistical EDA and ML predictive analytics backend for men's Indian Premier League cricket.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Cross-origin access for the local Vite dev server, or the origins in CORS_ALLOW_ORIGINS for a split
# deployment; the same-origin production site needs none. The API uses no cookies or credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Content-Type"],
)


@app.get(
    "/api/health",
    response_model=HealthCheckResponse,
    tags=["System"],
    summary="Health check and archive verification status",
)
async def health_check() -> HealthCheckResponse:
    try:
        derived = canonical_engine.derived_status()
        coverage = canonical_engine.archive_coverage()
    except Exception as exc:
        derived = {"available": False, "detail": f"Analytics data failed to load: {exc}"}
        coverage = None
    models = prediction_service.prediction_service.status()
    healthy = coverage is not None and derived["available"] and all(m["available"] for m in models.values())
    return HealthCheckResponse(
        status="healthy" if healthy else "degraded",
        derived_tables=derived,
        prediction_models=models,
        version=__version__,
        # Counted from the loaded match data; null when the data could not be loaded
        archive_matches=coverage["matches"] if coverage else None,
        archive=coverage,
        timestamp=datetime.now(timezone.utc).isoformat(),
        service="CricketLens Analytical Backend",
    )


# Mount feature routers
app.include_router(overview_router)
app.include_router(teams_router)
app.include_router(players_router)
app.include_router(eda_router)
app.include_router(predict_router)
