import React from 'react';
import { AlertTriangle, BookOpen, Database, Info } from 'lucide-react';
import { EDAArea, EDAFiltersEcho } from '../../types';
import { FOCUS_RING } from '../player/playerFormat';
import { fmtCount } from '../../utils/format';

const FILTER_NAMES: Record<string, string> = { season: 'Seasons', team: 'Team', venue: 'Venue' };

/** The selection this area was computed for: only the filters it applies. */
export const appliedSelection = (area: EDAArea<unknown>, filters: EDAFiltersEcho): string => {
  const parts = [
    filters.season_from === filters.season_to ? `${filters.season_from}` : `${filters.season_from}–${filters.season_to}`,
  ];
  if (filters.team && area.applied_filters.includes('team')) parts.push(filters.team.name);
  if (filters.venue && area.applied_filters.includes('venue')) parts.push(filters.venue);
  return parts.join(' · ');
};

/**
 * Header and footer shared by every live chart: active selection, actual season coverage, sample size,
 * units, notes for filters the chart does not support, definitions and data source. An empty area shows
 * its explanation instead of the chart.
 */
export const ChartFrame: React.FC<{
  area: EDAArea<unknown>;
  filters: EDAFiltersEcho;
  number: number;
  icon: React.ReactNode;
  controls?: React.ReactNode;
  children?: React.ReactNode;
}> = ({ area, filters, number, icon, controls, children }) => (
  <section
    aria-labelledby={`eda-${area.id}-title`}
    className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-6 space-y-4 min-w-0"
  >
    <header className="space-y-2 border-b border-[#D9B15F]/15 pb-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 id={`eda-${area.id}-title`} className="text-sm sm:text-base font-bold text-[#F6F6F3] flex items-center gap-2 min-w-0">
          {icon}
          <span className="text-[#8E8E88] font-mono text-xs">{number}.</span>
          <span>{area.title}</span>
        </h3>
        {controls}
      </div>
      <dl className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[#B9B9B3]">
        <div className="flex gap-1">
          <dt className="text-[#8E8E88]">Selection:</dt>
          <dd className="text-[#F6F6F3]">{appliedSelection(area, filters)}</dd>
        </div>
        <div className="flex gap-1">
          <dt className="text-[#8E8E88]">Data covers:</dt>
          <dd className="text-[#D9B15F] font-semibold">{area.coverage ? area.coverage.label : 'no seasons'}</dd>
        </div>
        {area.sample.length > 0 && (
          <div className="flex gap-1">
            <dt className="text-[#8E8E88]">Sample:</dt>
            <dd>{area.sample.map((s) => `${fmtCount(s.value)} ${s.label}`).join(' · ')}</dd>
          </div>
        )}
        <div className="flex gap-1">
          <dt className="text-[#8E8E88]">Units:</dt>
          <dd>{area.units}</dd>
        </div>
        <div className="flex gap-1">
          <dt className="text-[#8E8E88]">Filters supported:</dt>
          <dd>{area.supported_filters.map((f) => FILTER_NAMES[f] ?? f).join(', ')}</dd>
        </div>
      </dl>
      {area.unaffected_by.map((n) => (
        <p
          key={n.filter}
          role="note"
          className="flex items-start gap-2 text-[11px] font-semibold text-amber-200 bg-amber-950/40 border border-amber-500/30 rounded-lg px-3 py-2"
        >
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <span>{n.note}</span>
        </p>
      ))}
    </header>

    {area.state === 'empty' || area.data === null ? (
      <div role="status" className="flex items-start gap-2 p-4 rounded-xl bg-[#17181C] border border-white/5 text-xs text-[#B9B9B3]">
        <Info className="w-4 h-4 text-[#D9B15F] flex-shrink-0" aria-hidden="true" />
        <span>
          <span className="font-semibold text-[#F6F6F3]">No data for this selection. </span>
          {area.empty_reason}
        </span>
      </div>
    ) : (
      <div className="space-y-4 min-w-0">{children}</div>
    )}

    <footer className="space-y-2 border-t border-[#D9B15F]/10 pt-3">
      <details className="group">
        <summary className={`cursor-pointer inline-flex items-center gap-1.5 text-[11px] font-semibold text-[#D9B15F] rounded ${FOCUS_RING}`}>
          <BookOpen className="w-3.5 h-3.5" aria-hidden="true" />
          Definitions
        </summary>
        <dl className="mt-2 grid gap-1.5 text-[11px] text-[#B9B9B3]">
          {Object.entries(area.definitions).map(([k, v]) => (
            <div key={k}>
              <dt className="inline font-semibold text-[#F6F6F3]">{k.replace(/_/g, ' ')}: </dt>
              <dd className="inline">{v}</dd>
            </div>
          ))}
        </dl>
      </details>
      <p className="flex items-start gap-1.5 text-[10px] text-[#8E8E88]">
        <Database className="w-3 h-3 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <span>{area.source}</span>
      </p>
    </footer>
  </section>
);

/** A labelled select for a minimum-sample control. */
export const MinimumControl: React.FC<{
  id: string;
  label: string;
  value: number;
  options: { value: number; label: string }[];
  onChange: (v: number) => void;
}> = ({ id, label, value, options, onChange }) => (
  <div className="flex items-center gap-2 text-[11px]">
    <label htmlFor={id} className="text-[#B9B9B3] font-semibold">{label}</label>
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className={`bg-[#101114] border border-[#D9B15F]/30 rounded-lg px-2 py-1 text-[#F6F6F3] ${FOCUS_RING}`}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  </div>
);
