import React, { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, Star } from 'lucide-react';
import { MethodologyAlgorithm, MethodologyComparisonRow, MethodologyTaskKind } from '../../types';
import { FOCUS_RING } from '../player/playerFormat';
import { ScrollRegion, Tabs } from '../player/ProfileSections';
import { MODEL_COLORS, ReadingGuide, TASK_LABEL, TaskToggle, VerdictBadge, num, pct2, signed } from './common';

type MetricKey = 'brier' | 'log_loss' | 'accuracy' | 'balanced_accuracy' | 'macro_f1' | 'roc_auc' | 'average_precision';
const COLUMNS: { key: MetricKey; label: string; title: string; lower: boolean; percent: boolean }[] = [
  { key: 'brier', label: 'Brier', title: 'Mean squared probability error; lower is better (selection metric)', lower: true, percent: false },
  { key: 'log_loss', label: 'Log loss', title: 'Penalty for the probability given to what happened; lower is better', lower: true, percent: false },
  { key: 'accuracy', label: 'Accuracy', title: 'Share of rows whose most likely class happened; higher is better', lower: false, percent: true },
  { key: 'balanced_accuracy', label: 'Balanced acc.', title: 'Mean recall over the classes; higher is better', lower: false, percent: true },
  { key: 'macro_f1', label: 'Macro F1', title: 'Mean F1 over the classes; higher is better', lower: false, percent: false },
  { key: 'roc_auc', label: 'ROC-AUC', title: 'Chance a random event gets a higher forecast than a random non-event; higher is better', lower: false, percent: false },
  { key: 'average_precision', label: 'Avg. precision', title: 'Area under the precision–recall curve; higher is better', lower: false, percent: false },
];

