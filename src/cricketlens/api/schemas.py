"""Pydantic schemas for the CricketLens API."""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Operational status of the API, e.g. healthy")
    version: str = Field(..., description="Software version")
    archive_matches: int = Field(..., description="Verified number of men's IPL matches in archive")
    timestamp: str = Field(..., description="Current ISO 8601 UTC timestamp")
    service: str = Field(default="CricketLens Analytical Backend", description="Service identifier")
    derived_tables: Optional[Dict[str, Any]] = Field(
        None,
        description="Availability of data/derived tables used for bowler wickets; bowling endpoints return 503 when unavailable",
    )


class KPIMetricItem(BaseModel):
    id: str = Field(..., description="Unique metric identifier matching frontend card id")
    label: str = Field(..., description="Display label for the KPI card")
    value: str = Field(..., description="Formatted display value (e.g. '1,243' or '401,423')")
    numeric_value: float = Field(..., description="Raw unformatted numeric value for computations")
    statusText: str = Field(..., description="Secondary status text/badge")
    iconName: str = Field(..., description="Lucide icon component name")
    description: Optional[str] = Field(None, description="Analytical context or methodology note")


class CoverageMetadata(BaseModel):
    first_match_date: str = Field(..., description="Earliest match in archive (YYYY-MM-DD)")
    last_match_date: str = Field(..., description="Latest match in archive (YYYY-MM-DD)")
    seasons_count: int = Field(..., description="Count of distinct tournament seasons")
    seasons_span: str = Field(..., description="Span string, e.g. '2008–2026'")
    total_matches: int = Field(..., description="Total verified matches")
    gender: str = Field(default="male", description="Competition gender")
    competition: str = Field(default="Indian Premier League", description="Competition title")


class OverviewSummaryResponse(BaseModel):
    metrics: List[KPIMetricItem] = Field(..., description="List of 8 verified KPI card metrics")
    coverage: CoverageMetadata = Field(..., description="Temporal and competition scope metadata")
    notices: List[str] = Field(default_factory=list, description="Methodology, exclusions and definitions")


class MatchesPerSeasonItem(BaseModel):
    season: int = Field(..., description="IPL tournament year (2008–2026)")
    matches: int = Field(..., description="Total matches played in this season")


class ScoringTrendItem(BaseModel):
    season: int = Field(..., description="IPL tournament year")
    avg_first_innings_runs: float = Field(..., description="Mean runs recorded in first innings")
    median_first_innings_runs: float = Field(..., description="Median runs recorded in first innings")
    total_runs: int = Field(..., description="Total team runs scored across all innings in season")


class MatchResultDistributionItem(BaseModel):
    category: str = Field(..., description="Match outcome category")
    count: int = Field(..., description="Number of matches in this outcome category")
    percentage: float = Field(..., description="Percentage of all archive matches")
    description: str = Field(..., description="Cricket context and rule explanation")


class ScoringDistributionBin(BaseModel):
    span: str = Field(..., description="Innings score range, e.g. '<120', '120–149'")
    count: int = Field(..., description="Innings count in this score range")
    percentage: float = Field(..., description="Percentage of recorded first innings")
    description: str = Field(..., description="Contextual scoring descriptor")


class TeamRecordItem(BaseModel):
    team: str = Field(..., description="Franchise name (normalized for renames)")
    played: int = Field(..., description="Matches played in verification window (2022–2025 comparative)")
    wins: int = Field(..., description="Wins including Super Over decisions")
    losses: int = Field(..., description="Losses in regulation and Super Overs")
    tied_no_result: int = Field(..., description="Unresolved or no-result matches")
    win_pct: float = Field(..., description="Win percentage among decided matches (%)")
    titles: int = Field(..., description="Historical IPL championship titles won")
    title_years: List[int] = Field(default_factory=list, description="Championship winning years")
    status: str = Field(default="Active", description="Active or Defunct franchise status")


class OverviewChartsResponse(BaseModel):
    matches_per_season: List[MatchesPerSeasonItem] = Field(..., description="Matches count per season")
    scoring_trends: List[ScoringTrendItem] = Field(..., description="Scoring trends across seasons")
    result_distribution: List[MatchResultDistributionItem] = Field(..., description="Match result breakdown")
    scoring_distribution: List[ScoringDistributionBin] = Field(..., description="Score span distribution")
    team_records: List[TeamRecordItem] = Field(..., description="Verified franchise records")


