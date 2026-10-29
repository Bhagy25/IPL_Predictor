import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  EDAAreas,
  EDAHistogramBin,
  EDAMatchListItem,
  EDATossRecord,
  TeamPhaseRecord,
  TeamResultSummary,
} from '../../types';
import { Column, DataTable, StatCard } from '../player/ProfileSections';
import { FOCUS_RING, Stat, plural } from '../player/playerFormat';
import { fmtCount, fmtPct, fmtRate } from '../../utils/format';

type Data<K extends keyof EDAAreas> = NonNullable<EDAAreas[K]['data']>;

const CHART_TOOLTIP = {
  contentStyle: { backgroundColor: '#151619', borderColor: '#D9B15F', borderRadius: '0.75rem', fontSize: '12px' },
  labelStyle: { color: '#F6F6F3', fontWeight: 'bold' },
};
const AXIS = { stroke: '#8E8E88', fontSize: 11, tickLine: false };
const GOLD = '#D9B15F';
const BLUE = '#60A5FA';
const ROSE = '#FB7185';
const GREEN = '#34D399';

// Any per-season record; charts read their series by key
type SeasonRow = { season: number };

const NO_DECIDED = 'No decided matches in this selection';

/** Win % with its numerator and denominator, e.g. "55.8% (148/265)", or "—" with the reason. */
export const WinPct: React.FC<{ r: TeamResultSummary }> = ({ r }) => (
  <Stat
    value={r.win_pct === null ? null : `${fmtPct(r.win_pct)} (${fmtCount(r.wins)}/${fmtCount(r.win_pct_denominator)})`}
    reason={NO_DECIDED}
  />
);

const Rate: React.FC<{ v: number | null; reason?: string }> = ({ v, reason = 'No legal ball in this selection' }) => (
  <Stat value={fmtRate(v)} reason={reason} />
);

const SubHeading: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h4 className="text-[11px] font-bold uppercase tracking-wider text-[#B9B9B3]">{children}</h4>
);

