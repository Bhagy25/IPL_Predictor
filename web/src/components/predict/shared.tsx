import React from 'react';
import { AlertCircle, Info, RefreshCw, ShieldAlert } from 'lucide-react';
import { FOCUS_RING } from '../player/playerFormat';
import { PredictionTeamOption, PredictionVenueOption } from '../../types';

export const INPUT = `w-full bg-[#101114] border rounded-lg px-2.5 py-2 text-sm text-[#F6F6F3] min-w-0 ${FOCUS_RING}`;
export const inputBorder = (invalid: boolean) => (invalid ? 'border-red-500/70' : 'border-[#D9B15F]/30');
export const PRIMARY_BUTTON = `inline-flex items-center justify-center gap-2 px-4 py-2 rounded-full text-sm font-bold bg-[#D9B15F] text-[#0D0E10] hover:bg-[#E5C687] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer ${FOCUS_RING}`;
export const SECONDARY_BUTTON = `inline-flex items-center justify-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#101114] text-[#F6F6F3] border border-[#D9B15F]/30 hover:border-[#D9B15F]/60 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer ${FOCUS_RING}`;
export const DANGER_BUTTON = `inline-flex items-center justify-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#2A1B1E] hover:bg-[#3A2227] text-red-200 border border-red-500/40 cursor-pointer ${FOCUS_RING}`;

/** A probability (0–1) as a percentage with one decimal, for values the API did not already round. */
export const pct1 = (p: number): string => `${(Math.round(p * 1000) / 10).toFixed(1)}%`;

/** Brier scores and similar metrics to four decimals. */
export const dec4 = (v: number | null | undefined): string => (v == null ? '—' : v.toFixed(4));

export type FieldErrors = Record<string, string[]>;

/** A labelled form control with its error messages linked for screen readers. */
export const Field: React.FC<{
  id: string;
  label: string;
  hint?: string;
  errors?: string[];
  children: React.ReactNode;
}> = ({ id, label, hint, errors, children }) => (
  <div className="flex flex-col gap-1 min-w-0">
    <label htmlFor={id} className="text-[11px] text-[#B9B9B3] font-semibold">{label}</label>
    {children}
    {hint && !errors?.length && <p id={`${id}-hint`} className="text-[10px] text-[#8E8E88]">{hint}</p>}
    {!!errors?.length && (
      <div id={`${id}-error`} className="text-[11px] text-red-300 space-y-0.5">
        {errors.map((m) => <p key={m}>{m}</p>)}
      </div>
    )}
  </div>
);

/** aria props tying a control to its hint or error text. */
export const describe = (id: string, errors?: string[], hint?: string) => ({
  'aria-invalid': errors?.length ? true : undefined,
  'aria-describedby': errors?.length ? `${id}-error` : hint ? `${id}-hint` : undefined,
});

export const TeamSelect: React.FC<{
  id: string;
  value: string;
  teams: PredictionTeamOption[];
  onChange: (v: string) => void;
  invalid: boolean;
  describedBy: ReturnType<typeof describe>;
}> = ({ id, value, teams, onChange, invalid, describedBy }) => (
  <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={`${INPUT} ${inputBorder(invalid)}`} {...describedBy}>
    <option value="">Select a team…</option>
    {teams.map((t) => <option key={t.name} value={t.name}>{t.name} ({t.code})</option>)}
  </select>
);

export const VenueSelect: React.FC<{
  id: string;
  value: string;
  venues: PredictionVenueOption[];
  latestSeason: number;
  onChange: (v: string) => void;
  invalid: boolean;
  describedBy: ReturnType<typeof describe>;
}> = ({ id, value, venues, latestSeason, onChange, invalid, describedBy }) => (
  <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={`${INPUT} ${inputBorder(invalid)}`} {...describedBy}>
    <option value="">Select a venue…</option>
    <optgroup label={`Venues used in ${latestSeason}`}>
      {venues.filter((v) => v.used_in_latest_season).map((v) => <option key={v.name} value={v.name}>{v.name}</option>)}
    </optgroup>
    <optgroup label="Other venues in the archive">
      {venues.filter((v) => !v.used_in_latest_season).map((v) => (
        <option key={v.name} value={v.name}>{v.name}{v.last_season ? ` (last used ${v.last_season})` : ''}</option>
      ))}
    </optgroup>
  </select>
);

/** Request failure that is not an input problem (unreachable backend, model unavailable): message and Retry. */
export const ErrorRetry: React.FC<{ message: string; onRetry: () => void }> = ({ message, onRetry }) => (
  <div role="alert" className="bg-[#1C1517] border border-red-500/30 rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3">
    <p className="text-xs font-semibold text-red-200 flex items-start gap-2 min-w-0">
      <AlertCircle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
      <span className="min-w-0 break-words">{message}</span>
    </p>
    <button type="button" onClick={onRetry} className={DANGER_BUTTON}>
      <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" /> Retry
    </button>
  </div>
);

/** Input problems that belong to no single field. */
export const GeneralErrors: React.FC<{ messages: string[] }> = ({ messages }) =>
  messages.length ? (
    <div role="alert" className="bg-[#1C1517] border border-red-500/30 rounded-xl p-3 text-xs text-red-200 space-y-1">
      {messages.map((m) => <p key={m}>{m}</p>)}
    </div>
  ) : null;

export const Disclaimer: React.FC = () => (
  <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 flex items-start gap-3">
    <ShieldAlert className="w-5 h-5 text-[#D9B15F] flex-shrink-0 mt-0.5" aria-hidden="true" />
    <p className="text-xs sm:text-sm text-[#B9B9B3]">
      <strong className="text-[#F6F6F3] font-semibold">Probabilistic estimates, not guarantees. </strong>
      Each number is what a model trained on past IPL matches estimates for the situation you describe. You enter
      the inputs by hand; nothing here uses live match data, and a likely event can still fail to happen.
    </p>
  </div>
);

export const Note: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="text-[11px] text-[#8E8E88] flex items-start gap-1.5">
    <Info className="w-3.5 h-3.5 flex-shrink-0 mt-px" aria-hidden="true" />
    {/* File paths have no break points: let them wrap anywhere on narrow screens */}
    <span className="min-w-0 [overflow-wrap:anywhere]">{children}</span>
  </p>
);

/** The headline probability of a result card. */
export const BigNumber: React.FC<{ value: number; label: string }> = ({ value, label }) => (
  <div>
    <p className="text-4xl sm:text-5xl font-black text-[#D9B15F] tabular-nums">{value.toFixed(1)}%</p>
    <p className="text-xs text-[#B9B9B3] mt-1">{label}</p>
  </div>
);

/** Local calendar date (YYYY-MM-DD) n days from today. */
export const isoDaysFromToday = (n: number): string => {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

/** The day after a YYYY-MM-DD date. */
export const nextDay = (iso: string): string => {
  const [y, m, d] = iso.split('-').map(Number);
  const next = new Date(Date.UTC(y, m - 1, d + 1));
  return next.toISOString().slice(0, 10);
};
