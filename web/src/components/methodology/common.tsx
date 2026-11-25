import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { MethodologyTaskKind, Verdict } from '../../types';
import { FOCUS_RING } from '../player/playerFormat';

export const SELECTED = 'Histogram gradient boosting';

/** One colour per algorithm, the selected model in the site's gold; all pass 3:1 contrast on the dark cards. */
export const MODEL_COLORS: Record<string, string> = {
  'Histogram gradient boosting': '#D9B15F',
  'Random forest': '#34D399',
  'Multilayer perceptron': '#A78BFA',
  'Logistic regression': '#60A5FA',
  'Decision tree': '#F472B6',
  'Class-prior baseline': '#9CA3AF',
  'Gaussian naive Bayes': '#FB7185',
};

export const TASK_LABEL: Record<MethodologyTaskKind, string> = { wicket: 'Next-over wicket', batter: 'Batter milestones' };

export const CHART_TOOLTIP = {
  contentStyle: { backgroundColor: '#151619', borderColor: '#D9B15F', borderRadius: '0.75rem', fontSize: '12px' },
  labelStyle: { color: '#F6F6F3', fontWeight: 'bold' },
  itemStyle: { color: '#F6F6F3' },
};
export const AXIS = { stroke: '#8E8E88', fontSize: 11, tickLine: false };

export const pct2 = (v: number): string => `${(v * 100).toFixed(2)}%`;
export const num = (v: number, digits = 4): string => v.toFixed(digits);
export const signed = (v: number, digits = 6): string => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(digits)}`;

/** A page section with a numbered heading, a short intro and its content. */
export const Section: React.FC<{
  id: string;
  number: number;
  title: string;
  intro?: React.ReactNode;
  icon?: React.ReactNode;
  children: React.ReactNode;
}> = ({ id, number, title, intro, icon, children }) => (
  <section id={id} aria-labelledby={`${id}-title`} className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-6 space-y-4 min-w-0 scroll-mt-24">
    <header className="space-y-1.5 border-b border-[#D9B15F]/15 pb-3">
      <h2 id={`${id}-title`} className="text-base sm:text-lg font-bold text-[#F6F6F3] flex items-center gap-2">
        {icon}
        <span className="text-[#8E8E88] font-mono text-xs">{number}.</span>
        <span>{title}</span>
      </h2>
      {intro && <div className="text-xs sm:text-sm text-[#B9B9B3] max-w-4xl">{intro}</div>}
    </header>
    {children}
  </section>
);

const VERDICT_STYLE: Record<Verdict, { cls: string; Icon: React.ElementType }> = {
  Holds: { cls: 'bg-emerald-500/10 text-emerald-300 border-emerald-400/40', Icon: CheckCircle2 },
  'Partially holds': { cls: 'bg-amber-500/10 text-amber-200 border-amber-300/40', Icon: AlertTriangle },
  Violated: { cls: 'bg-red-500/10 text-red-300 border-red-400/40', Icon: XCircle },
};

/** The verdict in words plus an icon, never colour alone. */
export const VerdictBadge: React.FC<{ verdict: Verdict; prefix?: string }> = ({ verdict, prefix }) => {
  const { cls, Icon } = VERDICT_STYLE[verdict];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[11px] font-semibold whitespace-nowrap ${cls}`}>
      <Icon className="w-3 h-3" aria-hidden="true" />
      {prefix && <span className="text-[#B9B9B3] font-medium">{prefix}:</span>}
      {verdict}
    </span>
  );
};

/** A two-option segmented control for the wicket and batter tasks. */
export const TaskToggle: React.FC<{ value: MethodologyTaskKind; onChange: (t: MethodologyTaskKind) => void; label: string }> = ({ value, onChange, label }) => (
  <div role="group" aria-label={label} className="inline-flex rounded-full border border-[#D9B15F]/25 bg-[#101114] p-0.5">
    {(['wicket', 'batter'] as MethodologyTaskKind[]).map((t) => (
      <button
        key={t}
        type="button"
        aria-pressed={value === t}
        onClick={() => onChange(t)}
        className={`px-3 py-1 rounded-full text-xs font-semibold ${FOCUS_RING} ${value === t ? 'bg-[#D9B15F] text-[#0D0E10]' : 'text-[#B9B9B3] hover:text-[#F6F6F3]'}`}
      >
        {TASK_LABEL[t]}
      </button>
    ))}
  </div>
);

/** "How to read it" guidance placed next to a chart. */
export const ReadingGuide: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="bg-[#101114] border border-white/5 rounded-xl p-3 text-xs text-[#B9B9B3] space-y-1">
    <p className="text-[10px] uppercase tracking-wider font-bold text-[#D9B15F]">How to read it</p>
    {children}
  </div>
);
