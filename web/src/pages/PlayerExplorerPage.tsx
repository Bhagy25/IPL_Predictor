import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  User,
  Search,
  Filter,
  ArrowUpDown,
  TrendingUp,
  Award,
  Calendar,
  AlertCircle,
  RefreshCw,
  Loader2,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  Flame,
  Shield,
} from 'lucide-react';
import { DirectoryCounts, PlayerListItem, PlayerProfileResponse } from '../types';
import { fetchPlayers, fetchPlayerOverview } from '../api/players';

// Counts come from the API's directory_counts, never from fixed numbers
const ROLE_FILTERS: { id: string; label: string; countKey?: keyof DirectoryCounts }[] = [
  { id: 'all', label: 'All Players', countKey: 'all' },
  { id: 'batters', label: 'Batters', countKey: 'batters' },
  { id: 'bowlers', label: 'Bowlers', countKey: 'bowlers' },
  { id: 'all-rounders', label: 'All-Rounders' },
];

// Same rule as the API's role definition (canonical_data.derive_role)
const ROLE_RULE =
  'Role derived from IPL playing record: bowls regularly = bowled in at least 50% of matches with 12+ legal balls per bowling innings; ' +
  'bats regularly = batted in at least 50% of matches facing 8+ balls per innings; both = All-Rounder.';

const EXPERIENCE_FILTERS = [
  { id: 'all', label: 'All Tiers' },
  { id: 'leaderboard_only', label: '40+ Innings' },
  { id: 'veteran', label: 'Veterans (60+)' },
  { id: 'experienced', label: 'Experienced (31–60)' },
  { id: 'regular', label: 'Regular (11–30)' },
  { id: 'emerging', label: 'Emerging (1–10)' },
];

const SORT_OPTIONS = [
  { id: 'runs', label: 'Most Runs' },
  { id: 'wickets', label: 'Most Wickets' },
  { id: 'batting_avg', label: 'Best Batting Avg' },
  { id: 'bowling_avg', label: 'Best Bowling Avg' },
  { id: 'economy', label: 'Best Economy Rate' },
  { id: 'innings', label: 'Most Appearances' },
  { id: 'strike_rate', label: 'Highest Strike Rate' },
];

