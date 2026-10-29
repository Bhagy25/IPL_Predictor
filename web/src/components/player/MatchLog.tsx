import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, Calendar, ChevronLeft, ChevronRight, Loader2, RefreshCw } from 'lucide-react';
import { PlayerMatchAppearance, PlayerMatchLogResponse } from '../../types';
import { fetchPlayerMatches } from '../../api/players';
import { DataTable, Column } from './ProfileSections';
import { FOCUS_RING, Stat, Unmapped, appearanceLabel, fixed2, plural, resultLabel } from './playerFormat';

const PAGE_SIZE = 20;

const BattingCell: React.FC<{ m: PlayerMatchAppearance }> = ({ m }) => {
  const b = m.batting;
  if (b.state === 'did_not_bat') return <span className="text-[#8E8E88] italic">Did not bat</span>;
  if (b.state !== 'batted' || b.runs === null) return <Unmapped kind="batting state" value={b.state} />;
  return (
    <div className="leading-tight">
      <span className={`font-black ${b.runs >= 50 ? 'text-[#D9B15F]' : 'text-[#F6F6F3]'}`}>
        {b.runs}{b.dismissed ? '' : '*'}
      </span>
      <span className="text-[#B9B9B3]"> ({b.balls_faced})</span>
      <div className="text-[10px] text-[#8E8E88]">
        {b.fours}×4 {b.sixes}×6 &middot; {b.dismissal_kind ?? 'not out'}
      </div>
    </div>
  );
};

const BowlingCell: React.FC<{ m: PlayerMatchAppearance }> = ({ m }) => {
  const w = m.bowling;
  if (w.state === 'did_not_bowl') return <span className="text-[#8E8E88] italic">Did not bowl</span>;
  if (w.state !== 'bowled') return <Unmapped kind="bowling state" value={w.state} />;
  return (
    <div className="leading-tight">
      <span className="font-bold text-emerald-400" title="Overs-runs-wickets">{w.overs}-{w.runs_conceded}-{w.wickets}</span>
      <div className="text-[10px] text-[#8E8E88]">Econ <Stat value={fixed2(w.economy)} state={w.economy_state} /></div>
    </div>
  );
};

const ResultCell: React.FC<{ m: PlayerMatchAppearance }> = ({ m }) => {
  const label = resultLabel(m.result);
  if (!label) return <Unmapped kind="result" value={m.result.outcome ?? 'none'} />;
  const tone = label.startsWith('Won') || label.includes('won Super') ? 'text-emerald-300' : label.startsWith('Lost') || label.includes('lost Super') ? 'text-red-300' : 'text-[#B9B9B3]';
  return <span className={`font-semibold ${tone}`}>{label}</span>;
};

const AppearanceCell: React.FC<{ m: PlayerMatchAppearance }> = ({ m }) => {
  const label = appearanceLabel(m);
  if (!label) return <Unmapped kind="appearance state" value={m.appearance_state} />;
  if (m.appearance_state === 'playing_xi') return <span className="text-[#8E8E88]">{label}</span>;
  const detail = m.substitutions
    .map((s) => (s.direction === 'in' ? `Came in for ${s.counterpart_name}` : `Replaced by ${s.counterpart_name}`))
    .join('; ');
  return (
    <span title={detail} className="inline-block leading-snug text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#D9B15F]/15 text-[#D9B15F] border border-[#D9B15F]/30">
      {label}
      <span className="sr-only"> ({detail})</span>
    </span>
  );
};

const COLUMNS: Column<PlayerMatchAppearance>[] = [
  { header: 'Date', align: 'left', cell: (m) => <span className="font-mono text-[#B9B9B3]">{m.date}</span> },
  { header: 'Season', cell: (m) => <span className="font-bold text-[#F6F6F3]">{m.season}</span> },
  { header: 'Team', align: 'left', className: 'whitespace-normal min-w-[5rem]', cell: (m) => m.team },
  { header: 'Opposition', align: 'left', className: 'whitespace-normal min-w-[5rem]', cell: (m) => <span className="text-[#F6F6F3]">{m.opposition}</span> },
  { header: 'Venue', align: 'left', cell: (m) => <span className="block max-w-[7rem] truncate" title={m.venue}>{m.venue}</span> },
  { header: 'Batting', title: 'Runs* (balls), boundaries and dismissal; * = not out', cell: (m) => <BattingCell m={m} /> },
  { header: 'Bowling', title: 'Overs-runs-wickets and economy', cell: (m) => <BowlingCell m={m} /> },
  { header: 'Result', className: 'whitespace-normal min-w-[4.5rem]', title: "Result for the player's team", cell: (m) => <ResultCell m={m} /> },
  { header: 'Appearance', className: 'whitespace-normal min-w-[6rem]', cell: (m) => <AppearanceCell m={m} /> },
];

