export interface KPIMetric {
  id: string;
  label: string;
  value: string | number | null;
  statusText: string;
  iconName: string;
  description?: string;
  numeric_value?: number;
}

export interface CoverageMetadata {
  first_match_date: string;
  last_match_date: string;
  seasons_count: number;
  seasons_span: string;
  total_matches: number;
  gender: string;
  competition: string;
}

export interface OverviewSummaryResponse {
  metrics: KPIMetric[];
  coverage: CoverageMetadata;
  notices: string[];
}

export interface MatchesPerSeasonItem {
  season: number;
  matches: number;
}

export interface ScoringTrendItem {
  season: number;
  avg_first_innings_runs: number;
  median_first_innings_runs: number;
  total_runs: number;
}

export interface MatchResultDistributionItem {
  category: string;
  count: number;
  percentage: number;
  description: string;
}

export interface ScoringDistributionBin {
  span: string;
  count: number;
  percentage: number;
  description: string;
}

export interface TeamRecordItem {
  team: string;
  played: number;
  wins: number;
  losses: number;
  tied_no_result: number;
  win_pct: number;
  titles: number;
  title_years: number[];
  status: string;
}

export interface OverviewChartsResponse {
  matches_per_season: MatchesPerSeasonItem[];
  scoring_trends: ScoringTrendItem[];
  result_distribution: MatchResultDistributionItem[];
  scoring_distribution: ScoringDistributionBin[];
  team_records: TeamRecordItem[];
}

export interface ChartContainerProps {
  title: string;
  subtitle: string;
  statusBadge?: string;
  yAxisLabel: string;
  xAxisLabel: string;
  state?: 'loading' | 'empty' | 'error' | 'ready';
  noticeText?: string;
}

export interface TeamRecord {
  team: string;
  matchesPlayed: number | null;
  wins: number | null;
  losses: number | null;
  tiedOrNoResult: number | null;
  titles: number | null;
  winPct?: number | null;
  titleYears?: number[];
  status?: string;
}

// ==========================================
// Team Analysis Types
// ==========================================

export interface TeamListItem {
  id: string;
  name: string;
  short_name: string;
  status: 'Active' | 'Defunct';
  seasons_active: string;
  active_seasons: number[];
  titles: number;
  title_years: number[];
  primary_color: string;
}

export interface TeamSeasonRecord {
  season: number;
  played: number;
  wins: number;
  losses: number;
  tied_no_result: number;
  win_pct: number;
}

export interface TeamVenueRecord {
  venue: string;
  played: number;
  wins: number;
  losses: number;
  win_pct: number;
}

export interface TeamConditionRecord {
  played: number;
  wins: number;
  losses: number;
  win_pct: number;
}

export interface TeamPhaseScoring {
  powerplay_run_rate: number;
  middle_run_rate: number;
  death_run_rate: number;
  overall_run_rate?: number;
  wickets_lost_per_over?: number;
  powerplay_wickets_per_six_balls?: number;
  middle_wickets_per_six_balls?: number;
  death_wickets_per_six_balls?: number;
}

export interface TeamTossStats {
  total_tosses_won?: number;
  tosses_won?: number;
  opt_to_bat?: number;
  opt_to_field?: number;
  elected_to_bat?: number;
  elected_to_field?: number;
  win_rate_when_toss_won?: number;
  toss_match_win_rate?: number;
}

export interface TeamSummaryRecord {
  played: number;
  wins: number;
  losses: number;
  ties: number;
  no_results: number;
  win_pct: number;
  runs_scored?: number;
  runs_conceded?: number;
  wickets_lost?: number;
  wickets_taken?: number;
  denominator_description: string;
}

export interface TeamOverviewResponse {
  team: TeamListItem;
  coverage?: {
    season_filter?: string | number;
    first_season?: number;
    last_season?: number;
    total_seasons_participated?: number;
  };
  all_time: TeamSummaryRecord;
  comparative_2022_2025?: TeamSummaryRecord | null;
  batting_first: TeamConditionRecord;
  chasing: TeamConditionRecord;
  season_history: TeamSeasonRecord[];
  venue_records: TeamVenueRecord[];
  phase_scoring: TeamPhaseScoring;
  toss_stats: TeamTossStats;
  notices: string[];
}

