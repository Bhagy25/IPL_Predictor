"""Player Explorer API endpoints for CricketLens."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from cricketlens.api.schemas import (
    PlayerListResponse,
    PlayerMatchLogResponse,
    PlayerProfileResponse,
)
from cricketlens.api.services.player_service import player_service
from cricketlens.api.services.canonical_data import DerivedDataUnavailable

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
    min_innings: Optional[int] = Query(
        None, ge=1,
        description="Rate sorts only (batting_avg, strike_rate: batting innings; bowling_avg, economy: bowling "
                    "innings): list only players with at least this many innings. Ignored for other sorts.",
    ),
) -> PlayerListResponse:
    try:
        return player_service.list_players(
            query=query,
            role=role,
            experience_filter=experience_filter,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            min_innings=min_innings,
        )
    except DerivedDataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to query players: {exc}")


@router.get(
    "/{player_id}/overview",
    response_model=PlayerProfileResponse,
    summary="Get detailed career profile (Batting, Bowling, Match Logs) for a player",
    description="Returns the career summary with teams and seasons, career and season-wise batting and bowling "
                "figures, and splits by team, opposition and venue. With `season`, every number is computed "
                "from that season only (404 if the player has no appearance in it).",
)
async def get_player_overview(
    player_id: str,
    season: Optional[int] = Query(None, description="Compute every number for this season only"),
) -> PlayerProfileResponse:
    try:
        return player_service.get_player_overview(player_id, season=season)
    except KeyError as exc:
        # args[0] is the plain message; str(KeyError) would wrap it in quotes
        raise HTTPException(status_code=404, detail=exc.args[0])
    except DerivedDataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load player overview: {exc}")


@router.get(
    "/{player_id}/matches",
    response_model=PlayerMatchLogResponse,
    summary="Paginated match-by-match log for a player",
    description="One row per match appearance in an official squad list, most recent first, including matches "
                "where the player did not bat or bowl, with Impact Player / concussion substitution state and "
                "the result for the player's team.",
)
async def get_player_matches(
    player_id: str,
    season: Optional[int] = Query(None, description="Only this season's appearances"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Rows per page"),
) -> PlayerMatchLogResponse:
    try:
        return player_service.get_player_matches(player_id, season=season, page=page, page_size=page_size)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0])
    except DerivedDataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load player match log: {exc}")
