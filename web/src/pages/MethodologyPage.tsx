import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle, BookOpen, Boxes, ChevronRight, Database, FlaskConical, GitCompareArrows, Loader2, Target, TrendingUp, Trophy,
} from 'lucide-react';
import { fetchMethodology } from '../api/methodology';
import { MethodologyHoldout, MethodologyResponse, MethodologyTaskKind } from '../types';
import { fmtCount } from '../utils/format';
import { DataTable } from '../components/player/ProfileSections';
import { FOCUS_RING } from '../components/player/playerFormat';
import { ErrorRetry } from '../components/predict/shared';
import { ReadingGuide, Section, TASK_LABEL, VerdictBadge, num, pct2 } from '../components/methodology/common';
import { CalibrationChart, LearningCurves, PairedGaps } from '../components/methodology/Charts';
import { AlgorithmCards, ComparisonTable } from '../components/methodology/Comparison';

const CLASS_NAMES: Record<MethodologyTaskKind, string[]> = { wicket: ['No wicket', 'Wicket'], batter: ['Under 30', '30–49', '50+'] };

const SECTIONS = [
  ['workflow', 'Workflow'], ['questions', 'Questions'], ['data', 'Data assumptions'], ['algorithms', 'Algorithms'],
  ['comparison', 'Comparison'], ['convergence', 'Convergence'], ['final', 'Final model'], ['limitations', 'Limitations'],
];

