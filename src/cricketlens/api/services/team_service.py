"""Team Analysis Service for CricketLens.

Provides canonical team analytics for every season in the archive: results,
season filtering, venue and opponent breakdowns, phase rates, toss outcomes and
head-to-head records, backed directly by the verified canonical data engine.
"""
from __future__ import annotations

from typing import Optional
from cricketlens.api.schemas import (
    TeamListItem,
    TeamListResponse,
    TeamOverviewResponse,
    TeamVenueResponse,
    HeadToHeadResponse,
)
from cricketlens.api.services.canonical_data import canonical_engine, FRANCHISE_METADATA


class TeamService:
    """Analytical service providing verified team data, head-to-head records, and phase splits."""

    def list_teams(self) -> TeamListResponse:
        """Return every canonical franchise with active and defunct counts."""
        canonical_engine.ensure_loaded()
        teams = [TeamListItem(**meta) for meta in canonical_engine.list_teams()]
        active_count = sum(1 for m in teams if m.status == "Active")
        defunct_count = sum(1 for m in teams if m.status == "Defunct")
        return TeamListResponse(
            teams=teams,
            total_active=active_count,
            total_defunct=defunct_count,
        )

    def get_team_overview(self, team_id: str, season: Optional[int] = None) -> TeamOverviewResponse:
        """Return complete analytical summary for a team with optional season filter."""
        canonical_engine.ensure_loaded()
        data = canonical_engine.get_team_overview(team_id, season=season)
        return TeamOverviewResponse(**data)

    def get_team_venues(self, team_id: str, season: Optional[int] = None, min_matches: int = 3) -> TeamVenueResponse:
        """Venue records for a team, keeping venues with at least min_matches matches."""
        canonical_engine.ensure_loaded()
        return TeamVenueResponse(**canonical_engine.get_team_venues(team_id, season=season, min_matches=min_matches))

    def get_head_to_head(self, team1_id: str, team2_id: str, season: Optional[int] = None) -> HeadToHeadResponse:
        """Return head-to-head records between two teams, all seasons or one."""
        canonical_engine.ensure_loaded()
        data = canonical_engine.get_head_to_head(team1_id, team2_id, season=season)
        return HeadToHeadResponse(**data)


team_service = TeamService()
