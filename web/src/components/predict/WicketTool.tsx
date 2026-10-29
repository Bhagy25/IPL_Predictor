import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookmarkPlus, Check, Loader2, Target } from 'lucide-react';
import { ApiError, predictWicket } from '../../api/predict';
import { PredictionModelInfo, PredictionOptionsResponse, WicketPredictionRequest, WicketPredictionResponse } from '../../types';
import { FOCUS_RING } from '../player/playerFormat';
import { fmtCount } from '../../utils/format';
import {
  BigNumber, ErrorRetry, Field, FieldErrors, GeneralErrors, INPUT, Note, PRIMARY_BUTTON, SECONDARY_BUTTON,
  TeamSelect, VenueSelect, dec4, describe, inputBorder, pct1,
} from './shared';
import { saveWicketPrediction } from './trackerStore';

type Form = Record<keyof WicketPredictionRequest, string>;

const EMPTY: Form = {
  batting_team: '', bowling_team: '', venue: '', innings: '1', completed_overs: '', runs: '', wickets: '',
  last_over_runs: '', last_over_wickets: '',
};

const WHOLE = /^\d+$/;

/** The API's rules (predict_wicket.forecast() plus team and venue membership), checked before sending. */
export function validateWicket(f: Form, options: PredictionOptionsResponse): { errors: FieldErrors; payload: WicketPredictionRequest | null } {
  const errors: FieldErrors = {};
  const add = (k: string, m: string) => { (errors[k] ??= []).push(m); };
  const num = (k: keyof Form, label: string): number | null => {
    if (f[k].trim() === '') { add(k, `${label} is required.`); return null; }
    if (!WHOLE.test(f[k].trim())) { add(k, `${label} must be a whole number, 0 or more.`); return null; }
    return Number(f[k]);
  };
  const teams = new Set(options.teams.map((t) => t.name));
  if (!f.batting_team) add('batting_team', 'Choose the batting team.');
  else if (!teams.has(f.batting_team)) add('batting_team', 'Choose one of the listed teams.');
  if (!f.bowling_team) add('bowling_team', 'Choose the bowling team.');
  else if (!teams.has(f.bowling_team)) add('bowling_team', 'Choose one of the listed teams.');
  else if (f.bowling_team === f.batting_team) add('bowling_team', 'The two teams must be different.');
  if (!f.venue) add('venue', 'Choose a venue.');
  else if (!options.venues.some((v) => v.name === f.venue)) add('venue', 'Choose one of the listed venues.');
  const innings = Number(f.innings);
  if (innings !== 1 && innings !== 2) add('innings', 'Innings must be 1 or 2.');
  const overs = num('completed_overs', 'Completed overs');
  if (overs !== null && (overs < 1 || overs > 19)) add('completed_overs', 'Completed overs must be from 1 to 19.');
  const runs = num('runs', 'Runs');
  const wickets = num('wickets', 'Wickets');
  if (wickets !== null && wickets > 9) add('wickets', 'Wickets must be from 0 to 9 (10 wickets ends the innings).');
  const lastRuns = num('last_over_runs', 'Last-over runs');
  if (lastRuns !== null && runs !== null && lastRuns > runs) add('last_over_runs', 'Runs in the last over cannot exceed the current runs.');
  const lastWkts = num('last_over_wickets', 'Last-over wickets');
  if (lastWkts !== null && wickets !== null && lastWkts > wickets) add('last_over_wickets', 'Wickets in the last over cannot exceed the current wickets.');
  if (Object.keys(errors).length) return { errors, payload: null };
  return {
    errors,
    payload: {
      batting_team: f.batting_team, bowling_team: f.bowling_team, venue: f.venue, innings,
      completed_overs: overs as number, runs: runs as number, wickets: wickets as number,
      last_over_runs: lastRuns as number, last_over_wickets: lastWkts as number,
    },
  };
}