export interface HeadToHeadMeeting {
  match_id: number;
  season: number;
  date: string;
  venue: string;
  winner: string | null;
  margin_or_summary: string;
  innings1_runs: number;
  innings2_runs: number;
}

export interface HeadToHeadResponse {
  team1: TeamListItem;
  team2: TeamListItem;
  total_matches: number;
  team1_wins: number;
  team2_wins: number;
  ties_super_overs: number;
  no_results: number;
  team1_batting_first_wins: number;
  team2_batting_first_wins: number;
  team1_chasing_wins: number;
  team2_chasing_wins: number;
  recent_meetings: HeadToHeadMeeting[];
  notes: string[];
}

export interface TeamListResponse {
  teams: TeamListItem[];
  total_active: number;
  total_defunct: number;
}

// ==========================================
// Player Explorer Types (Batting & Bowling)
// ==========================================

export interface PlayerBattingSummary {
  innings: number;
  runs: number;
  balls_faced: number;
  dismissals: number;
  not_outs: number;
  average: number;
  strike_rate: number;
  highest_score: string;
  fours: number;
  sixes: number;
  ducks: number;
  scores_30_plus: number;
  scores_50_plus: number;
  scores_100_plus: number;
}

export interface PlayerBowlingSummary {
  innings: number;
  legal_deliveries: number;
  overs_bowled: string;
  runs_conceded: number;
  wickets: number;
  bowling_average: number | null;
  bowling_strike_rate: number | null;
  economy_rate: number;
  best_bowling: string;
  three_wicket_hauls: number;
  four_wicket_hauls: number;
  five_wicket_hauls: number;
}

export interface PlayerMatchLogItem {
  match_id: number;
  date: string;
  season: number;
  team: string;
  opponent: string;
  venue: string;
  // Batting
  runs: number | null;
  balls_faced: number | null;
  fours: number | null;
  sixes: number | null;
  dismissal_status: string;
  milestone_badge: string;
  // Bowling
  overs_bowled: string;
  runs_conceded: number | null;
  wickets: number | null;
  economy: number | null;
}

export interface PlayerListItem {
  player_id?: string;
  batter_id: string;
  name: string;
  role?: 'Batter' | 'Bowler' | 'All-Rounder';
  is_batter?: boolean;
  is_bowler?: boolean;
  first_season?: number;
  last_season?: number;
  seasons_count?: number;
  seasons_played?: number[];
  teams?: string[];
  batting_innings?: number;
  innings: number;
  total_runs: number;
  batting_avg?: number;
  strike_rate?: number;
  scores_30_plus?: number;
  scores_50_plus?: number;
  bowling_innings?: number;
  wickets?: number;
  bowling_avg?: number | null;
  economy?: number;
  best_bowling?: string;
  avg_per_appearance: number;
  milestone30_rate: number;
  milestone50_rate: number;
  is_stage02_leaderboard: boolean;
  experience_tier: 'veteran' | 'experienced' | 'regular' | 'emerging' | string;
}

export interface PlayerCareerSummary {
  innings: number;
  total_runs: number;
  avg_per_appearance: number;
  milestone30_count: number;
  milestone30_rate: number;
  milestone50_count: number;
  milestone50_rate: number;
  highest_score: number | string;
  experience_tier: string;
}

export interface PlayerMilestoneBreakdown {
  below_30_count: number;
  below_30_pct: number;
  score_30_to_49_count: number;
  score_30_to_49_pct: number;
  score_50_plus_count: number;
  score_50_plus_pct: number;
}

export interface PlayerRecentMatch {
  match_id: number;
  date: string;
  season: number;
  innings: number;
  team: string;
  opponent: string;
  venue: string;
  runs: number;
  milestone_class: number;
  milestone_label: string;
  prob_30_plus?: number | null;
  prob_50_plus?: number | null;
  actual_30_plus: number;
  actual_50_plus: number;
}

export interface PlayerOpponentRecord {
  opponent: string;
  innings: number;
  total_runs?: number;
  runs?: number;
  avg_runs?: number;
  average?: number;
  strike_rate?: number;
  count_30_plus?: number;
  count_50_plus?: number;
}

