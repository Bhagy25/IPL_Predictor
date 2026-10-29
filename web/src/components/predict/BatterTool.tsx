import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookmarkPlus, Check, Loader2, Search, Target } from 'lucide-react';
import { ApiError, predictBatter } from '../../api/predict';
import {
  BatterPredictionRequest, BatterPredictionResponse, PredictionBatterOption, PredictionModelInfo, PredictionOptionsResponse,
} from '../../types';
import { FOCUS_RING } from '../player/playerFormat';
import { fmtCount } from '../../utils/format';
import {
  BigNumber, ErrorRetry, Field, FieldErrors, GeneralErrors, INPUT, Note, PRIMARY_BUTTON, SECONDARY_BUTTON,
  TeamSelect, VenueSelect, dec4, describe, inputBorder, isoDaysFromToday, nextDay, pct1,
} from './shared';
import { saveBatterPrediction } from './trackerStore';

const MAX_SUGGESTIONS = 8;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

interface Form { batting_team: string; opponent: string; venue: string; match_date: string }

/** Players whose display name, a name variant or registry ID contains the query (most innings first). */
export function searchBatters(batters: PredictionBatterOption[], query: string): PredictionBatterOption[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return batters
    .filter((b) => b.player_id.toLowerCase() === q || [b.name, ...b.name_variants].some((n) => n.toLowerCase().includes(q)))
    .slice(0, MAX_SUGGESTIONS);
}

/** The API's rules (forecast_future_batter.forecast() plus team and venue membership), checked before sending. */
export function validateBatter(player: PredictionBatterOption | null, f: Form, options: PredictionOptionsResponse) {
  const errors: FieldErrors = {};
  const add = (k: string, m: string) => { (errors[k] ??= []).push(m); };
  const teams = new Set(options.teams.map((t) => t.name));
  if (!player) add('player_id', 'Search for a player and pick one from the list.');
  if (!f.batting_team) add('batting_team', 'Choose the player\'s team.');
  else if (!teams.has(f.batting_team)) add('batting_team', 'Choose one of the listed teams.');
  if (!f.opponent) add('opponent', 'Choose the opponent.');
  else if (!teams.has(f.opponent)) add('opponent', 'Choose one of the listed teams.');
  else if (f.opponent === f.batting_team) add('opponent', 'The two teams must be different.');
  if (!f.venue) add('venue', 'Choose a venue.');
  else if (!options.venues.some((v) => v.name === f.venue)) add('venue', 'Choose one of the listed venues.');
  if (!DATE.test(f.match_date) || Number.isNaN(Date.parse(f.match_date))) add('match_date', 'Enter a valid match date.');
  else if (f.match_date <= options.archive_last_match_date) {
    add('match_date', `Match date must be after the last match in the data (${options.archive_last_match_date}): forecasts are for future matches.`);
  } else if (player && f.match_date <= player.latest_innings_date) {
    add('match_date', `Match date must be after this player's latest eligible innings on ${player.latest_innings_date}.`);
  }
  const payload: BatterPredictionRequest | null = Object.keys(errors).length || !player ? null : {
    player_id: player.player_id, batting_team: f.batting_team, opponent: f.opponent, venue: f.venue, match_date: f.match_date,
  };
  return { errors, payload };
}