# ==========================================
# 2. Team Analysis Schemas
# ==========================================

class TeamListItem(BaseModel):
    id: str = Field(..., description="URL-friendly slug (e.g. 'chennai-super-kings')")
    name: str = Field(..., description="Canonical franchise name")
    short_name: str = Field(..., description="2-4 letter abbreviation (e.g. 'CSK')")
    status: str = Field(..., description="'Active' or 'Defunct'")
    seasons_active: str = Field(..., description="Seasons played as ranges derived from match data, e.g. '2008–2015, 2018–2026'")
    active_seasons: List[int] = Field(..., description="Every tournament season the franchise played, derived from match data")
    titles: int = Field(default=0, description="Championships won")
    title_years: List[int] = Field(default_factory=list, description="Championship winning years")
    primary_color: str = Field(default="#D9B15F", description="Hex brand color")


class TeamSeasonRecord(BaseModel):
    season: int = Field(..., description="Tournament year")
    played: int = Field(..., description="Matches played")
    wins: int = Field(..., description="Matches won")
    losses: int = Field(..., description="Matches lost")
    tied_no_result: int = Field(default=0, description="Tied or abandoned matches")
    win_pct: float = Field(..., description="Win percentage in season (%)")


class TeamVenueRecord(BaseModel):
    venue: str = Field(..., description="Canonical stadium name")
    played: int = Field(..., description="Matches at this ground")
    wins: int = Field(..., description="Wins at this ground")
    losses: int = Field(..., description="Losses at this ground")
    win_pct: float = Field(..., description="Win rate at this ground (%)")


class TeamConditionRecord(BaseModel):
    played: int = Field(..., description="Matches in this condition")
    wins: int = Field(..., description="Wins in this condition")
    losses: int = Field(..., description="Losses in this condition")
    win_pct: float = Field(..., description="Win rate (%)")


class TeamPhaseScoring(BaseModel):
    powerplay_run_rate: float = Field(..., description="Runs per 6 legal balls in Powerplay (overs 1-6)")
    middle_run_rate: float = Field(..., description="Runs per 6 legal balls in Middle overs (overs 7-16)")
    death_run_rate: float = Field(..., description="Runs per 6 legal balls in Death overs (overs 17-20)")
    overall_run_rate: Optional[float] = Field(None, description="Overall tournament run rate")
    wickets_lost_per_over: Optional[float] = Field(None, description="Average batting dismissals per over")
    powerplay_wickets_per_six_balls: Optional[float] = Field(None, description="Powerplay wickets lost per 6 balls")
    middle_wickets_per_six_balls: Optional[float] = Field(None, description="Middle overs wickets lost per 6 balls")
    death_wickets_per_six_balls: Optional[float] = Field(None, description="Death overs wickets lost per 6 balls")


class TeamTossStats(BaseModel):
    tosses_won: int = Field(..., description="Total toss victories")
    elected_to_bat: int = Field(default=0, description="Elected to bat first")
    elected_to_field: int = Field(default=0, description="Elected to chase/field first")
    toss_match_win_rate: float = Field(..., description="Win rate when winning the toss (%)")


class TeamSummaryRecord(BaseModel):
    played: int = Field(..., description="Total matches played")
    wins: int = Field(..., description="Total matches won")
    losses: int = Field(..., description="Total matches lost")
    ties: int = Field(default=0, description="Super Over or regulation ties")
    regulation_ties: Optional[int] = Field(default=0, description="Regulation ties")
    no_results: int = Field(default=0, description="Abandoned matches")
    win_pct: float = Field(..., description="Win percentage (%)")
    runs_scored: Optional[int] = Field(default=0, description="Total runs scored")
    runs_conceded: Optional[int] = Field(default=0, description="Total runs conceded")
    wickets_lost: Optional[int] = Field(default=0, description="Total batting wickets lost")
    wickets_taken: Optional[int] = Field(default=0, description="Total bowling wickets taken")
    denominator_description: str = Field(
        default="Wins divided by decided matches (matches with a confirmed winner), consistent with official IPL records.",
        description="Explicit definition of win percentage denominator"
    )


