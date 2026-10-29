import React from 'react';
import { BarChart3, Database, TrendingUp, CheckCircle2 } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  Legend,
} from 'recharts';
import { OverviewChartsResponse } from '../types';
import { fmtCount, fmtSeasons } from '../utils/format';

interface PerspectiveChartsProps {
  chartsData?: OverviewChartsResponse | null;
  loading?: boolean;
}

// Custom tooltip with black & gold theme
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#1A1B1E] border border-[#D9B15F]/40 p-3 rounded-xl shadow-xl text-xs space-y-1.5 backdrop-blur-md">
        <p className="font-semibold text-[#F6F6F3] border-b border-white/[0.08] pb-1">
          {label}
        </p>
        {payload.map((entry: any, index: number) => (
          <div key={`item-${index}`} className="flex items-center justify-between gap-4">
            <span className="text-[#B9B9B3] flex items-center gap-1.5">
              <span
                className="w-2 h-2 rounded-full inline-block"
                style={{ backgroundColor: entry.color || '#D9B15F' }}
              />
              {entry.name || 'Value'}:
            </span>
            <span className="font-mono font-bold text-[#F6F6F3]">
              {typeof entry.value === 'number'
                ? entry.value.toLocaleString(undefined, { maximumFractionDigits: 1 })
                : entry.value}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export const PerspectiveCharts: React.FC<PerspectiveChartsProps> = ({
  chartsData,
  loading = false,
}) => {
  const matchesPerSeason = chartsData?.matches_per_season || [];
  const scoringTrends = chartsData?.scoring_trends || [];
  const resultDistribution = chartsData?.result_distribution || [];
  const scoringDistribution = chartsData?.scoring_distribution || [];

  const hasData = matchesPerSeason.length > 0;

  // Every caption below is built from the API response; nothing is typed in
  const counts = matchesPerSeason.map((s) => s.matches);
  const totalMatches = counts.reduce((a, b) => a + b, 0);
  const maxTeams = Math.max(0, ...matchesPerSeason.map((s) => s.teams));
  const maxTeamSeasons = matchesPerSeason.filter((s) => s.teams === maxTeams).map((s) => s.season);
  const trend = chartsData?.scoring_trend;
  const outcomes = chartsData?.outcomes;
  const scoring = chartsData?.scoring_summary;
  const signed = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}`;

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1 pb-1">
        <div className="flex items-center gap-2.5">
          <span className="w-1.5 h-5 bg-[#D9B15F] rounded-full inline-block" />
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#F6F6F3]">
            The IPL in perspective
          </h2>
        </div>
        <span className="text-xs sm:text-sm font-medium text-[#B9B9B3]/75 ml-4 sm:ml-0">
          Historical insights{hasData ? <> &middot; {matchesPerSeason[0].season} to present</> : null}
        </span>
      </div>

      {/* 2x2 Grid of Chart Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        
        {/* Chart 1: Matches per Season */}
        <div className="bg-[#151619] border border-white/[0.08] rounded-2xl p-4 sm:p-6 flex flex-col justify-between hover:border-white/[0.12] transition-colors shadow-sm min-w-0">
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-[#D9B15F]" />
                <h3 className="text-sm sm:text-base font-semibold text-[#F6F6F3]">
                  Matches per season
                </h3>
              </div>
              <p className="text-xs text-[#B9B9B3] mt-0.5">
                The evolution of the IPL schedule{hasData ? ` (${Math.min(...counts)} to ${Math.max(...counts)} matches/yr)` : ''}
              </p>
            </div>
            {hasData && (
              <span className="inline-flex items-center text-[10px] sm:text-[11px] font-medium text-[#D9B15F] bg-[#D9B15F]/10 px-2.5 py-0.5 rounded-full border border-[#D9B15F]/20">
                {matchesPerSeason.length} seasons &middot; {fmtCount(totalMatches)} matches
              </span>
            )}
          </div>

          <div className="relative w-full h-64 sm:h-72 rounded-xl bg-[#0D0E10] border border-white/[0.04] p-2 sm:p-3 min-w-0">
            {loading ? (
              <div className="w-full h-full flex items-center justify-center">
                <div className="h-40 w-full bg-white/[0.04] rounded-lg animate-pulse" />
              </div>
            ) : hasData ? (
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <BarChart data={matchesPerSeason} margin={{ top: 12, right: 12, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#232428" vertical={false} />
                  <XAxis
                    dataKey="season"
                    tick={{ fill: '#8E8E88', fontSize: 10 }}
                    axisLine={{ stroke: '#2A2B30' }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 'auto']}
                    tick={{ fill: '#8E8E88', fontSize: 10 }}
                    axisLine={{ stroke: '#2A2B30' }}
                    tickLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="matches" name="Matches" fill="#D9B15F" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyStateNotice />
            )}
          </div>

          {hasData && (
            <div className="mt-3 flex items-center justify-between gap-2 text-[11px] text-[#B9B9B3]/75">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#D9B15F]" />
                <span>{maxTeams}-team seasons: {fmtSeasons(maxTeamSeasons)}</span>
              </div>
              <span className="font-mono text-[#D9B15F]">Total: {fmtCount(totalMatches)}</span>
            </div>
          )}
        </div>

        {/* Chart 2: Season-wise scoring trends */}
        <div className="bg-[#151619] border border-white/[0.08] rounded-2xl p-4 sm:p-6 flex flex-col justify-between hover:border-white/[0.12] transition-colors shadow-sm min-w-0">
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-[#D9B15F]" />
                <h3 className="text-sm sm:text-base font-semibold text-[#F6F6F3]">
                  Season-wise scoring trends
                </h3>
              </div>
              <p className="text-xs text-[#B9B9B3] mt-0.5">
                Mean and median first-innings scores per season
              </p>
            </div>
            {trend && (
              <span
                title={`Mean of all ${fmtCount(trend.first_innings)} recorded first innings, ${trend.seasons_label}`}
                className="inline-flex items-center text-[10px] sm:text-[11px] font-medium text-[#D9B15F] bg-[#D9B15F]/10 px-2.5 py-0.5 rounded-full border border-[#D9B15F]/20"
              >
                Mean: {trend.overall_mean.toFixed(1)} runs
              </span>
            )}
          </div>

          <div className="relative w-full h-64 sm:h-72 rounded-xl bg-[#0D0E10] border border-white/[0.04] p-2 sm:p-3 min-w-0">
            {loading ? (
              <div className="w-full h-full flex items-center justify-center">
                <div className="h-40 w-full bg-white/[0.04] rounded-lg animate-pulse" />
              </div>
            ) : hasData ? (
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <LineChart data={scoringTrends} margin={{ top: 12, right: 12, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#232428" vertical={false} />
                  <XAxis
                    dataKey="season"
                    tick={{ fill: '#8E8E88', fontSize: 10 }}
                    axisLine={{ stroke: '#2A2B30' }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[(min: number) => Math.floor(min / 10) * 10 - 10, (max: number) => Math.ceil(max / 10) * 10]}
                    allowDecimals={false}
                    tick={{ fill: '#8E8E88', fontSize: 10 }}
                    axisLine={{ stroke: '#2A2B30' }}
                    tickLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend
                    verticalAlign="top"
                    align="right"
                    iconType="circle"
                    iconSize={7}
                    wrapperStyle={{ fontSize: '11px', paddingBottom: '6px' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="avg_first_innings_runs"
                    name="Mean 1st Innings"
                    stroke="#D9B15F"
                    strokeWidth={2.2}
                    dot={{ r: 2.5, fill: '#D9B15F' }}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="median_first_innings_runs"
                    name="Median 1st Innings"
                    stroke="#8E8E88"
                    strokeWidth={1.8}
                    strokeDasharray="4 4"
                    dot={{ r: 2, fill: '#8E8E88' }}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyStateNotice />
            )}
          </div>

          {trend && (
            <div className="mt-3 flex items-center justify-between gap-2 text-[11px] text-[#B9B9B3]/75">
              <div className="flex items-center gap-1.5" title={trend.definition}>
                <span className="w-1.5 h-1.5 rounded-full bg-[#D9B15F]" />
                <span>Observational linear trend ({trend.seasons_label}): {signed(trend.slope_runs_per_season)} runs/season</span>
              </div>
              <span className="font-mono text-[#D9B15F]">{trend.peak_season} Peak: {trend.peak_mean.toFixed(1)}</span>
            </div>
          )}
        </div>

        {/* Chart 3: Historical match result distribution */}
        <div className="bg-[#151619] border border-white/[0.08] rounded-2xl p-4 sm:p-6 flex flex-col justify-between hover:border-white/[0.12] transition-colors shadow-sm min-w-0">
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#D9B15F]" />
                <h3 className="text-sm sm:text-base font-semibold text-[#F6F6F3]">
                  Historical match result distribution
                </h3>
              </div>
              <p className="text-xs text-[#B9B9B3] mt-0.5">
                Outcome categories: regulation wins, ties &amp; no results
              </p>
            </div>
            {outcomes && (
              <span className="inline-flex items-center text-[10px] sm:text-[11px] font-medium text-[#D9B15F] bg-[#D9B15F]/10 px-2.5 py-0.5 rounded-full border border-[#D9B15F]/20">
                {fmtCount(outcomes.decided_in_regulation)} wins &middot; {fmtCount(outcomes.decided_by_super_over)} ties &middot; {fmtCount(outcomes.no_result)} NR
              </span>
            )}
          </div>

          <div className="relative w-full h-64 sm:h-72 rounded-xl bg-[#0D0E10] border border-white/[0.04] p-2 sm:p-3 min-w-0">
            {loading ? (
              <div className="w-full h-full flex items-center justify-center">
                <div className="h-40 w-full bg-white/[0.04] rounded-lg animate-pulse" />
              </div>
            ) : resultDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <BarChart data={resultDistribution} margin={{ top: 16, right: 16, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#232428" vertical={false} />
                  <XAxis
                    dataKey="category"
                    tick={{ fill: '#8E8E88', fontSize: 11 }}
                    axisLine={{ stroke: '#2A2B30' }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 'auto']}
                    tick={{ fill: '#8E8E88', fontSize: 10 }}
                    axisLine={{ stroke: '#2A2B30' }}
                    tickLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" name="Matches" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                    {resultDistribution.map((_, idx) => (
                      <Cell
                        key={`cell-${idx}`}
                        fill={idx === 0 ? '#D9B15F' : idx === 1 ? '#E5C687' : '#6B7280'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyStateNotice />
            )}
          </div>

          <div className="mt-3 flex items-center justify-between gap-2 text-[11px] text-[#B9B9B3]/75">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#D9B15F]" />
              <span>Super Over winners credited in final team records</span>
            </div>
            {outcomes && outcomes.decided_pct !== null && (
              <span
                className="font-mono text-[#D9B15F]"
                title={`${fmtCount(outcomes.decided)} of ${fmtCount(outcomes.matches)} matches had a winner (regulation, D/L or Super Over)`}
              >
                {outcomes.decided_pct.toFixed(1)}% Decided
              </span>
            )}
          </div>
        </div>

        {/* Chart 4: Overall IPL scoring distribution */}
        <div className="bg-[#151619] border border-white/[0.08] rounded-2xl p-4 sm:p-6 flex flex-col justify-between hover:border-white/[0.12] transition-colors shadow-sm min-w-0">
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-[#D9B15F]" />
                <h3 className="text-sm sm:text-base font-semibold text-[#F6F6F3]">
                  Overall IPL scoring distribution
                </h3>
              </div>
              <p className="text-xs text-[#B9B9B3] mt-0.5" title={scoring?.eligibility_rule}>
                Histogram of first-innings score spans
                {scoring ? ` (${fmtCount(scoring.n)} completed innings of ${fmtCount(scoring.first_innings_recorded)} recorded)` : ''}
              </p>
            </div>
            {scoring && (
              <span className="inline-flex items-center text-[10px] sm:text-[11px] font-medium text-[#D9B15F] bg-[#D9B15F]/10 px-2.5 py-0.5 rounded-full border border-[#D9B15F]/20">
                IQR: {scoring.q1}–{scoring.q3} runs
              </span>
            )}
          </div>

          <div className="relative w-full h-64 sm:h-72 rounded-xl bg-[#0D0E10] border border-white/[0.04] p-2 sm:p-3 min-w-0">
            {loading ? (
              <div className="w-full h-full flex items-center justify-center">
                <div className="h-40 w-full bg-white/[0.04] rounded-lg animate-pulse" />
              </div>
            ) : scoringDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <BarChart data={scoringDistribution} margin={{ top: 16, right: 16, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#232428" vertical={false} />
                  <XAxis
                    dataKey="span"
                    tick={{ fill: '#8E8E88', fontSize: 10 }}
                    axisLine={{ stroke: '#2A2B30' }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 'auto']}
                    tick={{ fill: '#8E8E88', fontSize: 10 }}
                    axisLine={{ stroke: '#2A2B30' }}
                    tickLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" name="Innings Count" fill="#D9B15F" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                    {scoringDistribution.map((_, idx) => (
                      <Cell
                        key={`cell-${idx}`}
                        fill={idx === 2 ? '#D9B15F' : idx === 3 ? '#E5C687' : '#9E854E'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyStateNotice />
            )}
          </div>

          {scoring && (
            <div className="mt-3 flex items-center justify-between gap-2 text-[11px] text-[#B9B9B3]/75">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#D9B15F]" />
                <span>Modal category: {scoring.modal_span} runs ({scoring.modal_pct.toFixed(1)}% of innings)</span>
              </div>
              <span className="font-mono text-[#D9B15F]">Range: {scoring.min}–{scoring.max}</span>
            </div>
          )}
          {scoring && scoring.excluded.length > 0 && (
            <p className="mt-1.5 text-[10px] text-[#8E8E88]">
              Excludes {scoring.excluded.length} first innings cut short by a no-result abandonment.
            </p>
          )}
        </div>

      </div>
    </div>
  );
};

const EmptyStateNotice: React.FC = () => (
  <div className="flex flex-col items-center justify-center text-center my-auto space-y-2">
    <div className="w-9 h-9 rounded-xl bg-black/50 border border-[#D9B15F]/25 flex items-center justify-center text-[#D9B15F] shadow-gold-pill">
      <Database className="w-4 h-4" />
    </div>
    <div>
      <h4 className="text-sm font-medium text-[#F6F6F3]">Awaiting historical data</h4>
      <p className="text-xs text-[#B9B9B3]/75 mt-0.5">No verified data available to plot.</p>
    </div>
  </div>
);