const HoldoutCard: React.FC<{ task: MethodologyTaskKind; h: MethodologyHoldout }> = ({ task, h }) => {
  const m = h.metrics;
  const b = h.baseline_metrics;
  const rows: [string, string, string][] = [
    ['Brier score (lower is better)', num(m.brier, 5), num(b.brier, 5)],
    ['Log loss (lower is better)', num(m.log_loss, 5), num(b.log_loss, 5)],
    ['ROC-AUC (0.5 = no skill)', num(m.roc_auc, 4), num(b.roc_auc, 4)],
    ['Accuracy', pct2(m.accuracy), pct2(b.accuracy)],
    ['Balanced accuracy', pct2(m.balanced_accuracy), pct2(b.balanced_accuracy)],
  ];
  const names = CLASS_NAMES[task];
  return (
    <div className="bg-[#101114] border border-white/5 rounded-xl p-4 space-y-4 min-w-0">
      <div>
        <h3 className="text-sm font-bold text-[#F6F6F3]">{TASK_LABEL[task]}</h3>
        <p className="text-[11px] text-[#8E8E88]">
          Trained on {fmtCount(h.train_rows)} rows from {fmtCount(h.train_matches)} matches ({h.train_start} to {h.train_end}); tested on {fmtCount(h.rows)} rows from {h.matches} matches in 2026.
        </p>
      </div>
      <table className="w-full text-xs">
        <caption className="text-left text-[11px] text-[#B9B9B3] pb-1">2026 scores, gradient boosting vs the class-prior baseline trained on the same rows</caption>
        <thead>
          <tr className="text-[#8E8E88] text-[10px] uppercase">
            <th scope="col" className="text-left py-1">Metric</th>
            <th scope="col" className="text-right py-1">Boosting</th>
            <th scope="col" className="text-right py-1">Class prior</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.map(([label, model, base]) => (
            <tr key={label}>
              <th scope="row" className="text-left font-medium text-[#B9B9B3] py-1">{label}</th>
              <td className="text-right font-mono text-[#F6F6F3] py-1">{model}</td>
              <td className="text-right font-mono text-[#8E8E88] py-1">{base}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div>
        <h4 className="text-xs font-bold text-[#F6F6F3] mb-1">Calibration</h4>
        <CalibrationChart bins={h.calibration} task={task} />
      </div>
      <div className="overflow-x-auto">
        <table className="text-xs">
          <caption className="text-left text-[11px] text-[#B9B9B3] pb-1">Confusion matrix: rows are what happened, columns the most likely class</caption>
          <thead>
            <tr className="text-[#8E8E88] text-[10px] uppercase">
              <td />
              {names.map((n) => <th key={n} scope="col" className="px-3 py-1 text-right">{n}</th>)}
            </tr>
          </thead>
          <tbody>
            {h.confusion_matrix.map((row, i) => (
              <tr key={names[i]}>
                <th scope="row" className="text-left text-[#B9B9B3] font-medium pr-3 py-1">{names[i]}</th>
                {row.map((v, j) => (
                  <td key={j} className={`px-3 py-1 text-right font-mono ${i === j ? 'text-[#D9B15F] font-bold' : 'text-[#F6F6F3]'}`}>{fmtCount(v)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export const MethodologyPage: React.FC = () => {
  const [data, setData] = useState<MethodologyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setError(null);
    fetchMethodology(ctl.signal).then(setData).catch((e: Error) => { if (e.name !== 'AbortError') setError(e.message); });
    return () => ctl.abort();
  }, [reload]);

  return (
    <div className="space-y-8 max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-16">
      <div className="pb-2 border-b border-[#D9B15F]/20 space-y-2">
        <div className="flex items-center gap-3">
          <span className="w-1.5 h-6 bg-[#D9B15F] rounded-full inline-block" />
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#F6F6F3]">How the Predictions Work</h1>
        </div>
        <p className="text-xs sm:text-sm text-[#B9B9B3] ml-4 sm:ml-5 max-w-4xl">
          <strong className="text-[#F6F6F3]">What this page shows:</strong> the full workflow behind the two prediction tools: what is predicted, which data
          assumptions hold, the seven algorithms compared and what each assumes, how they scored season by season, why gradient boosting was chosen,
          and how it did on 2026. Every number is read from the project's saved evaluation files.
        </p>
      </div>

      {error && <ErrorRetry message={error} onRetry={() => setReload((n) => n + 1)} />}
      {!data && !error && (
        <p role="status" className="text-sm text-[#B9B9B3] flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> Loading the methodology…</p>
      )}

      {data && (
        <>
          <div className="bg-gradient-to-br from-[#D9B15F]/[0.12] to-[#151619] border border-[#D9B15F]/40 rounded-2xl p-4 sm:p-5 space-y-2">
            <p className="text-[11px] uppercase tracking-wider font-bold text-[#D9B15F] flex items-center gap-1.5"><Trophy className="w-4 h-4" aria-hidden="true" /> Final model</p>
            <p className="text-sm sm:text-base text-[#F6F6F3]">
              Both tools use <strong>{data.decision.algorithm}</strong> ({Object.entries(data.decision.params).map(([k, v]) => `${k} ${v}`).join(', ')}; learning rate {String(data.decision.fixed_settings.learning_rate)}).
            </p>
            <p className="text-xs sm:text-sm text-[#B9B9B3]">
              Selection rule: {data.decision.rule} It ranked first for both forecasts, but the leading algorithms are close: see the paired gaps below.
            </p>
            <nav aria-label="On this page" className="flex flex-wrap gap-1.5 pt-1">
              {SECTIONS.map(([id, label]) => (
                <a key={id} href={`#${id}`} className={`text-[11px] px-2.5 py-1 rounded-full bg-[#101114] border border-[#D9B15F]/20 text-[#B9B9B3] hover:text-[#F6F6F3] ${FOCUS_RING}`}>{label}</a>
              ))}
            </nav>
          </div>

          <Section id="workflow" number={1} title="The workflow" icon={<GitCompareArrows className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" />}
            intro="From raw scorecards to the website, every step keeps time in order: a model only ever learns from matches played before the ones it is judged on.">
            <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
              {data.workflow.map((s, i) => (
                <li key={s.step} className="relative bg-[#101114] border border-white/5 rounded-xl p-3 min-w-0">
                  <p className="text-[10px] font-mono text-[#D9B15F]">Step {s.step}</p>
                  <p className="text-sm font-bold text-[#F6F6F3]">{s.title}</p>
                  <p className="text-[11px] text-[#B9B9B3] mt-1">{s.detail}</p>
                  {i < data.workflow.length - 1 && (
                    <ChevronRight className="hidden lg:block absolute -right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#D9B15F]" aria-hidden="true" />
                  )}
                </li>
              ))}
            </ol>
          </Section>

          <Section id="questions" number={2} title="The prediction questions" icon={<Target className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" />}
            intro="Two separate forecasts, each with its own rows and target. Both give probabilities, not yes/no answers.">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {data.tasks.map((t) => (
                <div key={t.kind} className="bg-[#101114] border border-white/5 rounded-xl p-4 space-y-2 min-w-0">
                  <h3 className="text-sm font-bold text-[#F6F6F3]">{t.title}</h3>
                  <p className="text-sm text-[#F6F6F3]">{t.question}</p>
                  <dl className="text-xs text-[#B9B9B3] space-y-1">
                    <div><dt className="inline text-[#8E8E88]">Target: </dt><dd className="inline">{t.target}</dd></div>
                    <div><dt className="inline text-[#8E8E88]">Output: </dt><dd className="inline">{t.output}</dd></div>
                    <div><dt className="inline text-[#8E8E88]">Inputs: </dt><dd className="inline">{t.inputs}</dd></div>
                    <div><dt className="inline text-[#8E8E88]">Data: </dt><dd className="inline">{fmtCount(t.rows)} eligible {t.unit} from {fmtCount(t.matches)} matches (2008–2026); 2026 test: {fmtCount(t.test_rows)} rows from {t.test_matches} matches.</dd></div>
                    <div><dt className="inline text-[#8E8E88]">Class shares: </dt><dd className="inline">{Object.entries(t.class_shares).map(([k, v]) => `${CLASS_NAMES[t.kind][Number(k)]} ${pct2(v)}`).join(' · ')}</dd></div>
                  </dl>
                </div>
              ))}
            </div>
          </Section>

          <Section id="data" number={3} title="Data assumptions" icon={<Database className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" />}
            intro="What the modelling takes for granted about the data, whether it holds in this archive, and what that means for the results.">
            <ul className="space-y-2">
              {data.data_assumptions.map((d) => (
                <li key={d.assumption} className="bg-[#101114] border border-white/5 rounded-xl p-3 space-y-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-bold text-[#F6F6F3]">{d.assumption}</h3>
                    <VerdictBadge verdict={d.verdict} />
                  </div>
                  <p className="text-xs text-[#B9B9B3]"><span className="text-[#8E8E88]">Evidence: </span>{d.evidence}</p>
                  <p className="text-xs text-[#B9B9B3]"><span className="text-[#8E8E88]">Consequence: </span>{d.consequence}</p>
                </li>
              ))}
            </ul>
            <details className="text-xs text-[#B9B9B3]">
              <summary className={`cursor-pointer font-semibold text-[#D9B15F] ${FOCUS_RING}`}>Show the eligibility counts</summary>
              <div className="mt-2">
                <DataTable
                  caption="Eligibility rules and counts"
                  rows={data.eligibility}
                  rowKey={(r) => `${r.scope}-${r.rule}`}
                  dense
                  columns={[
                    { header: 'Scope', align: 'left', cell: (r) => r.scope },
                    { header: 'Rule', align: 'left', className: 'whitespace-normal', cell: (r) => r.rule },
                    { header: 'Count', align: 'right', cell: (r) => fmtCount(r.count) },
                  ]}
                />
              </div>
            </details>
          </Section>

          <Section id="algorithms" number={4} title="The seven algorithms" icon={<Boxes className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" />}
            intro={<>Each algorithm makes different assumptions about the data. For each one: how it works, what it assumes, whether that holds here (verdict and evidence), the settings tried on 2018–2020, its 2021–2025 results and why it was or was not chosen. <span className="text-[#8E8E88]">Verdicts: Holds, Partially holds or Violated, decided by rules stated in the analysis code.</span></>}>
            <AlgorithmCards algorithms={data.algorithms} />
          </Section>

          <Section id="comparison" number={5} title="Comparison table" icon={<FlaskConical className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" />}
            intro="Every algorithm, trained on all seasons before each of 2021–2025 and scored on that season.">
            <ComparisonTable comparison={data.comparison} />
          </Section>

          <Section id="convergence" number={6} title="Learning curves and convergence" icon={<TrendingUp className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" />}
            intro={<>
              <strong className="text-[#F6F6F3]">What "convergence" means here:</strong> whether, as more past seasons are used for training, the validation score stops improving
              (a plateau) and the gaps between the leading algorithms become small. It is examined with data, not proved mathematically, and it does not say how the models
              will do in seasons after 2026.
            </>}>
            <LearningCurves curves={data.learning_curves} convergence={data.convergence} />
            <div className="border-t border-[#D9B15F]/15 pt-4 space-y-2">
              <h3 className="text-sm font-bold text-[#F6F6F3]">Season by season against the selected model</h3>
              <PairedGaps gaps={data.paired_gaps} convergence={data.convergence} />
            </div>
            <ReadingGuide>
              {(['wicket', 'batter'] as MethodologyTaskKind[]).map((t) => {
                const c = data.convergence[t];
                const rf = c.paired_gaps_vs_selected['Random forest'];
                return (
                  <p key={t}>
                    <strong className="text-[#F6F6F3]">{TASK_LABEL[t]}:</strong> boosting's mean Brier {num(c.selected_mean_validation_brier, 6)} is {num(c.runner_up_gap, 6)} below the runner-up ({c.runner_up}).
                    Against the random forest the mean gap is {num(rf.mean, 6)} with a season-to-season SD of {num(rf.sd, 6)}, and boosting was better in {rf.selected_better_seasons} of {rf.seasons} seasons:
                    the two are statistically close, and boosting is chosen because the rule fixed in advance ranks it first.
                  </p>
                );
              })}
            </ReadingGuide>
          </Section>

          <Section id="final" number={7} title="The final model and its 2026 test" icon={<Trophy className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" />}
            intro={<>The selected setting was trained on 2008–2025 and scored once on 2026. <span className="text-amber-200">{data.holdout.wicket.caveat}</span></>}>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              {(['wicket', 'batter'] as MethodologyTaskKind[]).map((t) => <HoldoutCard key={t} task={t} h={data.holdout[t]} />)}
            </div>
            <ReadingGuide>
              <p>Calibration: each point compares the average forecast in a probability range with how often the event happened; points on the dashed line mean the forecasts were honest.</p>
              <p>Confusion matrix: the most likely class is nearly always the majority class, so the classification view looks weak. The value of these models is in the probabilities, which beat the class-prior baseline on Brier score and log loss.</p>
            </ReadingGuide>
            <p className="text-xs text-[#B9B9B3]">
              The website's tools use the same algorithm refitted on all 2008–2026 rows ({(['wicket', 'batter'] as MethodologyTaskKind[]).map((t) => `${TASK_LABEL[t].toLowerCase()}: ${fmtCount(data.final_models[t].final.train_rows)} rows`).join('; ')}).
              Try them in the <Link to="/predict" className="text-[#D9B15F] underline">Prediction Arena</Link>, or replay every 2026 forecast in the <Link to="/tracker" className="text-[#D9B15F] underline">Prediction Tracker</Link>.
            </p>
          </Section>

          <Section id="limitations" number={8} title="Limitations" icon={<AlertTriangle className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" />}>
            <ul className="list-disc ml-5 text-sm text-[#B9B9B3] space-y-1">
              {data.limitations.map((l) => <li key={l}>{l}</li>)}
            </ul>
            <p className="text-[11px] text-[#8E8E88] flex items-start gap-1.5">
              <BookOpen className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
              Sources: {data.sources.join(' · ')}
            </p>
          </Section>
        </>
      )}
    </div>
  );
};