class TeamOverviewResponse(BaseModel):
    team: TeamListItem = Field(..., description="Franchise metadata")
    coverage: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Active seasons coverage and filters")
    all_time: TeamSummaryRecord = Field(..., description="All-time historical performance")
    comparative_2022_2025: Optional[Dict[str, Any]] = Field(None, description="2022–2025 comparative window")
    batting_first: TeamConditionRecord = Field(..., description="Performance when batting first")
    chasing: TeamConditionRecord = Field(..., description="Performance when chasing")
    season_history: List[TeamSeasonRecord] = Field(..., description="Year-by-year performance breakdown")
    venue_records: List[TeamVenueRecord] = Field(..., description="Top venue performance records")
    phase_scoring: TeamPhaseScoring = Field(..., description="Phase-by-phase scoring rates")
    toss_stats: TeamTossStats = Field(..., description="Toss decision statistics")
    notices: List[str] = Field(default_factory=list, description="Methodology, exclusions and rules")


class HeadToHeadMeeting(BaseModel):
    match_id: int = Field(..., description="Match ID")
    season: int = Field(..., description="IPL season")
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    venue: str = Field(..., description="Canonical venue")
    winner: Optional[str] = Field(None, description="Match winner or null if no result")
    margin_or_summary: str = Field(..., description="Outcome description or scoreline")
    innings1_runs: int = Field(..., description="First innings score")
    innings2_runs: int = Field(..., description="Second innings score")


class HeadToHeadResponse(BaseModel):
    team1: TeamListItem = Field(..., description="First selected franchise")
    team2: TeamListItem = Field(..., description="Second selected franchise")
    total_matches: int = Field(..., description="Total encounters between teams")
    team1_wins: int = Field(..., description="Wins by Team 1")
    team2_wins: int = Field(..., description="Wins by Team 2")
    ties_super_overs: int = Field(default=0, description="Super Over or regulation ties")
    no_results: int = Field(default=0, description="Abandoned encounters")
    team1_batting_first_wins: int = Field(default=0, description="Team 1 wins when batting first")
    team2_batting_first_wins: int = Field(default=0, description="Team 2 wins when batting first")
    team1_chasing_wins: int = Field(default=0, description="Team 1 wins when chasing")
    team2_chasing_wins: int = Field(default=0, description="Team 2 wins when chasing")
    recent_meetings: List[HeadToHeadMeeting] = Field(default_factory=list, description="Recent encounters list")
    notes: List[str] = Field(default_factory=list, description="Historical and Super Over notes")


class TeamListResponse(BaseModel):
    teams: List[TeamListItem] = Field(..., description="List of all canonical franchises")
    total_active: int = Field(default=10, description="Count of currently active franchises")
    total_defunct: int = Field(default=5, description="Count of historical retired franchises")


# ==========================================
# 3. Player Explorer Schemas (Batting & Bowling)
# ==========================================

class PlayerBattingSummary(BaseModel):
    innings: int = Field(..., description="Batting innings: ordinary innings at the crease as striker or non-striker")
    runs: int = Field(..., description="Total runs scored off the bat")
    balls_faced: int = Field(..., description="Deliveries faced as striker, excluding wides")
    dismissals: int = Field(..., description="Times out (retired hurt and retired not out are not dismissals)")
    not_outs: int = Field(..., description="Innings minus dismissals")
    average: Optional[float] = Field(None, description="Runs / dismissals; null when never dismissed (see average_state)")
    average_state: Optional[str] = Field(None, description="'no_dismissals' when average is null, else null")
    strike_rate: Optional[float] = Field(None, description="Runs per 100 balls faced; null when no ball was faced")
    strike_rate_state: Optional[str] = Field(None, description="'no_balls_faced' when strike_rate is null, else null")
    highest_score: str = Field(..., description="Highest score; '*' marks not out (e.g. '113*' or '94')")
    fours: int = Field(default=0, description="Fours off the bat (non-boundary all-run fours excluded)")
    sixes: int = Field(default=0, description="Sixes off the bat")
    ducks: int = Field(default=0, description="Innings dismissed for 0, including without facing a ball")
    scores_30_plus: int = Field(default=0, description="Innings of 30 or more runs")
    scores_50_plus: int = Field(default=0, description="Innings of 50 or more runs")
    scores_100_plus: int = Field(default=0, description="Innings of 100 or more runs")


class PlayerBattingSeason(PlayerBattingSummary):
    season: int = Field(..., description="Season year")


class PlayerBattingTeamSplit(PlayerBattingSummary):
    team: str = Field(..., description="Player's canonical franchise")