const PHASE_LABEL: Record<string, string> = { powerplay: 'Powerplay', middle: 'Middle overs', death: 'Death overs' };

export const WicketTool: React.FC<{
  options: PredictionOptionsResponse;
  model: PredictionModelInfo | null;
}> = ({ options, model }) => {
  const [form, setForm] = useState<Form>(EMPTY);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [general, setGeneral] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [result, setResult] = useState<WicketPredictionResponse | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const lastPayload = useRef<WicketPredictionRequest | null>(null);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => controller.current?.abort(), []);

  const set = (k: keyof Form, v: string) => {
    setForm((f) => ({ ...f, [k]: v }));
    // A result always belongs to the inputs on screen: drop it and any request still running
    controller.current?.abort();
    setLoading(false);
    setResult(null);
    setSavedId(null);
    setFailure(null);
    setErrors((e) => { const rest = { ...e }; delete rest[k]; return rest; });
  };

  const run = async (payload: WicketPredictionRequest) => {
    controller.current?.abort();
    const ctl = new AbortController();
    controller.current = ctl;
    lastPayload.current = payload;
    setLoading(true);
    setFailure(null);
    setGeneral([]);
    try {
      const r = await predictWicket(payload, ctl.signal);
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
    const { errors: found, payload } = validateWicket(form, options);
    setErrors(found);
    setGeneral([]);
    if (payload) run(payload);
  };

  const holdout = model?.holdout_2026;
  const constant = model?.holdout_2026_constant;
  const nextOver = result ? result.inputs.completed_overs + 1 : null;
  const teamCode = (name: string) => options.teams.find((t) => t.name === name)?.code ?? name;

  const numberField = (k: keyof Form, label: string, hint: string, max?: number) => (
    <Field id={`wk-${k}`} label={label} hint={hint} errors={errors[k]}>
      <input
        id={`wk-${k}`}
        type="number"
        inputMode="numeric"
        min={0}
        max={max}
        step={1}
        value={form[k]}
        onChange={(e) => set(k, e.target.value)}
        className={`${INPUT} ${inputBorder(!!errors[k])}`}
        {...describe(`wk-${k}`, errors[k], hint)}
      />
    </Field>
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] gap-6">
      <form onSubmit={submit} noValidate aria-label="Next-over wicket risk inputs" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field id="wk-batting_team" label="Batting team" errors={errors.batting_team}>
            <TeamSelect id="wk-batting_team" value={form.batting_team} teams={options.teams} onChange={(v) => set('batting_team', v)} invalid={!!errors.batting_team} describedBy={describe('wk-batting_team', errors.batting_team)} />
          </Field>
          <Field id="wk-bowling_team" label="Bowling team" errors={errors.bowling_team}>
            <TeamSelect id="wk-bowling_team" value={form.bowling_team} teams={options.teams} onChange={(v) => set('bowling_team', v)} invalid={!!errors.bowling_team} describedBy={describe('wk-bowling_team', errors.bowling_team)} />
          </Field>
        </div>
        <Field id="wk-venue" label="Venue" errors={errors.venue}>
          <VenueSelect id="wk-venue" value={form.venue} venues={options.venues} latestSeason={options.latest_season} onChange={(v) => set('venue', v)} invalid={!!errors.venue} describedBy={describe('wk-venue', errors.venue)} />
        </Field>

        <fieldset className="space-y-1">
          <legend className="text-[11px] text-[#B9B9B3] font-semibold">Innings</legend>
          <div className="inline-flex rounded-lg bg-[#101114] p-1 border border-[#D9B15F]/20">
            {['1', '2'].map((v) => (
              <label key={v} className={`px-4 py-1.5 rounded-md text-xs font-bold cursor-pointer focus-within:ring-2 focus-within:ring-[#D9B15F] ${form.innings === v ? 'bg-[#D9B15F] text-[#0D0E10]' : 'text-[#B9B9B3]'}`}>
                <input type="radio" name="wk-innings" value={v} checked={form.innings === v} onChange={() => set('innings', v)} className="sr-only" />
                {v === '1' ? '1st innings' : '2nd innings'}
              </label>
            ))}
          </div>
          {errors.innings && <p className="text-[11px] text-red-300">{errors.innings.join(' ')}</p>}
        </fieldset>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {numberField('completed_overs', 'Completed overs', '1 to 19', 19)}
          {numberField('runs', 'Runs', '0 or more')}
          {numberField('wickets', 'Wickets', '0 to 9', 9)}
          {numberField('last_over_runs', 'Last-over runs', '0 to current runs')}
          {numberField('last_over_wickets', 'Last-over wickets', '0 to current wickets', 9)}
        </div>

        <GeneralErrors messages={general} />
        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" disabled={loading} className={PRIMARY_BUTTON}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Target className="w-4 h-4" aria-hidden="true" />}
            {loading ? 'Predicting…' : 'Predict wicket risk'}
          </button>
          <button type="button" onClick={() => { setForm(EMPTY); setErrors({}); setGeneral([]); setResult(null); setFailure(null); setSavedId(null); }} className={SECONDARY_BUTTON}>
            Reset
          </button>
        </div>
        <Note>Enter the score after the last completed over. The model predicts the over that comes next.</Note>
      </form>

      <section aria-label="Wicket risk result" aria-live="polite" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 space-y-4 min-w-0">
        {failure && lastPayload.current && <ErrorRetry message={failure} onRetry={() => run(lastPayload.current as WicketPredictionRequest)} />}
        {loading && !result && (
          <p className="text-xs text-[#B9B9B3] flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> Asking the wicket model…</p>
        )}
        {!result && !loading && !failure && (
          <p className="text-sm text-[#8E8E88]">Fill in the match situation and press <span className="text-[#F6F6F3] font-semibold">Predict wicket risk</span>. The result appears here.</p>
        )}
        {result && nextOver !== null && (
          <div className="space-y-4">
            <p className="text-[11px] uppercase tracking-wider font-bold text-[#D9B15F]">
              Over {nextOver} · {PHASE_LABEL[result.phase] ?? result.phase} · Innings {result.inputs.innings}
            </p>
            <BigNumber value={result.probability_pct} label={`chance of ${result.event} (over ${nextOver})`} />
            <p className="text-sm text-[#F6F6F3]">
              Out of 100 similar situations, about <strong>{Math.round(result.probability * 100)}</strong> had at least one wicket in the next over.
            </p>
            <p className="text-xs text-[#B9B9B3]">
              {teamCode(result.inputs.batting_team)} {result.inputs.runs}/{result.inputs.wickets} after {result.inputs.completed_overs} overs
              (last over {result.inputs.last_over_runs}/{result.inputs.last_over_wickets}) against {teamCode(result.inputs.bowling_team)} at {result.inputs.venue}.
            </p>
            {holdout && constant ? (
              <div className="bg-[#101114] border border-white/5 rounded-xl p-3 text-xs text-[#B9B9B3] space-y-1">
                <p>
                  <span className="text-[#F6F6F3] font-semibold">For context:</span> in the {fmtCount(Number(holdout.rows))} eligible next overs of the 2026 holdout season,{' '}
                  {pct1(Number(holdout.event_rate))} had at least one wicket.
                </p>
                <p>
                  On that season the holdout version of this model (trained through 2025) scored Brier {dec4(Number(holdout.brier_score))} against{' '}
                  {dec4(Number(constant.brier_score))} for a constant-rate forecast (lower is better).
                </p>
              </div>
            ) : (
              <Note>The evaluation report could not be loaded, so the base rate is not shown.</Note>
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
                <button type="button" onClick={() => setSavedId(saveWicketPrediction(result))} className={SECONDARY_BUTTON}>
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
