import React from 'react';
import { ShieldCheck, Trophy, Database } from 'lucide-react';
import { OverviewTeamRecordsWindow, SeasonChampion, TeamRecordItem } from '../types';

interface TeamRecordsTableProps {
  records?: TeamRecordItem[];
  window?: OverviewTeamRecordsWindow;
  champions?: SeasonChampion[];
  loading?: boolean;
}

const titleSummary = (champions: SeasonChampion[], activeFranchises: Set<string>): string => {
  const counts = new Map<string, { label: string; titles: number; first: number }>();
  champions.forEach((c) => {
    if (!c.champion) return;
    const entry = counts.get(c.champion) ?? {
      label: activeFranchises.has(c.champion) ? (c.champion_short_name ?? c.champion) : c.champion,
      titles: 0,
      first: c.season,
    };
    entry.titles += 1;
    counts.set(c.champion, entry);
  });
  const ranked = [...counts.entries()].sort((a, b) => b[1].titles - a[1].titles || a[1].first - b[1].first);
  const active = ranked.filter(([team]) => activeFranchises.has(team)).map(([, e]) => `${e.label} (${e.titles})`);
  const former = ranked.filter(([team]) => !activeFranchises.has(team)).map(([, e]) => `${e.label} (${e.titles}, former)`);
  return [...active, ...former].join(', ');
};

export const TeamRecordsTable: React.FC<TeamRecordsTableProps> = ({
  records = [],
  window,
  champions = [],
  loading = false,
}) => {
  const hasRecords = records.length > 0;
  const activeFranchises = new Set(records.filter((record) => record.status === 'Active').map((record) => record.team));

  return (
    <div className="bg-[#151619] border border-white/[0.08] rounded-2xl p-5 sm:p-6 space-y-4 shadow-sm">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" />
          <h3 className="text-base sm:text-lg font-bold text-[#F6F6F3]">IPL Franchise Records</h3>
        </div>

        {window && (
          <span className="self-start sm:self-center inline-flex items-center text-[10px] sm:text-[11px] font-medium text-[#D9B15F] bg-[#D9B15F]/10 px-2.5 py-1 rounded-full border border-[#D9B15F]/20">
            {window.label}
          </span>
        )}
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto" role="region" aria-label="Franchise records table" tabIndex={0}>
        <table className="w-full text-left text-xs sm:text-[13px]" aria-busy={loading}>
          <thead>
            <tr className="border-b border-white/[0.08] text-[#8E8E88] uppercase text-[10px] sm:text-[11px] tracking-wider font-semibold">
              <th className="py-3 px-3 sm:px-4">Franchise</th>
              <th className="py-3 px-3 sm:px-4 text-center">Played</th>
              <th className="py-3 px-3 sm:px-4 text-center">Wins</th>
              <th className="py-3 px-3 sm:px-4 text-center">Losses</th>
              <th className="py-3 px-3 sm:px-4 text-center" aria-label="Tied or no result">Tied / NR</th>
              <th className="py-3 px-3 sm:px-4 text-center">Win Rate</th>
              <th className="py-3 px-3 sm:px-4 text-center">IPL Titles</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {loading ? (
              [...Array(6)].map((_, i) => (
                <tr key={i} className="animate-pulse">
                  <td className="py-3.5 px-4"><div className="h-4 w-36 bg-white/[0.06] rounded" /></td>
                  <td className="py-3.5 px-4"><div className="h-4 w-12 mx-auto bg-white/[0.06] rounded" /></td>
                  <td className="py-3.5 px-4"><div className="h-4 w-12 mx-auto bg-white/[0.06] rounded" /></td>
                  <td className="py-3.5 px-4"><div className="h-4 w-12 mx-auto bg-white/[0.06] rounded" /></td>
                  <td className="py-3.5 px-4"><div className="h-4 w-12 mx-auto bg-white/[0.06] rounded" /></td>
                  <td className="py-3.5 px-4"><div className="h-4 w-14 mx-auto bg-white/[0.06] rounded" /></td>
                  <td className="py-3.5 px-4"><div className="h-4 w-10 mx-auto bg-white/[0.06] rounded" /></td>
                </tr>
              ))
            ) : hasRecords ? (
              records.map((r) => (
                <tr
                  key={r.team}
                  className="hover:bg-white/[0.02] transition-colors font-medium text-[#F6F6F3]"
                >
                  {/* Franchise Name */}
                  <th scope="row" className="min-w-[9rem] py-3.5 px-3 sm:px-4">
                    <span className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 shrink-0 rounded-full bg-[#D9B15F]" aria-hidden="true" />
                      <span className="font-semibold text-white">{r.team}</span>
                    </span>
                  </th>

                  {/* Played */}
                  <td className="py-3.5 px-3 sm:px-4 text-center font-mono text-[#B9B9B3]">
                    {r.played}
                  </td>

                  {/* Wins */}
                  <td className="py-3.5 px-3 sm:px-4 text-center font-mono text-[#F6F6F3] font-bold">
                    {r.wins}
                  </td>

                  {/* Losses */}
                  <td className="py-3.5 px-3 sm:px-4 text-center font-mono text-[#8E8E88]">
                    {r.losses}
                  </td>

                  {/* Tied / NR */}
                  <td className="py-3.5 px-3 sm:px-4 text-center font-mono text-[#8E8E88]">
                    {r.tied_no_result}
                  </td>

                  {/* Win % */}
                  <td className="py-3.5 px-3 sm:px-4 text-center font-mono text-[#D9B15F] font-bold">
                    {r.win_pct === null ? (
                      <span title="All matches ended with no result">—</span>
                    ) : (
                      `${r.win_pct.toFixed(1)}%`
                    )}
                  </td>

                  {/* Titles */}
                  <td className="py-3.5 px-3 sm:px-4 text-center">
                    {r.titles > 0 ? (
                      <span className="inline-flex items-center gap-1.5 whitespace-nowrap px-2.5 py-0.5 rounded-full text-xs font-bold text-[#D9B15F] bg-[#D9B15F]/15 border border-[#D9B15F]/30 shadow-gold-pill">
                        <Trophy className="w-3 h-3 text-[#D9B15F]" aria-hidden="true" />
                        <span>{r.titles}</span>
                        {r.title_years && r.title_years.length > 0 && (
                          <span className="min-w-0 text-[10px] text-[#D9B15F]/80">
                            ({r.title_years.join(', ')})
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-[#8E8E88] font-mono text-xs">—</span>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={7} className="py-12 sm:py-16 text-center">
                  <div className="flex flex-col items-center justify-center space-y-2.5">
                    <div className="w-10 h-10 rounded-xl bg-[#0D0E10] border border-[#D9B15F]/30 flex items-center justify-center text-[#D9B15F] shadow-gold-pill">
                      <Database className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-[#F6F6F3]">No team records available</p>
                    </div>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Footer Notes */}
      <div className="pt-2 border-t border-white/[0.04] flex flex-col sm:flex-row sm:items-center justify-between text-[11px] text-[#8E8E88] gap-1">
        <span title={window?.rule}>
          Win rate divides wins by matches played, excluding no results. Super Over wins count.
        </span>
        {champions.length > 0 && (
          <span className="font-mono text-[#D9B15F]/90">
            IPL champions by titles · {titleSummary(champions, activeFranchises)}
          </span>
        )}
      </div>
    </div>
  );
};
