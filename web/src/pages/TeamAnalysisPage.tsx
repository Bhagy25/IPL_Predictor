import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import {
  Shield,
  Swords,
  MapPin,
  Flame,
  Calendar,
  AlertCircle,
  RefreshCw,
  Info,
  Loader2,
  Database,
  BookOpen,
  Users,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  Legend,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import {
  TeamListItem,
  TeamOverviewResponse,
  TeamVenueResponse,
  TeamResultSummary,
  TeamSeasonRecord,
  TeamOpponentRecord,
  TeamVenueRecord,
  HeadToHeadResponse,
} from '../types';
import { fetchTeams, fetchTeamOverview, fetchTeamVenues, fetchHeadToHead } from '../api/teams';
import { Column, DataTable, Tabs } from '../components/player/ProfileSections';
import { FOCUS_RING, Stat, plural } from '../components/player/playerFormat';
import { fmtCount, fmtPct, fmtRate, fmtShare } from '../utils/format';

const VENUE_MINIMUMS = [1, 3, 5, 10];
const DEFAULT_VENUE_MINIMUM = 3;

const CHART_TOOLTIP = {
  contentStyle: { backgroundColor: '#151619', borderColor: '#D9B15F', borderRadius: '0.75rem', fontSize: '12px' },
  labelStyle: { color: '#F6F6F3', fontWeight: 'bold' },
};

export const TeamAnalysisPage: React.FC = () => {
  const [teams, setTeams] = useState<TeamListItem[]>([]);
  const [totals, setTotals] = useState<{ active: number; defunct: number } | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState<string>('chennai-super-kings');
  const [selectedSeason, setSelectedSeason] = useState<string>('all');
  const [teamOverview, setTeamOverview] = useState<TeamOverviewResponse | null>(null);

  // Venues (own request: the minimum-matches control refetches only this table)
  const [venueMinimum, setVenueMinimum] = useState<number>(DEFAULT_VENUE_MINIMUM);
  const [venues, setVenues] = useState<TeamVenueResponse | null>(null);
  const [venuesLoading, setVenuesLoading] = useState<boolean>(true);
  const [venuesError, setVenuesError] = useState<string | null>(null);

  // Head to Head state
  const [opponentId, setOpponentId] = useState<string>('mumbai-indians');
  const [h2h, setH2H] = useState<HeadToHeadResponse | null>(null);
  const [h2hLoading, setH2HLoading] = useState<boolean>(false);
  const [h2hError, setH2HError] = useState<string | null>(null);

  // Loading and error states
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [teamsError, setTeamsError] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<'Active' | 'Defunct' | 'All'>('Active');
  const [seasonView, setSeasonView] = useState<string>('win');

  // Only the latest request may update state, so a slow earlier response cannot overwrite it
  const overviewRequest = useRef(0);
  const venuesRequest = useRef(0);
  const h2hRequest = useRef(0);

  const seasonNumber = selectedSeason === 'all' ? undefined : parseInt(selectedSeason, 10);

  // Load teams list
  const loadTeams = useCallback(async () => {
    setTeamsError(null);
    try {
      const res = await fetchTeams();
      setTeams(res.teams);
      setTotals({ active: res.total_active, defunct: res.total_defunct });
      if (res.teams.length > 0 && !res.teams.some(t => t.id === selectedTeamId)) {
        setSelectedTeamId(res.teams[0].id);
      }
    } catch (err: any) {
      setTeamsError(err?.message || 'Failed to load teams list');
    }
  }, []);

  useEffect(() => {
    loadTeams();
  }, [loadTeams]);

  // Load team overview when selectedTeamId or selectedSeason changes
  const loadOverview = useCallback(async () => {
    if (!selectedTeamId) return;
    const requestId = ++overviewRequest.current;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTeamOverview(selectedTeamId, seasonNumber);
      if (requestId === overviewRequest.current) setTeamOverview(data);
    } catch (err: any) {
      if (requestId === overviewRequest.current) {
        // Never leave the previous franchise's numbers on screen after a failure
        setTeamOverview(null);
        setError(err?.message || 'Failed to load team analytics');
      }
    } finally {
      if (requestId === overviewRequest.current) setLoading(false);
    }
  }, [selectedTeamId, seasonNumber]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const loadVenues = useCallback(async () => {
    if (!selectedTeamId) return;
    const requestId = ++venuesRequest.current;
    setVenuesLoading(true);
    setVenuesError(null);
    try {
      const data = await fetchTeamVenues(selectedTeamId, seasonNumber, venueMinimum);
      if (requestId === venuesRequest.current) setVenues(data);
    } catch (err: any) {
      if (requestId === venuesRequest.current) {
        setVenues(null);
        setVenuesError(err?.message || 'Failed to load venue records');
      }
    } finally {
      if (requestId === venuesRequest.current) setVenuesLoading(false);
    }
  }, [selectedTeamId, seasonNumber, venueMinimum]);

  useEffect(() => {
    loadVenues();
  }, [loadVenues]);

  // Head-to-head follows the selected team, opponent and season
  const loadH2H = useCallback(async () => {
    if (!selectedTeamId || !opponentId || selectedTeamId === opponentId) return;
    const requestId = ++h2hRequest.current;
    setH2HLoading(true);
    setH2HError(null);
    try {
      const res = await fetchHeadToHead(selectedTeamId, opponentId, seasonNumber);
      if (requestId === h2hRequest.current) setH2H(res);
    } catch (err: any) {
      if (requestId === h2hRequest.current) {
        setH2H(null);
        setH2HError(err?.message || 'Failed to load head-to-head records');
      }
    } finally {
      if (requestId === h2hRequest.current) setH2HLoading(false);
    }
  }, [selectedTeamId, opponentId, seasonNumber]);

  useEffect(() => {
    loadH2H();
  }, [loadH2H]);

  const retryFailedRequests = () => {
    if (teamsError) loadTeams();
    loadOverview();
  };

  // Overview-backed sections render data only once the current request has succeeded
  const overviewReady = !loading && teamOverview !== null;

  const displayedTeams = useMemo(() => {
    if (filterCategory === 'All') return teams;
    return teams.filter(t => t.status === filterCategory);
  }, [teams, filterCategory]);

  // Opponents that played in the selected season (every other franchise for all seasons)
  const opponentOptions = useMemo(() => {
    return teams.filter(t => t.id !== selectedTeamId && (seasonNumber === undefined || t.active_seasons.includes(seasonNumber)));
  }, [teams, selectedTeamId, seasonNumber]);

  // Keep the head-to-head opponent valid for the selected team and season
  useEffect(() => {
    if (opponentOptions.length > 0 && !opponentOptions.some(t => t.id === opponentId)) {
      setOpponentId(opponentOptions[0].id);
    }
  }, [opponentOptions, opponentId]);

  const currentTeam = teamOverview?.team;
  const archiveSpan = useMemo(() => {
    const seasons = teams.flatMap(t => t.active_seasons);
    return seasons.length ? `${Math.min(...seasons)}–${Math.max(...seasons)}` : '';
  }, [teams]);

  // Seasons the selected franchise actually played, as reported by the API
  const seasonOptions = useMemo(() => {
    const listed = teams.find(t => t.id === selectedTeamId);
    return listed?.active_seasons ?? currentTeam?.active_seasons ?? [];
  }, [teams, selectedTeamId, currentTeam]);

  const stateText = (state: string | null) => (state ? teamOverview?.state_definitions[state] ?? state : undefined);
  const scopeLabel = seasonNumber ? `IPL ${seasonNumber}` : 'All seasons';
  const allTime = teamOverview?.all_time;

  return (
    <div className="space-y-12 sm:space-y-16 max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-16">

      {/* 1. Header */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#D9B15F]/20">
          <div>
            <div className="flex items-center gap-3">
              <span className="w-1.5 h-6 bg-[#D9B15F] rounded-full inline-block" />
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#F6F6F3]">
                Team Analysis
              </h1>
            </div>
            <p className="text-xs sm:text-sm text-[#B9B9B3] mt-1 ml-4 sm:ml-5">
              Franchise results, batting first and chasing, phase scoring and conceding, toss outcomes, venues and head-to-head records for every season or one season.
            </p>
          </div>

          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#151619] border border-[#D9B15F]/30 text-xs font-medium text-[#D9B15F] self-start sm:self-center shadow-gold-pill">
            <Shield className="w-3.5 h-3.5 text-[#D9B15F]" />
            <span>{teams.length ? `${plural(teams.length, 'franchise')} · ${archiveSpan} archive` : '…'}</span>
          </div>
        </div>

        {/* Status Alert Banner */}
        {(teamsError || error) && (
          <div className="bg-[#1C1517] border border-red-500/30 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs sm:text-sm font-semibold text-red-200">
                  Analytical backend error ({teamsError || error})
                </p>
                <p className="text-xs text-red-300/75 mt-0.5">
                  Unable to load franchise dataset from the CricketLens API.
                </p>
              </div>
            </div>
            <button
              onClick={retryFailedRequests}
              className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#2A1B1E] hover:bg-[#3A2227] text-red-200 border border-red-500/40 transition-colors ${FOCUS_RING}`}
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        )}
      </div>

      {/* 2. Team Selector Filter Bar */}
      <section aria-label="Franchise Selector" className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2 text-xs text-[#B9B9B3]">
            <span>Filter franchises:</span>
            <div className="inline-flex rounded-lg bg-[#151619] p-0.5 border border-[#D9B15F]/20">
              {(['Active', 'Defunct', 'All'] as const).map(cat => {
                const count = totals ? { Active: totals.active, Defunct: totals.defunct, All: totals.active + totals.defunct }[cat] : null;
                return (
                  <button
                    key={cat}
                    onClick={() => setFilterCategory(cat)}
                    aria-pressed={filterCategory === cat}
                    className={`px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${FOCUS_RING} ${
                      filterCategory === cat
                        ? 'bg-[#D9B15F] text-[#0D0E10] shadow-sm'
                        : 'text-[#B9B9B3] hover:text-[#F6F6F3]'
                    }`}
                  >
                    {cat === 'Defunct' ? 'Historical / Retired' : cat}{count !== null ? ` (${count})` : ''}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Franchise Pills Scrollable Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2.5">
          {displayedTeams.map(team => {
            const isSelected = team.id === selectedTeamId;
            return (
              <button
                key={team.id}
                aria-pressed={isSelected}
                onClick={() => {
                  setSelectedTeamId(team.id);
                  // Reset a season filter the newly selected franchise never played
                  if (selectedSeason !== 'all' && !team.active_seasons.includes(Number(selectedSeason))) {
                    setSelectedSeason('all');
                  }
                }}
                className={`relative flex items-center gap-2.5 p-3 rounded-xl border text-left transition-all cursor-pointer ${FOCUS_RING} ${
                  isSelected
                    ? 'bg-[#1D1E22] border-[#D9B15F] shadow-gold-pill'
                    : 'bg-[#151619] border-[#D9B15F]/15 hover:border-[#D9B15F]/40 hover:bg-[#1A1B1F]'
                }`}
              >
                <span
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: team.primary_color }}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-extrabold text-[#F6F6F3] truncate">
                      {team.short_name}
                    </span>
                    {team.titles > 0 && (
                      <span className="text-[10px] text-[#D9B15F] font-bold flex items-center gap-0.5">
                        🏆 {team.titles}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-[#B9B9B3] truncate">{team.name}</p>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* 3. Team Profile Banner Card */}
      {loading && !teamOverview ? (
        <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-12 text-center flex flex-col items-center justify-center gap-3 animate-pulse">
          <Loader2 className="w-8 h-8 text-[#D9B15F] animate-spin" />
          <p className="text-sm font-semibold text-[#F6F6F3]">Loading verified franchise records...</p>
        </div>
      ) : currentTeam && allTime ? (
        <section aria-label="Team Overview" aria-busy={loading} className={`bg-[#151619] border border-[#D9B15F]/30 rounded-2xl p-6 sm:p-8 space-y-6 transition-opacity ${loading ? 'opacity-60' : ''}`}>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#D9B15F]/15">
            <div className="flex items-center gap-4 min-w-0">
              <div
                className="w-14 h-14 flex-shrink-0 rounded-2xl flex items-center justify-center font-black text-lg text-white shadow-lg border border-white/20"
                style={{ backgroundColor: currentTeam.primary_color }}
              >
                {currentTeam.short_name}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-2xl sm:text-3xl font-black text-[#F6F6F3]">
                    {currentTeam.name}
                  </h2>
                  <span className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full border ${
                    currentTeam.status === 'Active'
                      ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30'
                      : 'bg-zinc-800/60 text-zinc-400 border-zinc-600/30'
                  }`}>
                    {currentTeam.status}
                  </span>
                </div>
                <p className="text-xs sm:text-sm text-[#B9B9B3] mt-1">
                  Seasons played: <strong className="text-[#F6F6F3]">{currentTeam.seasons_active}</strong> &middot;{' '}
                  {currentTeam.titles > 0 ? (
                    <span className="text-[#D9B15F] font-semibold">
                      🏆 {plural(currentTeam.titles, 'IPL title')} ({currentTeam.title_years.join(', ')})
                    </span>
                  ) : (
                    <span>No IPL titles</span>
                  )}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Season Filter Dropdown */}
              <div className="flex items-center gap-2 max-w-full bg-[#1A1B1F] border border-[#D9B15F]/30 rounded-xl px-3 py-2">
                <Calendar className="w-3.5 h-3.5 text-[#D9B15F]" />
                <label htmlFor="team-season" className="text-xs font-semibold text-[#B9B9B3]">Season:</label>
                <select
                  id="team-season"
                  value={selectedSeason}
                  onChange={e => setSelectedSeason(e.target.value)}
                  className={`min-w-0 max-w-full bg-[#121316] border border-[#D9B15F]/20 text-[#F6F6F3] text-xs font-bold rounded-lg px-2.5 py-1 cursor-pointer ${FOCUS_RING}`}
                >
                  <option value="all">All seasons</option>
                  {seasonOptions.map(s => (
                    <option key={s} value={s}>
                      IPL {s}
                    </option>
                  ))}
                </select>
              </div>

              {teamOverview?.comparative_window && selectedSeason === 'all' && (
                <div className="bg-[#1A1B1F] border border-[#D9B15F]/20 rounded-xl p-3 sm:p-4 text-right" title={teamOverview.comparative_window.rule}>
                  <span className="text-[10px] uppercase tracking-wider text-[#B9B9B3] font-semibold">
                    {teamOverview.comparative_window.window} win % (comparative window)
                  </span>
                  <p className="text-xl sm:text-2xl font-black text-[#D9B15F]">
                    <Stat value={fmtPct(teamOverview.comparative_window.win_pct)} reason={stateText(teamOverview.comparative_window.win_pct_state)} />
                  </p>
                  <p className="text-[11px] text-[#B9B9B3]">
                    {teamOverview.comparative_window.wins} / {teamOverview.comparative_window.win_pct_denominator} &middot; {teamOverview.comparative_window.wins}W {teamOverview.comparative_window.losses}L
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* 4. Results */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3 sm:gap-4">
            <KpiCard label={seasonNumber ? `IPL ${seasonNumber} matches` : 'Matches'} value={fmtCount(allTime.played)} note={scopeLabel} />
            <KpiCard label="Won" tone="text-emerald-400" value={fmtCount(allTime.wins)}
              note={allTime.super_over_wins ? `incl. ${plural(allTime.super_over_wins, 'Super Over win')}` : 'Regulation, D/L or Super Over'} />
            <KpiCard label="Lost" tone="text-rose-400" value={fmtCount(allTime.losses)}
              note={allTime.super_over_losses ? `incl. ${plural(allTime.super_over_losses, 'Super Over loss', 'Super Over losses')}` : 'Regulation, D/L or Super Over'} />
            <KpiCard label="Tied · No result" value={`${fmtCount(allTime.ties)} · ${fmtCount(allTime.no_results)}`} note="Ties without a Super Over result · abandoned" />
            <KpiCard label="Win %" highlight value={<Stat value={fmtPct(allTime.win_pct)} reason={stateText(allTime.win_pct_state)} />}
              note={`${fmtCount(allTime.wins)} / ${fmtCount(allTime.win_pct_denominator)} (matches − no results)`} />
            <KpiCard label="Batting first" value={<Stat value={fmtPct(teamOverview.batting_first.win_pct)} reason={stateText(teamOverview.batting_first.win_pct_state)} />}
              note={`${fmtCount(teamOverview.batting_first.wins)} / ${fmtCount(teamOverview.batting_first.win_pct_denominator)}`} />
            <KpiCard label="Chasing" value={<Stat value={fmtPct(teamOverview.chasing.win_pct)} reason={stateText(teamOverview.chasing.win_pct_state)} />}
              note={`${fmtCount(teamOverview.chasing.wins)} / ${fmtCount(teamOverview.chasing.win_pct_denominator)}`} />
          </div>

          {(allTime.super_over_wins + allTime.super_over_losses + allTime.ties > 0 || teamOverview.innings_order_no_results > 0) && (
            <ul className="text-[11px] text-[#B9B9B3] space-y-1">
              {allTime.super_over_wins + allTime.super_over_losses > 0 && (
                <li>Tied → won Super Over: <strong className="text-[#F6F6F3]">{allTime.super_over_wins}</strong> &middot; Tied → lost Super Over: <strong className="text-[#F6F6F3]">{allTime.super_over_losses}</strong> (counted in won / lost above)</li>
              )}
              {allTime.ties > 0 && <li>{plural(allTime.ties, 'tie')} with no Super Over result recorded.</li>}
              {teamOverview.innings_order_no_results > 0 && (
                <li>Batting first / chasing exclude {plural(teamOverview.innings_order_no_results, 'no-result match', 'no-result matches')}.</li>
              )}
            </ul>
          )}

          {/* Runs Scored, Conceded, Wickets Lost & Taken */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <TotalCard label="Runs scored" value={fmtCount(allTime.runs_scored)} icon={<Flame className="w-4 h-4 text-[#D9B15F]/70" />} />
            <TotalCard label="Runs conceded" value={fmtCount(allTime.runs_conceded)} icon={<Shield className="w-4 h-4 text-[#D9B15F]/70" />} />
            <TotalCard label="Wickets lost" value={fmtCount(allTime.wickets_lost)} tone="text-rose-300" />
            <TotalCard label="Wickets taken" value={fmtCount(allTime.wickets_taken)} tone="text-emerald-300" />
            <TotalCard label="Run rate" value={<Stat value={fmtRate(allTime.run_rate)} reason={stateText(allTime.run_rate_state)} />} />
            <TotalCard label="Economy (conceded)" value={<Stat value={fmtRate(allTime.economy)} reason={stateText(allTime.economy_state)} />} />
          </div>

          <div className="flex items-center gap-2 text-xs text-[#B9B9B3] bg-[#0E0F12] p-3 rounded-lg border border-[#D9B15F]/15">
            <Info className="w-4 h-4 text-[#D9B15F] flex-shrink-0" />
            <span>
              <strong>Win %:</strong> {allTime.denominator_description}
            </span>
          </div>
        </section>
      ) : (
        <section aria-label="Team Overview" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-6">
          <SectionState loading={loading} error={error} onRetry={loadOverview} />
        </section>
      )}

      {/* 5. Charts & Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8">

        {/* Season-wise performance and trends */}
        <section aria-label="Season History" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-4 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h3 className="text-base sm:text-lg font-bold text-[#F6F6F3] flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[#D9B15F]" />
                Season-wise Performance &amp; Trends
              </h3>
              <p className="text-xs text-[#B9B9B3] mt-0.5">Win %, run rate and economy for each season · {scopeLabel}</p>
            </div>
            {overviewReady && teamOverview && (
              <span className="text-xs px-2.5 py-1 rounded-full bg-[#1A1B1F] text-[#D9B15F] border border-[#D9B15F]/20 font-semibold whitespace-nowrap">
                {plural(teamOverview.season_history.length, 'season')}
              </span>
            )}
          </div>

          {overviewReady && teamOverview ? (
            teamOverview.season_history.length === 0 ? (
              <SectionState loading={false} error={null} onRetry={loadOverview} />
            ) : (
              <Tabs
                label="Season view"
                idPrefix="team-season"
                tabs={[{ id: 'win', label: 'Win %' }, { id: 'rates', label: 'Run rate vs economy' }, { id: 'table', label: 'Table' }]}
                active={seasonView}
                onChange={setSeasonView}
              >
                {seasonView === 'table' ? (
                  <DataTable
                    caption={`Season-wise performance, ${scopeLabel.toLowerCase()}`}
                    columns={seasonColumns(stateText)}
                    rows={teamOverview.season_history}
                    rowKey={r => r.season}
                    maxHeight="max-h-72"
                  />
                ) : (
                  <div className="h-64 sm:h-72 w-full pt-2" role="img"
                    aria-label={seasonView === 'win'
                      ? `Win % by season: ${teamOverview.season_history.map(s => `${s.season} ${s.win_pct ?? 'none'}`).join(', ')}`
                      : `Run rate and economy by season: ${teamOverview.season_history.map(s => `${s.season} ${s.run_rate ?? 'none'} / ${s.economy ?? 'none'}`).join(', ')}`}>
                    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                      {seasonView === 'win' ? (
                        <BarChart data={teamOverview.season_history}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#26272B" vertical={false} />
                          <XAxis dataKey="season" stroke="#8E8E88" fontSize={11} tickLine={false} />
                          <YAxis stroke="#8E8E88" fontSize={11} domain={[0, 100]} unit="%" tickLine={false} />
                          <Tooltip {...CHART_TOOLTIP} formatter={(val: any) => [fmtPct(val) ?? '—', 'Win %']} />
                          <Bar dataKey="win_pct" fill="#D9B15F" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      ) : (
                        <LineChart data={teamOverview.season_history}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#26272B" vertical={false} />
                          <XAxis dataKey="season" stroke="#8E8E88" fontSize={11} tickLine={false} />
                          <YAxis stroke="#8E8E88" fontSize={11} tickLine={false} domain={['auto', 'auto']} />
                          <Tooltip {...CHART_TOOLTIP} formatter={(val: any, name: any) => [fmtRate(val) ?? '—', name]} />
                          <Legend wrapperStyle={{ fontSize: 11, color: '#B9B9B3' }} />
                          <Line type="monotone" dataKey="run_rate" name="Run rate" stroke="#D9B15F" strokeWidth={2} dot={{ r: 2 }} />
                          <Line type="monotone" dataKey="economy" name="Economy (conceded)" stroke="#34D399" strokeWidth={2} dot={{ r: 2 }} />
                        </LineChart>
                      )}
                    </ResponsiveContainer>
                  </div>
                )}
              </Tabs>
            )
          ) : (
            <SectionState loading={loading} error={error} onRetry={loadOverview} className="h-64 sm:h-72" />
          )}
        </section>

        {/* Phase Scoring & Toss Analysis */}
        <section aria-label="Phase Scoring & Toss" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-6 min-w-0">
          <div>
            <h3 className="text-base sm:text-lg font-bold text-[#F6F6F3] flex items-center gap-2">
              <Flame className="w-4 h-4 text-[#D9B15F]" />
              Phase Scoring &amp; Conceding
            </h3>
            <p className="text-xs text-[#B9B9B3] mt-0.5">Runs per 6 legal balls when batting and when bowling, by phase · {scopeLabel}</p>
          </div>

          {overviewReady && teamOverview ? (
          <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {teamOverview.phases.map(p => (
              <div key={p.phase} className="bg-[#1A1B1F] border border-[#D9B15F]/15 rounded-xl p-3 space-y-2">
                <span className="text-[10px] uppercase font-bold text-[#B9B9B3]">{p.label}</span>
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[11px] text-[#B9B9B3]">Scored</span>
                  <span className="text-lg font-extrabold text-[#D9B15F]"><Stat value={fmtRate(p.batting_run_rate)} reason={stateText(p.batting_run_rate_state)} /></span>
                </div>
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[11px] text-[#B9B9B3]">Conceded</span>
                  <span className="text-lg font-extrabold text-emerald-400"><Stat value={fmtRate(p.economy)} reason={stateText(p.economy_state)} /></span>
                </div>
                <p className="text-[10px] text-[#8E8E88]">
                  Wickets lost {fmtCount(p.wickets_lost)} &middot; taken {fmtCount(p.wickets_taken)}
                </p>
              </div>
            ))}
          </div>

          <div className="border-t border-[#D9B15F]/15 pt-4 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#B9B9B3]">
              Toss Decisions &amp; Results
            </h4>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-[#1A1B1F] p-3 rounded-lg border border-[#D9B15F]/15">
                <span className="text-[#B9B9B3] block">Chose to field</span>
                <span className="font-extrabold text-[#F6F6F3]">
                  {plural(teamOverview.toss_stats.elected_to_field, 'toss', 'tosses')} (<Stat value={fmtShare(teamOverview.toss_stats.elected_to_field, teamOverview.toss_stats.tosses_won)} reason="No toss won in this selection" />)
                </span>
              </div>
              <div className="bg-[#1A1B1F] p-3 rounded-lg border border-[#D9B15F]/15">
                <span className="text-[#B9B9B3] block">Chose to bat</span>
                <span className="font-extrabold text-[#F6F6F3]">
                  {plural(teamOverview.toss_stats.elected_to_bat, 'toss', 'tosses')} (<Stat value={fmtShare(teamOverview.toss_stats.elected_to_bat, teamOverview.toss_stats.tosses_won)} reason="No toss won in this selection" />)
                </span>
              </div>
            </div>
            <DataTable
              caption={`Results after winning the toss, ${scopeLabel.toLowerCase()}, with the league comparison`}
              columns={tossColumns(stateText)}
              rows={[
                { label: `${currentTeam?.short_name ?? 'Team'}: won the toss`, r: teamOverview.toss_stats.after_winning_toss },
                { label: '… and chose to bat', r: teamOverview.toss_stats.chose_to_bat },
                { label: '… and chose to field', r: teamOverview.toss_stats.chose_to_field },
                { label: `${teamOverview.toss_stats.league.label}: toss winners`, r: teamOverview.toss_stats.league.after_winning_toss },
                { label: '… chose to bat', r: teamOverview.toss_stats.league.chose_to_bat },
                { label: '… chose to field', r: teamOverview.toss_stats.league.chose_to_field },
              ]}
              rowKey={row => row.label}
            />
          </div>
          </>
          ) : (
            <SectionState loading={loading} error={error} onRetry={loadOverview} />
          )}
        </section>
      </div>

      {/* 6. Venue Breakdown Table */}
      <section aria-label="Venue Breakdown" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base sm:text-lg font-bold text-[#F6F6F3] flex items-center gap-2">
              <MapPin className="w-4 h-4 text-[#D9B15F]" />
              Venue Records
            </h3>
            <p className="text-xs text-[#B9B9B3] mt-0.5" aria-live="polite">
              {venues
                ? `${plural(venues.venues_shown, 'venue')} of ${venues.venues_total} with at least ${plural(venues.min_matches, 'match', 'matches')} · ${plural(venues.matches_shown, 'match', 'matches')} · ${scopeLabel}`
                : `Venues with at least ${plural(venueMinimum, 'match', 'matches')} · ${scopeLabel}`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="venue-minimum" className="text-xs font-semibold text-[#B9B9B3]">Minimum matches:</label>
            <select
              id="venue-minimum"
              value={venueMinimum}
              onChange={e => setVenueMinimum(Number(e.target.value))}
              className={`bg-[#1D1E22] border border-[#D9B15F]/40 text-[#F6F6F3] text-xs font-bold rounded-lg px-3 py-1.5 cursor-pointer ${FOCUS_RING}`}
            >
              {VENUE_MINIMUMS.map(n => <option key={n} value={n}>{n === 1 ? 'Any' : n}</option>)}
            </select>
          </div>
        </div>

        {venuesLoading || venuesError || !venues ? (
          <SectionState loading={venuesLoading} error={venuesError} onRetry={loadVenues} />
        ) : venues.venues.length === 0 ? (
          <p className="p-6 text-center text-xs text-[#B9B9B3]">
            No venue has {plural(venues.min_matches, 'match', 'matches')} or more in this selection; choose a lower minimum.
          </p>
        ) : (
          <DataTable
            caption={`Venue records, ${scopeLabel.toLowerCase()}, minimum ${venues.min_matches} matches`}
            columns={resultColumns<TeamVenueRecord>({ header: 'Venue', align: 'left', className: 'whitespace-normal min-w-[10rem]', cell: v => v.venue }, stateText)}
            rows={venues.venues}
            rowKey={v => v.venue}
            maxHeight="max-h-96"
          />
        )}
      </section>

      {/* 7. Record against every opponent */}
      <section aria-label="Opponent Records" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-4">
        <div>
          <h3 className="text-base sm:text-lg font-bold text-[#F6F6F3] flex items-center gap-2">
            <Users className="w-4 h-4 text-[#D9B15F]" />
            Record Against Every Opponent
          </h3>
          <p className="text-xs text-[#B9B9B3] mt-0.5">Same result rules as above · {scopeLabel}</p>
        </div>
        {overviewReady && teamOverview ? (
          <DataTable
            caption={`Record against every opponent, ${scopeLabel.toLowerCase()}`}
            columns={resultColumns<TeamOpponentRecord>({ header: 'Opponent', align: 'left', className: 'whitespace-normal min-w-[9rem]', cell: o => `${o.opponent} (${o.opponent_short_name})` }, stateText)}
            rows={teamOverview.opponents}
            rowKey={o => o.opponent}
            maxHeight="max-h-96"
          />
        ) : (
          <SectionState loading={loading} error={error} onRetry={loadOverview} />
        )}
      </section>

      {/* 8. Head-to-Head Comparison Tool */}
      <section aria-label="Head-to-Head Comparison" className="bg-[#151619] border border-[#D9B15F]/30 rounded-2xl p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#D9B15F]/20">
          <div>
            <div className="flex items-center gap-2">
              <Swords className="w-5 h-5 text-[#D9B15F]" />
              <h3 className="text-xl sm:text-2xl font-black text-[#F6F6F3]">
                Head-to-Head Franchise Rivalry
              </h3>
            </div>
            <p className="text-xs sm:text-sm text-[#B9B9B3] mt-1">
              Every meeting with the selected opponent · {scopeLabel}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <label htmlFor="h2h-opponent" className="text-xs font-semibold text-[#B9B9B3]">vs Opponent:</label>
            <select
              id="h2h-opponent"
              value={opponentId}
              onChange={e => setOpponentId(e.target.value)}
              className={`bg-[#1D1E22] border border-[#D9B15F]/40 text-[#F6F6F3] text-xs font-bold rounded-xl px-4 py-2 cursor-pointer max-w-[16rem] ${FOCUS_RING}`}
            >
              {opponentOptions.map(opp => (
                <option key={opp.id} value={opp.id}>
                  {opp.name} ({opp.short_name})
                </option>
              ))}
            </select>
          </div>
        </div>

        {h2hLoading ? (
          <SectionState loading error={null} onRetry={loadH2H} />
        ) : h2h ? (
          h2h.total_matches === 0 ? (
            <p className="p-6 text-center text-xs text-[#B9B9B3]">
              {h2h.team1.name} and {h2h.team2.name} did not meet in this selection.
            </p>
          ) : (
          <div className="space-y-6">
            {/* Visual Head-to-Head Bar */}
            <div className="bg-[#1A1B1F] border border-[#D9B15F]/20 rounded-xl p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-sm sm:text-base font-extrabold text-[#F6F6F3]">
                <div className="flex items-center gap-2">
                  <span className="w-3.5 h-3.5 rounded-full flex-shrink-0" style={{ backgroundColor: h2h.team1.primary_color }} />
                  <span>{h2h.team1.name}: {plural(h2h.team1_wins, 'win')}</span>
                </div>
                <span className="text-xs text-[#B9B9B3] uppercase tracking-wider font-semibold">
                  {plural(h2h.total_matches, 'match', 'matches')}
                </span>
                <div className="flex items-center gap-2">
                  <span>{h2h.team2.name}: {plural(h2h.team2_wins, 'win')}</span>
                  <span className="w-3.5 h-3.5 rounded-full flex-shrink-0" style={{ backgroundColor: h2h.team2.primary_color }} />
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full h-4 bg-[#101114] rounded-full overflow-hidden flex" role="img"
                aria-label={`${h2h.team1.name} ${h2h.team1_wins} wins, ${h2h.team2.name} ${h2h.team2_wins} wins, ${h2h.total_matches} matches`}>
                <div className="h-full transition-all duration-500"
                  style={{ width: `${(h2h.team1_wins / h2h.total_matches) * 100}%`, backgroundColor: h2h.team1.primary_color }} />
                <div className="h-full transition-all duration-500"
                  style={{ width: `${(h2h.team2_wins / h2h.total_matches) * 100}%`, backgroundColor: h2h.team2.primary_color }} />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-2">
                <H2HStat label={`${h2h.team1.short_name} win %`} value={<Stat value={fmtPct(h2h.team1_win_pct)} reason="Every meeting was a no result" />} note={`${h2h.team1_wins} / ${h2h.win_pct_denominator}`} />
                <H2HStat label={`${h2h.team2.short_name} win %`} value={<Stat value={fmtPct(h2h.team2_win_pct)} reason="Every meeting was a no result" />} note={`${h2h.team2_wins} / ${h2h.win_pct_denominator}`} />
                <H2HStat label="Ties (Super Over)" value={fmtCount(h2h.ties_super_overs)}
                  note={h2h.ties_super_overs ? `${h2h.team1.short_name} ${h2h.team1_super_over_wins} · ${h2h.team2.short_name} ${h2h.team2_super_over_wins}${h2h.unresolved_ties ? ` · unresolved ${h2h.unresolved_ties}` : ''}` : 'None'} />
                <H2HStat label="No results" value={fmtCount(h2h.no_results)} note="Excluded from win %" />
                <H2HStat label={`${h2h.team1.short_name} batting first wins`} value={fmtCount(h2h.team1_batting_first_wins)} />
                <H2HStat label={`${h2h.team1.short_name} chasing wins`} value={fmtCount(h2h.team1_chasing_wins)} />
                <H2HStat label={`${h2h.team2.short_name} batting first wins`} value={fmtCount(h2h.team2_batting_first_wins)} />
                <H2HStat label={`${h2h.team2.short_name} chasing wins`} value={fmtCount(h2h.team2_chasing_wins)} />
              </div>
            </div>

            {/* Meetings List */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#B9B9B3]">
                Meetings, most recent first ({plural(h2h.recent_meetings.length, 'match', 'matches')})
              </h4>
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1" role="region" aria-label="Head-to-head meetings" tabIndex={0}>
                {h2h.recent_meetings.map(m => (
                  <div
                    key={m.match_id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-xl bg-[#1A1B1F] border border-[#D9B15F]/15 gap-2 text-xs"
                  >
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span className="font-mono text-[#D9B15F] font-bold">{m.season}</span>
                      <span className="text-[#B9B9B3]">{m.date}</span>
                      <span className="text-[#F6F6F3] font-medium">{m.venue}</span>
                    </div>
                    <div className="sm:text-right">
                      <span className="font-semibold text-[#F6F6F3]">{m.result_text}</span>
                      <span className="block text-[11px] text-[#8E8E88]">{m.margin_or_summary.split(' · ')[0]}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          )
        ) : (
          <SectionState loading={false} error={h2hError} onRetry={loadH2H} />
        )}
      </section>

      {/* 9. Definitions */}
      {teamOverview && (
        <details className="group bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5">
          <summary className={`cursor-pointer list-none flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#D9B15F] rounded ${FOCUS_RING}`}>
            <BookOpen className="w-4 h-4" />
            Definitions
            <span className="ml-auto text-[10px] font-semibold normal-case tracking-normal text-[#8E8E88] group-open:hidden">Show how every number is counted</span>
          </summary>
          <dl className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-xs">
            {Object.entries(teamOverview.definitions).map(([key, text]) => (
              <div key={key}>
                <dt className="font-semibold text-[#F6F6F3]">{DEFINITION_LABELS[key] ?? key}</dt>
                <dd className="text-[#B9B9B3]">{text}</dd>
              </div>
            ))}
            {Object.entries(teamOverview.state_definitions).map(([key, text]) => (
              <div key={key}>
                <dt className="font-semibold text-[#F6F6F3]">&ldquo;—&rdquo; ({key.replace(/_/g, ' ')})</dt>
                <dd className="text-[#B9B9B3]">{text}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}

    </div>
  );
};

const DEFINITION_LABELS: Record<string, string> = {
  won: 'Won', lost: 'Lost', super_over: 'Super Over results', tied: 'Tied', no_result: 'No result',
  win_pct: 'Win %', innings_order: 'Batting first / chasing', runs_wickets: 'Runs and wickets',
  phases: 'Phases', run_rate: 'Run rate', economy: 'Economy (conceded)', trends: 'Season trends',
  league_toss: 'League toss comparison', toss: 'Toss results', franchises: 'Franchise names',
  venues: 'Venues', season_filter: 'Season filter',
};

const KpiCard: React.FC<{ label: string; value: React.ReactNode; note: string; tone?: string; highlight?: boolean }> = ({ label, value, note, tone = 'text-[#F6F6F3]', highlight = false }) => (
  <div className={`${highlight ? 'bg-[#1D1E22] border-[#D9B15F]/40 shadow-sm' : 'bg-[#1A1B1F] border-[#D9B15F]/15'} border rounded-xl p-4`}>
    <span className={`text-[11px] uppercase tracking-wider font-semibold ${highlight ? 'text-[#D9B15F]' : 'text-[#B9B9B3]'}`}>{label}</span>
    <p className={`text-2xl sm:text-3xl font-extrabold mt-1 ${highlight ? 'text-[#D9B15F]' : tone}`}>{value}</p>
    <p className="text-[10px] text-[#B9B9B3] mt-1">{note}</p>
  </div>
);

const TotalCard: React.FC<{ label: string; value: React.ReactNode; icon?: React.ReactNode; tone?: string }> = ({ label, value, icon, tone = 'text-[#F6F6F3]' }) => (
  <div className="bg-[#121316] border border-[#D9B15F]/10 rounded-xl p-3 flex items-center justify-between gap-2">
    <div>
      <span className="text-[10px] uppercase font-bold text-[#B9B9B3]">{label}</span>
      <p className={`text-lg font-black ${tone}`}>{value}</p>
    </div>
    {icon}
  </div>
);

const H2HStat: React.FC<{ label: string; value: React.ReactNode; note?: string }> = ({ label, value, note }) => (
  <div className="bg-[#101114] p-3 rounded-lg border border-[#D9B15F]/10">
    <span className="text-[#B9B9B3]">{label}</span>
    <p className="font-extrabold text-[#F6F6F3] text-sm mt-0.5">{value}</p>
    {note && <p className="text-[10px] text-[#8E8E88]">{note}</p>}
  </div>
);

type StateText = (state: string | null) => string | undefined;

/** Played, won, lost, tied, no result and win % with its denominator, after a first column. */
function resultColumns<T extends TeamResultSummary>(first: Column<T>, stateText: StateText): Column<T>[] {
  return [
    first,
    { header: 'P', title: 'Matches', cell: r => fmtCount(r.played) },
    { header: 'W', title: 'Won (Super Over wins included)', cell: r => <span className="text-emerald-400 font-semibold">{fmtCount(r.wins)}</span> },
    { header: 'L', title: 'Lost (Super Over losses included)', cell: r => <span className="text-rose-400">{fmtCount(r.losses)}</span> },
    { header: 'T', title: 'Ties with no Super Over result', cell: r => fmtCount(r.ties) },
    { header: 'NR', title: 'No result', cell: r => fmtCount(r.no_results) },
    {
      header: 'Win %', title: 'Wins / (matches − no results)', align: 'right',
      cell: r => (
        <span className="font-extrabold text-[#D9B15F]">
          <Stat value={fmtPct(r.win_pct)} reason={stateText(r.win_pct_state)} />
          <span className="block text-[10px] font-normal text-[#8E8E88]">{fmtCount(r.wins)} / {fmtCount(r.win_pct_denominator)}</span>
        </span>
      ),
    },
  ];
}

const seasonColumns = (stateText: StateText): Column<TeamSeasonRecord>[] => [
  ...resultColumns<TeamSeasonRecord>({ header: 'Season', cell: s => s.season }, stateText),
  { header: 'Runs / inn', title: 'Runs scored per innings batted', cell: s => <Stat value={fmtRate(s.runs_per_innings)} reason="No innings batted" /> },
  { header: 'Run rate', cell: s => <Stat value={fmtRate(s.run_rate)} reason={stateText(s.run_rate_state)} /> },
  { header: 'Economy', title: 'Runs conceded per 6 legal balls', cell: s => <Stat value={fmtRate(s.economy)} reason={stateText(s.economy_state)} /> },
];

interface TossRow { label: string; r: TeamResultSummary }

const tossColumns = (stateText: StateText): Column<TossRow>[] => [
  { header: 'Toss', align: 'left', className: 'whitespace-normal min-w-[9rem]', cell: row => row.label },
  { header: 'P', title: 'Matches', cell: row => fmtCount(row.r.played) },
  { header: 'W', title: 'Won', cell: row => fmtCount(row.r.wins) },
  { header: 'L', title: 'Lost', cell: row => fmtCount(row.r.losses) },
  {
    header: 'Win %', title: 'Wins / (matches − no results)', align: 'right',
    cell: row => (
      <span className="font-bold text-[#D9B15F]">
        <Stat value={fmtPct(row.r.win_pct)} reason={stateText(row.r.win_pct_state)} />{' '}
        <span className="text-[10px] font-normal text-[#8E8E88]">{fmtCount(row.r.wins)} / {fmtCount(row.r.win_pct_denominator)}</span>
      </span>
    ),
  },
];

interface SectionStateProps {
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  className?: string;
}

// Loading / failed / no-data placeholder for a section, so no number is shown without verified data
const SectionState: React.FC<SectionStateProps> = ({ loading, error, onRetry, className = '' }) => {
  let body: React.ReactNode;
  if (loading) {
    body = (
      <>
        <Loader2 className="w-6 h-6 text-[#D9B15F] animate-spin" />
        <p className="text-xs font-semibold text-[#F6F6F3]">Loading verified franchise records...</p>
      </>
    );
  } else if (error) {
    body = (
      <>
        <AlertCircle className="w-5 h-5 text-red-400" />
        <p className="text-xs font-semibold text-red-200">Unable to load this section</p>
        <p className="text-[11px] text-red-300/75 max-w-sm">{error}</p>
        <button
          onClick={onRetry}
          className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#2A1B1E] hover:bg-[#3A2227] text-red-200 border border-red-500/40 transition-colors ${FOCUS_RING}`}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry</span>
        </button>
      </>
    );
  } else {
    body = (
      <>
        <div className="w-9 h-9 rounded-xl bg-black/50 border border-[#D9B15F]/25 flex items-center justify-center text-[#D9B15F] shadow-gold-pill">
          <Database className="w-4 h-4" />
        </div>
        <p className="text-xs font-semibold text-[#F6F6F3]">No verified data available</p>
      </>
    );
  }
  return (
    <div className={`flex flex-col items-center justify-center text-center gap-2 py-8 ${className}`} role={error ? 'alert' : undefined}>
      {body}
    </div>
  );
};