class PlayerBattingOppositionSplit(PlayerBattingSummary):
    opposition: str = Field(..., description="Opposing canonical franchise")


class PlayerBattingVenueSplit(PlayerBattingSummary):
    venue: str = Field(..., description="Canonical venue name")


class PlayerBowlingSummary(BaseModel):
    innings: int = Field(..., description="Innings in which the player bowled at least one delivery")
    legal_deliveries: int = Field(..., description="Legal deliveries bowled (excludes wides & noballs)")
    overs_bowled: str = Field(..., description="Overs bowled in cricket notation (e.g. 22 legal balls = '3.4')")
    runs_conceded: int = Field(..., description="Runs conceded off bat + wides + noballs")
    wickets: int = Field(
        ...,
        description="Bowler-credited wickets: bowled, caught, caught and bowled, lbw, stumped, hit wicket "
                    "(run outs, retirements and obstructing the field are not credited); super overs excluded",
    )
    bowling_average: Optional[float] = Field(None, description="Runs conceded per bowler-credited wicket; null when no wicket")
    bowling_average_state: Optional[str] = Field(None, description="'no_wickets' when bowling_average is null, else null")
    bowling_strike_rate: Optional[float] = Field(None, description="Legal balls bowled per bowler-credited wicket; null when no wicket")
    bowling_strike_rate_state: Optional[str] = Field(None, description="'no_wickets' when bowling_strike_rate is null, else null")
    economy_rate: Optional[float] = Field(None, description="Runs conceded per 6 legal balls; null when no legal ball was bowled")
    economy_rate_state: Optional[str] = Field(None, description="'no_legal_balls' when economy_rate is null, else null")
    best_bowling: str = Field(default="—", description="Best innings figures as wickets/runs: most wickets, ties broken by fewest runs (e.g. '5/10')")
    three_wicket_hauls: int = Field(default=0, description="Innings with exactly 3 bowler-credited wickets")
    four_wicket_hauls: int = Field(default=0, description="Innings with exactly 4 bowler-credited wickets")
    five_wicket_hauls: int = Field(default=0, description="Innings with 5 or more bowler-credited wickets (counted here only, not as 3- or 4-wicket hauls)")


class PlayerBowlingSeason(PlayerBowlingSummary):
    season: int = Field(..., description="Season year")


class PlayerBowlingOppositionSplit(PlayerBowlingSummary):
    opposition: str = Field(..., description="Opposing (batting) canonical franchise")


class PlayerBowlingVenueSplit(PlayerBowlingSummary):
    venue: str = Field(..., description="Canonical venue name")


class PlayerTeamSpell(BaseModel):
    team: str = Field(..., description="Canonical franchise name")
    short_name: Optional[str] = Field(None, description="Franchise short code")
    seasons: List[int] = Field(..., description="Seasons with at least one match appearance for this franchise")
    seasons_label: str = Field(..., description="Seasons as ranges, e.g. '2008–2010, 2014'")
    matches: int = Field(..., description="Match appearances for this franchise")


class PlayerSubstitution(BaseModel):
    direction: str = Field(..., description="'in' (came into the match) or 'out' (replaced)")
    reason: str = Field(..., description="Cricsheet reason, e.g. 'impact_player' or 'concussion_substitute'")
    innings: int = Field(..., description="Innings position where the substitution is recorded")
    counterpart_id: str = Field(..., description="Registry ID of the other player in the substitution")
    counterpart_name: str = Field(..., description="Name of the other player as listed for that match")


class PlayerMatchBatting(BaseModel):
    state: str = Field(..., description="'batted' or 'did_not_bat'; every other field is null when did_not_bat")
    runs: Optional[int] = Field(None, description="Runs off the bat")
    balls_faced: Optional[int] = Field(None, description="Balls faced, excluding wides")
    fours: Optional[int] = Field(None, description="Fours off the bat")
    sixes: Optional[int] = Field(None, description="Sixes off the bat")
    dismissed: Optional[bool] = Field(None, description="True when the innings ended in a dismissal")
    dismissal_kind: Optional[str] = Field(
        None,
        description="Cricsheet wicket kind (e.g. 'caught'); 'retired hurt' or 'retired not out' appear with "
                    "dismissed=false; null when not out",
    )