/** All seven algorithms with every metric as mean ± SD over 2021–2025; any column can be sorted. */
export const ComparisonTable: React.FC<{ comparison: Record<MethodologyTaskKind, MethodologyComparisonRow[]> }> = ({ comparison }) => {
  const [task, setTask] = useState<MethodologyTaskKind>('wicket');
  const [sort, setSort] = useState<{ key: MetricKey | 'rank'; asc: boolean }>({ key: 'rank', asc: true });
  const rows = useMemo(() => {
    const list = [...comparison[task]];
    const value = (r: MethodologyComparisonRow) => (sort.key === 'rank' ? r.rank : r[`${sort.key}_mean`]);
    list.sort((a, b) => (sort.asc ? value(a) - value(b) : value(b) - value(a)));
    return list;
  }, [comparison, task, sort]);
  const onSort = (key: MetricKey | 'rank') =>
    setSort((s) => (s.key === key ? { key, asc: !s.asc } : { key, asc: key === 'rank' || COLUMNS.find((c) => c.key === key)!.lower }));
  const ariaSort = (key: MetricKey | 'rank') => (sort.key === key ? (sort.asc ? 'ascending' : 'descending') : 'none');
  const SortIcon = ({ k }: { k: MetricKey | 'rank' }) =>
    sort.key !== k ? <ArrowUpDown className="w-3 h-3 opacity-50" aria-hidden="true" /> : sort.asc ? <ArrowUp className="w-3 h-3" aria-hidden="true" /> : <ArrowDown className="w-3 h-3" aria-hidden="true" />;
  const fmt = (c: typeof COLUMNS[number], r: MethodologyComparisonRow) => {
    const mean = r[`${c.key}_mean`];
    const sd = r[`${c.key}_std`];
    return c.percent ? `${pct2(mean)} ± ${(sd * 100).toFixed(2)}` : `${num(mean, c.key === 'brier' || c.key === 'log_loss' ? 5 : 4)} ± ${num(sd, c.key === 'brier' || c.key === 'log_loss' ? 5 : 4)}`;
  };
  return (
    <div className="space-y-3">
      <TaskToggle value={task} onChange={setTask} label="Forecast shown in the comparison table" />
      <ScrollRegion label={`Algorithm comparison, ${TASK_LABEL[task]}`}>
        <table className="w-full text-left text-xs">
          <caption className="sr-only">{`Mean ± SD over the 2021–2025 validation seasons, ${TASK_LABEL[task]}. Select a column heading to sort.`}</caption>
          <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20">
            <tr>
              <th scope="col" aria-sort={ariaSort('rank')} className="py-2 px-2">
                <button type="button" onClick={() => onSort('rank')} className={`inline-flex items-center gap-1 uppercase ${FOCUS_RING}`}>Rank <SortIcon k="rank" /></button>
              </th>
              <th scope="col" className="py-2 px-2">Algorithm</th>
              {COLUMNS.map((c) => (
                <th key={c.key} scope="col" aria-sort={ariaSort(c.key)} title={c.title} className="py-2 px-2 text-right whitespace-nowrap">
                  <button type="button" onClick={() => onSort(c.key)} className={`inline-flex items-center gap-1 uppercase ${FOCUS_RING}`}>
                    {c.label} <SortIcon k={c.key} />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#D9B15F]/10">
            {rows.map((r) => (
              <tr key={r.model} className={r.selected ? 'bg-[#D9B15F]/[0.07]' : 'hover:bg-[#1A1B1F]'}>
                <td className="py-2 px-2 text-[#B9B9B3] font-mono">{r.rank}</td>
                <th scope="row" className="py-2 px-2 font-semibold text-[#F6F6F3] whitespace-nowrap">
                  <span className="inline-flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: MODEL_COLORS[r.model] }} aria-hidden="true" />
                    {r.model}
                    {r.selected && <span className="inline-flex items-center gap-0.5 text-[10px] text-[#D9B15F] font-bold"><Star className="w-3 h-3" aria-hidden="true" /> Selected</span>}
                  </span>
                </th>
                {COLUMNS.map((c) => (
                  <td key={c.key} className={`py-2 px-2 text-right font-mono whitespace-nowrap ${c.key === 'brier' ? 'text-[#F6F6F3]' : 'text-[#B9B9B3]'}`}>{fmt(c, r)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollRegion>
      <ReadingGuide>
        <p>Each cell is the mean over the five validation seasons 2021–2025 ± the standard deviation across those seasons (accuracy columns in percentage points). Brier score decides the ranking; log loss breaks ties.</p>
        <p>The accuracy columns hardly differ because most rows belong to one class; that is why probability scores, not accuracy, pick the model.</p>
      </ReadingGuide>
    </div>
  );
};

const paramText = (params: Record<string, unknown>) =>
  Object.keys(params).length ? Object.entries(params).map(([k, v]) => `${k} = ${Array.isArray(v) ? `(${v.join(', ')})` : v}`).join(', ') : 'no settings';

/** One card per algorithm: how it works, its assumptions with evidence and verdicts, settings, results and the decision. */
export const AlgorithmCards: React.FC<{ algorithms: MethodologyAlgorithm[] }> = ({ algorithms }) => {
  const [active, setActive] = useState(algorithms.find((a) => a.selected)?.name ?? algorithms[0].name);
  const a = algorithms.find((x) => x.name === active)!;
  return (
    <Tabs label="Algorithms" idPrefix="algorithm" tabs={algorithms.map((x) => ({ id: x.name, label: x.selected ? `${x.short} ★` : x.short }))} active={active} onChange={setActive}>
      <article className="bg-[#101114] border border-white/5 rounded-xl p-4 space-y-4" aria-label={a.name}>
        <header className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-base font-bold text-[#F6F6F3] flex items-center gap-2">
            <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: MODEL_COLORS[a.name] }} aria-hidden="true" />
            {a.name}
            {a.selected && <span className="text-[11px] font-bold text-[#0D0E10] bg-[#D9B15F] rounded-full px-2 py-0.5">Selected</span>}
          </h3>
          <div className="flex flex-wrap gap-1.5">
            <VerdictBadge verdict={a.verdicts.wicket} prefix="Wicket" />
            <VerdictBadge verdict={a.verdicts.batter} prefix="Batter" />
          </div>
        </header>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="space-y-3 min-w-0">
            <div>
              <h4 className="text-[11px] uppercase tracking-wider font-bold text-[#D9B15F]">How it works</h4>
              <p className="text-sm text-[#B9B9B3] mt-1">{a.how_it_works}</p>
              <p className="mt-2 font-mono text-xs text-[#F6F6F3] bg-[#151619] border border-white/5 rounded-lg px-3 py-2 overflow-x-auto">{a.formula}</p>
            </div>
            <div>
              <h4 className="text-[11px] uppercase tracking-wider font-bold text-[#D9B15F]">What it assumes</h4>
              <ul className="list-disc ml-5 mt-1 text-sm text-[#B9B9B3] space-y-0.5">{a.assumptions.map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
            <div>
              <h4 className="text-[11px] uppercase tracking-wider font-bold text-[#D9B15F]">Does it hold here? Evidence</h4>
              <ul className="list-disc ml-5 mt-1 text-sm text-[#B9B9B3] space-y-0.5">{a.evidence.map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
          </div>
          <div className="space-y-3 min-w-0">
            {(['wicket', 'batter'] as MethodologyTaskKind[]).map((t) => {
              const r = a.results[t];
              return (
                <div key={t} className="bg-[#151619] border border-white/5 rounded-lg p-3 space-y-2">
                  <p className="text-xs font-bold text-[#F6F6F3]">{TASK_LABEL[t]}: rank {r.rank} of 7</p>
                  <p className="text-xs text-[#B9B9B3]">
                    Validation Brier <span className="font-mono text-[#F6F6F3]">{num(r.brier_mean, 5)} ± {num(r.brier_std, 5)}</span> · log loss <span className="font-mono">{num(r.log_loss_mean, 5)}</span> · accuracy <span className="font-mono">{pct2(r.accuracy_mean)}</span>
                    {r.paired_gap_mean !== null && r.seasons_selected_better !== null && (
                      <> · gap to boosting <span className="font-mono">{signed(r.paired_gap_mean)}</span> (boosting better in {r.seasons_selected_better} of 5 seasons)</>
                    )}
                  </p>
                  <table className="w-full text-[11px]">
                    <caption className="text-left text-[#8E8E88] pb-1">Settings tried on 2018–2020 (mean tuning Brier)</caption>
                    <tbody className="divide-y divide-white/5">
                      {a.grid[t].map((g) => (
                        <tr key={g.setting} className={g.chosen ? 'text-[#F6F6F3]' : 'text-[#8E8E88]'}>
                          <th scope="row" className="text-left font-normal py-1 pr-2">{g.chosen ? '✓ ' : ''}{paramText(g.params)}</th>
                          <td className="text-right font-mono py-1">{num(g.tuning_brier_mean, 5)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            })}
          </div>
        </div>
        <p className={`text-sm rounded-lg px-3 py-2 border ${a.selected ? 'border-[#D9B15F]/40 bg-[#D9B15F]/[0.07] text-[#F6F6F3]' : 'border-white/5 bg-[#151619] text-[#B9B9B3]'}`}>
          <strong className="text-[#F6F6F3]">Decision: </strong>{a.decision}
        </p>
      </article>
    </Tabs>
  );
};
