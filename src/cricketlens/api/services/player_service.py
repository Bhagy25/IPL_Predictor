"""Player Explorer Service for CricketLens.

Provides canonical 2008-2026 player directory covering all 806 players
(both batting and bowling careers, match logs, and splits), backed directly
by the verified canonical data engine.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from cricketlens.api.schemas import (
    PlayerListItem,
    PlayerCareerSummary,
    PlayerMilestoneBreakdown,
    PlayerProfileResponse,
    PlayerListResponse,
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
    ) -> PlayerListResponse:
        canonical_engine.ensure_loaded()
        res = canonical_engine.list_players(
            search=query,
            role=role,
            tier=experience_filter,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
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
        )

    def get_player_overview(self, player_id: str) -> PlayerProfileResponse:
        canonical_engine.ensure_loaded()
        data = canonical_engine.get_player_profile(player_id)
        d_copy = dict(data)
        d_copy["batter_id"] = data["player_id"]

        if data["career_batting"]:
            cb = data["career_batting"]
            total_inn = max(1, cb["innings"])
            d_copy["career_summary"] = PlayerCareerSummary(
                innings=cb["innings"],
                total_runs=cb["runs"],
                avg_per_appearance=cb["average"],
                milestone30_count=cb["scores_30_plus"],
                milestone30_rate=round(cb["scores_30_plus"] / total_inn, 3),
                milestone50_count=cb["scores_50_plus"],
                milestone50_rate=round(cb["scores_50_plus"] / total_inn, 3),
                highest_score=cb["highest_score"],
                experience_tier="veteran" if cb["innings"] >= 60 else "experienced" if cb["innings"] >= 31 else "regular" if cb["innings"] >= 11 else "emerging",
            )
            d_copy["milestone_breakdown"] = PlayerMilestoneBreakdown(
                below_30_count=total_inn - cb["scores_30_plus"],
                below_30_pct=round((total_inn - cb["scores_30_plus"]) / total_inn * 100, 1),
                score_30_to_49_count=cb["scores_30_plus"] - cb["scores_50_plus"],
                score_30_to_49_pct=round((cb["scores_30_plus"] - cb["scores_50_plus"]) / total_inn * 100, 1),
                score_50_plus_count=cb["scores_50_plus"],
                score_50_plus_pct=round(cb["scores_50_plus"] / total_inn * 100, 1),
            )

        return PlayerProfileResponse(**d_copy)


player_service = PlayerService()