class PlayerMatchBowling(BaseModel):
    state: str = Field(..., description="'bowled' or 'did_not_bowl'; every other field is null when did_not_bowl")
    legal_balls: Optional[int] = Field(None, description="Legal deliveries bowled")
    overs: Optional[str] = Field(None, description="Overs in cricket notation, e.g. '4.0'")
    runs_conceded: Optional[int] = Field(None, description="Runs off the bat plus wides and no-balls")
    wickets: Optional[int] = Field(None, description="Bowler-credited wickets")
    economy: Optional[float] = Field(None, description="Runs per 6 legal balls; null when no legal ball was bowled")
    economy_state: Optional[str] = Field(None, description="'no_legal_balls' when economy is null after bowling")


class PlayerMatchResult(BaseModel):
    outcome: Optional[str] = Field(None, description="For the player's team: 'won', 'lost', 'tied' or 'no_result'")
    outcome_state: Optional[str] = Field(None, description="'not_recorded_in_source' when outcome is null")
    winner: Optional[str] = Field(None, description="Winning franchise in regulation play; null for ties and no results")
    method: Optional[str] = Field(None, description="Result method when recorded, e.g. 'D/L'")
    super_over_winner: Optional[str] = Field(None, description="Franchise that won the super over (ties only)")
    super_over_outcome: Optional[str] = Field(None, description="'won' or 'lost' for the player's team (ties only)")
    super_over_state: Optional[str] = Field(None, description="'not_recorded_in_source' for a tie without a recorded super-over winner")


class PlayerMatchAppearance(BaseModel):
    match_id: int = Field(..., description="Cricsheet match ID")
    date: str = Field(..., description="Match date (YYYY-MM-DD)")
    season: int = Field(..., description="Season year")
    team: str = Field(..., description="Player's canonical franchise")
    opposition: str = Field(..., description="Opposing canonical franchise")
    venue: str = Field(..., description="Canonical venue name")
    appearance_state: str = Field(
        ...,
        description="'playing_xi', 'substituted_in' (Impact Player or concussion substitute), 'substituted_out' "
                    "or 'substituted_in_and_out'",
    )
    substitutions: List[PlayerSubstitution] = Field(default_factory=list, description="Substitutions involving the player")
    batting: PlayerMatchBatting = Field(..., description="Batting in this match")
    bowling: PlayerMatchBowling = Field(..., description="Bowling in this match")
    result: PlayerMatchResult = Field(..., description="Match result for the player's team")


class PlayerMatchLogResponse(BaseModel):
    player_id: str = Field(..., description="Cricsheet registry ID")
    name: str = Field(..., description="Display name")
    season_filter: Optional[int] = Field(None, description="Season applied, or null for the full career")
    total_count: int = Field(..., description="Match appearances matching the filter")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Rows per page")
    total_pages: int = Field(..., description="Total pages (at least 1)")
    matches: List[PlayerMatchAppearance] = Field(..., description="Appearances on this page, most recent first")


class PlayerMatchLogItem(BaseModel):
    match_id: int = Field(..., description="Match ID")
    date: str = Field(..., description="Match date")
    season: int = Field(..., description="Season year")
    team: str = Field(..., description="Player's franchise")
    opponent: str = Field(..., description="Opposition team")
    venue: str = Field(..., description="Canonical stadium")
    # Batting
    runs: Optional[int] = Field(None, description="Runs scored or None if did not bat")
    balls_faced: Optional[int] = Field(None, description="Balls faced or None if did not bat")
    fours: Optional[int] = Field(None, description="Fours hit or None if did not bat")
    sixes: Optional[int] = Field(None, description="Sixes hit or None if did not bat")
    dismissal_status: str = Field(..., description="'Out', 'Not Out', or 'Did not bat'")
    milestone_badge: str = Field(..., description="'50+ Milestone', '30–49 Runs', 'Below 30', or 'DNB'")
    # Bowling
    overs_bowled: str = Field(..., description="Overs bowled (e.g. '4.0') or 'Did not bowl'")
    runs_conceded: Optional[int] = Field(None, description="Runs conceded or None if did not bowl")
    wickets: Optional[int] = Field(None, description="Bowler wickets or None if did not bowl")
    economy: Optional[float] = Field(None, description="Innings economy rate; None if did not bowl or no legal ball")


