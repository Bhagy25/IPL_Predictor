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

# Configure CORS for local Vite development and staging
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    except Exception as exc:
        derived = {"available": False, "detail": f"Analytics data failed to load: {exc}"}
    models = prediction_service.prediction_service.status()
    healthy = derived["available"] and all(m["available"] for m in models.values())
    return HealthCheckResponse(
        status="healthy" if healthy else "degraded",
        derived_tables=derived,
        prediction_models=models,
        version=__version__,
        archive_matches=1243,
        timestamp=datetime.now(timezone.utc).isoformat(),
        service="CricketLens Analytical Backend",
    )


# Mount feature routers
app.include_router(overview_router)
app.include_router(teams_router)
app.include_router(players_router)
app.include_router(eda_router)
app.include_router(predict_router)
