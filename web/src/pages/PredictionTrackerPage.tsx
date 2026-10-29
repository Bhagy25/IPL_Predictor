import React, { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Download, HardDrive, ListChecks, Trash2, Upload } from 'lucide-react';
import { FOCUS_RING } from '../components/player/playerFormat';
import { fmtCount } from '../utils/format';
import { DANGER_BUTTON, INPUT, Note, SECONDARY_BUTTON, dec4, inputBorder, pct1 } from '../components/predict/shared';
import { HoldoutReplay } from '../components/predict/HoldoutReplay';
import {
  BatterEntry, BinaryForecast, MAX_RUNS, STORAGE_KEY, TrackerEntry, WicketEntry, brier, clearAll, exportFile, hitRateBins,
  importEntries, parseTrackerFile, removeEntry, resolvedForecasts, setOutcome, useTracker,
} from '../components/predict/trackerStore';

const MIN_MEANINGFUL = 20;
const LABELS: BinaryForecast['label'][] = ['Wicket next over', 'Batter 30+', 'Batter 50+'];

const savedAt = (iso: string) => new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });

const StatusPill: React.FC<{ resolved: boolean }> = ({ resolved }) => (
  <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${resolved ? 'text-emerald-300 border-emerald-500/40 bg-emerald-950/30' : 'text-[#D9B15F] border-[#D9B15F]/40 bg-[#D9B15F]/10'}`}>
    {resolved ? 'Resolved' : 'Pending'}
  </span>
);

/** Two-step delete inside the card, never a browser dialog. */
const RemoveButton: React.FC<{ onConfirm: () => void }> = ({ onConfirm }) => {
  const [asking, setAsking] = useState(false);
  return asking ? (
    <span className="inline-flex items-center gap-2 text-xs text-[#B9B9B3]">
      Remove this prediction?
      <button type="button" className={DANGER_BUTTON} onClick={onConfirm}>Remove</button>
      <button type="button" className={SECONDARY_BUTTON} onClick={() => setAsking(false)}>Keep</button>
    </span>
  ) : (
    <button type="button" className={`text-xs text-[#8E8E88] hover:text-red-300 underline ${FOCUS_RING}`} onClick={() => setAsking(true)}>Remove</button>
  );
};

const WicketCard: React.FC<{ e: WicketEntry }> = ({ e }) => {
  const i = e.inputs;
  const nextOver = i.completed_overs + 1;
  const name = `wicket-outcome-${e.id}`;
  const value = e.outcome === null ? 'pending' : e.outcome.wicket_fell ? 'yes' : 'no';
  const score = e.outcome === null ? null : (e.prediction.probability - (e.outcome.wicket_fell ? 1 : 0)) ** 2;
  return (
    <div className="space-y-3">
      <div>
        <p className="text-sm text-[#F6F6F3] font-semibold">{e.prediction.probability_pct.toFixed(1)}% chance of a wicket in over {nextOver}</p>
        <p className="text-xs text-[#B9B9B3]">
          {i.batting_team} {i.runs}/{i.wickets} after {i.completed_overs} overs (innings {i.innings}, last over {i.last_over_runs}/{i.last_over_wickets})
          against {i.bowling_team} at {i.venue}
        </p>
      </div>
      <fieldset className="flex flex-wrap items-center gap-2">
        <legend className="text-[11px] text-[#B9B9B3] font-semibold mb-1">Did a wicket fall in over {nextOver}?</legend>
        {[['yes', 'Yes'], ['no', 'No'], ['pending', 'Not known yet']].map(([v, label]) => (
          <label key={v} className={`px-3 py-1 rounded-full text-xs font-semibold cursor-pointer border focus-within:ring-2 focus-within:ring-[#D9B15F] ${value === v ? 'bg-[#D9B15F] text-[#0D0E10] border-[#D9B15F]' : 'bg-[#101114] text-[#B9B9B3] border-[#D9B15F]/20'}`}>
            <input type="radio" className="sr-only" name={name} value={v} checked={value === v}
              onChange={() => setOutcome(e.id, v === 'pending' ? null : { wicket_fell: v === 'yes' })} />
            {label}
          </label>
        ))}
        {score !== null && <span className="text-[11px] text-[#8E8E88]">Brier for this prediction: {dec4(score)}</span>}
      </fieldset>
    </div>
  );
};