class PlayerListItem(BaseModel):
    player_id: str = Field(..., description="Cricsheet registry ID")
    batter_id: Optional[str] = Field(None, description="Backward-compatible batter ID alias")
    name: str = Field(..., description="Most-used name variant; players sharing a name get franchise and season span added")
    name_variants: List[str] = Field(default_factory=list, description="Every name this registry ID was listed under")
    role: str = Field(
        default="Batter",
        description="'Batter', 'Bowler' or 'All-Rounder', derived from the IPL playing record. Bowls regularly: "
                    "bowled in >= 50% of matches and >= 12 legal balls per bowling innings. Bats regularly: batted "
                    "in >= 50% of matches and faced >= 8 balls per batting innings. Both: All-Rounder; only bowling: "
                    "Bowler; only batting: Batter; neither: Bowler if legal balls bowled exceed balls faced, else Batter.",
    )
    is_batter: bool = Field(default=True, description="Whether player has batting records")
    is_bowler: bool = Field(default=False, description="Whether player has bowling records")
    matches: int = Field(default=0, description="Matches in an official squad list")
    first_season: int = Field(default=2008, description="First IPL season")
    last_season: int = Field(default=2026, description="Most recent IPL season")
    seasons_count: int = Field(default=1, description="Count of seasons active")
    seasons_played: List[int] = Field(default_factory=list, description="Seasons participated in")
    teams: List[str] = Field(default_factory=list, description="Franchises represented")
    # Batting preview
    batting_innings: int = Field(default=0, description="Batting appearances")
    innings: Optional[int] = Field(None, description="Backward-compatible innings alias")
    total_runs: int = Field(default=0, description="Total career runs scored")
    batting_avg: Optional[float] = Field(None, description="Runs / dismissals; null when never dismissed or never batted")
    strike_rate: Optional[float] = Field(None, description="Runs per 100 balls faced; null when no ball was faced")
    scores_30_plus: int = Field(default=0, description="Scores >= 30")
    scores_50_plus: int = Field(default=0, description="Scores >= 50")
    # Bowling preview
    bowling_innings: int = Field(default=0, description="Bowling appearances")
    wickets: int = Field(default=0, description="Bowler-credited wickets (run outs and retirements excluded; super overs excluded)")
    bowling_avg: Optional[float] = Field(None, description="Runs conceded per bowler-credited wicket")
    economy: Optional[float] = Field(None, description="Runs conceded per 6 legal balls; null when no legal ball was bowled")
    best_bowling: str = Field(default="—", description="Career best bowling figures")
    # Tier flags
    is_stage02_leaderboard: bool = Field(default=False, description="Whether in 69-player leaderboard")
    experience_tier: str = Field(default="regular", description="Experience category")
    avg_per_appearance: Optional[float] = Field(None, description="Backward-compatible average alias")
    milestone30_rate: Optional[float] = Field(None, description="Backward-compatible 30+ rate")
    milestone50_rate: Optional[float] = Field(None, description="Backward-compatible 50+ rate")


class PlayerCareerSummary(BaseModel):
    innings: int = Field(..., description="Recorded batting appearances")
    total_runs: int = Field(..., description="Total runs scored")
    avg_per_appearance: Optional[float] = Field(None, description="Batting average (runs / dismissals); null when never dismissed")
    milestone30_count: int = Field(default=0, description="Count of scores >= 30")
    milestone30_rate: float = Field(default=0.0, description="Rate of scoring 30+ runs")
    milestone50_count: int = Field(default=0, description="Count of scores >= 50")
    milestone50_rate: float = Field(default=0.0, description="Rate of scoring 50+ runs")
    highest_score: Any = Field(..., description="Highest score recorded in logs")
    experience_tier: str = Field(default="regular", description="Experience tier categorization")


class PlayerMilestoneBreakdown(BaseModel):
    below_30_count: int = Field(default=0, description="Innings scoring < 30 runs")
    below_30_pct: float = Field(default=0.0, description="Percentage scoring < 30 runs")
    score_30_to_49_count: int = Field(default=0, description="Innings scoring 30–49 runs")
    score_30_to_49_pct: float = Field(default=0.0, description="Percentage scoring 30–49 runs")
    score_50_plus_count: int = Field(default=0, description="Innings scoring 50+ runs")
    score_50_plus_pct: float = Field(default=0.0, description="Percentage scoring 50+ runs")


