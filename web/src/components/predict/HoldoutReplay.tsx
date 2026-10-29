import React, { useEffect, useMemo, useState } from 'react';
import { CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts';
import { CheckCircle2, ChevronLeft, ChevronRight, History, Loader2, XCircle } from 'lucide-react';
import { fetchHoldoutReplay, fetchHoldoutReplayMatch } from '../../api/replay';
import { CalibrationBin, HoldoutReplayMatchResponse, HoldoutReplayResponse, ReplayBatterRow, ReplayWicketRow } from '../../types';
import { Column, DataTable } from '../player/ProfileSections';
import { FOCUS_RING } from '../player/playerFormat';
import { fmtCount } from '../../utils/format';
import { ErrorRetry, INPUT, Note, SECONDARY_BUTTON, dec4, inputBorder, pct1 } from './shared';

const SERIES = [
  { key: 'wicket', label: 'Wicket next over', color: '#D9B15F' },
  { key: '30+', label: 'Batter 30+', color: '#60A5FA' },
  { key: '50+', label: 'Batter 50+', color: '#34D399' },
];

interface Point { x: number; y: number; n: number; lower: number; upper: number; series: string }

const toPoints = (bins: CalibrationBin[], series: string): Point[] =>
  bins.map((b) => ({ x: b.avg_predicted, y: b.observed_rate, n: b.n, lower: b.lower, upper: b.upper, series }));

const CalibrationTooltip: React.FC<{ active?: boolean; payload?: { payload: Point }[] }> = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="bg-[#151619] border border-[#D9B15F] rounded-xl px-3 py-2 text-xs text-[#B9B9B3] space-y-0.5">
      <p className="font-bold text-[#F6F6F3]">{p.series}</p>
      <p>Forecasts between {pct1(p.lower)} and {pct1(p.upper)}: {fmtCount(p.n)}</p>
      <p>Average forecast {pct1(p.x)} · happened {pct1(p.y)}</p>
    </div>
  );
};

