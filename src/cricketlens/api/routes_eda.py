"""Statistics and EDA Lab API endpoints for CricketLens."""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from cricketlens.api.schemas import (
    EDAAnalysisResponse,
    EDACatalogResponse,
    EDAFilterOptionsResponse,
    EDAPlayerComparisonResponse,
    EDASummaryResponse,
)
from cricketlens.api.services.eda_service import eda_service
from cricketlens.api.services import eda_analysis
from cricketlens.api.services.canonical_data import canonical_engine, DerivedDataUnavailable
from cricketlens.api.settings import PROJECT_ROOT

router = APIRouter(prefix="/api/eda", tags=["Statistics & EDA"])

SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+\.png$")

SEASON_FROM = Query(None, description="First season (default: first season in the archive)")
SEASON_TO = Query(None, description="Last season (default: last season in the archive)")
TEAM = Query(None, description="Franchise id, name or short code (optional)")
VENUE = Query(None, description="Canonical venue name (optional)")


@router.get(
    "/filters",
    response_model=EDAFilterOptionsResponse,
    summary="Filter options for the full-history analysis",
    description="Available seasons, franchises and canonical venues, and which filters each area supports.",
)
async def get_eda_filters() -> EDAFilterOptionsResponse:
    try:
        return EDAFilterOptionsResponse(**eda_analysis.filter_options(canonical_engine))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load EDA filter options: {exc}")


@router.get(
    "/analysis",
    response_model=EDAAnalysisResponse,
    summary="Filterable full-history EDA across the analysis areas",
    description="Every area is recomputed for the season range, team and venue, with coverage, sample size, "
                "definitions, units and source. Invalid parameters return 422.",
)
async def get_eda_analysis(
    season_from: Optional[int] = SEASON_FROM,
    season_to: Optional[int] = SEASON_TO,
    team: Optional[str] = TEAM,
    venue: Optional[str] = VENUE,
    venue_min_matches: int = Query(1, ge=1, le=200, description="Venue analysis: minimum matches at a venue"),
    bat_min_balls: int = Query(1, ge=1, le=120, description="Strike-rate distribution: minimum balls faced"),
    bowl_min_balls: int = Query(1, ge=1, le=24, description="Economy distribution: minimum legal balls bowled"),
) -> EDAAnalysisResponse:
    try:
        filters = eda_analysis.resolve_filters(
            canonical_engine, season_from, season_to, team, venue, venue_min_matches, bat_min_balls, bowl_min_balls,
        )
        return EDAAnalysisResponse(**eda_analysis.get_analysis(canonical_engine, filters))
    except eda_analysis.FilterError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except DerivedDataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get(
    "/player-comparison",
    response_model=EDAPlayerComparisonResponse,
    summary="Compare 2–4 players within a season range",
    description="Batting and bowling for 2–4 registry IDs (comma-separated), using the Player Explorer definitions.",
)
async def get_eda_player_comparison(
    players: str = Query(..., description="Comma-separated registry IDs (2–4)"),
    season_from: Optional[int] = SEASON_FROM,
    season_to: Optional[int] = SEASON_TO,
    team: Optional[str] = TEAM,
    venue: Optional[str] = VENUE,
) -> EDAPlayerComparisonResponse:
    try:
        filters = eda_analysis.resolve_filters(canonical_engine, season_from, season_to, team, venue)
        return EDAPlayerComparisonResponse(
            **eda_analysis.get_player_comparison(canonical_engine, players.split(","), filters)
        )
    except eda_analysis.FilterError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except DerivedDataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get(
    "/catalog",
    response_model=EDACatalogResponse,
    summary="Get catalog of 20 Stage 2 exploratory figures",
    description="Returns metadata, descriptions, key findings, and image paths for all 20 systematic Stage 2 figures.",
)
async def get_eda_catalog() -> EDACatalogResponse:
    try:
        return eda_service.get_catalog()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load EDA catalog: {exc}")


@router.get(
    "/summary",
    response_model=EDASummaryResponse,
    summary="Get raw statistical tables backing Stage 2 figures",
    description="Returns correlation matrices, phase run rates, venue scoring means, toss cross-tabulations, and missingness audits.",
)
async def get_eda_summary() -> EDASummaryResponse:
    try:
        return eda_service.get_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load EDA summary tables: {exc}")


@router.get(
    "/figures/{figure_name}",
    summary="Serve high-resolution Stage 2 PNG figure",
    description="Streams the requested PNG figure from the reports directory.",
)
async def get_eda_figure(figure_name: str):
    if not SAFE_FILENAME_RE.match(figure_name):
        raise HTTPException(status_code=400, detail="Invalid figure filename.")

    fig_path = PROJECT_ROOT / "reports" / "figures" / "stage_02" / figure_name
    if not fig_path.exists():
        raise HTTPException(status_code=404, detail=f"Figure '{figure_name}' not found.")

    return FileResponse(
        path=fig_path,
        media_type="image/png",
        filename=figure_name,
    )
