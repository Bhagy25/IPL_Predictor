"""Player Explorer API endpoints for CricketLens."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from cricketlens.api.schemas import (
    PlayerListResponse,
    PlayerProfileResponse,
)
from cricketlens.api.services.player_service import player_service

router = APIRouter(prefix="/api/players", tags=["Players"])


@router.get(
    "",
    response_model=PlayerListResponse,
    summary="List and search players with pagination and filters",
    description="Returns searchable IPL players across all 806 canonical players with role, tier, and sorting options.",
)
async def list_players(
    query: Optional[str] = Query(None, description="Search by player name or ID"),
    role: Optional[str] = Query(None, description="Filter by role: 'All', 'Batters', 'Bowlers', 'All-Rounders'"),
    experience_filter: Optional[str] = Query(
        None,
        description="Filter by tier: 'leaderboard_only', 'veteran', 'experienced', 'regular', 'emerging'",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("runs", description="Sort by: 'runs', 'wickets', 'batting_avg', 'bowling_avg', 'economy', 'innings', 'strike_rate'"),
) -> PlayerListResponse:
    try:
        return player_service.list_players(
            query=query,
            role=role,
            experience_filter=experience_filter,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to query players: {exc}")


@router.get(
    "/{player_id}/overview",
    response_model=PlayerProfileResponse,
    summary="Get detailed career profile (Batting, Bowling, Match Logs) for a player",
    description="Returns career batting figures, bowling figures, recent match appearances with batting & bowling columns, opposition splits, and venue records.",
)
async def get_player_overview(player_id: str) -> PlayerProfileResponse:
    try:
        return player_service.get_player_overview(player_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load player overview: {exc}")
