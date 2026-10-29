export interface KPIMetric {
  id: string;
  label: string;
  value: string | number | null;
  statusText: string;
  iconName: string;
  description?: string;
  numeric_value?: number | null;
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
  teams: number;
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
  win_pct: number | null;
  titles: number;
  title_years: number[];
  status: string;
}

export interface OverviewScoringTrend {
  first_innings: number;
  overall_mean: number;
  slope_runs_per_season: number;
  seasons_label: string;
  peak_season: number;
  peak_mean: number;
  definition: string;
}

export interface OverviewOutcomes {
  matches: number;
  decided: number;
  decided_in_regulation: number;
  decided_by_super_over: number;
  no_result: number;
  other_not_recorded: number;
  dl_method: number;
  decided_pct: number | null;
}

export interface OverviewScoringSummary {
  n: number;
  first_innings_recorded: number;
  eligibility_rule: string;
  excluded: { match_id: number; date: string; season: number; batting_team: string; runs: number; wickets: number; legal_balls: number; reason: string }[];
  mean: number;
  median: number;
  q1: number;
  q3: number;
  min: number;
  max: number;
  modal_span: string;
  modal_pct: number;
}

export interface OverviewTeamRecordsWindow {
  first_season: number;
  last_season: number;
  label: string;
  rule: string;
  win_pct_definition: string;
  franchises: number;
}

export interface SeasonChampion {
  season: number;
  match_id: number;
  date: string;
  champion: string | null;
  champion_short_name: string | null;
  runner_up: string | null;
  venue: string;
  state: string | null;
}