const PageButton: React.FC<{ disabled: boolean; onClick: () => void; children: React.ReactNode; label: string }> = ({ disabled, onClick, children, label }) => (
  <button
    type="button"
    disabled={disabled}
    onClick={onClick}
    aria-label={label}
    className={`inline-flex items-center gap-1 px-3 py-2 rounded-lg text-xs font-semibold bg-[#101114] text-[#F6F6F3] border border-[#D9B15F]/20 hover:border-[#D9B15F]/50 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer ${FOCUS_RING}`}
  >
    {children}
  </button>
);

/** Paginated match-by-match log; remount (key) it when the player or season changes. */
export const MatchLog: React.FC<{ playerId: string; season: number | null; scopeLabel: string }> = ({ playerId, season, scopeLabel }) => {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PlayerMatchLogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Kept from the last successful page, so the pager stays right while a page fails
  const [totalPages, setTotalPages] = useState(1);
  const request = useRef(0);

  const load = useCallback(async () => {
    const requestId = ++request.current;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchPlayerMatches(playerId, { season, page, page_size: PAGE_SIZE });
      if (requestId === request.current) {
        setData(res);
        setTotalPages(res.total_pages);
      }
    } catch (err: any) {
      if (requestId === request.current) {
        setData(null);
        setError(err?.message || 'Failed to load the match log');
      }
    } finally {
      if (requestId === request.current) setLoading(false);
    }
  }, [playerId, season, page]);

  useEffect(() => {
    load();
  }, [load]);

  let body: React.ReactNode;
  if (loading) {
    body = (
      <div className="p-10 flex flex-col items-center gap-2 text-xs text-[#B9B9B3]" role="status">
        <Loader2 className="w-5 h-5 text-[#D9B15F] animate-spin" />
        <span>Loading page {page} of the match log...</span>
      </div>
    );
  } else if (error) {
    body = (
      <div className="p-8 flex flex-col items-center gap-2 text-center" role="alert">
        <AlertCircle className="w-5 h-5 text-red-400" />
        <p className="text-xs font-semibold text-red-200">Unable to load this page of the match log</p>
        <p className="text-[11px] text-red-300/75 max-w-sm">{error}</p>
        <button
          type="button"
          onClick={load}
          className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#2A1B1E] hover:bg-[#3A2227] text-red-200 border border-red-500/40 ${FOCUS_RING}`}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry</span>
        </button>
      </div>
    );
  } else if (!data || data.total_count === 0) {
    body = <div className="p-8 text-center text-xs text-[#B9B9B3]">No match appearances in this selection.</div>;
  } else {
    body = (
      <DataTable
        caption={`Match log, ${scopeLabel.toLowerCase()}, page ${data.page} of ${data.total_pages}, most recent first`}
        columns={COLUMNS}
        rows={data.matches}
        rowKey={(m) => m.match_id}
        dense
      />
    );
  }

  return (
    <section aria-label="Match Log" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-[#D9B15F]/15 gap-2">
        <div>
          <h3 className="text-base font-bold text-[#F6F6F3] flex items-center gap-2">
            <Calendar className="w-4 h-4 text-[#D9B15F]" />
            Match-by-Match Log
          </h3>
          <p className="text-xs text-[#B9B9B3] mt-0.5">
            Every match in an official squad list, most recent first &middot; {scopeLabel}
          </p>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-[#101114] text-[#D9B15F] border border-[#D9B15F]/20 self-start sm:self-center">
          {data ? plural(data.total_count, 'appearance') : '…'}
        </span>
      </div>

      {body}

      <nav aria-label="Match log pages" className="flex items-center justify-between gap-3 pt-3 border-t border-[#D9B15F]/15">
        <PageButton label="Previous page" disabled={loading || page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
          <ChevronLeft className="w-3.5 h-3.5" />
          <span>Previous</span>
        </PageButton>
        <span className="text-xs text-[#B9B9B3]" aria-live="polite">
          Page {page} of {totalPages}
        </span>
        <PageButton label="Next page" disabled={loading || !!error || page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>
          <span>Next</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </PageButton>
      </nav>
    </section>
  );
};
