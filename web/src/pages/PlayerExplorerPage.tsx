import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  User,
  Search,
  Filter,
  ArrowUpDown,
  AlertCircle,
  RefreshCw,
  Loader2,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { DirectoryCounts, PlayerListItem, PlayerProfileResponse } from '../types';
import { fetchPlayers, fetchPlayerOverview } from '../api/players';
import { BattingSection, BowlingSection, CareerSummary, DefinitionsDisclosure } from '../components/player/ProfileSections';
import { FOCUS_RING } from '../components/player/playerFormat';
import { MatchLog } from '../components/player/MatchLog';

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

const RoleBadge: React.FC<{ role?: string }> = ({ role }) =>
  role ? (
    <span title={ROLE_RULE} className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase cursor-help ${
      role === 'All-Rounder'
        ? 'bg-[#D9B15F]/15 text-[#D9B15F] border border-[#D9B15F]/30'
        : role === 'Bowler'
        ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-500/30'
        : 'bg-zinc-800 text-zinc-300 border border-zinc-600/30'
    }`}>
      {role}
    </span>
  ) : null;

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
  // null = full career; otherwise every number on the profile is for that season
  const [profileSeason, setProfileSeason] = useState<number | null>(null);
  // The selected player's seasons, from the full-career profile
  const [seasonOptions, setSeasonOptions] = useState<number[]>([]);
  // Directory roles seen so far, so the profile can show the badge for the selected player
  const [roleById, setRoleById] = useState<Record<string, string>>({});

  // Loading and error states
  const [listLoading, setListLoading] = useState<boolean>(true);
  const [profileLoading, setProfileLoading] = useState<boolean>(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Only the latest request may update state, so a slow earlier response cannot overwrite it
  const listRequest = useRef(0);
  const profileRequest = useRef(0);

  const selectPlayer = useCallback((pid: string) => {
    setSelectedPlayerId(pid);
    setProfileSeason(null);
    setSeasonOptions([]);
  }, []);

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
      setRoleById(prev => {
        const next = { ...prev };
        res.players.forEach(p => { if (p.role) next[p.player_id || p.batter_id] = p.role; });
        return next;
      });

      // Auto-select first player if current selected is not in list
      const activeId = selectedPlayerId;
      if (res.players.length > 0 && !res.players.some(p => (p.player_id || p.batter_id) === activeId)) {
        selectPlayer(res.players[0].player_id || res.players[0].batter_id);
      }
    } catch (err: any) {
      if (requestId === listRequest.current) setError(err?.message || 'Failed to load players directory');
    } finally {
      if (requestId === listRequest.current) setListLoading(false);
    }
  }, [debouncedQuery, selectedRole, selectedTier, page, sortBy, selectedPlayerId, selectPlayer]);

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
      const data = await fetchPlayerOverview(selectedPlayerId, profileSeason);
      if (requestId === profileRequest.current) {
        setProfile(data);
        if (profileSeason === null) setSeasonOptions(data.seasons_played);
      }
    } catch (err: any) {
      if (requestId === profileRequest.current) {
        // Never leave the previous player's figures on screen after a failure
        setProfile(null);
        setProfileError(err?.message || 'Failed to load player profile');
      }
    } finally {
      if (requestId === profileRequest.current) setProfileLoading(false);
    }
  }, [selectedPlayerId, profileSeason]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const totalPages = Math.ceil(totalCount / pageSize);

  const scopeLabel = profile?.season_filter != null
    ? `${profile.season_filter} season`
    : profile ? `Full career ${profile.first_season}–${profile.last_season}` : '';

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
                    onClick={() => selectPlayer(pid)}
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
                        <RoleBadge role={p.role} />
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
          {profileLoading && !profile ? (
            <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-16 text-center flex flex-col items-center justify-center gap-3 animate-pulse">
              <Loader2 className="w-8 h-8 text-[#D9B15F] animate-spin" />
              <p className="text-sm font-semibold text-[#F6F6F3]">Loading career profile &amp; match logs...</p>
            </div>
          ) : profile ? (
            <div className={`space-y-6 transition-opacity ${profileLoading ? 'opacity-60' : ''}`} aria-busy={profileLoading}>

              {/* Profile Card Header with the season selector */}
              <div className="bg-[#151619] border border-[#D9B15F]/30 rounded-2xl p-5 sm:p-7 space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-[#D9B15F]/15">
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-14 h-14 flex-shrink-0 rounded-2xl bg-[#1D1E22] border border-[#D9B15F]/40 flex items-center justify-center text-[#D9B15F] shadow-sm">
                      <User className="w-7 h-7" />
                    </div>
                    <div className="min-w-0">
                      <h2 className="text-2xl sm:text-3xl font-black text-[#F6F6F3] break-words">
                        {profile.name}
                      </h2>
                      {(profile.name_variants ?? []).some(n => n !== profile.name) && (
                        <p className="text-xs text-[#B9B9B3] mt-1">
                          Listed as: {(profile.name_variants ?? []).join(', ')}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5 sm:items-end">
                    <label htmlFor="profile-season" className="text-[10px] uppercase tracking-wider font-bold text-[#8E8E88]">
                      Showing
                    </label>
                    <select
                      id="profile-season"
                      value={profileSeason ?? 'career'}
                      disabled={profileLoading}
                      onChange={e => setProfileSeason(e.target.value === 'career' ? null : Number(e.target.value))}
                      className={`bg-[#101114] border border-[#D9B15F]/40 text-[#F6F6F3] text-xs font-semibold rounded-lg px-3 py-2 cursor-pointer ${FOCUS_RING}`}
                    >
                      <option value="career">Full career</option>
                      {seasonOptions.map(s => (
                        <option key={s} value={s}>{s} season</option>
                      ))}
                    </select>
                    <span
                      aria-live="polite"
                      className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${
                        profile.season_filter != null
                          ? 'bg-[#D9B15F] text-[#0D0E10] border-[#D9B15F]'
                          : 'bg-[#101114] text-[#D9B15F] border-[#D9B15F]/30'
                      }`}
                    >
                      {profileLoading ? 'Updating…' : `Every number below: ${scopeLabel.toLowerCase()}`}
                    </span>
                  </div>
                </div>

                <CareerSummary
                  profile={profile}
                  roleBadge={roleById[profile.player_id ?? ''] ? <RoleBadge role={roleById[profile.player_id ?? '']} /> : '…'}
                />
              </div>

              <BattingSection profile={profile} scopeLabel={scopeLabel} />
              <BowlingSection profile={profile} scopeLabel={scopeLabel} />

              <MatchLog
                key={`${profile.player_id}-${profile.season_filter ?? 'career'}`}
                playerId={profile.player_id ?? profile.batter_id}
                season={profile.season_filter}
                scopeLabel={scopeLabel}
              />

              <DefinitionsDisclosure profile={profile} />

              {/* Disclosures & Notes */}
              <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#D9B15F] flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#D9B15F]" />
                  Data Integrity Disclosures
                </h4>
                <ul className="list-disc list-inside text-xs text-[#B9B9B3] space-y-1">
                  <li>Full career directory encompasses all {directoryCounts ? directoryCounts.all.toLocaleString() : '…'} players with recorded appearances across 19 tournament editions (2008–2026).</li>
                  <li>Batting average is runs divided by dismissals; a player never dismissed has no average, shown as &ldquo;—&rdquo;.</li>
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
