"""Overview API endpoints for CricketLens."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from cricketlens.api.schemas import OverviewSummaryResponse, OverviewChartsResponse
from cricketlens.api.services.overview_service import overview_service

router = APIRouter(prefix="/api/overview", tags=["Overview"])


@router.get(
    "/summary",
    response_model=OverviewSummaryResponse,
    summary="Get 8 verified historical IPL KPI metrics and dataset coverage",
    description="Returns audited historical totals including seasons, matches, deliveries, runs, and wickets.",
)
async def get_overview_summary() -> OverviewSummaryResponse:
    try:
        return overview_service.get_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load overview summary: {exc}")


@router.get(
    "/charts",
    response_model=OverviewChartsResponse,
    summary="Get historical IPL charts and verified team records",
    description="Returns data for matches per season, scoring trends, result distribution, score spans, and franchise records.",
)
async def get_overview_charts() -> OverviewChartsResponse:
    try:
        return overview_service.get_charts()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load overview charts: {exc}")