/** A season line chart; the role=img label lists every plotted value for screen readers. */
const SeasonLines: React.FC<{
  rows: SeasonRow[];
  lines: { key: string; label: string; color: string }[];
  title: string;
  unit?: string;
}> = ({ rows, lines, title, unit = '' }) => (
  <div
    className="h-60 w-full min-w-0"
    role="img"
    aria-label={`${title}: ${rows.map((r) => `${r.season} ${lines.map((l) => `${l.label} ${(r as unknown as Record<string, unknown>)[l.key] ?? 'not available'}`).join(', ')}`).join('; ')}`}
  >
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <LineChart data={rows} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#25262B" />
        <XAxis dataKey="season" {...AXIS} />
        <YAxis {...AXIS} domain={['auto', 'auto']} />
        <Tooltip {...CHART_TOOLTIP} formatter={(v: any, name: any) => [`${v}${unit}`, name]} />
        {lines.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
        {lines.map((l) => (
          <Line key={l.key} type="monotone" dataKey={l.key} name={l.label} stroke={l.color} strokeWidth={2} dot={{ r: 2.5, fill: l.color }} connectNulls={false} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  </div>
);

const SeasonBars: React.FC<{ rows: SeasonRow[]; dataKey: string; label: string; color: string }> = ({ rows, dataKey, label, color }) => (
  <div className="h-56 w-full min-w-0" role="img" aria-label={`${label} per season: ${rows.map((r) => `${r.season} ${(r as unknown as Record<string, unknown>)[dataKey]}`).join(', ')}`}>
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <BarChart data={rows} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#25262B" vertical={false} />
        <XAxis dataKey="season" {...AXIS} />
        <YAxis {...AXIS} allowDecimals={false} />
        <Tooltip {...CHART_TOOLTIP} formatter={(v: any) => [fmtCount(v), label]} cursor={{ fill: '#ffffff08' }} />
        <Bar dataKey={dataKey} name={label} fill={color} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  </div>
);

const Histogram: React.FC<{ bins: EDAHistogramBin[]; label: string; color?: string }> = ({ bins, label, color = GOLD }) => (
  <div className="h-56 w-full min-w-0" role="img" aria-label={`${label}: ${bins.map((b) => `${b.bin} ${b.count}`).join(', ')}`}>
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <BarChart data={bins} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#25262B" vertical={false} />
        <XAxis dataKey="bin" {...AXIS} interval={0} fontSize={10} />
        <YAxis {...AXIS} allowDecimals={false} />
        <Tooltip {...CHART_TOOLTIP} formatter={(v: any, _n: any, p: any) => [`${fmtCount(v)} (${fmtPct(p.payload.pct)})`, label]} cursor={{ fill: '#ffffff08' }} />
        <Bar dataKey="count" name={label} fill={color} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  </div>
);

const StatGrid: React.FC<{ items: [string, React.ReactNode][] }> = ({ items }) => (
  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
    {items.map(([label, value]) => (
      <StatCard key={label} label={label}>{value}</StatCard>
    ))}
  </div>
);

const resultColumns = <T,>(get: (row: T) => TeamResultSummary): Column<T>[] => [
  { header: 'P', title: 'Matches', cell: (r) => fmtCount(get(r).played) },
  { header: 'W', title: 'Wins', cell: (r) => fmtCount(get(r).wins) },
  { header: 'L', title: 'Losses', cell: (r) => fmtCount(get(r).losses) },
  { header: 'T', title: 'Ties with no Super Over result', cell: (r) => fmtCount(get(r).ties) },
  { header: 'NR', title: 'No results', cell: (r) => fmtCount(get(r).no_results) },
  { header: 'Win %', title: 'Wins ÷ (matches − no results)', align: 'right', cell: (r) => <WinPct r={get(r)} /> },
];

// ------------------------------------------------------------------ 1. matches and runs

export const MatchesRunsView: React.FC<{ data: Data<'matches_runs'> }> = ({ data }) => (
  <>
    <StatGrid items={[
      ['Matches', fmtCount(data.totals.matches)],
      ['Runs', fmtCount(data.totals.runs)],
      ['Deliveries', fmtCount(data.totals.deliveries)],
      ['Legal balls', fmtCount(data.totals.legal_balls)],
      ['Wickets', fmtCount(data.totals.wickets)],
      ['Runs per over', <Rate key="rr" v={data.totals.run_rate} />],
    ]} />
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="space-y-1 min-w-0"><SubHeading>Matches per season</SubHeading><SeasonBars rows={data.by_season} dataKey="matches" label="Matches" color={GOLD} /></div>
      <div className="space-y-1 min-w-0"><SubHeading>Runs per season</SubHeading><SeasonBars rows={data.by_season} dataKey="runs" label="Runs" color="#C89B3C" /></div>
    </div>
  </>
);

// ------------------------------------------------------------------ 2. scoring trends

export const ScoringTrendsView: React.FC<{ data: Data<'scoring_trends'> }> = ({ data }) => (
  <>
    <StatGrid items={[
      ['Innings', fmtCount(data.totals.innings)],
      ['Runs per innings', fmtRate(data.totals.runs_per_innings)],
      ['Runs per over', <Rate key="rr" v={data.totals.run_rate} />],
    ]} />
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="space-y-1 min-w-0">
        <SubHeading>Mean innings total by season (runs)</SubHeading>
        <SeasonLines
          title="Mean innings totals by season"
          rows={data.by_season}
          lines={[
            { key: 'runs_per_innings', label: 'All innings', color: GOLD },
            { key: 'first_innings_mean', label: 'First innings', color: BLUE },
            { key: 'second_innings_mean', label: 'Second innings', color: ROSE },
          ]}
        />
      </div>
      <div className="space-y-1 min-w-0">
        <SubHeading>Run rate by season (runs per over)</SubHeading>
        <SeasonLines title="Run rate by season" rows={data.by_season} lines={[{ key: 'run_rate', label: 'Runs per over', color: GOLD }]} />
      </div>
    </div>
  </>
);

// ------------------------------------------------------------------ 3. batting distributions

export const BattingView: React.FC<{ data: Data<'batting_distribution'> }> = ({ data }) => (
  <>
    <StatGrid items={[
      ['Innings', fmtCount(data.summary.innings)],
      ['Mean runs / innings', fmtRate(data.summary.mean_runs)],
      ['Median runs', fmtCount(data.summary.median_runs)],
      ['Average', <Stat key="avg" value={fmtRate(data.summary.average)} state={data.summary.average_state} />],
      ['Strike rate', <Stat key="sr" value={fmtRate(data.summary.strike_rate)} state={data.summary.strike_rate_state} />],
      ['50+ / 100+', `${fmtCount(data.summary.scores_50_plus)} / ${fmtCount(data.summary.scores_100_plus)}`],
    ]} />
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="space-y-1 min-w-0">
        <SubHeading>Runs per batting innings ({plural(data.summary.innings, 'innings', 'innings')})</SubHeading>
        <Histogram bins={data.runs_histogram} label="Batting innings" />
      </div>
      <div className="space-y-1 min-w-0">
        <SubHeading>
          Strike rate per innings ({plural(data.strike_rate_innings, 'innings', 'innings')} with at least {plural(data.strike_rate_min_balls, 'ball')} faced
          {data.strike_rate_median !== null ? `; median ${fmtRate(data.strike_rate_median)}` : ''})
        </SubHeading>
        {data.strike_rate_histogram.length ? (
          <Histogram bins={data.strike_rate_histogram} label="Innings" color={BLUE} />
        ) : (
          <p className="text-xs text-[#8E8E88] italic">No innings meet the minimum balls faced.</p>
        )}
      </div>
    </div>
    <DataTable
      caption="Top run scorers in this selection"
      rows={data.leaders}
      rowKey={(r) => r.player_id}
      columns={[
        { header: 'Batter', cell: (r) => r.name },
        { header: 'Inns', title: 'Innings', cell: (r) => fmtCount(r.innings) },
        { header: 'Runs', cell: (r) => <span className="font-bold text-[#D9B15F]">{fmtCount(r.runs)}</span> },
        { header: 'Avg', title: 'Runs ÷ dismissals', cell: (r) => <Stat value={fmtRate(r.average)} state={r.average_state} /> },
        { header: 'SR', title: 'Runs per 100 balls', cell: (r) => <Stat value={fmtRate(r.strike_rate)} state={r.strike_rate_state} /> },
        { header: '4s / 6s', cell: (r) => `${fmtCount(r.fours)} / ${fmtCount(r.sixes)}` },
        { header: 'HS', title: 'Highest score (* not out)', align: 'right', cell: (r) => r.highest_score },
      ]}
    />
  </>
);

// ------------------------------------------------------------------ 4. bowling

export const BowlingView: React.FC<{ data: Data<'bowling'> }> = ({ data }) => (
  <>
    <StatGrid items={[
      ['Bowling innings', fmtCount(data.summary.innings)],
      ['Wickets', fmtCount(data.summary.wickets)],
      ['Overs', data.summary.overs_bowled],
      ['Economy', <Stat key="econ" value={fmtRate(data.summary.economy_rate)} state={data.summary.economy_rate_state} />],
      ['Average', <Stat key="avg" value={fmtRate(data.summary.bowling_average)} state={data.summary.bowling_average_state} />],
      ['Strike rate', <Stat key="sr" value={fmtRate(data.summary.bowling_strike_rate)} state={data.summary.bowling_strike_rate_state} />],
    ]} />
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="space-y-1 min-w-0">
        <SubHeading>
          Economy per bowling innings ({plural(data.economy_innings, 'innings', 'innings')} with at least {plural(data.economy_min_balls, 'legal ball')}
          {data.economy_median !== null ? `; median ${fmtRate(data.economy_median)}` : ''})
        </SubHeading>
        {data.economy_histogram.length ? (
          <Histogram bins={data.economy_histogram} label="Bowling innings" color={GREEN} />
        ) : (
          <p className="text-xs text-[#8E8E88] italic">No bowling innings meet the minimum legal balls.</p>
        )}
      </div>
      <div className="space-y-1 min-w-0">
        <SubHeading>Top wicket takers</SubHeading>
        <DataTable
          caption="Top wicket takers in this selection"
          rows={data.leaders}
          rowKey={(r) => r.player_id}
          columns={[
            { header: 'Bowler', cell: (r) => r.name },
            { header: 'Inns', title: 'Innings', cell: (r) => fmtCount(r.innings) },
            { header: 'Wkts', title: 'Bowler-credited wickets', cell: (r) => <span className="font-bold text-emerald-400">{fmtCount(r.wickets)}</span> },
            { header: 'Econ', title: 'Runs conceded per over', cell: (r) => <Stat value={fmtRate(r.economy_rate)} state={r.economy_rate_state} /> },
            { header: 'Avg', title: 'Runs conceded ÷ wickets', cell: (r) => <Stat value={fmtRate(r.bowling_average)} state={r.bowling_average_state} /> },
            { header: 'Best', align: 'right', cell: (r) => r.best_bowling },
          ]}
        />
      </div>
    </div>
  </>
);

// ------------------------------------------------------------------ 5. phases

const PHASE_COLORS: Record<string, string> = { powerplay: GOLD, middle: BLUE, death: ROSE };

export const PhasesView: React.FC<{ data: Data<'phases'> }> = ({ data }) => {
  const rows = data.by_season.map((s) => ({
    season: s.season,
    ...Object.fromEntries(s.phases.map((p) => [p.phase, p.batting_run_rate])),
  }));
  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {data.overall.map((p: TeamPhaseRecord) => (
          <div key={p.phase} className="bg-[#17181C] rounded-xl p-3 border border-white/5 space-y-1">
            <p className="text-[11px] font-bold uppercase tracking-wider" style={{ color: PHASE_COLORS[p.phase] }}>{p.label}</p>
            <p className="text-xs text-[#B9B9B3]">
              {data.team_view ? 'Batting run rate' : 'Run rate'}{' '}
              <span className="text-base font-black text-[#F6F6F3]"><Rate v={p.batting_run_rate} /></span>
            </p>
            <p className="text-[11px] text-[#8E8E88]">
              {fmtCount(p.batting_runs)} runs off {fmtCount(p.batting_legal_balls)} legal balls · wickets per over{' '}
              <Stat value={p.wickets_lost_per_six === null ? null : p.wickets_lost_per_six.toFixed(3)} reason="No legal ball in this selection" />
            </p>
            {data.team_view && (
              <p className="text-[11px] text-[#8E8E88]">
                Economy <span className="font-bold text-[#F6F6F3]"><Rate v={p.economy} /></span> ({fmtCount(p.conceded_runs)} conceded off {fmtCount(p.bowling_legal_balls)})
              </p>
            )}
          </div>
        ))}
      </div>
      <SubHeading>{data.team_view ? 'Batting run rate' : 'Run rate'} by phase and season (runs per over)</SubHeading>
      <SeasonLines
        title="Phase run rates by season"
        rows={rows}
        lines={data.overall.map((p) => ({ key: p.phase, label: p.label, color: PHASE_COLORS[p.phase] }))}
      />
    </>
  );
};

// ------------------------------------------------------------------ 6. team comparison

export const TeamComparisonView: React.FC<{ data: Data<'team_comparison'> }> = ({ data }) => (
  <DataTable
    caption="Franchise records in this selection, best win percentage first"
    rows={data.teams}
    rowKey={(r) => r.id}
    maxHeight="max-h-[30rem]"
    columns={[
      {
        header: 'Team',
        cell: (r) => (
          <span className={r.selected ? 'text-[#D9B15F] font-bold' : ''}>
            {r.team}
            {r.selected && <span className="sr-only"> (selected team)</span>}
            {r.status === 'Defunct' && <span className="ml-1 text-[10px] text-[#8E8E88]">(defunct)</span>}
          </span>
        ),
        className: 'whitespace-normal min-w-[9rem]',
      },
      { header: 'Seasons', title: 'Seasons in this selection', cell: (r) => r.seasons_label, className: 'whitespace-normal min-w-[6rem]' },
      ...resultColumns<Data<'team_comparison'>['teams'][number]>((r) => r),
      { header: 'RR', title: 'Batting runs per over', cell: (r) => <Rate v={r.run_rate} /> },
      { header: 'Econ', title: 'Runs conceded per over', align: 'right', cell: (r) => <Rate v={r.economy} /> },
    ]}
  />
);

// ------------------------------------------------------------------ 8. venues

export const VenuesView: React.FC<{ data: Data<'venues'> }> = ({ data }) => (
  <>
    <p className="text-xs text-[#B9B9B3]" aria-live="polite">
      Showing {plural(data.venues_shown, 'venue')} of {fmtCount(data.venues_total)} with at least {plural(data.min_matches, 'match', 'matches')} ({plural(data.matches_shown, 'match', 'matches')}).
    </p>
    {data.venues.length ? (
      <DataTable
        caption="Venues in this selection, most matches first"
        rows={data.venues}
        rowKey={(r) => r.venue}
        maxHeight="max-h-[30rem]"
        columns={[
          {
            header: 'Venue',
            cell: (r) => (
              <span className={r.selected ? 'text-[#D9B15F] font-bold' : ''}>
                {r.venue}{r.selected && <span className="sr-only"> (selected venue)</span>}
              </span>
            ),
            className: 'whitespace-normal min-w-[11rem]',
          },
          { header: 'Matches', cell: (r) => fmtCount(r.matches) },
          { header: '1st inns mean', title: 'Mean first-innings total', cell: (r) => <Stat value={fmtRate(r.first_innings_mean)} reason="No first innings recorded" /> },
          { header: 'Median', title: 'Median first-innings total', cell: (r) => <Stat value={r.first_innings_median === null ? null : fmtCount(r.first_innings_median)} reason="No first innings recorded" /> },
          { header: 'RR', title: 'Runs per over, all innings', cell: (r) => <Rate v={r.run_rate} /> },
          { header: 'Result', title: 'Batting-first result, or the selected team\'s result', cell: (r) => `${r.result_label}: ${fmtCount(r.result.wins)}–${fmtCount(r.result.losses)}`, className: 'whitespace-normal min-w-[9rem]' },
          { header: 'Win %', align: 'right', cell: (r) => <WinPct r={r.result} /> },
        ]}
      />
    ) : (
      <p className="text-xs text-[#8E8E88] italic">No venue has that many matches in this selection; lower the minimum.</p>
    )}
  </>
);

// ------------------------------------------------------------------ 9. toss

type TossRow = { label: string; r: TeamResultSummary };

export const TossView: React.FC<{ data: Data<'toss'> }> = ({ data }) => {
  const o: EDATossRecord = data.overall;
  const rows = data.by_season.map((s) => ({
    season: s.season,
    field_share: s.tosses_won ? Math.round((s.elected_to_field * 1000) / s.tosses_won) / 10 : null,
    toss_winner_win_pct: s.after_winning_toss.win_pct,
  }));
  return (
    <>
      <StatGrid items={[
        [data.team_view ? 'Tosses won' : 'Tosses', fmtCount(o.tosses_won)],
        ['Chose to field', `${fmtCount(o.elected_to_field)} (${fmtPct(o.tosses_won ? Math.round((o.elected_to_field * 1000) / o.tosses_won) / 10 : null)})`],
        ['Chose to bat', `${fmtCount(o.elected_to_bat)} (${fmtPct(o.tosses_won ? Math.round((o.elected_to_bat * 1000) / o.tosses_won) / 10 : null)})`],
      ]} />
      <DataTable<TossRow>
        caption="Results of the toss winner"
        rows={[
          { label: 'After winning the toss', r: o.after_winning_toss },
          { label: 'Chose to bat', r: o.chose_to_bat },
          { label: 'Chose to field', r: o.chose_to_field },
        ]}
        rowKey={(r) => r.label}
        columns={[{ header: 'Toss winner', cell: (r) => r.label }, ...resultColumns<TossRow>((r) => r.r)]}
      />
      <SubHeading>By season: share choosing to field and toss winner's win % (%)</SubHeading>
      <SeasonLines
        title="Toss decisions and toss winner results by season"
        unit="%"
        rows={rows}
        lines={[
          { key: 'field_share', label: 'Chose to field', color: BLUE },
          { key: 'toss_winner_win_pct', label: "Toss winner's win %", color: GOLD },
        ]}
      />
    </>
  );
};

// ------------------------------------------------------------------ 10. batting first vs chasing

export const InningsOrderView: React.FC<{ data: Data<'innings_order'>; teamName?: string }> = ({ data, teamName }) => {
  const oc = data.outcomes;
  const rows = data.by_season.map((s) => ({
    season: s.season,
    batting_first: s.batting_first.win_pct,
    chasing: s.chasing.win_pct,
  }));
  const who = data.team_view && teamName ? teamName : 'The side';
  return (
    <>
      <p className="text-xs text-[#B9B9B3] bg-[#17181C] border border-white/5 rounded-lg px-3 py-2">
        <span className="font-bold text-[#F6F6F3]">{plural(oc.decided, 'decided match', 'decided matches')}</span>
        {' '}= {fmtCount(oc.decided_in_regulation)} decided in regulation (including {fmtCount(oc.dl_method)} by D/L) + {fmtCount(oc.decided_by_super_over)} by Super Over.
        {' '}{plural(oc.no_result, 'no result', 'no results')} excluded{oc.other_not_recorded ? `, ${plural(oc.other_not_recorded, 'match', 'matches')} without a recorded result` : ''}.
        {' '}Total: {plural(oc.matches, 'match', 'matches')}.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {([['batting first', data.overall.batting_first, GOLD], ['chasing', data.overall.chasing, BLUE]] as const).map(([label, r, color]) => (
          <div key={label} className="bg-[#17181C] rounded-xl p-3 border border-white/5">
            <p className="text-[11px] font-bold uppercase tracking-wider" style={{ color }}>{who} {label}</p>
            <p className="text-lg font-black text-[#F6F6F3]"><WinPct r={r} /></p>
            <p className="text-[11px] text-[#8E8E88]">{fmtCount(r.wins)} won, {fmtCount(r.losses)} lost{r.ties ? `, ${fmtCount(r.ties)} tied` : ''} · Super Over wins {fmtCount(r.super_over_wins)}</p>
          </div>
        ))}
      </div>
      <SubHeading>Win % by season (wins ÷ decided matches)</SubHeading>
      <SeasonLines
        title="Batting first and chasing win percentage by season"
        unit="%"
        rows={rows}
        lines={[
          { key: 'batting_first', label: 'Batting first', color: GOLD },
          { key: 'chasing', label: 'Chasing', color: BLUE },
        ]}
      />
    </>
  );
};

// ------------------------------------------------------------------ 11. innings scores

export const InningsScoresView: React.FC<{ data: Data<'innings_scores'> }> = ({ data }) => (
  <>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {data.by_innings.map((d) => (
        <div key={d.innings} className="space-y-1 min-w-0">
          <SubHeading>{d.innings === 1 ? 'First' : 'Second'} innings totals ({plural(d.n, 'innings', 'innings')})</SubHeading>
          {d.histogram.length ? (
            <Histogram bins={d.histogram} label={`${d.innings === 1 ? 'First' : 'Second'} innings`} color={d.innings === 1 ? GOLD : BLUE} />
          ) : (
            <p className="text-xs text-[#8E8E88] italic">No {d.innings === 1 ? 'first' : 'second'} innings in this selection.</p>
          )}
        </div>
      ))}
    </div>
    <DataTable
      caption="Innings-score summary"
      rows={data.by_innings}
      rowKey={(r) => r.innings}
      columns={[
        { header: 'Innings', cell: (r) => (r.innings === 1 ? 'First' : 'Second') },
        { header: 'n', cell: (r) => fmtCount(r.n) },
        { header: 'Mean', cell: (r) => <Stat value={fmtRate(r.mean)} reason="No innings" /> },
        { header: 'Q1', cell: (r) => <Stat value={r.q1 === null ? null : r.q1.toFixed(1)} reason="No innings" /> },
        { header: 'Median', cell: (r) => <Stat value={r.median === null ? null : r.median.toFixed(1)} reason="No innings" /> },
        { header: 'Q3', cell: (r) => <Stat value={r.q3 === null ? null : r.q3.toFixed(1)} reason="No innings" /> },
        { header: 'Min–Max', cell: (r) => <Stat value={r.min === null ? null : `${r.min}–${r.max}`} reason="No innings" /> },
        { header: 'Full (120 balls)', align: 'right', cell: (r) => fmtCount(r.full_innings) },
      ]}
    />
  </>
);

// ------------------------------------------------------------------ 12. dismissals

const KIND_LABEL = (k: string) => k.charAt(0).toUpperCase() + k.slice(1);

export const DismissalsView: React.FC<{ data: Data<'dismissals'> }> = ({ data }) => (
  <>
    <StatGrid items={[
      ['Dismissal events', fmtCount(data.events)],
      ['Bowler-credited', fmtCount(data.bowler_credited)],
      ['Not credited', fmtCount(data.not_bowler_credited)],
      ['Team wickets', fmtCount(data.team_wickets)],
      ['Not team wickets', fmtCount(data.not_team_wickets)],
      ['Super-over events (excluded)', fmtCount(data.super_over_events_excluded)],
    ]} />
    <p className="text-[11px] text-[#8E8E88]">
      Reconciliation: {fmtCount(data.events)} events − {fmtCount(data.not_team_wickets)} retired hurt / not out = {fmtCount(data.team_wickets)} team wickets
      {data.team_wickets === data.team_wickets_from_deliveries ? ', equal to' : ', compare'} the {fmtCount(data.team_wickets_from_deliveries)} wickets in the ball-by-ball data.
    </p>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div
        className="h-72 w-full min-w-0"
        role="img"
        aria-label={`Dismissal types: ${data.kinds.map((k) => `${k.kind} ${k.count}`).join(', ')}`}
      >
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <BarChart data={data.kinds} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#25262B" horizontal={false} />
            <XAxis type="number" {...AXIS} allowDecimals={false} />
            <YAxis type="category" dataKey="kind" {...AXIS} width={104} fontSize={10} tickFormatter={KIND_LABEL} />
            <Tooltip {...CHART_TOOLTIP} formatter={(v: any, _n: any, p: any) => [`${fmtCount(v)} (${fmtPct(p.payload.pct)})`, 'Events']} cursor={{ fill: '#ffffff08' }} />
            <Bar dataKey="bowler_credited" stackId="k" name="Bowler-credited" fill={GOLD} />
            <Bar dataKey="not_bowler_credited" stackId="k" name="Not credited" fill="#6B7280" radius={[0, 4, 4, 0]} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <DataTable
        caption="Dismissal types"
        rows={data.kinds}
        rowKey={(r) => r.kind}
        columns={[
          { header: 'Kind', cell: (r) => KIND_LABEL(r.kind) },
          { header: 'Events', cell: (r) => fmtCount(r.count) },
          { header: 'Share', cell: (r) => fmtPct(r.pct) },
          { header: 'Bowler', title: 'Credited to the bowler', cell: (r) => (r.bowler_credited === r.count ? 'Credited' : r.bowler_credited ? `${fmtCount(r.bowler_credited)} credited` : 'Not credited') },
          { header: 'Team wicket', align: 'right', cell: (r) => (r.team_wickets === r.count ? 'Yes' : r.team_wickets ? `${fmtCount(r.team_wickets)}` : 'No') },
        ]}
      />
    </div>
  </>
);

// ------------------------------------------------------------------ 13. boundaries

export const BoundariesView: React.FC<{ data: Data<'boundaries'> }> = ({ data }) => (
  <>
    <StatGrid items={[
      ['Fours', fmtCount(data.totals.fours)],
      ['Sixes', fmtCount(data.totals.sixes)],
      ['Boundary runs', `${fmtCount(data.totals.boundary_runs)} (${fmtPct(data.totals.boundary_run_pct)})`],
      ['Dot balls', `${fmtCount(data.totals.dot_balls)} (${fmtPct(data.totals.dot_ball_pct)})`],
      ['Balls per boundary', <Stat key="bpb" value={fmtRate(data.totals.balls_per_boundary)} reason="No boundary in this selection" />],
      ['Legal balls', fmtCount(data.totals.legal_balls)],
    ]} />
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="space-y-1 min-w-0">
        <SubHeading>Boundary-run % and dot-ball % by season (%)</SubHeading>
        <SeasonLines
          title="Boundary run percentage and dot ball percentage by season"
          unit="%"
          rows={data.by_season}
          lines={[
            { key: 'boundary_run_pct', label: 'Boundary runs % of runs', color: GOLD },
            { key: 'dot_ball_pct', label: 'Dot balls % of legal balls', color: '#9CA3AF' },
          ]}
        />
      </div>
      <div className="space-y-1 min-w-0">
        <SubHeading>Fours and sixes by season</SubHeading>
        <div
          className="h-60 w-full min-w-0"
          role="img"
          aria-label={`Fours and sixes by season: ${data.by_season.map((s) => `${s.season} ${s.fours} fours ${s.sixes} sixes`).join('; ')}`}
        >
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart data={data.by_season} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#25262B" vertical={false} />
              <XAxis dataKey="season" {...AXIS} />
              <YAxis {...AXIS} allowDecimals={false} />
              <Tooltip {...CHART_TOOLTIP} formatter={(v: any, n: any) => [fmtCount(v), n]} cursor={{ fill: '#ffffff08' }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="fours" name="Fours" fill={BLUE} radius={[3, 3, 0, 0]} />
              <Bar dataKey="sixes" name="Sixes" fill={GOLD} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  </>
);

// ------------------------------------------------------------------ 14. anomalies

const REASONS: Record<string, string> = { impact_player: 'Impact Player', concussion_substitute: 'Concussion substitute' };

const MatchList: React.FC<{ title: string; matches: EDAMatchListItem[] }> = ({ title, matches }) => (
  <details className="bg-[#17181C] rounded-lg border border-white/5 px-3 py-2">
    <summary className={`cursor-pointer text-xs font-semibold text-[#F6F6F3] rounded ${FOCUS_RING}`}>
      {title} ({fmtCount(matches.length)})
    </summary>
    {matches.length ? (
      <ul className="mt-2 space-y-1 text-[11px] text-[#B9B9B3]">
        {matches.map((m) => (
          <li key={m.match_id}>
            {m.date} · {m.teams} · {m.venue} · {m.winner ? `${m.winner} won` : 'no winner'}
          </li>
        ))}
      </ul>
    ) : (
      <p className="mt-2 text-[11px] text-[#8E8E88] italic">None in this selection.</p>
    )}
  </details>
);

export const AnomaliesView: React.FC<{ data: Data<'anomalies'> }> = ({ data }) => {
  const audit = data.stage1_audit;
  return (
    <>
      <StatGrid items={[
        ['Super Over matches', fmtCount(data.super_over_matches)],
        ['D/L-decided matches', fmtCount(data.dl_matches)],
        ['No results', fmtCount(data.no_results)],
        ['Penalty-run deliveries', `${fmtCount(data.penalty_run_deliveries)} (${plural(data.penalty_runs, 'run')})`],
        ['Substitutions', fmtCount(data.substitutions)],
        ['Missing city', plural(data.missing_city_matches, 'match', 'matches')],
      ]} />
      <p className="text-[11px] text-[#8E8E88]">
        Substitutions: {Object.entries(data.substitutions_by_reason).map(([k, v]) => `${REASONS[k] ?? k} ${fmtCount(v)}`).join(', ') || 'none'}
        {data.substitutions_in_super_overs ? ` (${plural(data.substitutions_in_super_overs, 'substitution')} recorded during a Super Over)` : ''}.
        {' '}Matches with fewer than two innings: {fmtCount(data.matches_without_two_innings)}.
      </p>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-2">
        <MatchList title="Super Over matches" matches={data.lists.super_over} />
        <MatchList title="D/L-decided matches" matches={data.lists.dl} />
        <MatchList title="No-result matches" matches={data.lists.no_result} />
      </div>
      <div className="border border-dashed border-[#8E8E88]/40 rounded-xl p-3 sm:p-4 space-y-2 bg-[#101114]">
        <p className="text-[11px] font-bold uppercase tracking-wider text-[#B9B9B3]">{audit.label}</p>
        <p className="text-[11px] text-[#8E8E88]">Coverage: {audit.coverage}. {audit.source}</p>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <DataTable
            caption="Stage 1 screening issues"
            rows={Object.entries(audit.screening_issue_counts)}
            rowKey={([k]) => k}
            columns={[
              { header: 'Screening issue', cell: ([k]) => k.replace(/_/g, ' ') },
              { header: 'Count', align: 'right', cell: ([, v]) => fmtCount(v) },
            ]}
          />
          <DataTable
            caption="Stage 1 missing fields"
            rows={audit.missingness}
            rowKey={(r) => `${r.table}.${r.column}`}
            columns={[
              { header: 'Field', cell: (r) => `${r.table}.${r.column}` },
              { header: 'Missing', cell: (r) => `${fmtCount(r.missing_count)} of ${fmtCount(r.total_rows)}` },
              { header: '%', align: 'right', cell: (r) => fmtPct(Math.round(r.missing_pct * 10) / 10) },
            ]}
          />
        </div>
      </div>
    </>
  );
};

// ------------------------------------------------------------------ 15. correlations

const corrColor = (v: number | null) =>
  v === null ? 'text-[#8E8E88]' : v >= 0.5 ? 'text-emerald-400 font-bold' : v <= -0.3 ? 'text-rose-400 font-bold' : 'text-[#B9B9B3]';

export const CorrelationsView: React.FC<{ data: Data<'correlations'> }> = ({ data }) => {
  const label = Object.fromEntries(data.variables.map((v) => [v.key, v.label]));
  if (data.state !== 'ok' || !data.pearson || !data.spearman) {
    return (
      <p role="status" className="text-xs text-amber-200 bg-amber-950/40 border border-amber-500/30 rounded-lg px-3 py-2">
        {data.explanation}
      </p>
    );
  }
  const pearson = data.pearson;
  const coef = (v: number | null) => <span className={corrColor(v)}><Stat value={v === null ? null : v.toFixed(3)} reason="Undefined: a variable is constant in this selection" /></span>;
  return (
    <>
      <p className="text-[11px] text-[#8E8E88]">n = {fmtCount(data.n)} first innings (minimum {data.min_n}). Coefficient types: Pearson (linear) and Spearman (rank).</p>
      <DataTable
        caption="Correlation of each first-innings variable with the innings total"
        rows={data.pairs_with_total}
        rowKey={(r) => r.x}
        columns={[
          { header: 'Variable vs total runs', cell: (r) => label[r.x] },
          { header: 'Pearson r', cell: (r) => coef(r.pearson) },
          { header: 'Spearman ρ', align: 'right', cell: (r) => coef(r.spearman) },
        ]}
      />
      <details>
        <summary className={`cursor-pointer text-[11px] font-semibold text-[#D9B15F] rounded ${FOCUS_RING}`}>Full Pearson matrix</summary>
        <div className="mt-2">
          <DataTable
            caption="Pearson correlation matrix of first-innings variables"
            rows={data.variables}
            rowKey={(r) => r.key}
            dense
            columns={[
              { header: 'Variable', cell: (r) => r.label },
              ...data.variables.map((c) => ({ header: c.label, cell: (r: { key: string }) => coef(pearson[r.key][c.key]) })),
            ]}
          />
        </div>
      </details>
    </>
  );
};
