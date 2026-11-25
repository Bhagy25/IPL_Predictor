import React, { useMemo, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import { MethodologyCalibrationBin, MethodologyConvergence, MethodologyCurvePoint, MethodologyTaskKind } from '../../types';
import { FOCUS_RING } from '../player/playerFormat';
import { DataTable } from '../player/ProfileSections';
import { fmtCount } from '../../utils/format';
import { AXIS, CHART_TOOLTIP, MODEL_COLORS, ReadingGuide, SELECTED, TaskToggle, num, pct2, signed } from './common';

const CURVE_METRICS = [
  { key: 'validation_brier', label: 'Brier score', lower: true, percent: false },
  { key: 'validation_log_loss', label: 'Log loss', lower: true, percent: false },
  { key: 'validation_accuracy', label: 'Accuracy', lower: false, percent: true },
  { key: 'validation_balanced_accuracy', label: 'Balanced accuracy', lower: false, percent: true },
] as const;
type CurveKey = typeof CURVE_METRICS[number]['key'];
const NAIVE_BAYES = 'Gaussian naive Bayes';

const Toggle: React.FC<{ pressed: boolean; onClick: () => void; children: React.ReactNode }> = ({ pressed, onClick, children }) => (
  <button
    type="button"
    aria-pressed={pressed}
    onClick={onClick}
    className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border ${FOCUS_RING} ${pressed ? 'bg-[#D9B15F] text-[#0D0E10] border-[#D9B15F]' : 'bg-[#101114] text-[#B9B9B3] border-[#D9B15F]/20 hover:text-[#F6F6F3]'}`}
  >
    {children}
  </button>
);

/** Validation score against training size: one line per algorithm, the selected model drawn thicker in gold. */
export const LearningCurves: React.FC<{
  curves: Record<MethodologyTaskKind, MethodologyCurvePoint[]>;
  convergence: Record<MethodologyTaskKind, MethodologyConvergence>;
}> = ({ curves, convergence }) => {
  const [task, setTask] = useState<MethodologyTaskKind>('wicket');
  const [metric, setMetric] = useState<CurveKey>('validation_brier');
  const [showNB, setShowNB] = useState(false);
  const spec = CURVE_METRICS.find((m) => m.key === metric)!;
  const models = useMemo(() => Array.from(new Set(curves[task].map((p) => p.model))), [curves, task]);
  const visible = models.filter((m) => showNB || m !== NAIVE_BAYES);
  // One row per training size with one column per algorithm
  const rows = useMemo(() => {
    const byFraction = new Map<number, Record<string, number>>();
    for (const p of curves[task]) {
      const row = byFraction.get(p.training_fraction) ?? { fraction: p.training_fraction, matches: 0 };
      row[p.model] = p[metric];
      if (p.model === SELECTED) row.matches = p.train_matches;
      byFraction.set(p.training_fraction, row);
    }
    return Array.from(byFraction.values()).sort((a, b) => a.fraction - b.fraction);
  }, [curves, task, metric]);
  const fmt = (v: number) => (spec.percent ? `${(v * 100).toFixed(1)}%` : v.toFixed(4));
  const c = convergence[task];
  const plateau = c.selected_plateau;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <TaskToggle value={task} onChange={setTask} label="Forecast shown in the learning curves" />
        <div role="group" aria-label="Metric shown" className="flex flex-wrap gap-1.5">
          {CURVE_METRICS.map((m) => (
            <Toggle key={m.key} pressed={metric === m.key} onClick={() => setMetric(m.key)}>{m.label}</Toggle>
          ))}
        </div>
        <Toggle pressed={showNB} onClick={() => setShowNB((v) => !v)}>Show naive Bayes</Toggle>
      </div>
      <div className="h-80 sm:h-96" role="img" aria-label={`${spec.label} against training size for the ${task} forecast; the table below lists every value`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 10, right: 16, bottom: 28, left: 8 }}>
            <CartesianGrid stroke="#2A2B30" strokeDasharray="3 3" />
            <XAxis dataKey="matches" type="number" domain={['dataMin', 'dataMax']} {...AXIS}
              tickFormatter={(v: number) => fmtCount(Math.round(v)) ?? ''}
              label={{ value: 'Mean training matches', position: 'insideBottom', offset: -16, fill: '#8E8E88', fontSize: 11 }} />
            <YAxis {...AXIS} width={56} domain={['auto', 'auto']} tickFormatter={fmt} />
            <Tooltip {...CHART_TOOLTIP} formatter={(v: number, name: string) => [fmt(v), name]}
              labelFormatter={(v: number) => `${fmtCount(Math.round(v))} training matches`} />
            <Legend wrapperStyle={{ fontSize: 11, color: '#B9B9B3' }} verticalAlign="top" height={44} />
            {visible.map((m) => (
              <Line key={m} type="linear" dataKey={m} name={m} stroke={MODEL_COLORS[m]} dot={{ r: 2.5 }}
                strokeWidth={m === SELECTED ? 3.5 : 1.5} strokeDasharray={m === 'Class-prior baseline' ? '5 4' : undefined}
                isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <ReadingGuide>
        <p>Each point is the mean over the five validation seasons (2021–2025) when each model is trained on the most recent 10%, 25%, 50%, 75% or 100% of the earlier matches. {spec.lower ? 'Lower is better.' : 'Higher is better.'}</p>
        <p>
          <strong className="text-[#F6F6F3]">Plateau:</strong> the selected model's validation Brier improved by {signed(plateau.change_10_to_50)} from 10% to 50% of the history,
          then changed by {signed(plateau.change_50_to_75)} (50→75%) and {signed(plateau.change_75_to_100)} (75→100%).
          The top three algorithms end {num(c.leader_brier_spread_by_fraction['1.0'], 6)} apart in mean Brier, against {num(c.leader_brier_spread_by_fraction['0.1'], 6)} at 10%.
        </p>
        <p>
          <strong className="text-[#F6F6F3]">Accuracy:</strong> always predicting the majority class already scores {pct2(c.majority_class_accuracy_mean)}, so the accuracy lines sit close together; Brier and log loss separate the models.
          {!showNB && ' Naive Bayes is hidden by default: its Brier and log loss are far off the scale of the others.'}
        </p>
      </ReadingGuide>
      <details className="text-xs text-[#B9B9B3]">
        <summary className={`cursor-pointer font-semibold text-[#D9B15F] ${FOCUS_RING}`}>Show the values</summary>
        <div className="mt-2">
          <DataTable<Record<string, number>>
            caption={`${spec.label} by training size`}
            rows={rows}
            rowKey={(r) => r.fraction}
            dense
            columns={[
              { header: 'Share', align: 'left', cell: (r) => `${Math.round(r.fraction * 100)}%` },
              { header: 'Matches', align: 'right', cell: (r) => fmtCount(Math.round(r.matches)) },
              ...models.map((m) => ({ header: m, align: 'right' as const, cell: (r: Record<string, number>) => fmt(r[m]) })),
            ]}
          />
        </div>
      </details>
    </div>
  );
};

/** Each algorithm's Brier minus boosting's in every validation season: above zero means boosting was better. */
export const PairedGaps: React.FC<{
  gaps: Record<MethodologyTaskKind, { year: number; model: string; gap: number }[]>;
  convergence: Record<MethodologyTaskKind, MethodologyConvergence>;
}> = ({ gaps, convergence }) => {
  const [task, setTask] = useState<MethodologyTaskKind>('wicket');
  const models = Array.from(new Set(gaps[task].map((g) => g.model))).filter((m) => m !== NAIVE_BAYES);
  const rows = useMemo(() => {
    const byYear = new Map<number, Record<string, number>>();
    for (const g of gaps[task]) {
      const row = byYear.get(g.year) ?? { year: g.year };
      row[g.model] = g.gap;
      byYear.set(g.year, row);
    }
    return Array.from(byYear.values()).sort((a, b) => a.year - b.year);
  }, [gaps, task]);
  const summary = convergence[task].paired_gaps_vs_selected;
  const order = Object.keys(summary).sort((a, b) => summary[a].mean - summary[b].mean);
  return (
    <div className="space-y-3">
      <TaskToggle value={task} onChange={setTask} label="Forecast shown in the paired gaps" />
      <div className="h-72 sm:h-80" role="img" aria-label={`Per-season Brier gap of each algorithm against boosting for the ${task} forecast; the table below lists every value`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 10, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid stroke="#2A2B30" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="year" {...AXIS} />
            <YAxis {...AXIS} width={64} tickFormatter={(v: number) => v.toFixed(4)} />
            <ReferenceLine y={0} stroke="#D9B15F" />
            <Tooltip {...CHART_TOOLTIP} formatter={(v: number, name: string) => [signed(v), name]} cursor={{ fill: 'rgba(217,177,95,0.06)' }} />
            <Legend wrapperStyle={{ fontSize: 11, color: '#B9B9B3' }} verticalAlign="top" height={44} />
            {models.map((m) => <Bar key={m} dataKey={m} name={m} fill={MODEL_COLORS[m]} isAnimationActive={false} />)}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ReadingGuide>
        <p>A bar above zero means that algorithm's Brier score was higher (worse) than boosting's in that season; below zero means it beat boosting that season. Each season is compared on exactly the same rows.</p>
        <p>Naive Bayes is left out of the chart because its gaps are far larger; it is in the table.</p>
      </ReadingGuide>
      <DataTable<string>
        caption="Paired per-season Brier gaps against boosting, 2021–2025"
        rows={order}
        rowKey={(m) => m}
        dense
        columns={[
          { header: 'Algorithm', align: 'left', cell: (m) => m },
          { header: 'Mean gap', align: 'right', cell: (m) => signed(summary[m].mean) },
          { header: 'SD', align: 'right', cell: (m) => num(summary[m].sd, 6) },
          { header: 'Seasons boosting better', align: 'right', cell: (m) => `${summary[m].selected_better_seasons} of ${summary[m].seasons}` },
        ]}
      />
    </div>
  );
};

/** Average forecast against observed rate per probability bin, with the diagonal of perfect calibration. */
export const CalibrationChart: React.FC<{ bins: MethodologyCalibrationBin[]; task: MethodologyTaskKind }> = ({ bins, task }) => {
  const events = Array.from(new Set(bins.map((b) => b.event)));
  const colors = ['#D9B15F', '#60A5FA'];
  const max = Math.min(1, Math.ceil(Math.max(...bins.map((b) => Math.max(b.mean_probability, b.observed_rate))) * 10) / 10 + 0.1);
  const ticks = Array.from({ length: Math.round(max * 10) + 1 }, (_, i) => i / 10);
  const name = (e: string) => (e === 'wicket' ? 'Wicket next over' : `${e}+ runs`);
  return (
    <div className="space-y-2">
      <div className="h-64 sm:h-72" role="img" aria-label={`Calibration of the 2026 ${task} forecasts; the table lists every bin`}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 16, bottom: 24, left: 4 }}>
            <CartesianGrid stroke="#2A2B30" strokeDasharray="3 3" />
            <XAxis type="number" dataKey="x" domain={[0, max]} ticks={ticks} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} {...AXIS}
              label={{ value: 'Average forecast', position: 'insideBottom', offset: -14, fill: '#8E8E88', fontSize: 11 }} />
            <YAxis type="number" dataKey="y" domain={[0, max]} ticks={ticks} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} {...AXIS} width={40} />
            <ReferenceLine segment={[{ x: 0, y: 0 }, { x: max, y: max }]} stroke="#8E8E88" strokeDasharray="5 5" />
            <Tooltip {...CHART_TOOLTIP} formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
            <Legend verticalAlign="top" height={26} wrapperStyle={{ fontSize: 11, color: '#B9B9B3' }} />
            {events.map((e, i) => (
              <Scatter key={e} name={name(e)} fill={colors[i]} line={{ stroke: colors[i], strokeWidth: 1.5 }} isAnimationActive={false}
                data={bins.filter((b) => b.event === e).map((b) => ({ x: b.mean_probability, y: b.observed_rate, n: b.rows }))} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <details className="text-xs text-[#B9B9B3]">
        <summary className={`cursor-pointer font-semibold text-[#D9B15F] ${FOCUS_RING}`}>Show the calibration bins</summary>
        <div className="mt-2">
          <DataTable<MethodologyCalibrationBin>
            caption={`2026 calibration bins, ${task}`}
            rows={bins}
            rowKey={(b) => `${b.event}-${b.bin}`}
            dense
            columns={[
              { header: 'Event', align: 'left', cell: (b) => name(b.event) },
              { header: 'Forecast range', align: 'right', cell: (b) => `${Math.round(b.lower * 100)}–${Math.round(b.upper * 100)}%` },
              { header: 'Rows', align: 'right', cell: (b) => fmtCount(b.rows) },
              { header: 'Avg forecast', align: 'right', cell: (b) => `${(b.mean_probability * 100).toFixed(1)}%` },
              { header: 'Happened', align: 'right', cell: (b) => `${(b.observed_rate * 100).toFixed(1)}%` },
            ]}
          />
        </div>
      </details>
    </div>
  );
};
