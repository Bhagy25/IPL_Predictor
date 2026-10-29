import React, { useEffect, useState } from 'react';
import { Cpu, Loader2, Zap } from 'lucide-react';
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

/** One model's official 2026 holdout numbers next to the constant-rate forecast. */
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
            ? <>Deployment model <span className="font-mono">{m.name}</span>, trained on {m.training_span} ({fmtCount(m.rows.final_refit_2008_2026)} rows).</>
            : <span className="text-red-300">Unavailable: {m.status_detail}</span>}
        </p>
      </div>
      <table className="w-full text-xs">
        <caption className="text-left text-[11px] text-[#B9B9B3] pb-1">
          2026 holdout ({fmtCount(m.rows.test_2026_rows)} {m.kind === 'wicket' ? 'next overs' : 'innings'} in {m.rows.test_2026_matches} matches), holdout model trained through 2025
        </caption>
        <thead>
          <tr className="text-[#8E8E88] text-[10px] uppercase">
            <th scope="col" className="text-left font-bold py-1">Metric</th>
            <th scope="col" className="text-right font-bold py-1">Model</th>
            <th scope="col" className="text-right font-bold py-1">Constant rate</th>
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
        Chosen on 2025 validation only ({m.selection_metric}). Brier and log loss: lower is better. ROC AUC: higher is better; 0.5 is no ranking skill.
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
            Ask the two trained Stage 3 models about a situation you describe: wicket risk in the next over, and a batter's chance of 30+ and 50+.
          </p>
        </div>
        {models && (
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#151619] border border-[#D9B15F]/30 text-xs font-medium text-[#D9B15F] self-start sm:self-center max-w-full">
            <Cpu className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
            <span>{models.models.filter((m) => m.available).length} of {models.models.length} deployment models ready</span>
          </div>
        )}
      </div>

      <Disclaimer />

      {optionsError && <ErrorRetry message={optionsError} onRetry={() => setReload((n) => n + 1)} />}
      {!options && !optionsError && (
        <p className="text-sm text-[#B9B9B3] flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> Loading teams, venues and players…</p>
      )}

      {options && (
        <section aria-label="Prediction tools" className="space-y-4">
          <Tabs label="Prediction tools" idPrefix="arena" tabs={TOOLS} active={tool} onChange={setTool}>
            {available === false && (
              <ErrorRetry
                message={`The ${tool === 'wicket' ? 'wicket' : 'batter'} model is unavailable on the server, so no prediction can be made. ${model(tool)?.status_detail ?? ''}`}
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
            <p className="text-xs sm:text-sm text-[#B9B9B3]">{models.holdout_statement}</p>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {models.models.map((m) => <EvaluationCard key={m.kind} m={m} />)}
            </div>
            <Note>Source: {models.source}. The full replay of the 2026 holdout forecasts is on the Prediction Tracker page.</Note>
          </>
        )}
      </section>
    </div>
  );
};
