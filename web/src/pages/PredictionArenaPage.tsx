import React, { useEffect, useState } from 'react';
import { Loader2, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import { fetchPredictModels, fetchPredictOptions } from '../api/predict';
import { PredictionModelInfo, PredictionModelsResponse, PredictionOptionsResponse } from '../types';
import { Tabs } from '../components/player/ProfileSections';
import { fmtCount } from '../utils/format';
import { Disclaimer, ErrorRetry, Note, dec4 } from '../components/predict/shared';
import { WicketTool } from '../components/predict/WicketTool';
import { BatterTool } from '../components/predict/BatterTool';

const TOOLS = [
  { id: 'wicket', label: 'Next-Over Wicket Risk' },
  { id: 'batter', label: 'Batter Milestone (30+ / 50+)' },
];

/** One final model's 2026 retrospective test next to the class-prior (constant-rate) forecast. */
const EvaluationCard: React.FC<{ m: PredictionModelInfo }> = ({ m }) => {
  const h = m.holdout_2026;
  const c = m.holdout_2026_constant;
  const rows: [string, string, string][] = m.kind === 'wicket'
    ? [
      ['Brier score', dec4(Number(h.brier_score)), dec4(Number(c.brier_score))],
      ['Log loss', dec4(Number(h.log_loss)), dec4(Number(c.log_loss))],
      ['ROC AUC', dec4(Number(h.roc_auc)), dec4(Number(c.roc_auc))],
    ]
    : [
      ['Brier 30+', dec4(Number(h.brier_30)), dec4(Number(c.brier_30))],
      ['Brier 50+', dec4(Number(h.brier_50)), dec4(Number(c.brier_50))],
      ['Log loss (3 classes)', dec4(Number(h.multiclass_log_loss)), dec4(Number(c.multiclass_log_loss))],
      ['ROC AUC 30+', dec4(Number(h.roc_auc_30)), dec4(Number(c.roc_auc_30))],
      ['ROC AUC 50+', dec4(Number(h.roc_auc_50)), dec4(Number(c.roc_auc_50))],
    ];
  return (
    <div className="bg-[#101114] border border-white/5 rounded-xl p-4 space-y-3 min-w-0">
      <div>
        <h3 className="text-sm font-bold text-[#F6F6F3]">{m.title}</h3>
        <p className="text-[11px] text-[#8E8E88]">
          {m.available
            ? <>{m.algorithm}, refitted on {m.training_span} ({fmtCount(m.rows.final_refit_2008_2026)} {m.kind === 'wicket' ? 'next-over examples' : 'innings'}), is the model this tool uses.</>
            : <span className="text-red-300">This prediction tool is currently unavailable.</span>}
        </p>
      </div>
      <table className="w-full text-xs">
        <caption className="text-left text-[11px] text-[#B9B9B3] pb-1">
          2026 retrospective test ({fmtCount(m.rows.test_2026_rows)} {m.kind === 'wicket' ? 'next overs' : 'innings'} in {m.rows.test_2026_matches} matches), same algorithm trained through 2025
        </caption>
        <thead>
          <tr className="text-[#8E8E88] text-[10px] uppercase">
            <th scope="col" className="text-left font-bold py-1">Metric</th>
            <th scope="col" className="text-right font-bold py-1">Model</th>
            <th scope="col" className="text-right font-bold py-1">Class prior</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.map(([label, model, constant]) => (
            <tr key={label}>
              <th scope="row" className="text-left font-medium text-[#B9B9B3] py-1">{label}</th>
              <td className="text-right font-mono text-[#F6F6F3] py-1">{model}</td>
              <td className="text-right font-mono text-[#8E8E88] py-1">{constant}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[10px] text-[#8E8E88]">
        Chosen from seven algorithms by the {m.selection_metric}. Lower Brier scores and log loss are better. A higher ROC AUC is better, with 0.5 indicating no ranking skill.
      </p>
    </div>
  );
};

export const PredictionArenaPage: React.FC = () => {
  const [options, setOptions] = useState<PredictionOptionsResponse | null>(null);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [models, setModels] = useState<PredictionModelsResponse | null>(null);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [tool, setTool] = useState('wicket');

  useEffect(() => {
    const ctl = new AbortController();
    setOptionsError(null);
    setModelsError(null);
    fetchPredictOptions(ctl.signal).then(setOptions).catch((e: Error) => { if (e.name !== 'AbortError') setOptionsError(e.message); });
    fetchPredictModels(ctl.signal).then(setModels).catch((e: Error) => { if (e.name !== 'AbortError') setModelsError(e.message); });
    return () => ctl.abort();
  }, [reload]);

  const model = (kind: string) => models?.models.find((m) => m.kind === kind) ?? null;
  const available = options?.models_available[tool];

  return (
    <div className="space-y-8 max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-16">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#D9B15F]/20">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <span className="w-1.5 h-6 bg-[#D9B15F] rounded-full inline-block" />
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#F6F6F3]">Prediction Arena</h1>
          </div>
          <p className="text-xs sm:text-sm text-[#B9B9B3] mt-1 ml-4 sm:ml-5">
            Estimate the chance of a wicket in the next over or a batter reaching 30 or 50 runs.
          </p>
        </div>
      </div>

      <Disclaimer />

      {optionsError && <ErrorRetry message={optionsError} onRetry={() => setReload((n) => n + 1)} />}
      {!options && !optionsError && (
        <p role="status" className="text-sm text-[#B9B9B3] flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> Loading teams, venues and players…</p>
      )}

      {options && (
        <section aria-label="Prediction tools" className="space-y-4">
          <Tabs label="Prediction tools" idPrefix="arena" tabs={TOOLS} active={tool} onChange={setTool}>
            {available === false && (
              <ErrorRetry
                message={`The ${tool === 'wicket' ? 'wicket risk' : 'batter milestone'} tool is currently unavailable.`}
                onRetry={() => setReload((n) => n + 1)}
              />
            )}
            {/* Both tools stay mounted so switching tabs keeps what was entered */}
            <div hidden={tool !== 'wicket' || available === false}>
              <WicketTool options={options} model={model('wicket')} />
            </div>
            <div hidden={tool !== 'batter' || available === false}>
              <BatterTool options={options} model={model('batter')} />
            </div>
          </Tabs>
        </section>
      )}

      <section aria-label="How the models were evaluated" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 space-y-4">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#D9B15F]">
          <Zap className="w-4 h-4" aria-hidden="true" /> How the models were evaluated
        </div>
        {modelsError && <ErrorRetry message={modelsError} onRetry={() => setReload((n) => n + 1)} />}
        {models && (
          <>
            <p className="text-xs sm:text-sm text-[#B9B9B3]">
              Both tools use Histogram gradient boosting, the algorithm a benchmark of seven algorithms selected. The 2026 test used the same algorithm and settings trained through 2025; 2026 had already been examined during development, so it is a retrospective test. The tools use models refitted through 2026, which have no independent test season yet.
            </p>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {models.models.map((m) => <EvaluationCard key={m.kind} m={m} />)}
            </div>
            <Note>See the 2026 forecasts and match results in the <Link to="/tracker" className="text-[#D9B15F] underline">Prediction Tracker</Link>.</Note>
          </>
        )}
      </section>
    </div>
  );
};
