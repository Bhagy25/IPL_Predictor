import React, { useEffect, useRef, useState } from 'react';
import { Legend, Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Loader2, Search, Users, X } from 'lucide-react';
import { EDAFiltersEcho, EDAPlayerComparisonResponse, PlayerListItem } from '../../types';
import { fetchPlayers } from '../../api/players';
import { fetchPlayerComparison } from '../../api/eda';
import { ChartFrame } from './ChartFrame';
import { DataTable } from '../player/ProfileSections';
import { FOCUS_RING, Stat } from '../player/playerFormat';
import { fmtCount, fmtRate } from '../../utils/format';

const MIN_PLAYERS = 2;
const MAX_PLAYERS = 4;
const LINE_COLORS = ['#D9B15F', '#60A5FA', '#FB7185', '#34D399'];

export interface PickedPlayer { id: string; name: string }

/**
 * Area 7: 2–4 players chosen by registry ID through the directory search, compared within the
 * season range of the filter bar. Team and venue filters do not apply (the API returns the note).
 */
export const PlayerComparison: React.FC<{
  filters: EDAFiltersEcho;
  picked: PickedPlayer[];
  onPickedChange: (players: PickedPlayer[]) => void;
}> = ({ filters, picked, onPickedChange }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<PlayerListItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [comparison, setComparison] = useState<EDAPlayerComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const requestId = useRef(0);

  // Directory search, debounced
  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) { setResults([]); return; }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setSearching(true);
      fetchPlayers({ query: q, page_size: 8 }, controller.signal)
        .then((res) => setResults(res.players))
        .catch(() => { if (!controller.signal.aborted) setResults([]); })
        .finally(() => { if (!controller.signal.aborted) setSearching(false); });
    }, 250);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [query]);

  const ids = picked.map((p) => p.id).join(',');
  useEffect(() => {
    if (picked.length < MIN_PLAYERS) { setComparison(null); setError(null); return; }
    const controller = new AbortController();
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    fetchPlayerComparison(picked.map((p) => p.id), {
      season_from: filters.season_from,
      season_to: filters.season_to,
      team: filters.team?.id,
      venue: filters.venue ?? undefined,
    }, controller.signal)
      .then((res) => { if (id === requestId.current) setComparison(res); })
      .catch((err) => { if (id === requestId.current && !controller.signal.aborted) { setComparison(null); setError(err?.message ?? 'Unable to load the comparison'); } })
      .finally(() => { if (id === requestId.current) setLoading(false); });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids, filters.season_from, filters.season_to, filters.team?.id, filters.venue, retry]);

  const add = (p: PlayerListItem) => {
    const id = p.player_id ?? p.batter_id;
    if (picked.length >= MAX_PLAYERS || picked.some((x) => x.id === id)) return;
    onPickedChange([...picked, { id, name: p.name }]);
    setQuery('');
    setResults([]);
  };

  const picker = (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {picked.map((p) => (
          <span key={p.id} className="inline-flex items-center gap-1 pl-2.5 pr-1 py-1 rounded-full bg-[#D9B15F]/15 border border-[#D9B15F]/40 text-xs text-[#F6F6F3]">
            {p.name}
            <button
              type="button"
              onClick={() => onPickedChange(picked.filter((x) => x.id !== p.id))}
              aria-label={`Remove ${p.name}`}
              className={`p-0.5 rounded-full hover:bg-white/10 ${FOCUS_RING}`}
            >
              <X className="w-3 h-3" aria-hidden="true" />
            </button>
          </span>
        ))}
        <span className="text-[11px] text-[#8E8E88]">
          {picked.length < MIN_PLAYERS ? `Choose ${MIN_PLAYERS}–${MAX_PLAYERS} players` : `${picked.length} of ${MAX_PLAYERS} players`}
        </span>
      </div>
      {picked.length < MAX_PLAYERS && (
        <div className="relative max-w-md">
          <label htmlFor="eda-player-search" className="sr-only">Search players to compare</label>
          <Search className="w-3.5 h-3.5 text-[#8E8E88] absolute left-2.5 top-1/2 -translate-y-1/2" aria-hidden="true" />
          <input
            id="eda-player-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search a player by name or ID"
            autoComplete="off"
            className={`w-full bg-[#101114] border border-[#D9B15F]/30 rounded-lg pl-8 pr-8 py-1.5 text-xs text-[#F6F6F3] ${FOCUS_RING}`}
          />
          {searching && <Loader2 className="w-3.5 h-3.5 text-[#D9B15F] animate-spin absolute right-2.5 top-1/2 -translate-y-1/2" aria-hidden="true" />}
          {results.length > 0 && (
            <ul aria-label="Matching players" className="absolute z-20 mt-1 w-full bg-[#151619] border border-[#D9B15F]/30 rounded-lg shadow-xl max-h-64 overflow-auto">
              {results.map((p) => {
                const id = p.player_id ?? p.batter_id;
                const chosen = picked.some((x) => x.id === id);
                return (
                  <li key={id}>
                    <button
                      type="button"
                      disabled={chosen}
                      onClick={() => add(p)}
                      className={`w-full text-left px-3 py-2 text-xs hover:bg-[#1E1F22] disabled:opacity-50 ${FOCUS_RING}`}
                    >
                      <span className="font-semibold text-[#F6F6F3]">{p.name}</span>
                      <span className="text-[#8E8E88]"> · {p.first_season}–{p.last_season} · {id}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );

  const area = comparison?.area;
  const players = area?.data?.players ?? [];
  const seasons = Array.from(new Set(players.flatMap((p) => p.batting_by_season.map((s) => s.season)))).sort((a, b) => a - b);
  const runRows = seasons.map((season) => ({
    season,
    ...Object.fromEntries(players.map((p) => [p.player_id, p.batting_by_season.find((s) => s.season === season)?.runs ?? null])),
  }));

  return (
    <section aria-labelledby="eda-player_comparison-title" className="space-y-3 min-w-0">
      {area ? (
        <ChartFrame area={area} filters={comparison!.filters} number={7} icon={<Users className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" />}>
          {picker}
          {loading && <p className="text-[11px] text-[#8E8E88]" role="status">Updating…</p>}
          <DataTable
            caption="Player comparison within the selected seasons"
            rows={players}
            rowKey={(p) => p.player_id}
            columns={[
              { header: 'Player', cell: (p) => p.name },
              { header: 'Seasons', title: 'Seasons played within the range', cell: (p) => <Stat value={p.coverage} reason={p.empty_reason ?? 'No matches in range'} />, className: 'whitespace-normal min-w-[6rem]' },
              { header: 'M', title: 'Matches', cell: (p) => fmtCount(p.matches) },
              { header: 'Runs', cell: (p) => <Stat value={p.batting ? fmtCount(p.batting.runs) : null} reason="Did not bat in this range" /> },
              { header: 'Avg', cell: (p) => <Stat value={p.batting ? fmtRate(p.batting.average) : null} state={p.batting?.average_state} reason={p.batting ? undefined : 'Did not bat in this range'} /> },
              { header: 'SR', cell: (p) => <Stat value={p.batting ? fmtRate(p.batting.strike_rate) : null} state={p.batting?.strike_rate_state} reason={p.batting ? undefined : 'Did not bat in this range'} /> },
              { header: '50+ / 100+', cell: (p) => <Stat value={p.batting ? `${p.batting.scores_50_plus} / ${p.batting.scores_100_plus}` : null} reason="Did not bat in this range" /> },
              { header: 'Wkts', cell: (p) => <Stat value={p.bowling ? fmtCount(p.bowling.wickets) : null} reason="Did not bowl in this range" /> },
              { header: 'Econ', align: 'right', cell: (p) => <Stat value={p.bowling ? fmtRate(p.bowling.economy_rate) : null} state={p.bowling?.economy_rate_state} reason={p.bowling ? undefined : 'Did not bowl in this range'} /> },
            ]}
          />
          {runRows.length > 0 && (
            <div
              className="h-60 w-full min-w-0"
              role="img"
              aria-label={`Runs by season: ${players.map((p) => `${p.name} ${p.batting_by_season.map((s) => `${s.season} ${s.runs}`).join(', ')}`).join('; ')}`}
            >
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <LineChart data={runRows} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#25262B" />
                  <XAxis dataKey="season" stroke="#8E8E88" fontSize={11} tickLine={false} />
                  <YAxis stroke="#8E8E88" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ backgroundColor: '#151619', borderColor: '#D9B15F', borderRadius: '0.75rem', fontSize: '12px' }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {players.map((p, i) => (
                    <Line key={p.player_id} type="monotone" dataKey={p.player_id} name={p.name} stroke={LINE_COLORS[i]} strokeWidth={2} dot={{ r: 2 }} connectNulls={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </ChartFrame>
      ) : (
        <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-6 space-y-3">
          <h3 id="eda-player_comparison-title" className="text-sm sm:text-base font-bold text-[#F6F6F3] flex items-center gap-2">
            <Users className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" />
            <span className="text-[#8E8E88] font-mono text-xs">7.</span> Player comparison
          </h3>
          <p className="text-xs text-[#B9B9B3]">
            Compare {MIN_PLAYERS}–{MAX_PLAYERS} players within the selected seasons. Players are identified by Cricsheet registry ID.
          </p>
          {picker}
          {loading && <p className="text-[11px] text-[#8E8E88]" role="status">Loading comparison…</p>}
          {error && (
            <div role="alert" className="flex flex-wrap items-center gap-3 text-xs text-red-200 bg-[#1C1517] border border-red-500/30 rounded-lg px-3 py-2">
              <span>{error}</span>
              <button type="button" onClick={() => setRetry((n) => n + 1)} className={`px-2.5 py-1 rounded-full bg-[#2A1B1E] border border-red-500/40 ${FOCUS_RING}`}>Retry</button>
            </div>
          )}
        </div>
      )}
    </section>
  );
};
