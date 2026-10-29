"""Statistics and EDA Lab API endpoints for CricketLens."""
from __future__ import annotations

import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from cricketlens.api.schemas import (
    EDACatalogResponse,
    EDASummaryResponse,
    EDAFullHistoryResponse,
)
from cricketlens.api.services.eda_service import eda_service
from cricketlens.api.services.canonical_data import canonical_engine, DerivedDataUnavailable

router = APIRouter(prefix="/api/eda", tags=["Statistics & EDA"])

SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+\.png$")


@router.get(
    "/full-history",
    response_model=EDAFullHistoryResponse,
    summary="Get comprehensive 2008–2026 historical EDA across all 15 analytical areas",
    description="Returns complete tournament scoring evolution, 19-season first innings trends, era phase patterns, boundary analysis, toss/chasing records, venue par, correlations, and all-time leaderboards.",
)
async def get_eda_full_history() -> EDAFullHistoryResponse:
    try:
        canonical_engine.ensure_loaded()
        return EDAFullHistoryResponse(**canonical_engine.get_eda_full_history())
    except DerivedDataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load full history EDA: {exc}")


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

    fig_path = Path.cwd() / "reports" / "figures" / "stage_02" / figure_name
    if not fig_path.exists():
        raise HTTPException(status_code=404, detail=f"Figure '{figure_name}' not found.")

    return FileResponse(
        path=fig_path,
        media_type="image/png",
        filename=figure_name,
    )
