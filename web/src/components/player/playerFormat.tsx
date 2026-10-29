import React from 'react';
import { PlayerMatchAppearance, PlayerMatchResult } from '../../types';

// Plain-language reason for every null-value state code the API returns (state_definitions)
export const STATE_LABELS: Record<string, string> = {
  no_dismissals: 'Not dismissed in any innings',
  no_balls_faced: 'No ball faced (only at the non-striker\'s end)',
  no_wickets: 'No wicket taken',
  no_legal_balls: 'No legal ball bowled (only wides or no-balls)',
  not_recorded_in_source: 'Not recorded in the source match data',
};

export const FOCUS_RING = 'focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D9B15F] focus-visible:ring-offset-1 focus-visible:ring-offset-[#0D0E10]';

export const plural = (n: number, singular: string, pluralForm = `${singular}s`): string =>
  `${n.toLocaleString()} ${n === 1 ? singular : pluralForm}`;

const reportUnmapped = (kind: string, value: string) => {
  if (import.meta.env.DEV) console.error(`Player Explorer: unmapped ${kind} "${value}"`);
};

// A state the page has no wording for is shown, never hidden
export const Unmapped: React.FC<{ kind: string; value: string }> = ({ kind, value }) => {
  reportUnmapped(kind, value);
  return (
    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-950/60 text-red-300 border border-red-500/40">
      Unmapped {kind}: {value}
    </span>
  );
};

/** A value, or "—" with the reason it is unavailable (title for pointers, screen-reader text for everyone). */
export const Stat: React.FC<{ value: React.ReactNode; state?: string | null; reason?: string }> = ({ value, state, reason }) => {
  if (value !== null && value !== undefined) return <>{value}</>;
  const label = reason ?? (state ? STATE_LABELS[state] : undefined);
  if (!label) return <Unmapped kind="null state" value={state ?? 'none'} />;
  return (
    <span title={label} className="cursor-help underline decoration-dotted decoration-[#8E8E88] underline-offset-2">
      <span aria-hidden="true">—</span>
      <span className="sr-only">Not available: {label}</span>
    </span>
  );
};

export const fixed2 = (v: number | null | undefined): string | null => (v === null || v === undefined ? null : v.toFixed(2));

// ------------------------------------------------------------------ match log wording

const SUBSTITUTION_REASONS: Record<string, string> = {
  impact_player: 'Impact Player',
  concussion_substitute: 'concussion',
};

/** Plain words for an appearance state; null for an unmapped state or reason. */
export const appearanceLabel = (m: PlayerMatchAppearance): string | null => {
  if (m.appearance_state === 'playing_xi') return 'Playing XI';
  const reasons = m.substitutions.map((s) => SUBSTITUTION_REASONS[s.reason]);
  if (!reasons.length || reasons.some((r) => r === undefined)) return null;
  const sub = m.substitutions[0];
  switch (m.appearance_state) {
    case 'substituted_in':
      return sub.reason === 'concussion_substitute' ? 'Concussion substitute' : 'Substituted in (Impact Player)';
    case 'substituted_out':
      return sub.reason === 'concussion_substitute' ? 'Substituted out (concussion)' : 'Substituted out (Impact Player)';
    case 'substituted_in_and_out':
      return 'Substituted in, then substituted out';
    default:
      return null;
  }
};

/** Result for the player's team in plain words; null for an unmapped outcome. */
export const resultLabel = (r: PlayerMatchResult): string | null => {
  const method = r.method ? ` (${r.method})` : '';
  switch (r.outcome) {
    case 'won':
      return `Won${method}`;
    case 'lost':
      return `Lost${method}`;
    case 'no_result':
      return 'No result';
    case 'tied':
      if (r.super_over_outcome === 'won') return 'Tied (won Super Over)';
      if (r.super_over_outcome === 'lost') return 'Tied (lost Super Over)';
      return r.super_over_state === 'not_recorded_in_source' ? 'Tied (Super Over result not recorded)' : null;
    default:
      return r.outcome_state === 'not_recorded_in_source' ? 'Result not recorded' : null;
  }
};
