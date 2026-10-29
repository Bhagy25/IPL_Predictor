// Saved predictions, kept only in this browser (localStorage) as versioned JSON. Every storage call is
// wrapped: when storage is blocked or full, the tracker keeps working in memory for this visit.
import { useSyncExternalStore } from 'react';
import { BatterPredictionResponse, WicketPredictionResponse } from '../../types';

export const STORAGE_KEY = 'cricketlens.predictionTracker';
export const FILE_VERSION = 1;
export const MAX_RUNS = 400;

export interface WicketEntry {
  id: string;
  kind: 'wicket';
  saved_at: string;
  inputs: {
    batting_team: string;
    bowling_team: string;
    venue: string;
    innings: number;
    completed_overs: number;
    runs: number;
    wickets: number;
    last_over_runs: number;
    last_over_wickets: number;
  };
  prediction: { probability: number; probability_pct: number; phase: string; model: string; training_span: string };
  outcome: { wicket_fell: boolean } | null;
}

export interface BatterEntry {
  id: string;
  kind: 'batter';
  saved_at: string;
  inputs: { player_id: string; player_name: string; batting_team: string; opponent: string; venue: string; match_date: string };
  prediction: {
    chance_30_plus: number;
    chance_50_plus: number;
    chance_30_plus_pct: number;
    chance_50_plus_pct: number;
    prior_eligible_innings: number;
    model: string;
    training_span: string;
  };
  outcome: { runs: number } | null;
}

export type TrackerEntry = WicketEntry | BatterEntry;

export interface TrackerFile {
  version: number;
  exported_at?: string;
  entries: TrackerEntry[];
}

export type StorageState = 'available' | 'unavailable' | 'write_failed';

interface State {
  entries: TrackerEntry[];
  storage: StorageState;
  // Stored data that could not be read; it is copied aside, never silently discarded
  unreadable: string | null;
}

// ------------------------------------------------------------------ validation

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const isStr = (v: unknown): v is string => typeof v === 'string' && v.length > 0;
const isInt = (v: unknown, min: number, max: number): v is number => Number.isInteger(v) && (v as number) >= min && (v as number) <= max;
const isProb = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1;
const isPct = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 100;
const isDate = (v: unknown): v is string => isStr(v) && /^\d{4}-\d{2}-\d{2}$/.test(v) && !Number.isNaN(Date.parse(v));
const isTime = (v: unknown): v is string => isStr(v) && !Number.isNaN(Date.parse(v));

/** Why one entry is invalid, or null when it matches the version 1 schema. */
export function entryProblem(e: unknown): string | null {
  if (!isObj(e)) return 'not an object';
  if (!isStr(e.id)) return 'missing id';
  if (!isTime(e.saved_at)) return 'invalid saved_at';
  const i = e.inputs;
  const p = e.prediction;
  const o = e.outcome;
  if (!isObj(i) || !isObj(p)) return 'missing inputs or prediction';
  if (!isStr(p.model) || !isStr(p.training_span)) return 'missing model details';
  if (e.kind === 'wicket') {
    if (!isStr(i.batting_team) || !isStr(i.bowling_team) || !isStr(i.venue)) return 'missing teams or venue';
    if (!isInt(i.innings, 1, 2) || !isInt(i.completed_overs, 1, 19) || !isInt(i.wickets, 0, 9)) return 'innings, overs or wickets out of range';
    if (!isInt(i.runs, 0, 1000) || !isInt(i.last_over_runs, 0, i.runs as number) || !isInt(i.last_over_wickets, 0, i.wickets as number)) return 'runs or last-over values out of range';
    if (!isProb(p.probability) || !isPct(p.probability_pct) || !isStr(p.phase)) return 'invalid wicket probability';
    if (o !== null && !(isObj(o) && typeof o.wicket_fell === 'boolean')) return 'invalid wicket outcome';
    return null;
  }
  if (e.kind === 'batter') {
    if (!isStr(i.player_id) || !isStr(i.player_name) || !isStr(i.batting_team) || !isStr(i.opponent) || !isStr(i.venue)) return 'missing player, teams or venue';
    if (!isDate(i.match_date)) return 'invalid match date';
    if (!isProb(p.chance_30_plus) || !isProb(p.chance_50_plus) || !isPct(p.chance_30_plus_pct) || !isPct(p.chance_50_plus_pct)) return 'invalid milestone probability';
    if ((p.chance_50_plus as number) > (p.chance_30_plus as number)) return 'P(50+) is greater than P(30+)';
    if (!isInt(p.prior_eligible_innings, 0, 100000)) return 'invalid prior innings';
    if (o !== null && !(isObj(o) && isInt(o.runs, 0, MAX_RUNS))) return 'invalid batter outcome';
    return null;
  }
  return 'unknown kind';
}