export interface OverviewChartsResponse {
  matches_per_season: MatchesPerSeasonItem[];
  scoring_trends: ScoringTrendItem[];
  scoring_trend: OverviewScoringTrend;
  result_distribution: MatchResultDistributionItem[];
  outcomes: OverviewOutcomes;
  scoring_distribution: ScoringDistributionBin[];
  scoring_summary: OverviewScoringSummary;
  team_records: TeamRecordItem[];
  team_records_window: OverviewTeamRecordsWindow;
  champions: SeasonChampion[];
  champion_rule: string;
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

// Results for a selection: a null win_pct always comes with win_pct_state (see state_definitions)
export interface TeamResultSummary {
  played: number;
  wins: number;
  losses: number;
  ties: number;
  no_results: number;
  results_not_recorded: number;
  super_over_wins: number;
  super_over_losses: number;
  win_pct: number | null;
  win_pct_denominator: number;
  win_pct_state: string | null;
}

export interface TeamRunTotals {
  runs_scored: number;
  runs_conceded: number;
  wickets_lost: number;
  wickets_taken: number;
  balls_faced: number;
  balls_bowled: number;
  innings_batted: number;
  innings_bowled: number;
  run_rate: number | null;
  run_rate_state: string | null;
  economy: number | null;
  economy_state: string | null;
  runs_per_innings: number | null;
}

export type TeamSeasonRecord = TeamResultSummary & TeamRunTotals & { season: number; regulation_ties: number };
export type TeamVenueRecord = TeamResultSummary & { venue: string };
export type TeamOpponentRecord = TeamResultSummary & { opponent: string; opponent_short_name: string };
export type TeamSummaryRecord = TeamResultSummary & TeamRunTotals & { regulation_ties: number; denominator_description: string };

export interface TeamPhaseRecord {
  phase: 'powerplay' | 'middle' | 'death';
  label: string;
  overs: string;
  batting_runs: number;
  batting_legal_balls: number;
  batting_run_rate: number | null;
  batting_run_rate_state: string | null;
  wickets_lost: number;
  wickets_lost_per_six: number | null;
  conceded_runs: number;
  bowling_legal_balls: number;
  economy: number | null;
  economy_state: string | null;
  wickets_taken: number;
  wickets_taken_per_six: number | null;
}

export interface TeamLeagueToss {
  label: string;
  seasons: number[];
  after_winning_toss: TeamResultSummary;
  chose_to_bat: TeamResultSummary;
  chose_to_field: TeamResultSummary;
}

export interface TeamTossStats {
  tosses_won: number;
  elected_to_bat: number;
  elected_to_field: number;
  toss_match_win_rate: number | null;
  after_winning_toss: TeamResultSummary;
  chose_to_bat: TeamResultSummary;
  chose_to_field: TeamResultSummary;
  league: TeamLeagueToss;
}

export interface TeamOverviewResponse {
  team: TeamListItem;
  coverage: {
    season_filter: number | null;
    seasons_in_scope: number[];
    first_season: number;
    last_season: number;
    total_seasons_participated: number;
  };
  all_time: TeamSummaryRecord;
  // Same window as the homepage team records: first season every current franchise played to the latest season
  comparative_window?: (TeamResultSummary & { window: string; first_season: number; last_season: number; rule: string }) | null;
  batting_first: TeamResultSummary;
  chasing: TeamResultSummary;
  innings_order_no_results: number;
  season_history: TeamSeasonRecord[];
  venue_records: TeamVenueRecord[];
  opponents: TeamOpponentRecord[];
  phases: TeamPhaseRecord[];
  toss_stats: TeamTossStats;
  definitions: Record<string, string>;
  state_definitions: Record<string, string>;
  notices: string[];
}

export interface TeamVenueResponse {
  team: TeamListItem;
  season_filter: number | null;
  min_matches: number;
  venues_total: number;
  venues_shown: number;
  matches_shown: number;
  venues: TeamVenueRecord[];
}

export interface HeadToHeadMeeting {
  match_id: number;
  season: number;
  date: string;
  venue: string;
  winner: string | null;
  result_text: string;
  super_over: boolean;
  margin_or_summary: string;
  innings1_runs: number;
  innings2_runs: number;
}

export interface HeadToHeadResponse {
  team1: TeamListItem;
  team2: TeamListItem;
  season_filter: number | null;
  total_matches: number;
  team1_wins: number;
  team2_wins: number;
  ties_super_overs: number;
  unresolved_ties: number;
  team1_super_over_wins: number;
  team2_super_over_wins: number;
  no_results: number;
  win_pct_denominator: number;
  team1_win_pct: number | null;
  team2_win_pct: number | null;
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

// A null rate always comes with a *_state code explaining why (see state_definitions)
export interface PlayerBattingSummary {
  innings: number;
  runs: number;
  balls_faced: number;
  dismissals: number;
  not_outs: number;
  average: number | null;
  average_state: string | null;
  strike_rate: number | null;
  strike_rate_state: string | null;
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
  bowling_average_state: string | null;
  bowling_strike_rate: number | null;
  bowling_strike_rate_state: string | null;
  economy_rate: number | null;
  economy_rate_state: string | null;
  best_bowling: string;
  three_wicket_hauls: number;
  four_wicket_hauls: number;
  five_wicket_hauls: number;
}

export type PlayerBattingSeason = PlayerBattingSummary & { season: number };
export type PlayerBattingTeamSplit = PlayerBattingSummary & { team: string };
export type PlayerBattingOppositionSplit = PlayerBattingSummary & { opposition: string };
export type PlayerBattingVenueSplit = PlayerBattingSummary & { venue: string };
export type PlayerBowlingSeason = PlayerBowlingSummary & { season: number };
export type PlayerBowlingOppositionSplit = PlayerBowlingSummary & { opposition: string };
export type PlayerBowlingVenueSplit = PlayerBowlingSummary & { venue: string };

export interface PlayerTeamSpell {
  team: string;
  short_name: string | null;
  seasons: number[];
  seasons_label: string;
  matches: number;
}

export interface PlayerSubstitution {
  direction: 'in' | 'out';
  reason: string;
  innings: number;
  counterpart_id: string;
  counterpart_name: string;
}

export interface PlayerMatchBatting {
  state: string;
  runs: number | null;
  balls_faced: number | null;
  fours: number | null;
  sixes: number | null;
  dismissed: boolean | null;
  dismissal_kind: string | null;
}

export interface PlayerMatchBowling {
  state: string;
  legal_balls: number | null;
  overs: string | null;
  runs_conceded: number | null;
  wickets: number | null;
  economy: number | null;
  economy_state: string | null;
}

export interface PlayerMatchResult {
  outcome: string | null;
  outcome_state: string | null;
  winner: string | null;
  method: string | null;
  super_over_winner: string | null;
  super_over_outcome: string | null;
  super_over_state: string | null;
}

export interface PlayerMatchAppearance {
  match_id: number;
  date: string;
  season: number;
  team: string;
  opposition: string;
  venue: string;
  appearance_state: string;
  substitutions: PlayerSubstitution[];
  batting: PlayerMatchBatting;
  bowling: PlayerMatchBowling;
  result: PlayerMatchResult;
}

export interface PlayerMatchLogResponse {
  player_id: string;
  name: string;
  season_filter: number | null;
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  matches: PlayerMatchAppearance[];
}

export interface PlayerListItem {
  player_id?: string;
  batter_id: string;
  name: string;
  name_variants?: string[];
  matches?: number;
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
  batting_avg?: number | null;
  strike_rate?: number | null;
  scores_30_plus?: number;
  scores_50_plus?: number;
  bowling_innings?: number;
  wickets?: number;
  bowling_avg?: number | null;
  economy?: number | null;
  best_bowling?: string;
  avg_per_appearance: number;
  milestone30_rate: number;
  milestone50_rate: number;
  is_stage02_leaderboard: boolean;
  experience_tier: 'veteran' | 'experienced' | 'regular' | 'emerging' | string;
}

export interface PlayerProfileResponse {
  player_id?: string;
  batter_id: string;
  name: string;
  name_variants?: string[];
  season_filter: number | null;
  matches: number;
  first_season: number;
  last_season: number;
  seasons_played: number[];
  seasons_count: number;
  teams?: string[];
  team_history: PlayerTeamSpell[];
  batting_state: 'batted' | 'did_not_bat';
  bowling_state: 'bowled' | 'did_not_bowl';
  career_batting?: PlayerBattingSummary | null;
  career_bowling?: PlayerBowlingSummary | null;
  batting_by_season: PlayerBattingSeason[];
  batting_by_team: PlayerBattingTeamSplit[];
  batting_by_opposition: PlayerBattingOppositionSplit[];
  batting_by_venue: PlayerBattingVenueSplit[];
  bowling_by_season: PlayerBowlingSeason[];
  bowling_by_opposition: PlayerBowlingOppositionSplit[];
  bowling_by_venue: PlayerBowlingVenueSplit[];
  metric_definitions: Record<string, string>;
  state_definitions: Record<string, string>;
  coverage_period?: string;
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
  directory_counts?: DirectoryCounts;
  qualification?: PlayerListQualification | null;
}

export interface PlayerListQualification {
  sort_by: string;
  min_innings: number;
  innings_kind: 'batting' | 'bowling';
}

export interface DirectoryCounts {
  all: number;
  batters: number;
  bowlers: number;
  all_rounders: number;
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
  coverage_evidence?: string | null;
  static_note?: string | null;
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


// ==========================================
// Statistics & EDA: filterable full-history analysis
// ==========================================

export type EDAFilterKey = 'season' | 'team' | 'venue';

export interface EDAArea<D = Record<string, any>> {
  id: string;
  title: string;
  supported_filters: EDAFilterKey[];
  applied_filters: EDAFilterKey[];
  unaffected_by: { filter: EDAFilterKey; note: string }[];
  coverage: { seasons: number[]; first_season: number; last_season: number; label: string } | null;
  sample: { label: string; value: number }[];
  definitions: Record<string, string>;
  units: string;
  source: string;
  state: 'ok' | 'empty';
  empty_reason: string | null;
  data: D | null;
}

export interface EDAFiltersEcho {
  season_from: number;
  season_to: number;
  team: { id: string; name: string; short_name: string; seasons_label: string } | null;
  venue: string | null;
  venue_min_matches: number;
  bat_min_balls: number;
  bowl_min_balls: number;
  label: string;
}

export interface EDAHistogramBin { bin: string; count: number; pct: number | null }

export interface EDAOutcomes {
  matches: number;
  decided: number;
  decided_in_regulation: number;
  decided_by_super_over: number;
  no_result: number;
  other_not_recorded: number;
  dl_method: number;
}

export interface EDATossRecord {
  tosses_won: number;
  elected_to_bat: number;
  elected_to_field: number;
  after_winning_toss: TeamResultSummary;
  chose_to_bat: TeamResultSummary;
  chose_to_field: TeamResultSummary;
}

export interface EDAInningsOrderRecord {
  batting_first: TeamResultSummary;
  chasing: TeamResultSummary;
  innings_order_no_results: number;
}

export interface EDAMatchListItem {
  match_id: number;
  date: string;
  season: number;
  teams: string;
  venue: string;
  winner: string | null;
}

export interface EDABoundaryRecord {
  fours: number;
  sixes: number;
  boundary_runs: number;
  runs: number;
  legal_balls: number;
  dot_balls: number;
  boundary_run_pct: number | null;
  dot_ball_pct: number | null;
  balls_per_boundary: number | null;
}

export type EDALeaderBatter = PlayerBattingSummary & { player_id: string; name: string };
export type EDALeaderBowler = PlayerBowlingSummary & { player_id: string; name: string };

export interface EDATeamComparisonRow extends TeamResultSummary {
  team: string;
  id: string;
  short_name: string;
  status: string;
  seasons_label: string;
  run_rate: number | null;
  economy: number | null;
  runs_per_innings: number | null;
  selected: boolean;
}

export interface EDAVenueRow {
  venue: string;
  matches: number;
  first_innings: number;
  first_innings_mean: number | null;
  first_innings_median: number | null;
  run_rate: number | null;
  result_label: string;
  result: TeamResultSummary;
  selected: boolean;
}

export interface EDAInningsDistribution {
  innings: number;
  n: number;
  mean: number | null;
  median: number | null;
  q1: number | null;
  q3: number | null;
  min: number | null;
  max: number | null;
  full_innings: number;
  histogram: EDAHistogramBin[];
}

export interface EDADismissalKind {
  kind: string;
  count: number;
  pct: number | null;
  bowler_credited: number;
  not_bowler_credited: number;
  team_wickets: number;
}

export interface EDAStage1Audit {
  label: string;
  coverage: string;
  source: string;
  screening_issue_counts: Record<string, number>;
  missingness: { table: string; column: string; missing_count: number; total_rows: number; missing_pct: number }[];
  raw_over_anomalies: { match_id: number; innings: number; over_index: number; issue: string; detail: string }[];
}

export interface EDAAreas {
  matches_runs: EDAArea<{
    by_season: { season: number; matches: number; runs: number; deliveries: number; legal_balls: number; wickets: number; run_rate: number | null }[];
    totals: { matches: number; runs: number; deliveries: number; legal_balls: number; wickets: number; run_rate: number | null };
  }>;
  scoring_trends: EDAArea<{
    by_season: {
      season: number;
      innings: number;
      runs: number;
      legal_balls: number;
      runs_per_innings: number;
      run_rate: number | null;
      first_innings: number;
      first_innings_mean: number | null;
      second_innings: number;
      second_innings_mean: number | null;
    }[];
    totals: { innings: number; runs: number; legal_balls: number; runs_per_innings: number; run_rate: number | null };
  }>;
  batting_distribution: EDAArea<{
    summary: PlayerBattingSummary & { mean_runs: number; median_runs: number };
    runs_histogram: EDAHistogramBin[];
    strike_rate_min_balls: number;
    strike_rate_innings: number;
    strike_rate_median: number | null;
    strike_rate_histogram: EDAHistogramBin[];
    leaders: EDALeaderBatter[];
  }>;
  bowling: EDAArea<{
    summary: PlayerBowlingSummary;
    economy_min_balls: number;
    economy_innings: number;
    economy_median: number | null;
    economy_histogram: EDAHistogramBin[];
    leaders: EDALeaderBowler[];
  }>;
  phases: EDAArea<{ team_view: boolean; overall: TeamPhaseRecord[]; by_season: { season: number; phases: TeamPhaseRecord[] }[] }>;
  team_comparison: EDAArea<{ teams: EDATeamComparisonRow[] }>;
  venues: EDAArea<{ min_matches: number; venues_total: number; venues_shown: number; matches_shown: number; venues: EDAVenueRow[] }>;
  toss: EDAArea<{ team_view: boolean; overall: EDATossRecord; by_season: (EDATossRecord & { season: number })[] }>;
  innings_order: EDAArea<{
    team_view: boolean;
    outcomes: EDAOutcomes;
    overall: EDAInningsOrderRecord;
    by_season: (EDAInningsOrderRecord & { season: number })[];
  }>;
  innings_scores: EDAArea<{ by_innings: EDAInningsDistribution[] }>;
  dismissals: EDAArea<{
    kinds: EDADismissalKind[];
    events: number;
    bowler_credited: number;
    not_bowler_credited: number;
    team_wickets: number;
    not_team_wickets: number;
    team_wickets_from_deliveries: number;
    super_over_events_excluded: number;
  }>;
  boundaries: EDAArea<{ totals: EDABoundaryRecord; by_season: (EDABoundaryRecord & { season: number })[] }>;
  anomalies: EDAArea<{
    outcomes: EDAOutcomes;
    super_over_matches: number;
    dl_matches: number;
    no_results: number;
    penalty_run_deliveries: number;
    penalty_runs: number;
    substitutions: number;
    substitutions_by_reason: Record<string, number>;
    substitutions_in_super_overs: number;
    missing_city_matches: number;
    matches_without_two_innings: number;
    lists: { super_over: EDAMatchListItem[]; dl: EDAMatchListItem[]; no_result: EDAMatchListItem[] };
    stage1_audit: EDAStage1Audit;
  }>;
  correlations: EDAArea<{
    n: number;
    min_n: number;
    state: 'ok' | 'insufficient_sample';
    explanation: string | null;
    variables: { key: string; label: string }[];
    pearson: Record<string, Record<string, number | null>> | null;
    spearman: Record<string, Record<string, number | null>> | null;
    pairs_with_total: { x: string; y: string; pearson: number | null; spearman: number | null }[];
  }>;
}

export interface EDAAnalysisResponse {
  filters: EDAFiltersEcho;
  areas: EDAAreas;
}

export interface EDAFilterOptionsResponse {
  seasons: number[];
  teams: { id: string; name: string; short_name: string; status: string; seasons_label: string }[];
  venues: { name: string; matches: number; seasons_label: string }[];
  correlation_min_n: number;
  areas: Record<string, { title: string; supports: EDAFilterKey[] }>;
}

export interface EDAComparedPlayer {
  player_id: string;
  name: string;
  seasons_played: string;
  state: 'ok' | 'empty';
  empty_reason: string | null;
  coverage: string | null;
  matches: number;
  batting: PlayerBattingSummary | null;
  bowling: PlayerBowlingSummary | null;
  batting_by_season: PlayerBattingSeason[];
  bowling_by_season: PlayerBowlingSeason[];
}

export interface EDAPlayerComparisonResponse {
  filters: EDAFiltersEcho;
  area: EDAArea<{ players: EDAComparedPlayer[] }>;
}

// ==========================================
// Prediction Arena (/api/predict)
// ==========================================

export interface PredictionTeamOption {
  name: string;
  code: string;
  slug: string;
  primary_color: string;
}

export interface PredictionVenueOption {
  name: string;
  matches: number;
  last_season: number | null;
  used_in_latest_season: boolean;
}

export interface PredictionBatterOption {
  player_id: string;
  name: string;
  name_variants: string[];
  eligible_innings: number;
  latest_innings_date: string;
  latest_team: string;
  last_season: number;
  appeared_in_latest_season: boolean;
}

export interface PredictionOptionsResponse {
  teams: PredictionTeamOption[];
  venues: PredictionVenueOption[];
  latest_season: number;
  archive_last_match_date: string;
  wicket_rules: Record<string, unknown>;
  batters: PredictionBatterOption[];
  batter_date_rule: string;
  models_available: Record<string, boolean>;
}

export interface WicketPredictionRequest {
  batting_team: string;
  bowling_team: string;
  venue: string;
  innings: number;
  completed_overs: number;
  runs: number;
  wickets: number;
  last_over_runs: number;
  last_over_wickets: number;
}

export interface WicketPredictionResponse {
  event: string;
  probability: number;
  probability_pct: number;
  phase: string;
  model: string;
  model_file: string;
  version: string;
  status: string;
  training_end: number;
  training_span: string;
  inputs: WicketPredictionRequest;
  notice: string;
  function_notice: string;
  input_range: InputRangeCheck;
}

/** Inputs outside the deployment model's training rows at this checkpoint; the probability is unchanged. */
export interface InputRangeCheck {
  checked: boolean;
  completed_overs: number;
  outside: { field: string; label: string; value: number; observed_min: number; observed_max: number }[];
  warning: string | null;
  source: string;
}

export interface BatterPredictionRequest {
  player_id: string;
  batting_team: string;
  opponent: string;
  venue: string;
  match_date: string;
}

export interface BatterRecentInnings {
  date: string;
  runs: number;
  batting_team: string;
  opponent: string;
  venue: string;
}

export interface BatterPredictionResponse {
  player_id: string;
  player_name: string;
  source_name: string;
  batting_team: string;
  opponent: string;
  venue: string;
  date: string;
  prior_eligible_innings: number;
  chance_30_plus: number;
  chance_50_plus: number;
  chance_30_plus_pct: number;
  chance_50_plus_pct: number;
  model: string;
  model_file: string;
  model_train_end: number;
  version: string;
  training_span: string;
  scope: string;
  appeared_in_latest_season: boolean;
  return_note: string | null;
  function_scope: string;
  warning: string;
  notice: string;
  form_context: {
    prior_eligible_innings: number;
    latest_innings_date: string;
    recent_innings: BatterRecentInnings[];
    definition: string;
  };
}

export interface WicketEvaluationMetrics {
  model?: string | null;
  training_rows?: number | null;
  rows: number;
  event_rate: number;
  brier_score: number;
  log_loss: number;
  roc_auc?: number | null;
}

export interface BatterEvaluationMetrics {
  model?: string | null;
  training_rows?: number | null;
  rows: number;
  observed_30_rate: number;
  observed_50_rate: number;
  brier_30: number;
  brier_50: number;
  avg_milestone_brier: number;
  multiclass_log_loss: number;
  roc_auc_30?: number | null;
  roc_auc_50?: number | null;
}

export interface PredictionModelInfo {
  kind: 'wicket' | 'batter';
  title: string;
  available: boolean;
  status_detail: string;
  deployment_file: string;
  holdout_file: string;
  name: string | null;
  version: string | null;
  training_end: number | null;
  training_span: string | null;
  features: string[];
  classes: number[];
  condition: string | null;
  selected_name: string;
  selection_metric: string;
  validation_2025: Record<string, number | string>[];
  validation_2025_constant: Record<string, number | string>;
  holdout_2026: Record<string, number | string>;
  holdout_2026_constant: Record<string, number | string>;
  rows: Record<string, number>;
  exclusions: string | null;
  notes: string[];
}

export interface PredictionModelsResponse {
  models: PredictionModelInfo[];
  holdout_statement: string;
  caveats: string[];
  source: string;
  report_created_utc: string | null;
}

// ==========================================
// Prediction Tracker: 2026 holdout replay (/api/predict/holdout-replay)
// ==========================================

export interface CalibrationBin {
  milestone?: string | null;
  bin: number;
  lower: number;
  upper: number;
  n: number;
  avg_predicted: number;
  observed_rate: number;
}

export interface MetricCheck {
  matches_official: boolean;
  compared: string[];
  mismatched: string[];
  tolerance: number;
}

export interface ReplayMatchItem {
  match_id: number;
  date: string;
  team1: string;
  team2: string;
  team1_code: string;
  team2_code: string;
  venue: string;
  winner: string | null;
  wicket_checkpoints: number;
  batter_forecasts: number;
}

export interface HoldoutReplayResponse {
  label: string;
  statement: string;
  matches: ReplayMatchItem[];
  wicket: {
    computed: WicketEvaluationMetrics & { calibration: CalibrationBin[] };
    official: WicketEvaluationMetrics;
    official_constant: WicketEvaluationMetrics;
    check: MetricCheck;
    matches_count: number;
    eligibility: string;
  };
  batter: {
    computed: BatterEvaluationMetrics & { calibration: CalibrationBin[] };
    official: BatterEvaluationMetrics;
    official_constant: BatterEvaluationMetrics;
    check: MetricCheck;
    matches_count: number;
    eligibility: string;
  };
  sources: string[];
}

export interface ReplayBatterRow {
  innings: number;
  batting_team: string;
  batter_id: string;
  batter: string;
  prior_innings: number;
  probability_30_plus: number;
  probability_50_plus: number;
  actual_runs: number;
  actual_30_plus: boolean;
  actual_50_plus: boolean;
}

export interface ReplayWicketRow {
  innings: number;
  batting_team: string;
  completed_overs: number;
  next_over: number;
  phase: string;
  predicted_probability: number;
  wicket_fell: boolean;
}

export interface HoldoutReplayMatchResponse {
  label: string;
  match_id: number;
  date: string;
  team1: string;
  team2: string;
  venue: string;
  winner: string | null;
  batters: ReplayBatterRow[];
  wickets: ReplayWicketRow[];
  wicket_summary: WicketEvaluationMetrics | null;
  batter_summary: BatterEvaluationMetrics | null;
}
