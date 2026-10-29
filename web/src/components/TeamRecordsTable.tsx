import React from 'react';
import { ShieldCheck, Trophy, Database } from 'lucide-react';
import { TeamRecordItem } from '../types';

interface TeamRecordsTableProps {
  records?: TeamRecordItem[];
  loading?: boolean;
}

export const TeamRecordsTable: React.FC<TeamRecordsTableProps> = ({
  records = [],
  loading = false,
}) => {
  const hasRecords = records && records.length > 0;

  return (
    <div className="bg-[#151619] border border-white/[0.08] rounded-2xl p-5 sm:p-6 space-y-4 shadow-sm">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-white/[0.06]">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#D9B15F]" />
            <h3 className="text-base sm:text-lg font-bold text-[#F6F6F3]">
              Verified IPL team records
            </h3>
          </div>
          <p className="text-xs text-[#B9B9B3] mt-0.5">
            Active 10-franchise performance with Super Over corrections &amp; championship titles.
          </p>
        </div>

        <span className="self-start sm:self-center inline-flex items-center text-[10px] sm:text-[11px] font-medium text-[#D9B15F] bg-[#D9B15F]/10 px-2.5 py-1 rounded-full border border-[#D9B15F]/20">
          {hasRecords ? '10 active franchises' : 'Awaiting data'}
        </span>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs sm:text-[13px]">
          <thead>
            <tr className="border-b border-white/[0.08] text-[#8E8E88] uppercase text-[10px] sm:text-[11px] tracking-wider font-semibold">
              <th className="py-3 px-3 sm:px-4">Franchise</th>
              <th className="py-3 px-3 sm:px-4 text-center">Played (2022–25)</th>
              <th className="py-3 px-3 sm:px-4 text-center">Wins</th>
              <th className="py-3 px-3 sm:px-4 text-center">Losses</th>
              <th className="py-3 px-3 sm:px-4 text-center">Tied / NR</th>
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
                  <td className="py-3.5 px-3 sm:px-4 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#D9B15F]" />
                    <span className="font-semibold text-white">{r.team}</span>
                  </td>

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
                    {r.win_pct.toFixed(1)}%
                  </td>

                  {/* Titles */}
                  <td className="py-3.5 px-3 sm:px-4 text-center">
                    {r.titles > 0 ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold text-[#D9B15F] bg-[#D9B15F]/15 border border-[#D9B15F]/30 shadow-gold-pill">
                        <Trophy className="w-3 h-3 text-[#D9B15F]" />
                        <span>{r.titles}</span>
                        {r.title_years && r.title_years.length > 0 && (
                          <span className="hidden md:inline text-[10px] text-[#D9B15F]/80">
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
                      <p className="text-sm font-semibold text-[#F6F6F3]">
                        No verified team records yet
                      </p>
                      <p className="text-xs text-[#B9B9B3]/75 mt-1 max-w-sm">
                        Records will appear when the analytical backend is connected and verified.
                      </p>
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
        <span>
          Win rates calculated among decided matches (2022–2025 comparative window); includes Super Over eliminator victories.
        </span>
        <span className="font-mono text-[#D9B15F]/90">
          Historical titles (19 seasons): CSK (5), MI (5), KKR (3), RCB (2), RR (1), SRH (1), GT (1) &middot; Defunct: Deccan Chargers (1)
        </span>
      </div>
    </div>
  );
};
