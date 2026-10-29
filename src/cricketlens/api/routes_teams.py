"""Team Analysis API endpoints for CricketLens."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from cricketlens.api.schemas import (
    TeamListResponse,
    TeamOverviewResponse,
    TeamVenueResponse,
    HeadToHeadResponse,
)
from cricketlens.api.services.team_service import team_service

router = APIRouter(prefix="/api/teams", tags=["Teams"])


@router.get(
    "",
    response_model=TeamListResponse,
    summary="List all canonical IPL franchises",
    description="Returns all 10 active and 5 historical defunct teams with brand colors, active years, and titles.",
)
async def list_teams() -> TeamListResponse:
    try:
        return team_service.list_teams()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list teams: {exc}")


@router.get(
    "/head-to-head",
    response_model=HeadToHeadResponse,
    summary="Get head-to-head records between two franchises",
    description="Returns every encounter, wins (Super Over wins included and also reported separately), ties, "
                "no results, batting first/chasing wins and the meetings list, for all seasons or one season. "
                "Swapping team1 and team2 mirrors the record.",
)
async def get_head_to_head(
    team1: str = Query(..., description="First team slug or name (e.g. 'chennai-super-kings' or 'CSK')"),
    team2: str = Query(..., description="Second team slug or name (e.g. 'mumbai-indians' or 'MI')"),
    season: Optional[int] = Query(None, description="Only this season's meetings (both teams must have played it)"),
) -> HeadToHeadResponse:
    try:
        return team_service.get_head_to_head(team1, team2, season=season)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        # Same franchise on both sides (including aliases such as 'csk' and 'chennai-super-kings')
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to calculate head-to-head records: {exc}")


@router.get(
    "/{team_id}/overview",
    response_model=TeamOverviewResponse,
    summary="Get comprehensive analytical profile for a team",
    description="Returns results (with Super Over and no-result handling), win percentage with its denominator, "
                "runs and wickets, batting first/chasing, season history, venues, every opponent, phase rates and "
                "toss outcomes. With `season`, every number is computed from that season only.",
)
async def get_team_overview(
    team_id: str,
    season: Optional[int] = Query(None, description="Optional tournament season year (2008–2026)"),
) -> TeamOverviewResponse:
    try:
        return team_service.get_team_overview(team_id, season=season)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve team overview: {exc}")


@router.get(
    "/{team_id}/venues",
    response_model=TeamVenueResponse,
    summary="Venue records for a team with a minimum-matches filter",
    description="Venues where the team played at least `min_matches` matches in the selection (all seasons or one).",
)
async def get_team_venues(
    team_id: str,
    season: Optional[int] = Query(None, description="Only this season's matches"),
    min_matches: int = Query(3, ge=1, description="Minimum matches at a venue (1 = every venue)"),
) -> TeamVenueResponse:
    try:
        return team_service.get_team_venues(team_id, season=season, min_matches=min_matches)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve team venues: {exc}")