const BatterCard: React.FC<{ e: BatterEntry }> = ({ e }) => {
  const i = e.inputs;
  const [draft, setDraft] = useState(e.outcome ? String(e.outcome.runs) : '');
  const [error, setError] = useState<string | null>(null);
  const id = `runs-${e.id}`;
  const save = () => {
    const v = draft.trim();
    if (!/^\d+$/.test(v) || Number(v) > MAX_RUNS) {
      setError(`Enter the runs scored as a whole number from 0 to ${MAX_RUNS}.`);
      return;
    }
    setError(null);
    setOutcome(e.id, { runs: Number(v) });
  };
  return (
    <div className="space-y-3">
      <div>
        <p className="text-sm text-[#F6F6F3] font-semibold">
          {i.player_name}: {e.prediction.chance_30_plus_pct.toFixed(1)}% for 30+, {e.prediction.chance_50_plus_pct.toFixed(1)}% for 50+
        </p>
        <p className="text-xs text-[#B9B9B3]">
          For {i.batting_team} against {i.opponent} at {i.venue} on {i.match_date} · {fmtCount(e.prediction.prior_eligible_innings)} prior eligible innings
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex flex-col gap-1">
          <label htmlFor={id} className="text-[11px] text-[#B9B9B3] font-semibold">Runs scored</label>
          <input id={id} type="number" inputMode="numeric" min={0} max={MAX_RUNS} step={1} value={draft}
            onChange={(ev) => { setDraft(ev.target.value); setError(null); }}
            onKeyDown={(ev) => { if (ev.key === 'Enter') save(); }}
            aria-invalid={error ? true : undefined} aria-describedby={error ? `${id}-error` : undefined}
            className={`${INPUT} ${inputBorder(!!error)} w-28`} />
        </div>
        <button type="button" className={SECONDARY_BUTTON} onClick={save}>Save runs</button>
        {e.outcome !== null && (
          <button type="button" className={SECONDARY_BUTTON} onClick={() => { setOutcome(e.id, null); setDraft(''); }}>Mark pending</button>
        )}
        {e.outcome !== null && (
          <span className="text-[11px] text-[#8E8E88]">
            Recorded {e.outcome.runs}: 30+ {e.outcome.runs >= 30 ? 'yes' : 'no'}, 50+ {e.outcome.runs >= 50 ? 'yes' : 'no'}
          </span>
        )}
      </div>
      {error && <p id={`${id}-error`} className="text-[11px] text-red-300">{error}</p>}
      <p className="text-[10px] text-[#8E8E88]">If the player did not bat, leave it pending: the forecast assumes they bat.</p>
    </div>
  );
};

