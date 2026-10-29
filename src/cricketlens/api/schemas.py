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
    innings: int = Field(..., description="Recorded batting appearances")
    runs: int = Field(..., description="Total runs scored")
    balls_faced: int = Field(..., description="Deliveries faced")
    dismissals: int = Field(..., description="Times out")
    not_outs: int = Field(..., description="Innings remaining not out")
    average: float = Field(..., description="Batting average (runs / dismissals)")
    strike_rate: float = Field(..., description="Runs scored per 100 balls")
    highest_score: str = Field(..., description="Highest score (e.g. '113*' or '94')")
    fours: int = Field(default=0, description="Fours hit")
    sixes: int = Field(default=0, description="Sixes hit")
    ducks: int = Field(default=0, description="Dismissed for 0")
    scores_30_plus: int = Field(default=0, description="Scores >= 30")
    scores_50_plus: int = Field(default=0, description="Scores >= 50")
    scores_100_plus: int = Field(default=0, description="Centuries (>= 100)")


class PlayerBowlingSummary(BaseModel):
    innings: int = Field(..., description="Innings bowled")
    legal_deliveries: int = Field(..., description="Legal deliveries bowled (excludes wides & noballs)")
    overs_bowled: str = Field(..., description="Overs bowled in cricket notation (e.g. '342.4')")
    runs_conceded: int = Field(..., description="Runs conceded off bat + wides + noballs")
    wickets: int = Field(..., description="Bowler dismissals (excludes run outs)")
    bowling_average: Optional[float] = Field(None, description="Runs conceded per wicket")
    bowling_strike_rate: Optional[float] = Field(None, description="Balls per wicket")
    economy_rate: float = Field(..., description="Runs conceded per 6 legal balls")
    best_bowling: str = Field(default="—", description="Best figures in an innings (e.g. '5/10')")
    three_wicket_hauls: int = Field(default=0, description="3-wicket hauls")
    four_wicket_hauls: int = Field(default=0, description="4-wicket hauls")
    five_wicket_hauls: int = Field(default=0, description="5+ wicket hauls")


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
    economy: Optional[float] = Field(None, description="Innings economy rate or None if did not bowl")


class PlayerListItem(BaseModel):
    player_id: str = Field(..., description="Unique stable player hash ID")
    batter_id: Optional[str] = Field(None, description="Backward-compatible batter ID alias")
    name: str = Field(..., description="Player display name")
    role: str = Field(default="Batter", description="'Batter', 'Bowler', or 'All-Rounder'")
    is_batter: bool = Field(default=True, description="Whether player has batting records")
    is_bowler: bool = Field(default=False, description="Whether player has bowling records")
    first_season: int = Field(default=2008, description="First IPL season")
    last_season: int = Field(default=2026, description="Most recent IPL season")
    seasons_count: int = Field(default=1, description="Count of seasons active")
    seasons_played: List[int] = Field(default_factory=list, description="Seasons participated in")
    teams: List[str] = Field(default_factory=list, description="Franchises represented")
    # Batting preview
    batting_innings: int = Field(default=0, description="Batting appearances")
    innings: Optional[int] = Field(None, description="Backward-compatible innings alias")
    total_runs: int = Field(default=0, description="Total career runs scored")
    batting_avg: float = Field(default=0.0, description="Batting average")
    strike_rate: float = Field(default=0.0, description="Batting strike rate")
    scores_30_plus: int = Field(default=0, description="Scores >= 30")
    scores_50_plus: int = Field(default=0, description="Scores >= 50")
    # Bowling preview
    bowling_innings: int = Field(default=0, description="Bowling appearances")
    wickets: int = Field(default=0, description="Total wickets taken")
    bowling_avg: Optional[float] = Field(None, description="Bowling average")
    economy: float = Field(default=0.0, description="Career economy rate")
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
    avg_per_appearance: float = Field(..., description="Average runs per appearance")
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
    player_id: str = Field(..., description="Unique stable player ID")
    batter_id: Optional[str] = Field(None, description="Backward compatible ID")
    name: str = Field(..., description="Player display name")
    first_season: int = Field(default=2008, description="First IPL season")
    last_season: int = Field(default=2026, description="Latest IPL season")
    seasons_played: List[int] = Field(default_factory=list, description="Seasons active")
    teams: List[str] = Field(default_factory=list, description="Teams represented")
    career_batting: Optional[PlayerBattingSummary] = Field(None, description="Verified career batting figures")
    career_bowling: Optional[PlayerBowlingSummary] = Field(None, description="Verified career bowling figures")
    career_summary: Optional[PlayerCareerSummary] = Field(None, description="Backward-compatible batting summary")
    milestone_breakdown: Optional[PlayerMilestoneBreakdown] = Field(None, description="Score tier distribution")
    coverage_period: str = Field(default="2008–2026 Complete History", description="Data coverage span")
    recent_matches: List[PlayerMatchLogItem] = Field(default_factory=list, description="Chronological match logs")
    opposition_splits: List[Dict[str, Any]] = Field(default_factory=list, description="Performance by opponent")
    venue_splits: List[Dict[str, Any]] = Field(default_factory=list, description="Performance by venue")
    season_splits: List[Dict[str, Any]] = Field(default_factory=list, description="Season-by-season figures")
    notes: List[str] = Field(default_factory=list, description="Cricket context notes")


class PlayerListResponse(BaseModel):
    players: List[PlayerListItem] = Field(..., description="List of players")
    total_count: int = Field(..., description="Total matching players")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Page size")
    total_pages: Optional[int] = Field(None, description="Total pages")
    query: Optional[str] = Field(None, description="Search query string applied")
    experience_filter: Optional[str] = Field(None, description="Experience tier filter applied")


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