export const BatterTool: React.FC<{
  options: PredictionOptionsResponse;
  model: PredictionModelInfo | null;
}> = ({ options, model }) => {
  const [query, setQuery] = useState('');
  const [player, setPlayer] = useState<PredictionBatterOption | null>(null);
  const [open, setOpen] = useState(false);
  // By default only players who appeared in the latest season are searchable
  const [includeInactive, setIncludeInactive] = useState(false);
  const [active, setActive] = useState(0);
  const [form, setForm] = useState<Form>({ batting_team: '', opponent: '', venue: '', match_date: isoDaysFromToday(1) });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [general, setGeneral] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [result, setResult] = useState<BatterPredictionResponse | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const lastPayload = useRef<BatterPredictionRequest | null>(null);
  const controller = useRef<AbortController | null>(null);
  // Closing the list on blur is delayed so a click on an option still lands; refocusing cancels it
  const closeTimer = useRef<number | undefined>(undefined);
  const activeTeams = useMemo(() => new Set(options.teams.map((t) => t.name)), [options.teams]);
  const pool = useMemo(
    () => (includeInactive ? options.batters : options.batters.filter((b) => b.appeared_in_latest_season)),
    [options.batters, includeInactive],
  );
  const activeCount = useMemo(() => options.batters.filter((b) => b.appeared_in_latest_season).length, [options.batters]);
  const suggestions = useMemo(() => (player ? [] : searchBatters(pool, query)), [pool, query, player]);

  useEffect(() => () => { controller.current?.abort(); window.clearTimeout(closeTimer.current); }, []);

  const invalidate = (field: string) => {
    // A result always belongs to the inputs on screen: drop it and any request still running
    controller.current?.abort();
    setLoading(false);
    setResult(null);
    setSavedId(null);
    setFailure(null);
    setErrors((e) => { const rest = { ...e }; delete rest[field]; return rest; });
  };

  const set = (k: keyof Form, v: string) => {
    setForm((f) => ({ ...f, [k]: v }));
    invalidate(k);
  };

  const choose = (b: PredictionBatterOption) => {
    setPlayer(b);
    setQuery(b.name);
    setOpen(false);
    invalidate('player_id');
    // Start from the team of the player's latest innings when it is an active franchise; it stays editable
    if (activeTeams.has(b.latest_team)) setForm((f) => ({ ...f, batting_team: b.latest_team }));
  };

  const onQuery = (v: string) => {
    setQuery(v);
    setPlayer(null);
    setOpen(true);
    setActive(0);
    invalidate('player_id');
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!suggestions.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive((a) => (a + 1) % suggestions.length); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setOpen(true); setActive((a) => (a - 1 + suggestions.length) % suggestions.length); }
    else if (e.key === 'Enter' && open) { e.preventDefault(); choose(suggestions[active]); }
    else if (e.key === 'Escape') setOpen(false);
  };

  const run = async (payload: BatterPredictionRequest) => {
    controller.current?.abort();
    const ctl = new AbortController();
    controller.current = ctl;
    lastPayload.current = payload;
    setLoading(true);
    setFailure(null);
    setGeneral([]);
    try {
      const r = await predictBatter(payload, ctl.signal);
      setResult(r);
      setSavedId(null);
    } catch (exc) {
      if ((exc as Error).name === 'AbortError') return;
      const err = exc as ApiError;
      if (err.status === 422) {
        setErrors(err.fieldErrors);
        setGeneral(err.generalErrors);
      } else {
        setFailure(err.message);
      }
    } finally {
      if (controller.current === ctl) setLoading(false);
    }
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const { errors: found, payload } = validateBatter(player, form, options);
    setErrors(found);
    setGeneral([]);
    if (payload) run(payload);
  };

  const holdout = model?.holdout_2026;
  const constant = model?.holdout_2026_constant;
  const listId = 'bt-player-list';
  const playerHint = player
    ? `${fmtCount(player.eligible_innings)} eligible innings · latest ${player.latest_innings_date} (${player.latest_team}) · ID ${player.player_id}`
    : `Search ${fmtCount(pool.length)} players by name, a name variant or registry ID.`;
  const toggleInactive = (on: boolean) => {
    setIncludeInactive(on);
    // A player hidden by the filter cannot stay selected
    if (!on && player && !player.appeared_in_latest_season) {
      setPlayer(null);
      setQuery('');
      invalidate('player_id');
    }
  };
  const earliestDate = [options.archive_last_match_date, player?.latest_innings_date ?? ''].sort().slice(-1)[0];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] gap-6">
      <form onSubmit={submit} noValidate aria-label="Batter milestone inputs" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 space-y-4">
        <Field id="bt-player_id" label="Player" hint={playerHint} errors={errors.player_id}>
          <div className="relative">
            <Search className="w-4 h-4 text-[#8E8E88] absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" aria-hidden="true" />
            <input
              id="bt-player_id"
              type="text"
              role="combobox"
              autoComplete="off"
              aria-autocomplete="list"
              aria-expanded={open && suggestions.length > 0}
              aria-controls={listId}
              aria-activedescendant={open && suggestions.length ? `bt-player-${suggestions[active]?.player_id}` : undefined}
              placeholder="e.g. Kohli"
              value={query}
              onChange={(e) => onQuery(e.target.value)}
              onKeyDown={onKeyDown}
              onFocus={() => { window.clearTimeout(closeTimer.current); setOpen(true); }}
              onBlur={() => { closeTimer.current = window.setTimeout(() => setOpen(false), 150); }}
              className={`${INPUT} pl-8 ${inputBorder(!!errors.player_id)}`}
              {...describe('bt-player_id', errors.player_id, playerHint)}
            />
            {open && suggestions.length > 0 && (
              <ul id={listId} role="listbox" aria-label="Matching players" className="absolute z-20 mt-1 w-full max-h-72 overflow-auto bg-[#17181C] border border-[#D9B15F]/30 rounded-lg shadow-xl">
                {suggestions.map((b, i) => (
                  <li
                    key={b.player_id}
                    id={`bt-player-${b.player_id}`}
                    role="option"
                    aria-selected={i === active}
                    onMouseDown={(e) => { e.preventDefault(); choose(b); }}
                    onMouseEnter={() => setActive(i)}
                    className={`px-3 py-2 cursor-pointer text-xs ${i === active ? 'bg-[#D9B15F]/15 text-[#F6F6F3]' : 'text-[#B9B9B3]'}`}
                  >
                    <span className="font-semibold text-[#F6F6F3]">{b.name}</span>
                    {b.name_variants.filter((n) => n !== b.name).length > 0 && (
                      <span className="text-[#8E8E88]"> (also {b.name_variants.filter((n) => n !== b.name).join(', ')})</span>
                    )}
                    <span className="block text-[10px] text-[#8E8E88]">{fmtCount(b.eligible_innings)} eligible innings · latest {b.latest_innings_date} · {b.latest_team}</span>
                  </li>
                ))}
              </ul>
            )}
            {open && !player && query.trim() !== '' && suggestions.length === 0 && (
              <p role="status" className="absolute z-20 mt-1 w-full bg-[#17181C] border border-[#D9B15F]/30 rounded-lg px-3 py-2 text-xs text-[#B9B9B3]">
                No {includeInactive ? '' : `${options.latest_season} `}player with eligible batting innings matches “{query.trim()}”.
              </p>
            )}
          </div>
        </Field>
        <div className="space-y-1">
          <label className="inline-flex items-center gap-2 text-xs text-[#B9B9B3] cursor-pointer">
            <input type="checkbox" checked={includeInactive} onChange={(e) => toggleInactive(e.target.checked)}
              className={`w-4 h-4 accent-[#D9B15F] ${FOCUS_RING}`} />
            Include players without a {options.latest_season} appearance
          </label>
          <p className="text-[10px] text-[#8E8E88]">
            {includeInactive
              ? `All ${fmtCount(options.batters.length)} players with eligible batting history. A forecast for someone who did not appear in ${options.latest_season} assumes they play again.`
              : `${fmtCount(activeCount)} players who were in a ${options.latest_season} match squad.`}
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field id="bt-batting_team" label="Player's team" errors={errors.batting_team}>
            <TeamSelect id="bt-batting_team" value={form.batting_team} teams={options.teams} onChange={(v) => set('batting_team', v)} invalid={!!errors.batting_team} describedBy={describe('bt-batting_team', errors.batting_team)} />
          </Field>
          <Field id="bt-opponent" label="Opponent" errors={errors.opponent}>
            <TeamSelect id="bt-opponent" value={form.opponent} teams={options.teams} onChange={(v) => set('opponent', v)} invalid={!!errors.opponent} describedBy={describe('bt-opponent', errors.opponent)} />
          </Field>
        </div>
        <Field id="bt-venue" label="Venue" errors={errors.venue}>
          <VenueSelect id="bt-venue" value={form.venue} venues={options.venues} latestSeason={options.latest_season} onChange={(v) => set('venue', v)} invalid={!!errors.venue} describedBy={describe('bt-venue', errors.venue)} />
        </Field>
        <Field id="bt-match_date" label="Match date" hint={`Must be after ${earliestDate}, the last match in the data or the player's latest eligible innings.`} errors={errors.match_date}>
          <input
            id="bt-match_date"
            type="date"
            min={nextDay(earliestDate)}
            value={form.match_date}
            onChange={(e) => set('match_date', e.target.value)}
            className={`${INPUT} ${inputBorder(!!errors.match_date)} [color-scheme:dark]`}
            {...describe('bt-match_date', errors.match_date, 'hint')}
          />
        </Field>

        <GeneralErrors messages={general} />
        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" disabled={loading} className={PRIMARY_BUTTON}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Target className="w-4 h-4" aria-hidden="true" />}
            {loading ? 'Predicting…' : 'Predict milestones'}
          </button>
        </div>
        <Note>{options.batter_date_rule}</Note>
      </form>

      <section aria-label="Batter milestone result" aria-live="polite" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 space-y-4 min-w-0">
        {failure && lastPayload.current && <ErrorRetry message={failure} onRetry={() => run(lastPayload.current as BatterPredictionRequest)} />}
        {loading && !result && (
          <p className="text-xs text-[#B9B9B3] flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> Asking the batter model…</p>
        )}
        {!result && !loading && !failure && (
          <p className="text-sm text-[#8E8E88]">Pick a player, the teams, a venue and a date, then press <span className="text-[#F6F6F3] font-semibold">Predict milestones</span>.</p>
        )}
        {result && (
          <div className="space-y-4">
            <p className="text-[11px] uppercase tracking-wider font-bold text-[#D9B15F]">
              {result.player_name} · {result.date}
            </p>
            <div className="grid grid-cols-2 gap-4">
              <BigNumber value={result.chance_30_plus_pct} label="chance of 30 or more runs" />
              <BigNumber value={result.chance_50_plus_pct} label="chance of 50 or more runs" />
            </div>
            <p className="text-sm text-[#F6F6F3]">
              Out of 100 similar innings, about <strong>{Math.round(result.chance_30_plus * 100)}</strong> reached 30 or more and about{' '}
              <strong>{Math.round(result.chance_50_plus * 100)}</strong> reached 50 or more.
            </p>
            <p className="text-xs text-[#B9B9B3]">
              For {result.batting_team} against {result.opponent} at {result.venue}. {result.scope}
              {result.return_note && <span className="block mt-1 text-[#E5C687]">{result.return_note}</span>}
            </p>
            <div className="bg-[#101114] border border-white/5 rounded-xl p-3 text-xs text-[#B9B9B3] space-y-2">
              <p>
                <span className="text-[#F6F6F3] font-semibold">Form used:</span> {fmtCount(result.form_context.prior_eligible_innings)} prior eligible innings, the latest on {result.form_context.latest_innings_date}.
              </p>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-[#8E8E88] font-bold mb-1">Latest {result.form_context.recent_innings.length} eligible innings</p>
                <ul className="space-y-0.5">
                  {result.form_context.recent_innings.map((r) => (
                    <li key={`${r.date}-${r.opponent}`} className="flex justify-between gap-3">
                      <span className="min-w-0 truncate">{r.date} v {r.opponent}</span>
                      <span className="font-mono text-[#F6F6F3]">{r.runs}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <p className="text-[10px] text-[#8E8E88]">{result.form_context.definition}</p>
            </div>
            {holdout && constant ? (
              <div className="bg-[#101114] border border-white/5 rounded-xl p-3 text-xs text-[#B9B9B3] space-y-1">
                <p>
                  <span className="text-[#F6F6F3] font-semibold">For context:</span> of the {fmtCount(Number(holdout.rows))} eligible innings in the 2026 holdout season,{' '}
                  {pct1(Number(holdout.observed_30_rate))} reached 30+ and {pct1(Number(holdout.observed_50_rate))} reached 50+.
                </p>
                <p>
                  The holdout version of this model (trained through 2025) scored Brier {dec4(Number(holdout.brier_30))} (30+) and {dec4(Number(holdout.brier_50))} (50+),
                  against {dec4(Number(constant.brier_30))} and {dec4(Number(constant.brier_50))} for constant-rate forecasts (lower is better).
                </p>
              </div>
            ) : (
              <Note>The evaluation report could not be loaded, so the base rates are not shown.</Note>
            )}
            <p className="text-[11px] text-[#8E8E88]">
              Model <span className="font-mono text-[#B9B9B3]">{result.model}</span> · deployment model trained on {result.training_span} data
              ({result.model_file}). {result.notice}
            </p>
            <div className="flex flex-wrap items-center gap-3">
              {savedId ? (
                <span className="inline-flex items-center gap-2 text-xs font-semibold text-emerald-300" role="status">
                  <Check className="w-4 h-4" aria-hidden="true" /> Saved.{' '}
                  <Link to="/tracker" className={`underline text-[#D9B15F] ${FOCUS_RING}`}>Open the Prediction Tracker</Link>
                </span>
              ) : (
                <button type="button" onClick={() => setSavedId(saveBatterPrediction(result))} className={SECONDARY_BUTTON}>
                  <BookmarkPlus className="w-4 h-4" aria-hidden="true" /> Save to Tracker
                </button>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