const EntryCard: React.FC<{ e: TrackerEntry }> = ({ e }) => (
  <li className="bg-[#101114] border border-white/5 rounded-xl p-4 space-y-3">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-bold uppercase tracking-wider text-[#D9B15F]">{e.kind === 'wicket' ? 'Next-over wicket risk' : 'Batter milestones'}</span>
        <StatusPill resolved={e.outcome !== null} />
      </div>
      <span className="text-[11px] text-[#8E8E88]">Saved {savedAt(e.saved_at)}</span>
    </div>
    {e.kind === 'wicket' ? <WicketCard e={e} /> : <BatterCard e={e} />}
    <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-white/5">
      <span className="text-[10px] text-[#8E8E88]">Model {e.prediction.model} · trained on {e.prediction.training_span}</span>
      <RemoveButton onConfirm={() => removeEntry(e.id)} />
    </div>
  </li>
);

const Summary: React.FC<{ entries: TrackerEntry[] }> = ({ entries }) => {
  const resolved = entries.filter((e) => e.outcome !== null).length;
  const forecasts = resolvedForecasts(entries);
  if (!resolved) {
    return <p className="text-sm text-[#8E8E88]">No resolved predictions yet. Record an outcome above to score a prediction.</p>;
  }
  return (
    <div className="space-y-4">
      {resolved < MIN_MEANINGFUL && (
        <div role="note" className="bg-[#2A2414] border border-[#D9B15F]/40 rounded-xl p-3 text-xs text-[#E5C687] flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
          <span>
            Only {resolved} resolved {resolved === 1 ? 'prediction' : 'predictions'}. With fewer than {MIN_MEANINGFUL}, these scores mostly reflect
            chance and say little about the model.
          </span>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <caption className="text-left text-[11px] text-[#B9B9B3] pb-2">
            {resolved} resolved {resolved === 1 ? 'prediction' : 'predictions'} ({forecasts.length} yes/no forecasts: one per wicket prediction, two per batter prediction)
          </caption>
          <thead>
            <tr className="text-[#8E8E88] text-[10px] uppercase">
              <th scope="col" className="text-left font-bold py-1 pr-3">Event</th>
              <th scope="col" className="text-right font-bold py-1 px-2">Forecasts</th>
              <th scope="col" className="text-right font-bold py-1 px-2">Brier</th>
              <th scope="col" className="text-right font-bold py-1 px-2">Avg forecast</th>
              <th scope="col" className="text-right font-bold py-1 pl-2">Happened</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {LABELS.map((label) => {
              const fs = forecasts.filter((f) => f.label === label);
              return (
                <tr key={label}>
                  <th scope="row" className="text-left font-medium text-[#B9B9B3] py-1 pr-3">{label}</th>
                  <td className="text-right font-mono text-[#F6F6F3] py-1 px-2">{fs.length}</td>
                  <td className="text-right font-mono text-[#F6F6F3] py-1 px-2">{fs.length ? dec4(brier(fs)) : '—'}</td>
                  <td className="text-right font-mono py-1 px-2">{fs.length ? pct1(fs.reduce((s, f) => s + f.p, 0) / fs.length) : '—'}</td>
                  <td className="text-right font-mono py-1 pl-2">{fs.length ? pct1(fs.filter((f) => f.happened).length / fs.length) : '—'}</td>
                </tr>
              );
            })}
            <tr>
              <th scope="row" className="text-left font-semibold text-[#F6F6F3] py-1 pr-3">All forecasts</th>
              <td className="text-right font-mono text-[#F6F6F3] py-1 px-2">{forecasts.length}</td>
              <td className="text-right font-mono text-[#F6F6F3] py-1 px-2">{dec4(brier(forecasts))}</td>
              <td className="text-right font-mono py-1 px-2">{pct1(forecasts.reduce((s, f) => s + f.p, 0) / forecasts.length)}</td>
              <td className="text-right font-mono py-1 pl-2">{pct1(forecasts.filter((f) => f.happened).length / forecasts.length)}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <caption className="text-left text-[11px] text-[#B9B9B3] pb-2">Hit rate by forecast range (all yes/no forecasts)</caption>
          <thead>
            <tr className="text-[#8E8E88] text-[10px] uppercase">
              <th scope="col" className="text-left font-bold py-1 pr-3">Forecast range</th>
              <th scope="col" className="text-right font-bold py-1 px-2">Forecasts</th>
              <th scope="col" className="text-right font-bold py-1 px-2">Avg forecast</th>
              <th scope="col" className="text-right font-bold py-1 pl-2">Happened</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {hitRateBins(forecasts).map((b) => (
              <tr key={b.lower}>
                <th scope="row" className="text-left font-medium text-[#B9B9B3] py-1 pr-3">{Math.round(b.lower * 100)}–{Math.round(b.upper * 100)}%</th>
                <td className="text-right font-mono text-[#F6F6F3] py-1 px-2">{b.n}</td>
                <td className="text-right font-mono py-1 px-2">{b.avgPredicted === null ? '—' : pct1(b.avgPredicted)}</td>
                <td className="text-right font-mono py-1 pl-2">{b.observed === null ? '—' : pct1(b.observed)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note>
        Brier score is the average of (forecast − outcome)², with the outcome 1 if the event happened and 0 if not: 0 is perfect, and always
        forecasting 50% scores 0.25. In a well-calibrated set, each forecast range's &ldquo;Happened&rdquo; rate is close to its average forecast.
      </Note>
    </div>
  );
};

export const PredictionTrackerPage: React.FC = () => {
  const { entries, storage, unreadable } = useTracker();
  const [confirmClear, setConfirmClear] = useState(false);
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const pending = entries.filter((e) => e.outcome === null).length;

  const doExport = () => {
    const blob = new Blob([JSON.stringify(exportFile(), null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cricketlens-predictions-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setMessage({ kind: 'ok', text: `Exported ${entries.length} ${entries.length === 1 ? 'prediction' : 'predictions'}.` });
  };

  const doImport = async (file: File) => {
    let data: unknown;
    try {
      data = JSON.parse(await file.text());
    } catch {
      setMessage({ kind: 'error', text: `${file.name} is not valid JSON. Nothing was imported.` });
      return;
    }
    const parsed = parseTrackerFile(data);
    if (!parsed.ok) {
      setMessage({ kind: 'error', text: `${file.name}: ${parsed.error}` });
      return;
    }
    const { added, skipped } = importEntries(parsed.entries);
    setMessage({ kind: 'ok', text: `Imported ${added} ${added === 1 ? 'prediction' : 'predictions'}${skipped ? `; ${skipped} already saved were left unchanged` : ''}.` });
  };

  return (
    <div className="space-y-8 max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-16">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#D9B15F]/20">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <span className="w-1.5 h-6 bg-[#D9B15F] rounded-full inline-block" />
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#F6F6F3]">Prediction Tracker</h1>
          </div>
          <p className="text-xs sm:text-sm text-[#B9B9B3] mt-1 ml-4 sm:ml-5">
            Record what happened after your saved predictions and see how they score, next to the official 2026 holdout replay.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#151619] border border-[#D9B15F]/30 text-xs font-medium text-[#D9B15F] self-start sm:self-center max-w-full">
          <ListChecks className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
          <span>{entries.length} saved · {pending} pending · {entries.length - pending} resolved</span>
        </div>
      </div>

      <section aria-labelledby="saved-title" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 id="saved-title" className="text-lg font-bold text-[#F6F6F3]">Your saved predictions</h2>
            <p className="text-xs text-[#B9B9B3] mt-1 flex items-start gap-1.5">
              <HardDrive className="w-3.5 h-3.5 flex-shrink-0 mt-px text-[#D9B15F]" aria-hidden="true" />
              <span><strong className="text-[#F6F6F3]">Stored only in this browser. Not shared, not used to retrain models.</strong></span>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className={SECONDARY_BUTTON} onClick={doExport} disabled={!entries.length}>
              <Download className="w-3.5 h-3.5" aria-hidden="true" /> Export JSON
            </button>
            <button type="button" className={SECONDARY_BUTTON} onClick={() => fileInput.current?.click()}>
              <Upload className="w-3.5 h-3.5" aria-hidden="true" /> Import JSON
            </button>
            <input ref={fileInput} type="file" accept="application/json,.json" className="hidden" aria-label="Import saved predictions from a JSON file"
              onChange={(ev) => { const f = ev.target.files?.[0]; if (f) doImport(f); ev.target.value = ''; }} />
            <button type="button" className={DANGER_BUTTON} onClick={() => { setConfirmClear(true); setMessage(null); }} disabled={!entries.length}>
              <Trash2 className="w-3.5 h-3.5" aria-hidden="true" /> Clear all
            </button>
          </div>
        </div>

        {storage !== 'available' && (
          <div role="alert" className="bg-[#2A2414] border border-[#D9B15F]/40 rounded-xl p-3 text-xs text-[#E5C687] flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            <span>
              {storage === 'unavailable'
                ? 'Browser storage is not available here (it may be blocked or disabled). Saved predictions are kept only while this page stays open and are lost on reload. Export them to keep a copy.'
                : 'The browser refused to save the latest change (storage may be full or blocked). It is kept for this visit only; export to keep a copy.'}
            </span>
          </div>
        )}
        {unreadable !== null && (
          <div role="alert" className="bg-[#2A2414] border border-[#D9B15F]/40 rounded-xl p-3 text-xs text-[#E5C687]">
            Saved data in this browser could not be read (it does not match the expected format). A copy was kept under the key
            <span className="font-mono"> {STORAGE_KEY}.unreadable</span>, and the tracker starts empty.
          </div>
        )}
        {confirmClear && (
          <div role="alertdialog" aria-labelledby="clear-title" className="bg-[#1C1517] border border-red-500/40 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3">
            <p id="clear-title" className="text-xs text-red-200 font-semibold">
              Delete all {entries.length} saved {entries.length === 1 ? 'prediction' : 'predictions'} from this browser? This cannot be undone; export first to keep a copy.
            </p>
            <div className="flex gap-2">
              <button type="button" className={DANGER_BUTTON} autoFocus
                onClick={() => { const n = entries.length; clearAll(); setConfirmClear(false); setMessage({ kind: 'ok', text: `Deleted ${n} saved ${n === 1 ? 'prediction' : 'predictions'}.` }); }}>
                Delete all
              </button>
              <button type="button" className={SECONDARY_BUTTON} onClick={() => setConfirmClear(false)}>Cancel</button>
            </div>
          </div>
        )}
        {message && (
          <p role="status" className={`text-xs font-semibold ${message.kind === 'ok' ? 'text-emerald-300' : 'text-red-300'}`}>{message.text}</p>
        )}

        {entries.length ? (
          <ul className="space-y-3" aria-label="Saved predictions">
            {entries.map((e) => <EntryCard key={e.id} e={e} />)}
          </ul>
        ) : (
          <p className="text-sm text-[#8E8E88]">
            No saved predictions yet. Make one in the <Link to="/predict" className={`underline text-[#D9B15F] ${FOCUS_RING}`}>Prediction Arena</Link> and press Save to Tracker,
            or import an exported file.
          </p>
        )}
      </section>

      <section aria-labelledby="summary-title" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 space-y-4">
        <h2 id="summary-title" className="text-lg font-bold text-[#F6F6F3]">How your saved predictions scored</h2>
        <Summary entries={entries} />
      </section>

      <HoldoutReplay />
    </div>
  );
};