/** Validates a whole tracker file; every entry must be valid and ids must be unique. */
export function parseTrackerFile(data: unknown): { ok: true; entries: TrackerEntry[] } | { ok: false; error: string } {
  if (!isObj(data)) return { ok: false, error: 'The file is not a tracker export (expected a JSON object).' };
  if (data.version !== FILE_VERSION) return { ok: false, error: `Unsupported version ${String(data.version)}: expected version ${FILE_VERSION}.` };
  if (!Array.isArray(data.entries)) return { ok: false, error: 'The file has no "entries" list.' };
  const seen = new Set<string>();
  for (let n = 0; n < data.entries.length; n += 1) {
    const problem = entryProblem(data.entries[n]);
    if (problem) return { ok: false, error: `Entry ${n + 1} is invalid: ${problem}. Nothing was imported.` };
    const id = (data.entries[n] as TrackerEntry).id;
    if (seen.has(id)) return { ok: false, error: `Entry ${n + 1} repeats id ${id}. Nothing was imported.` };
    seen.add(id);
  }
  return { ok: true, entries: data.entries as TrackerEntry[] };
}

// ------------------------------------------------------------------ storage

function readStorage(): State {
  let raw: string | null;
  try {
    raw = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return { entries: [], storage: 'unavailable', unreadable: null };
  }
  if (raw === null) return { entries: [], storage: 'available', unreadable: null };
  try {
    const parsed = parseTrackerFile(JSON.parse(raw));
    if (parsed.ok) return { entries: parsed.entries, storage: 'available', unreadable: null };
  } catch {
    // not JSON: handled below
  }
  try {
    window.localStorage.setItem(`${STORAGE_KEY}.unreadable`, raw);
  } catch {
    // the copy is best effort; the original stays until the next save
  }
  return { entries: [], storage: 'available', unreadable: raw };
}

let state: State | null = null;
const listeners = new Set<() => void>();

const current = (): State => {
  if (state === null) state = readStorage();
  return state;
};

function commit(entries: TrackerEntry[]) {
  const prev = current();
  let storage: StorageState = prev.storage === 'unavailable' ? 'unavailable' : 'available';
  if (storage === 'available') {
    try {
      const file: TrackerFile = { version: FILE_VERSION, entries };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(file));
    } catch {
      storage = 'write_failed';
    }
  }
  state = { entries, storage, unreadable: prev.unreadable };
  listeners.forEach((l) => l());
}

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  // Another tab changed the saved predictions
  const onStorage = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) {
      state = readStorage();
      listeners.forEach((l) => l());
    }
  };
  window.addEventListener('storage', onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener('storage', onStorage);
  };
};

export const useTracker = (): State => useSyncExternalStore(subscribe, current, current);

const newId = (): string =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;

// ------------------------------------------------------------------ actions

export function saveWicketPrediction(r: WicketPredictionResponse): string {
  const entry: WicketEntry = {
    id: newId(),
    kind: 'wicket',
    saved_at: new Date().toISOString(),
    inputs: { ...r.inputs },
    prediction: { probability: r.probability, probability_pct: r.probability_pct, phase: r.phase, model: r.model, training_span: r.training_span },
    outcome: null,
  };
  commit([entry, ...current().entries]);
  return entry.id;
}

