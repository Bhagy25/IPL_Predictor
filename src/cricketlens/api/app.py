"""FastAPI Application entry point for CricketLens."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cricketlens.api import __version__
from cricketlens.api.schemas import HealthCheckResponse
from cricketlens.api.routes_overview import router as overview_router
from cricketlens.api.routes_teams import router as teams_router
from cricketlens.api.routes_players import router as players_router
from cricketlens.api.routes_eda import router as eda_router

app = FastAPI(
    title="CricketLens Analytical API",
    description="Statistical EDA and ML predictive analytics backend for men's Indian Premier League cricket.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
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
    return HealthCheckResponse(
        status="healthy",
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