const Check: React.FC<{ ok: boolean; count: number }> = ({ ok, count }) => (
  <span className={`inline-flex items-center gap-1 text-[11px] font-semibold ${ok ? 'text-emerald-300' : 'text-red-300'}`}>
    {ok ? <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" /> : <XCircle className="w-3.5 h-3.5" aria-hidden="true" />}
    {ok ? `Recomputed from the CSV: all ${count} metrics match the official report` : 'Recomputed metrics differ from the official report'}
  </span>
);

const MetricRow: React.FC<{ label: string; model: number | null | undefined; constant: number | null | undefined }> = ({ label, model, constant }) => (
  <tr>
    <th scope="row" className="text-left font-medium text-[#B9B9B3] py-1">{label}</th>
    <td className="text-right font-mono text-[#F6F6F3] py-1">{dec4(model)}</td>
    <td className="text-right font-mono text-[#8E8E88] py-1">{dec4(constant)}</td>
  </tr>
);

const MetricTable: React.FC<{ caption: string; children: React.ReactNode }> = ({ caption, children }) => (
  <table className="w-full text-xs">
    <caption className="text-left text-[11px] text-[#B9B9B3] pb-1">{caption}</caption>
    <thead>
      <tr className="text-[#8E8E88] text-[10px] uppercase">
        <th scope="col" className="text-left font-bold py-1">Metric</th>
        <th scope="col" className="text-right font-bold py-1">Model</th>
        <th scope="col" className="text-right font-bold py-1">Constant rate</th>
      </tr>
    </thead>
    <tbody className="divide-y divide-white/5">{children}</tbody>
  </table>
);

const yesNo = (v: boolean) => (v ? <span className="text-emerald-300 font-semibold">Yes</span> : <span className="text-[#8E8E88]">No</span>);

export const HoldoutReplay: React.FC = () => {
  const [index, setIndex] = useState<HoldoutReplayResponse | null>(null);
  const [indexError, setIndexError] = useState<string | null>(null);
  const [indexReload, setIndexReload] = useState(0);
  const [matchId, setMatchId] = useState<number | null>(null);
  const [match, setMatch] = useState<HoldoutReplayMatchResponse | null>(null);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [matchReload, setMatchReload] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setIndexError(null);
    fetchHoldoutReplay(ctl.signal)
      .then((r) => { setIndex(r); setMatchId((m) => m ?? r.matches[0]?.match_id ?? null); })
      .catch((e: Error) => { if (e.name !== 'AbortError') setIndexError(e.message); });
    return () => ctl.abort();
  }, [indexReload]);

  useEffect(() => {
    if (matchId === null) return undefined;
    const ctl = new AbortController();
    setMatch(null);
    setMatchError(null);
    fetchHoldoutReplayMatch(matchId, ctl.signal)
      .then(setMatch)
      .catch((e: Error) => { if (e.name !== 'AbortError') setMatchError(e.message); });
    return () => ctl.abort();
  }, [matchId, matchReload]);

  const points = useMemo(() => (index ? {
    wicket: toPoints(index.wicket.computed.calibration, SERIES[0].label),
    '30+': toPoints(index.batter.computed.calibration.filter((b) => b.milestone === '30+'), SERIES[1].label),
    '50+': toPoints(index.batter.computed.calibration.filter((b) => b.milestone === '50+'), SERIES[2].label),
  } as Record<string, Point[]> : null), [index]);

  const axisMax = useMemo(() => {
    if (!points) return 1;
    const all = Object.values(points).flat();
    return Math.min(1, Math.ceil(Math.max(...all.map((p) => Math.max(p.x, p.y))) * 10) / 10);
  }, [points]);

  // A tick every 10 percentage points up to the axis maximum
  const ticks = useMemo(() => Array.from({ length: Math.round(axisMax * 10) + 1 }, (_, i) => i / 10), [axisMax]);

  const position = index && matchId !== null ? index.matches.findIndex((m) => m.match_id === matchId) : -1;
  const item = position >= 0 && index ? index.matches[position] : null;
  const code = (team: string) => (item && team === item.team1 ? item.team1_code : item && team === item.team2 ? item.team2_code : team);

  const batterColumns: Column<ReplayBatterRow>[] = [
    { header: 'Batter', cell: (r) => r.batter },
    { header: 'Team', cell: (r) => code(r.batting_team) },
    { header: 'Prior inns', title: 'Eligible innings before this match', cell: (r) => fmtCount(r.prior_innings) },
    { header: 'P(30+)', align: 'right', cell: (r) => pct1(r.probability_30_plus) },
    { header: 'P(50+)', align: 'right', cell: (r) => pct1(r.probability_50_plus) },
    { header: 'Runs', align: 'right', cell: (r) => <span className="font-mono text-[#F6F6F3]">{r.actual_runs}</span> },
    { header: '30+', cell: (r) => yesNo(r.actual_30_plus) },
    { header: '50+', cell: (r) => yesNo(r.actual_50_plus) },
  ];
  const wicketColumns: Column<ReplayWicketRow>[] = [
    { header: 'Innings', cell: (r) => `${r.innings} · ${code(r.batting_team)}` },
    { header: 'Next over', title: 'The over being forecast (completed overs + 1)', cell: (r) => r.next_over },
    { header: 'Phase', cell: (r) => r.phase },
    { header: 'P(wicket)', align: 'right', cell: (r) => pct1(r.predicted_probability) },
    { header: 'Wicket fell', cell: (r) => yesNo(r.wicket_fell) },
  ];

  const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);

  return (
    <section aria-labelledby="replay-title" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id="replay-title" className="text-lg font-bold text-[#F6F6F3] flex items-center gap-2">
            <History className="w-5 h-5 text-[#D9B15F]" aria-hidden="true" /> 2026 Holdout Replay — model trained through 2025
          </h2>
          <p className="text-xs text-[#B9B9B3] mt-1">
            The official out-of-sample evaluation: forecasts the holdout models made for 2026 matches they never trained on, next to what happened.
            These are separate from your saved predictions above.
          </p>
        </div>
        <span className="self-start inline-flex items-center px-3 py-1 rounded-full text-[11px] font-semibold bg-[#101114] border border-[#D9B15F]/30 text-[#D9B15F] whitespace-nowrap">
          Official evaluation
        </span>
      </div>

      {indexError && <ErrorRetry message={indexError} onRetry={() => setIndexReload((n) => n + 1)} />}
      {!index && !indexError && (
        <p className="text-sm text-[#B9B9B3] flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> Loading the 2026 holdout forecasts…</p>
      )}

      {index && points && (
        <>
          <p className="text-xs text-[#8E8E88]">{index.statement}</p>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-[#101114] border border-white/5 rounded-xl p-4 space-y-2 min-w-0">
              <h3 className="text-sm font-bold text-[#F6F6F3]">Next-over wicket risk</h3>
              <MetricTable caption={`${fmtCount(index.wicket.computed.rows)} next overs in ${index.wicket.matches_count} matches; a wicket fell in ${pct1(index.wicket.computed.event_rate)}`}>
                <MetricRow label="Brier score" model={index.wicket.computed.brier_score} constant={index.wicket.official_constant.brier_score} />
                <MetricRow label="Log loss" model={index.wicket.computed.log_loss} constant={index.wicket.official_constant.log_loss} />
                <MetricRow label="ROC AUC" model={index.wicket.computed.roc_auc} constant={index.wicket.official_constant.roc_auc} />
              </MetricTable>
              <Check ok={index.wicket.check.matches_official} count={index.wicket.check.compared.length} />
              <p className="text-[10px] text-[#8E8E88]">{index.wicket.eligibility}</p>
            </div>
            <div className="bg-[#101114] border border-white/5 rounded-xl p-4 space-y-2 min-w-0">
              <h3 className="text-sm font-bold text-[#F6F6F3]">Batter milestones</h3>
              <MetricTable caption={`${fmtCount(index.batter.computed.rows)} innings in ${index.batter.matches_count} matches; ${pct1(index.batter.computed.observed_30_rate)} reached 30+, ${pct1(index.batter.computed.observed_50_rate)} reached 50+`}>
                <MetricRow label="Brier 30+" model={index.batter.computed.brier_30} constant={index.batter.official_constant.brier_30} />
                <MetricRow label="Brier 50+" model={index.batter.computed.brier_50} constant={index.batter.official_constant.brier_50} />
                <MetricRow label="Log loss (3 classes)" model={index.batter.computed.multiclass_log_loss} constant={index.batter.official_constant.multiclass_log_loss} />
                <MetricRow label="ROC AUC 30+" model={index.batter.computed.roc_auc_30} constant={index.batter.official_constant.roc_auc_30} />
                <MetricRow label="ROC AUC 50+" model={index.batter.computed.roc_auc_50} constant={index.batter.official_constant.roc_auc_50} />
              </MetricTable>
              <Check ok={index.batter.check.matches_official} count={index.batter.check.compared.length} />
              <p className="text-[10px] text-[#8E8E88]">{index.batter.eligibility}</p>
            </div>
          </div>

          <div className="bg-[#101114] border border-white/5 rounded-xl p-4 space-y-3 min-w-0">
            <h3 className="text-sm font-bold text-[#F6F6F3]">Calibration: forecast vs what happened</h3>
            <p className="text-xs text-[#B9B9B3]">
              Forecasts are grouped into equal-width probability bins: across is the bin's average forecast, up is the share of those
              forecasts where the event happened. A well-calibrated model's points sit on the dashed diagonal: of the overs given about a
              30% chance, about 30% had a wicket.
            </p>
            <div className="h-72 sm:h-80" role="img" aria-label="Calibration chart of the 2026 holdout forecasts; the bin tables below list every value">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 16, bottom: 24, left: 4 }}>
                  <CartesianGrid stroke="#2A2B30" strokeDasharray="3 3" />
                  <XAxis type="number" dataKey="x" domain={[0, axisMax]} ticks={ticks} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} stroke="#8E8E88" fontSize={11}
                    label={{ value: 'Average forecast', position: 'insideBottom', offset: -14, fill: '#8E8E88', fontSize: 11 }} />
                  <YAxis type="number" dataKey="y" domain={[0, axisMax]} ticks={ticks} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} stroke="#8E8E88" fontSize={11} width={40} />
                  <ReferenceLine segment={[{ x: 0, y: 0 }, { x: axisMax, y: axisMax }]} stroke="#8E8E88" strokeDasharray="5 5" ifOverflow="extendDomain" />
                  <Tooltip content={<CalibrationTooltip />} cursor={{ stroke: '#D9B15F', strokeOpacity: 0.3 }} />
                  <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 11, color: '#B9B9B3' }} />
                  {SERIES.map((s) => (
                    <Scatter key={s.key} name={s.label} data={points[s.key]} fill={s.color} line={{ stroke: s.color, strokeWidth: 1.5 }} />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            <details className="text-xs text-[#B9B9B3]">
              <summary className={`cursor-pointer font-semibold text-[#D9B15F] ${FOCUS_RING}`}>Show the calibration bins</summary>
              <div className="mt-3 grid grid-cols-1 lg:grid-cols-3 gap-3">
                {SERIES.map((s) => (
                  <DataTable<Point>
                    key={s.key}
                    caption={`${s.label} calibration bins`}
                    rows={points[s.key]}
                    rowKey={(p) => p.lower}
                    dense
                    columns={[
                      { header: s.label, cell: (p) => `${pct1(p.lower)}–${pct1(p.upper)}` },
                      { header: 'n', align: 'right', cell: (p) => fmtCount(p.n) },
                      { header: 'Avg forecast', align: 'right', cell: (p) => pct1(p.x) },
                      { header: 'Happened', align: 'right', cell: (p) => pct1(p.y) },
                    ]}
                  />
                ))}
              </div>
            </details>
          </div>

          <div className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-end gap-3">
              <div className="flex flex-col gap-1 min-w-0 flex-1">
                <label htmlFor="replay-match" className="text-[11px] text-[#B9B9B3] font-semibold">2026 match ({index.matches.length} with holdout forecasts)</label>
                <select id="replay-match" value={matchId ?? ''} onChange={(e) => setMatchId(Number(e.target.value))} className={`${INPUT} ${inputBorder(false)}`}>
                  {index.matches.map((m) => (
                    <option key={m.match_id} value={m.match_id}>{m.date} · {m.team1_code} v {m.team2_code} · {m.venue}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <button type="button" className={SECONDARY_BUTTON} disabled={position <= 0} onClick={() => setMatchId(index.matches[position - 1].match_id)}>
                  <ChevronLeft className="w-4 h-4" aria-hidden="true" /> Previous
                </button>
                <button type="button" className={SECONDARY_BUTTON} disabled={position < 0 || position >= index.matches.length - 1} onClick={() => setMatchId(index.matches[position + 1].match_id)}>
                  Next <ChevronRight className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>
            </div>

            {matchError && <ErrorRetry message={matchError} onRetry={() => setMatchReload((n) => n + 1)} />}
            {!match && !matchError && (
              <p className="text-sm text-[#B9B9B3] flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> Loading match forecasts…</p>
            )}
            {match && item && (
              <div className="space-y-4" aria-live="polite">
                <p className="text-sm text-[#F6F6F3] font-semibold">
                  {match.team1} v {match.team2} · {match.date} · {match.venue}
                  <span className="block text-xs text-[#B9B9B3] font-normal">{match.winner ? `Won by ${match.winner}` : 'No winner recorded'} · {match.label}</span>
                </p>
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                  <div className="space-y-2 min-w-0">
                    <h3 className="text-sm font-bold text-[#F6F6F3]">Batter forecasts vs actual runs</h3>
                    {match.batters.length ? (
                      <>
                        <p className="text-[11px] text-[#8E8E88]">
                          {match.batters.length} eligible innings · Brier 30+ {dec4(match.batter_summary?.brier_30)} · Brier 50+ {dec4(match.batter_summary?.brier_50)}
                        </p>
                        <DataTable caption={`Batter forecasts for match ${match.match_id}`} columns={batterColumns} rows={match.batters} rowKey={(r) => `${r.innings}-${r.batter_id}`} maxHeight="max-h-96" dense />
                      </>
                    ) : (
                      <Note>No eligible batter forecasts for this match (it is excluded from the batter evaluation, for example a D/L-marked or no-result match).</Note>
                    )}
                  </div>
                  <div className="space-y-2 min-w-0">
                    <h3 className="text-sm font-bold text-[#F6F6F3]">Next-over wicket forecasts vs what happened</h3>
                    {match.wickets.length ? (
                      <>
                        <p className="text-[11px] text-[#8E8E88]">
                          {match.wickets.length} next overs · average forecast {pct1(mean(match.wickets.map((w) => w.predicted_probability)) ?? 0)} ·
                          a wicket fell in {match.wickets.filter((w) => w.wicket_fell).length} · Brier {dec4(match.wicket_summary?.brier_score)}
                        </p>
                        <DataTable caption={`Wicket forecasts for match ${match.match_id}`} columns={wicketColumns} rows={match.wickets} rowKey={(r) => `${r.innings}-${r.completed_overs}`} maxHeight="max-h-96" dense />
                      </>
                    ) : (
                      <Note>No eligible next-over checkpoints for this match.</Note>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
          <Note>Sources: {index.sources.join(', ')}.</Note>
        </>
      )}
    </section>
  );
};