export function saveBatterPrediction(r: BatterPredictionResponse): string {
  const entry: BatterEntry = {
    id: newId(),
    kind: 'batter',
    saved_at: new Date().toISOString(),
    inputs: { player_id: r.player_id, player_name: r.player_name, batting_team: r.batting_team, opponent: r.opponent, venue: r.venue, match_date: r.date },
    prediction: {
      chance_30_plus: r.chance_30_plus,
      chance_50_plus: r.chance_50_plus,
      chance_30_plus_pct: r.chance_30_plus_pct,
      chance_50_plus_pct: r.chance_50_plus_pct,
      prior_eligible_innings: r.prior_eligible_innings,
      model: r.model,
      training_span: r.training_span,
    },
    outcome: null,
  };
  commit([entry, ...current().entries]);
  return entry.id;
}

export function setOutcome(id: string, outcome: WicketEntry['outcome'] | BatterEntry['outcome']) {
  commit(current().entries.map((e) => (e.id === id ? ({ ...e, outcome } as TrackerEntry) : e)));
}

export function removeEntry(id: string) {
  commit(current().entries.filter((e) => e.id !== id));
}

export function clearAll() {
  commit([]);
}

/** Adds valid imported entries; ids already saved are kept as they are. */
export function importEntries(entries: TrackerEntry[]): { added: number; skipped: number } {
  const existing = new Set(current().entries.map((e) => e.id));
  const fresh = entries.filter((e) => !existing.has(e.id));
  commit([...current().entries, ...fresh].sort((a, b) => b.saved_at.localeCompare(a.saved_at)));
  return { added: fresh.length, skipped: entries.length - fresh.length };
}

export function exportFile(): TrackerFile {
  return { version: FILE_VERSION, exported_at: new Date().toISOString(), entries: current().entries };
}

// ------------------------------------------------------------------ scoring

export interface BinaryForecast { label: 'Wicket next over' | 'Batter 30+' | 'Batter 50+'; p: number; happened: boolean }

/** One yes/no forecast per resolved wicket entry and two (30+ and 50+) per resolved batter entry. */
export function resolvedForecasts(entries: TrackerEntry[]): BinaryForecast[] {
  const out: BinaryForecast[] = [];
  entries.forEach((e) => {
    if (e.outcome === null) return;
    if (e.kind === 'wicket') {
      out.push({ label: 'Wicket next over', p: e.prediction.probability, happened: (e.outcome as { wicket_fell: boolean }).wicket_fell });
    } else {
      const runs = (e.outcome as { runs: number }).runs;
      out.push({ label: 'Batter 30+', p: e.prediction.chance_30_plus, happened: runs >= 30 });
      out.push({ label: 'Batter 50+', p: e.prediction.chance_50_plus, happened: runs >= 50 });
    }
  });
  return out;
}

export const brier = (fs: BinaryForecast[]): number | null =>
  fs.length ? fs.reduce((s, f) => s + (f.p - (f.happened ? 1 : 0)) ** 2, 0) / fs.length : null;

export const HIT_RATE_BINS = [0, 0.2, 0.4, 0.6, 0.8, 1];

/** Forecasts grouped by predicted probability (0–20%, …, 80–100%) with the share that happened. */
export function hitRateBins(fs: BinaryForecast[]) {
  return HIT_RATE_BINS.slice(0, -1).map((lower, i) => {
    const upper = HIT_RATE_BINS[i + 1];
    const inBin = fs.filter((f) => f.p >= lower && (i === HIT_RATE_BINS.length - 2 ? f.p <= upper : f.p < upper));
    return {
      lower,
      upper,
      n: inBin.length,
      avgPredicted: inBin.length ? inBin.reduce((s, f) => s + f.p, 0) / inBin.length : null,
      observed: inBin.length ? inBin.filter((f) => f.happened).length / inBin.length : null,
    };
  });
}