export interface PlayerVenueRecord {
  venue: string;
  innings: number;
  total_runs?: number;
  runs?: number;
  avg_runs?: number;
  average?: number;
  strike_rate?: number;
}

export interface PlayerProfileResponse {
  player_id?: string;
  batter_id: string;
  name: string;
  first_season?: number;
  last_season?: number;
  seasons_played?: number[];
  teams?: string[];
  career_batting?: PlayerBattingSummary | null;
  career_bowling?: PlayerBowlingSummary | null;
  career_summary?: PlayerCareerSummary;
  milestone_breakdown?: PlayerMilestoneBreakdown;
  coverage_period?: string;
  recent_matches: (PlayerMatchLogItem | PlayerRecentMatch)[];
  vs_opponents?: PlayerOpponentRecord[];
  opposition_splits?: PlayerOpponentRecord[];
  at_venues?: PlayerVenueRecord[];
  venue_splits?: PlayerVenueRecord[];
  season_splits?: Record<string, any>[];
  notes?: string[];
}

export interface PlayerListResponse {
  players: PlayerListItem[];
  total_count: number;
  total_players?: number;
  page: number;
  page_size: number;
  total_pages?: number;
  query?: string | null;
  experience_filter?: string | null;
}

// ==========================================
// Statistics & EDA Lab Types
// ==========================================

export interface EDAFigureItem {
  id: string;
  figure_num: number;
  title: string;
  category: string;
  description: string;
  figure_url: string;
  coverage_span: string;
  sample_size: string;
  key_findings: string[];
  source_file: string;
}

export interface EDACatalogResponse {
  categories: string[];
  figures: EDAFigureItem[];
  total_figures: number;
}

export interface EDACorrelationMatrix {
  variables: string[];
  pearson: Record<string, Record<string, number>>;
  spearman: Record<string, Record<string, number>>;
  sample_size: number;
  notes: string;
}

export interface EDAPhaseStats {
  phase: string;
  total_runs: number;
  legal_balls: number;
  team_wickets: number;
  runs_per_six_legal_balls: number;
  wickets_per_six_legal_balls: number;
}

export interface EDASummaryResponse {
  scoring_trends: Record<string, any>[];
  phase_patterns: EDAPhaseStats[];
  correlations: EDACorrelationMatrix;
  toss_crosstab: Record<string, any>[];
  venue_means: Record<string, any>[];
  missingness_audit: Record<string, any>[];
  notices: string[];
}

export interface EDAFullHistoryResponse {
  coverage: string;
  season_evolution: {
    season: number;
    matches: number;
    runs: number;
    wickets: number;
    legal_balls: number;
    run_rate: number;
  }[];
  first_innings_trends: {
    season: number;
    innings_count: number;
    mean_runs: number;
    median_runs: number;
    std_runs: number;
    min_runs: number;
    max_runs: number;
  }[];
  era_phase_patterns: {
    era: string;
    phase: string;
    runs: number;
    legal_balls: number;
    wickets: number;
    run_rate: number;
    wickets_per_six_balls: number;
  }[];
  boundaries_by_season: {
    season: number;
    fours: number;
    sixes: number;
    boundary_runs: number;
    boundary_run_pct: number;
  }[];
  toss_and_chasing: {
    season: number;
    matches: number;
    decided_matches: number;
    field_elected: number;
    bat_elected: number;
    toss_winner_match_win_pct: number;
    chasing_win_pct: number;
  }[];
  venue_par: {
    venue: string;
    first_innings_count: number;
    mean_runs: number;
    median_runs: number;
    min_runs: number;
    max_runs: number;
  }[];
  correlations: {
    variables: string[];
    pearson: Record<string, Record<string, number>>;
    spearman: Record<string, Record<string, number>>;
  };
  dismissal_distribution: Record<string, number>;
  top_all_time_batters: {
    batter: string;
    runs: number;
    innings: number;
    fours: number;
    sixes: number;
    scores_50: number;
  }[];
  top_all_time_bowlers: {
    bowler: string;
    wickets: number;
    innings: number;
    legal_deliveries: number;
    runs_conceded: number;
    economy: number;
  }[];
}