class PlayerProfileResponse(BaseModel):
    player_id: str = Field(..., description="Cricsheet registry ID")
    batter_id: Optional[str] = Field(None, description="Backward compatible ID")
    name: str = Field(..., description="Most-used name variant; players sharing a name get franchise and season span added")
    name_variants: List[str] = Field(default_factory=list, description="Every name this registry ID was listed under")
    season_filter: Optional[int] = Field(None, description="Season every number is computed for, or null for the full career")
    matches: int = Field(default=0, description="Match appearances: matches in an official squad list")
    first_season: int = Field(default=2008, description="First season with a match appearance")
    last_season: int = Field(default=2026, description="Latest season with a match appearance")
    seasons_played: List[int] = Field(default_factory=list, description="Seasons with a match appearance")
    seasons_count: int = Field(default=0, description="Number of seasons with a match appearance")
    teams: List[str] = Field(default_factory=list, description="Canonical franchises represented, alphabetical")
    team_history: List[PlayerTeamSpell] = Field(default_factory=list, description="Franchises with their seasons, in order first played")
    batting_state: str = Field(default="did_not_bat", description="'batted' or 'did_not_bat' (career_batting is then null)")
    bowling_state: str = Field(default="did_not_bowl", description="'bowled' or 'did_not_bowl' (career_bowling is then null)")
    career_batting: Optional[PlayerBattingSummary] = Field(None, description="Career batting figures (or the filtered season's)")
    career_bowling: Optional[PlayerBowlingSummary] = Field(None, description="Career bowling figures (or the filtered season's)")
    batting_by_season: List[PlayerBattingSeason] = Field(default_factory=list, description="Batting figures per season, ascending")
    batting_by_team: List[PlayerBattingTeamSplit] = Field(default_factory=list, description="Batting per franchise, most runs first")
    batting_by_opposition: List[PlayerBattingOppositionSplit] = Field(default_factory=list, description="Batting per opposition, most runs first")
    batting_by_venue: List[PlayerBattingVenueSplit] = Field(default_factory=list, description="Batting per venue, most runs first")
    bowling_by_season: List[PlayerBowlingSeason] = Field(default_factory=list, description="Bowling figures per season, ascending")
    bowling_by_opposition: List[PlayerBowlingOppositionSplit] = Field(default_factory=list, description="Bowling per opposition, most wickets first")
    bowling_by_venue: List[PlayerBowlingVenueSplit] = Field(default_factory=list, description="Bowling per venue, most wickets first")
    metric_definitions: Dict[str, str] = Field(default_factory=dict, description="How every statistic is defined")
    state_definitions: Dict[str, str] = Field(default_factory=dict, description="Meaning of each *_state value")
    career_summary: Optional[PlayerCareerSummary] = Field(None, description="Backward-compatible batting summary")
    milestone_breakdown: Optional[PlayerMilestoneBreakdown] = Field(None, description="Score tier distribution")
    coverage_period: str = Field(default="2008–2026 Complete History", description="Data coverage span")
    recent_matches: List[PlayerMatchLogItem] = Field(
        default_factory=list,
        description="Deprecated: every match appearance in the old row shape; use /api/players/{id}/matches",
    )
    opposition_splits: List[Dict[str, Any]] = Field(default_factory=list, description="Deprecated: top 10 of batting_by_opposition")
    venue_splits: List[Dict[str, Any]] = Field(default_factory=list, description="Deprecated: top 10 of batting_by_venue")
    season_splits: List[Dict[str, Any]] = Field(default_factory=list, description="Deprecated: use batting_by_season and bowling_by_season")
    notes: List[str] = Field(default_factory=list, description="Cricket context notes")


class PlayerListQualification(BaseModel):
    sort_by: str = Field(..., description="Rate the directory is sorted by")
    min_innings: int = Field(..., description="Minimum innings a player needs to be listed")
    innings_kind: str = Field(..., description="'batting' or 'bowling': which innings count towards the minimum")


class PlayerListResponse(BaseModel):
    players: List[PlayerListItem] = Field(..., description="List of players")
    total_count: int = Field(..., description="Total matching players")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Page size")
    total_pages: Optional[int] = Field(None, description="Total pages")
    query: Optional[str] = Field(None, description="Search query string applied")
    experience_filter: Optional[str] = Field(None, description="Experience tier filter applied")
    directory_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Unfiltered directory size: all players, batters, bowlers and all-rounders",
    )
    qualification: Optional[PlayerListQualification] = Field(
        None, description="Minimum-innings qualification applied to a rate sort; null when none is applied",
    )