export const PlayerExplorerPage: React.FC = () => {
  // Query parameters state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedQuery, setDebouncedQuery] = useState<string>('');
  const [selectedRole, setSelectedRole] = useState<string>('all');
  const [selectedTier, setSelectedTier] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('runs');
  const [page, setPage] = useState<number>(1);
  const pageSize = 15;

  // Data state
  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [directoryCounts, setDirectoryCounts] = useState<DirectoryCounts | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string>('ba607b88'); // Default to V Kohli
  const [profile, setProfile] = useState<PlayerProfileResponse | null>(null);

  // Loading and error states
  const [listLoading, setListLoading] = useState<boolean>(true);
  const [profileLoading, setProfileLoading] = useState<boolean>(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Only the latest request may update state, so a slow earlier response cannot overwrite it
  const listRequest = useRef(0);
  const profileRequest = useRef(0);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load players list
  const loadPlayers = useCallback(async () => {
    const requestId = ++listRequest.current;
    setListLoading(true);
    setError(null);
    try {
      const res = await fetchPlayers({
        query: debouncedQuery || undefined,
        role: selectedRole === 'all' ? undefined : selectedRole,
        experience_filter: selectedTier === 'all' ? undefined : selectedTier,
        page,
        page_size: pageSize,
        sort_by: sortBy,
      });
      if (requestId !== listRequest.current) return;
      setPlayers(res.players);
      setTotalCount(res.total_count);
      if (res.directory_counts) setDirectoryCounts(res.directory_counts);

      // Auto-select first player if current selected is not in list
      const activeId = selectedPlayerId;
      if (res.players.length > 0 && !res.players.some(p => (p.player_id || p.batter_id) === activeId)) {
        setSelectedPlayerId(res.players[0].player_id || res.players[0].batter_id);
      }
    } catch (err: any) {
      if (requestId === listRequest.current) setError(err?.message || 'Failed to load players directory');
    } finally {
      if (requestId === listRequest.current) setListLoading(false);
    }
  }, [debouncedQuery, selectedRole, selectedTier, page, sortBy, selectedPlayerId]);

  useEffect(() => {
    loadPlayers();
  }, [loadPlayers]);

  // Load selected player profile
  const loadProfile = useCallback(async () => {
    if (!selectedPlayerId) return;
    const requestId = ++profileRequest.current;
    setProfileLoading(true);
    setProfileError(null);
    try {
      const data = await fetchPlayerOverview(selectedPlayerId);
      if (requestId === profileRequest.current) setProfile(data);
    } catch (err: any) {
      if (requestId === profileRequest.current) {
        // Never leave the previous player's figures on screen after a failure
        setProfile(null);
        setProfileError(err?.message || 'Failed to load player profile');
      }
    } finally {
      if (requestId === profileRequest.current) setProfileLoading(false);
    }
  }, [selectedPlayerId]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const totalPages = Math.ceil(totalCount / pageSize);

  const batting = profile?.career_batting;
  const bowling = profile?.career_bowling;

  return (
    <div className="space-y-10 sm:space-y-12 max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-16">
      
      {/* 1. Page Header */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#D9B15F]/20">
          <div>
            <div className="flex items-center gap-3">
              <span className="w-1.5 h-6 bg-[#D9B15F] rounded-full inline-block" />
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#F6F6F3]">
                Player Explorer
              </h1>
            </div>
            <p className="text-xs sm:text-sm text-[#B9B9B3] mt-1 ml-4 sm:ml-5">
              Complete 2008–2026 IPL player directory: verified career batting &amp; bowling statistics, chronological match logs, and split records.
            </p>
          </div>

          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#151619] border border-[#D9B15F]/30 text-xs font-medium text-[#D9B15F] self-start sm:self-center shadow-gold-pill">
            <User className="w-3.5 h-3.5 text-[#D9B15F]" />
            <span>{directoryCounts ? directoryCounts.all.toLocaleString() : '…'} Verified Players &middot; 2008–2026 History</span>
          </div>
        </div>

        {error && (
          <div className="bg-[#1C1517] border border-red-500/30 rounded-2xl p-4 sm:p-5 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-xs sm:text-sm font-semibold text-red-200">
                {error}
              </p>
            </div>
            <button
              onClick={loadPlayers}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#2A1B1E] hover:bg-[#3A2227] text-red-200 border border-red-500/40"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        )}
      </div>

      {/* 2. Search & Filter Bar */}
      <section aria-label="Player Filters" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-[#D9B15F] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder={`Search ${directoryCounts ? `all ${directoryCounts.all.toLocaleString()} ` : ''}players by name or ID (e.g. Kohli, Bumrah, Narine)...`}
              className="w-full bg-[#101114] border border-[#D9B15F]/30 rounded-xl pl-10 pr-4 py-2 text-xs sm:text-sm text-[#F6F6F3] placeholder-[#8E8E88] focus:outline-none focus:ring-1 focus:ring-[#D9B15F]"
            />
          </div>

          {/* Sort Selector */}
          <div className="flex items-center gap-2 self-start md:self-center">
            <ArrowUpDown className="w-3.5 h-3.5 text-[#B9B9B3]" />
            <span className="text-xs text-[#B9B9B3]">Sort:</span>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              className="bg-[#101114] border border-[#D9B15F]/30 text-[#F6F6F3] text-xs font-semibold rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#D9B15F] cursor-pointer"
            >
              {SORT_OPTIONS.map(opt => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Role & Experience Filter Pills */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-[#D9B15F]/10">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-semibold text-[#8E8E88] uppercase tracking-wider mr-1 flex items-center gap-1">
              Role:
            </span>
            {ROLE_FILTERS.map(f => (
              <button
                key={f.id}
                onClick={() => {
                  setSelectedRole(f.id);
                  setPage(1);
                }}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                  selectedRole === f.id
                    ? 'bg-[#D9B15F] text-[#0D0E10] shadow-sm'
                    : 'bg-[#101114] text-[#B9B9B3] hover:text-[#F6F6F3] border border-[#D9B15F]/15'
                }`}
              >
                {f.label}
                {f.countKey && directoryCounts ? ` (${directoryCounts[f.countKey].toLocaleString()})` : ''}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-semibold text-[#8E8E88] uppercase tracking-wider mr-1 flex items-center gap-1">
              <Filter className="w-3 h-3 text-[#D9B15F]" /> Tier:
            </span>
            {EXPERIENCE_FILTERS.map(f => (
              <button
                key={f.id}
                onClick={() => {
                  setSelectedTier(f.id);
                  setPage(1);
                }}
                className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                  selectedTier === f.id
                    ? 'bg-[#D9B15F]/20 text-[#D9B15F] border border-[#D9B15F]/40'
                    : 'bg-[#101114] text-[#8E8E88] hover:text-[#F6F6F3] border border-white/5'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 3. Main Master-Detail Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 items-start">
        
        {/* Left Column: Player Master List (4 Cols) */}
        <section aria-label="Player Directory" className="lg:col-span-4 bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#D9B15F]/15">
            <span className="text-xs font-bold uppercase tracking-wider text-[#B9B9B3]">
              Directory ({totalCount} players)
            </span>
            <span className="text-[11px] text-[#D9B15F] font-mono">
              Page {page} of {Math.max(1, totalPages)}
            </span>
          </div>

          {listLoading ? (
            <div className="p-10 text-center flex flex-col items-center justify-center gap-2 text-xs text-[#B9B9B3]">
              <Loader2 className="w-5 h-5 text-[#D9B15F] animate-spin" />
              <span>Fetching player registry...</span>
            </div>
          ) : players.length === 0 ? (
            <div className="p-8 text-center text-xs text-[#B9B9B3]">
              No players found matching &ldquo;{searchQuery}&rdquo;.
            </div>
          ) : (
            <div className="space-y-2 max-h-[720px] overflow-y-auto pr-1">
              {players.map(p => {
                const pid = p.player_id || p.batter_id;
                const isSelected = pid === selectedPlayerId;
                return (
                  <button
                    key={pid}
                    onClick={() => setSelectedPlayerId(pid)}
                    className={`w-full text-left p-3 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-[#1D1E22] border-[#D9B15F] shadow-gold-pill'
                        : 'bg-[#101114] border-[#D9B15F]/15 hover:border-[#D9B15F]/35 hover:bg-[#16171B]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs sm:text-sm font-extrabold text-[#F6F6F3]">
                          {p.name}
                        </span>
                        {p.role && (
                          <span title={ROLE_RULE} className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                            p.role === 'All-Rounder'
                              ? 'bg-[#D9B15F]/15 text-[#D9B15F] border border-[#D9B15F]/30'
                              : p.role === 'Bowler'
                              ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-500/30'
                              : 'bg-zinc-800 text-zinc-300 border border-zinc-600/30'
                          }`}>
                            {p.role}
                          </span>
                        )}
                      </div>
                      <div className="text-right">
                        {p.total_runs > 0 && (
                          <span className="text-xs font-black text-[#D9B15F] block">
                            {p.total_runs.toLocaleString()} r
                          </span>
                        )}
                        {(p.wickets ?? 0) > 0 && (
                          <span className="text-[11px] font-bold text-emerald-400 block">
                            {p.wickets} wkt
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-[#B9B9B3] mt-1.5">
                      <span>
                        {p.batting_innings ?? p.innings} bat inn &middot; {p.bowling_innings ?? 0} bowl inn
                      </span>
                      <span className="text-[10px] text-[#8E8E88] font-mono">
                        {p.first_season && p.last_season ? `${p.first_season}–${p.last_season}` : '2008–2026'}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-3 border-t border-[#D9B15F]/15">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#101114] text-[#F6F6F3] border border-[#D9B15F]/20 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>

              <span className="text-xs text-[#B9B9B3]">
                {page} / {totalPages}
              </span>

              <button
                disabled={page >= totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#101114] text-[#F6F6F3] border border-[#D9B15F]/20 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </section>

        {/* Right Column: Player Profile Details (8 Cols) */}
        <section aria-label="Player Profile Detail" className="lg:col-span-8 space-y-6">
          {profileLoading ? (
            <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-16 text-center flex flex-col items-center justify-center gap-3 animate-pulse">
              <Loader2 className="w-8 h-8 text-[#D9B15F] animate-spin" />
              <p className="text-sm font-semibold text-[#F6F6F3]">Loading career profile &amp; match logs...</p>
            </div>
          ) : profile ? (
            <div className="space-y-6">
              
              {/* Profile Card Header */}
              <div className="bg-[#151619] border border-[#D9B15F]/30 rounded-2xl p-6 sm:p-7 space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#D9B15F]/15">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-2xl bg-[#1D1E22] border border-[#D9B15F]/40 flex items-center justify-center text-[#D9B15F] shadow-sm">
                      <User className="w-7 h-7" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2.5">
                        <h2 className="text-2xl sm:text-3xl font-black text-[#F6F6F3]">
                          {profile.name}
                        </h2>
                      </div>
                      <p className="text-xs text-[#B9B9B3] mt-1 flex flex-wrap items-center gap-2">
                        <span>Career: <strong className="text-[#F6F6F3]">{profile.first_season}–{profile.last_season}</strong></span>
                        <span>&middot;</span>
                        <span>Teams: <span className="text-[#D9B15F] font-semibold">{profile.teams?.join(', ') || 'IPL Franchise'}</span></span>
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {batting && (
                      <div className="bg-[#101114] border border-[#D9B15F]/20 rounded-xl px-3.5 py-2 text-right">
                        <span className="text-[10px] uppercase tracking-wider text-[#B9B9B3] font-semibold">Batting Avg</span>
                        <p className="text-lg font-black text-[#D9B15F]">{batting.average}</p>
                      </div>
                    )}
                    {bowling && (
                      <div className="bg-[#101114] border border-emerald-500/20 rounded-xl px-3.5 py-2 text-right">
                        <span className="text-[10px] uppercase tracking-wider text-[#B9B9B3] font-semibold">Bowling Econ</span>
                        <p className="text-lg font-black text-emerald-400">{bowling.economy_rate}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Dual Career Cards: Batting & Bowling */}
                <div className="space-y-4">
                  {/* Career Batting Card */}
                  <div className="bg-[#121316] border border-[#D9B15F]/20 rounded-xl p-4 sm:p-5 space-y-3">
                    <div className="flex items-center justify-between border-b border-[#D9B15F]/10 pb-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-[#D9B15F] flex items-center gap-2">
                        <Flame className="w-4 h-4 text-[#D9B15F]" />
                        Career Batting Figures (2008–2026)
                      </span>
                      {batting && (
                        <span className="text-[11px] text-[#B9B9B3]">
                          Highest Score: <strong className="text-[#F6F6F3] font-mono">{batting.highest_score}</strong>
                        </span>
                      )}
                    </div>

                    {batting ? (
                      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 pt-1">
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">Runs</span>
                          <p className="text-base font-black text-[#D9B15F]">{batting.runs.toLocaleString()}</p>
                        </div>
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">Innings</span>
                          <p className="text-base font-black text-[#F6F6F3]">{batting.innings}</p>
                        </div>
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">Average</span>
                          <p className="text-base font-black text-[#F6F6F3]">{batting.average}</p>
                        </div>
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">Strike Rate</span>
                          <p className="text-base font-black text-[#F6F6F3]">{batting.strike_rate}</p>
                        </div>
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">4s / 6s</span>
                          <p className="text-base font-black text-[#F6F6F3]">{batting.fours} / {batting.sixes}</p>
                        </div>
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">50s / 100s</span>
                          <p className="text-base font-black text-[#D9B15F]">{batting.scores_50_plus} / {batting.scores_100_plus}</p>
                        </div>
                      </div>
                    ) : (
                      <div className="p-3 text-center text-xs text-[#8E8E88] italic bg-[#17181C] rounded-lg">
                        Did not bat in official IPL matches (Pure Bowler).
                      </div>
                    )}
                  </div>

                  {/* Career Bowling Card */}
                  <div className="bg-[#121316] border border-emerald-500/20 rounded-xl p-4 sm:p-5 space-y-3">
                    <div className="flex items-center justify-between border-b border-emerald-500/10 pb-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-2">
                        <Shield className="w-4 h-4 text-emerald-400" />
                        Career Bowling Figures (2008–2026)
                      </span>
                      {bowling && (
                        <span className="text-[11px] text-[#B9B9B3]">
                          Best Bowling: <strong className="text-emerald-300 font-mono">{bowling.best_bowling}</strong>
                        </span>
                      )}
                    </div>

                    {bowling ? (
                      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 pt-1">
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">Wickets</span>
                          <p className="text-base font-black text-emerald-400">{bowling.wickets}</p>
                        </div>
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">Innings</span>
                          <p className="text-base font-black text-[#F6F6F3]">{bowling.innings}</p>
                        </div>
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">Overs Bowled</span>
                          <p className="text-base font-black text-[#F6F6F3]">{bowling.overs_bowled}</p>
                        </div>
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">Economy</span>
                          <p className="text-base font-black text-[#F6F6F3]">{bowling.economy_rate}</p>
                        </div>
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">Average</span>
                          <p className="text-base font-black text-[#F6F6F3]">{bowling.bowling_average ?? '—'}</p>
                        </div>
                        <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
                          <span className="text-[10px] uppercase text-[#8E8E88] font-bold">3w / 4w / 5w</span>
                          <p className="text-base font-black text-emerald-300">
                            {bowling.three_wicket_hauls} / {bowling.four_wicket_hauls} / {bowling.five_wicket_hauls}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="p-3 text-center text-xs text-[#8E8E88] italic bg-[#17181C] rounded-lg">
                        Did not bowl in official IPL matches (Pure Batter).
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Chronological Match Performance Logs Table */}
              <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-[#D9B15F]/15 gap-2">
                  <div>
                    <h3 className="text-base font-bold text-[#F6F6F3] flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-[#D9B15F]" />
                      Chronological Match-by-Match Logs (2008–2026)
                    </h3>
                    <p className="text-xs text-[#B9B9B3] mt-0.5">
                      Verified match appearances showing both Batting and Bowling performances
                    </p>
                  </div>
                  <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-[#101114] text-[#D9B15F] border border-[#D9B15F]/20 self-start sm:self-center">
                    {profile.recent_matches.length} matches logged
                  </span>
                </div>

                {profile.recent_matches.length === 0 ? (
                  <div className="p-8 text-center text-xs text-[#B9B9B3] bg-[#101114] rounded-xl border border-[#D9B15F]/10">
                    <ShieldAlert className="w-6 h-6 text-[#D9B15F] mx-auto mb-2 opacity-60" />
                    <span>No match logs recorded for this player.</span>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20">
                        <tr>
                          <th className="py-2.5 px-3">Date</th>
                          <th className="py-2.5 px-3">Season</th>
                          <th className="py-2.5 px-3">Opponent</th>
                          <th className="py-2.5 px-3">Venue</th>
                          <th className="py-2.5 px-3 text-center bg-[#17181C]">Bat Runs</th>
                          <th className="py-2.5 px-3 text-center bg-[#17181C]">Balls (4s/6s)</th>
                          <th className="py-2.5 px-3 text-center bg-[#17181C]">Dismissal</th>
                          <th className="py-2.5 px-3 text-center bg-[#151917]">Overs</th>
                          <th className="py-2.5 px-3 text-center bg-[#151917]">Wkts / Runs</th>
                          <th className="py-2.5 px-3 text-right bg-[#151917]">Economy</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#D9B15F]/10">
                        {profile.recent_matches.map((m: any) => (
                          <tr key={m.match_id} className="hover:bg-[#1A1B1F] transition-colors">
                            <td className="py-2.5 px-3 font-mono text-[#B9B9B3]">{m.date}</td>
                            <td className="py-2.5 px-3 text-[#F6F6F3] font-bold">{m.season}</td>
                            <td className="py-2.5 px-3 text-[#F6F6F3] font-medium">{m.opponent}</td>
                            <td className="py-2.5 px-3 text-[#B9B9B3] truncate max-w-[140px]">{m.venue}</td>
                            
                            {/* Batting Columns */}
                            <td className="py-2.5 px-3 text-center bg-[#17181C]">
                              {m.runs !== null && m.runs !== undefined ? (
                                <span className={`font-black ${m.runs >= 50 ? 'text-[#D9B15F]' : m.runs >= 30 ? 'text-amber-300' : 'text-[#F6F6F3]'}`}>
                                  {m.runs}
                                </span>
                              ) : (
                                <span className="text-[#666] italic">Did not bat</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-center bg-[#17181C] text-[#B9B9B3]">
                              {m.balls_faced !== null && m.balls_faced !== undefined ? (
                                <span>{m.balls_faced} ({m.fours}×4, {m.sixes}×6)</span>
                              ) : (
                                <span className="text-[#555]">—</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-center bg-[#17181C]">
                              {m.dismissal_status ? (
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                  m.dismissal_status === 'Not Out'
                                    ? 'bg-emerald-950/60 text-emerald-300'
                                    : m.dismissal_status === 'Out'
                                    ? 'bg-zinc-800 text-zinc-300'
                                    : 'text-[#666]'
                                }`}>
                                  {m.dismissal_status}
                                </span>
                              ) : (
                                <span className="text-[#555]">—</span>
                              )}
                            </td>

                            {/* Bowling Columns */}
                            <td className="py-2.5 px-3 text-center bg-[#151917] font-mono text-[#F6F6F3]">
                              {m.overs_bowled && m.overs_bowled !== 'Did not bowl' ? (
                                m.overs_bowled
                              ) : (
                                <span className="text-[#666] italic">Did not bowl</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-center bg-[#151917]">
                              {m.wickets !== null && m.wickets !== undefined ? (
                                <span className="font-bold text-emerald-400">
                                  {m.wickets} / {m.runs_conceded}
                                </span>
                              ) : (
                                <span className="text-[#555]">—</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-right bg-[#151917] font-mono text-[#D9B15F]">
                              {m.economy !== null && m.economy !== undefined ? m.economy.toFixed(2) : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Opposition & Venue Splits */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* Opposition Table */}
                <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-[#B9B9B3] flex items-center gap-1.5">
                    <Award className="w-3.5 h-3.5 text-[#D9B15F]" />
                    Performance by Opposition
                  </h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20">
                        <tr>
                          <th className="py-2 px-3">Opponent</th>
                          <th className="py-2 px-3 text-center">Inn</th>
                          <th className="py-2 px-3 text-center">Runs</th>
                          <th className="py-2 px-3 text-right">Avg</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#D9B15F]/10">
                        {(profile.vs_opponents || profile.opposition_splits || []).map((o: any) => (
                          <tr key={o.opponent} className="hover:bg-[#1A1B1F]">
                            <td className="py-2 px-3 font-medium text-[#F6F6F3]">{o.opponent}</td>
                            <td className="py-2 px-3 text-center text-[#B9B9B3]">{o.innings}</td>
                            <td className="py-2 px-3 text-center text-[#D9B15F] font-bold">{o.runs ?? o.total_runs}</td>
                            <td className="py-2 px-3 text-right font-mono text-[#F6F6F3]">{o.average ?? o.avg_runs}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Venues Table */}
                <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-[#B9B9B3] flex items-center gap-1.5">
                    <TrendingUp className="w-3.5 h-3.5 text-[#D9B15F]" />
                    Performance by Venue
                  </h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20">
                        <tr>
                          <th className="py-2 px-3">Stadium</th>
                          <th className="py-2 px-3 text-center">Inn</th>
                          <th className="py-2 px-3 text-center">Runs</th>
                          <th className="py-2 px-3 text-right">Avg</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#D9B15F]/10">
                        {(profile.at_venues || profile.venue_splits || []).map((v: any) => (
                          <tr key={v.venue} className="hover:bg-[#1A1B1F]">
                            <td className="py-2 px-3 font-medium text-[#F6F6F3] truncate max-w-[140px]">{v.venue}</td>
                            <td className="py-2 px-3 text-center text-[#B9B9B3]">{v.innings}</td>
                            <td className="py-2 px-3 text-center text-[#D9B15F] font-bold">{v.runs ?? v.total_runs}</td>
                            <td className="py-2 px-3 text-right font-mono text-[#F6F6F3]">{v.average ?? v.avg_runs}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>

              {/* Disclosures & Notes */}
              <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#D9B15F] flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#D9B15F]" />
                  Data Integrity Disclosures
                </h4>
                <ul className="list-disc list-inside text-xs text-[#B9B9B3] space-y-1">
                  <li>Full career directory encompasses all {directoryCounts ? directoryCounts.all.toLocaleString() : '…'} players with recorded appearances across 19 tournament editions (2008–2026).</li>
                  <li>Batting averages represent career runs divided by verified dismissals; players remaining undefeated throughout their career show total runs.</li>
                  <li>{ROLE_RULE}</li>
                  <li>Bowler statistics credit legal dismissals only (bowled, caught, lbw, stumped, hit wicket); run outs are strictly attributed to team fielding.</li>
                  <li>Overs bowled use standard cricket notation (e.g. 342.4 signifies 342 complete six-ball overs plus 4 balls).</li>
                </ul>
              </div>

            </div>
          ) : (
            <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-12 sm:p-16 text-center flex flex-col items-center justify-center gap-3">
              {profileError ? (
                <>
                  <AlertCircle className="w-7 h-7 text-red-400" />
                  <p className="text-sm font-semibold text-red-200">Unable to load this player profile</p>
                  <p className="text-xs text-red-300/75 max-w-md">{profileError}</p>
                  <button
                    onClick={loadProfile}
                    className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#2A1B1E] hover:bg-[#3A2227] text-red-200 border border-red-500/40"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Retry</span>
                  </button>
                </>
              ) : (
                <p className="text-sm font-semibold text-[#B9B9B3]">Select a player to view their career profile.</p>
              )}
            </div>
          )}
        </section>

      </div>
    </div>
  );
};
