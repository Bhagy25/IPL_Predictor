"""Player Explorer Service for CricketLens.

Provides the canonical player directory (every registry ID who batted or
bowled), career and season profiles with splits, and paginated match logs,
backed directly by the verified canonical data engine.
"""
from __future__ import annotations

from typing import Optional
from cricketlens.api.schemas import (
    PlayerListItem,
    PlayerProfileResponse,
    PlayerListResponse,
    PlayerMatchLogResponse,
)
from cricketlens.api.services.canonical_data import canonical_engine


class PlayerService:
    """Service providing comprehensive player queries, career summaries, and match logs."""

    def list_players(
        self,
        query: Optional[str] = None,
        role: Optional[str] = None,
        experience_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "runs",
        min_innings: Optional[int] = None,
    ) -> PlayerListResponse:
        canonical_engine.ensure_loaded()
        res = canonical_engine.list_players(
            search=query,
            role=role,
            tier=experience_filter,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
            min_innings=min_innings,
        )

        items = []
        for p in res["players"]:
            p_copy = dict(p)
            p_copy["batter_id"] = p["player_id"]
            p_copy["innings"] = p["batting_innings"]
            p_copy["avg_per_appearance"] = p["batting_avg"]
            p_copy["milestone30_rate"] = round(p["scores_30_plus"] / max(1, p["batting_innings"]), 3)
            p_copy["milestone50_rate"] = round(p["scores_50_plus"] / max(1, p["batting_innings"]), 3)
            p_copy["is_stage02_leaderboard"] = p["batting_innings"] >= 40
            items.append(PlayerListItem(**p_copy))

        return PlayerListResponse(
            players=items,
            total_count=res["total_players"],
            page=res["page"],
            page_size=res["page_size"],
            total_pages=res["total_pages"],
            query=query,
            experience_filter=experience_filter,
            directory_counts=res["directory_counts"],
            qualification=res["qualification"],
        )

    def get_player_overview(self, player_id: str, season: Optional[int] = None) -> PlayerProfileResponse:
        canonical_engine.ensure_loaded()
        data = canonical_engine.get_player_profile(player_id, season=season)
        d_copy = dict(data)
        d_copy["batter_id"] = data["player_id"]
        return PlayerProfileResponse(**d_copy)

    def get_player_matches(
        self, player_id: str, season: Optional[int] = None, page: int = 1, page_size: int = 20,
    ) -> PlayerMatchLogResponse:
        canonical_engine.ensure_loaded()
        return PlayerMatchLogResponse(
            **canonical_engine.get_player_matches(player_id, season=season, page=page, page_size=page_size)
        )


player_service = PlayerService()