# ==========================================
# 4. Statistics & EDA Lab Schemas
# ==========================================

class EDAFigureItem(BaseModel):
    id: str = Field(..., description="Figure identifier, e.g. '01_season_scoring_trend'")
    figure_num: int = Field(..., description="Figure number 1–20")
    title: str = Field(..., description="Display title of the analytical plot")
    category: str = Field(..., description="Analytical category tag")
    description: str = Field(..., description="Detailed statistical and methodological narrative")
    figure_url: str = Field(..., description="Path or API endpoint to access the PNG figure")
    coverage_span: str = Field(..., description="Coverage scope, e.g. '2008–2025' or '2018–2025'")
    sample_size: str = Field(..., description="Eligible sample size (e.g. '1,169 matches', '533 first innings')")
    key_findings: List[str] = Field(default_factory=list, description="Bullet points of key findings")
    source_file: str = Field(..., description="Stage 2 source CSV or JSON reference file")


class EDACatalogResponse(BaseModel):
    categories: List[str] = Field(..., description="List of unique analytical category tags")
    figures: List[EDAFigureItem] = Field(..., description="List of all 20 Stage 2 figures with metadata")
    total_figures: int = Field(default=20, description="Total cataloged analytical figures")


class EDACorrelationMatrix(BaseModel):
    variables: List[str] = Field(..., description="List of variables evaluated")
    pearson: Dict[str, Dict[str, float]] = Field(..., description="Pearson linear correlation coefficients")
    spearman: Dict[str, Dict[str, float]] = Field(..., description="Spearman monotonic correlation coefficients")
    sample_size: int = Field(default=533, description="Recent first-innings sample size (2018–2025)")
    notes: str = Field(..., description="Observational correlation context")


class EDAPhaseStats(BaseModel):
    phase: str = Field(..., description="Cricket phase (Powerplay, Middle, Death)")
    total_runs: int = Field(..., description="Runs scored across all observed balls")
    legal_balls: int = Field(..., description="Legal deliveries bowled")
    team_wickets: int = Field(..., description="Wickets lost by batting team")
    runs_per_six_legal_balls: float = Field(..., description="Run rate per 6 legal balls")
    wickets_per_six_legal_balls: float = Field(..., description="Wickets lost per 6 legal balls")


class EDASummaryResponse(BaseModel):
    scoring_trends: List[Dict[str, Any]] = Field(..., description="Season-wise first-innings averages and medians")
    phase_patterns: List[EDAPhaseStats] = Field(..., description="Phase-by-phase scoring and wicket rates")
    correlations: EDACorrelationMatrix = Field(..., description="First-innings Pearson and Spearman correlations")
    toss_crosstab: List[Dict[str, Any]] = Field(..., description="Toss decision vs match winner cross-tabulation")
    venue_means: List[Dict[str, Any]] = Field(..., description="Venue scoring averages for grounds with >=20 matches")
    missingness_audit: List[Dict[str, Any]] = Field(..., description="Data quality and feature missingness table")
    notices: List[str] = Field(default_factory=list, description="Analytical limitations and development holdout rules")


class EDAFullHistoryResponse(BaseModel):
    coverage: str = Field(..., description="Dataset coverage description")
    season_evolution: List[Dict[str, Any]] = Field(..., description="Evolution across all 19 seasons (2008–2026)")
    first_innings_trends: List[Dict[str, Any]] = Field(..., description="First innings mean, median, std, min, max")
    era_phase_patterns: List[Dict[str, Any]] = Field(..., description="Powerplay, Middle, Death across 5 tournament eras")
    boundaries_by_season: List[Dict[str, Any]] = Field(..., description="Fours, sixes, boundary runs, percentage per season")
    toss_and_chasing: List[Dict[str, Any]] = Field(..., description="Toss decision and chasing outcomes across 1,243 matches")
    venue_par: List[Dict[str, Any]] = Field(..., description="First innings scoring averages at top grounds (min 10 matches)")
    correlations: Dict[str, Any] = Field(..., description="Pearson and Spearman correlation matrices")
    dismissal_distribution: Dict[str, int] = Field(..., description="All-time wicket dismissal mode counts")
    top_all_time_batters: List[Dict[str, Any]] = Field(..., description="Top 10 all-time run scorers (2008–2026)")
    top_all_time_bowlers: List[Dict[str, Any]] = Field(..., description="Top 10 all-time wicket takers (2008–2026)")
