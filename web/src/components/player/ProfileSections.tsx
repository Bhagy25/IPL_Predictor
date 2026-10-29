import React, { useRef, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { BookOpen, Flame, Info, MapPin, Shield } from 'lucide-react';
import {
  PlayerBattingSeason,
  PlayerBattingSummary,
  PlayerBowlingSeason,
  PlayerBowlingSummary,
  PlayerProfileResponse,
  PlayerTeamSpell,
} from '../../types';
import { FOCUS_RING, Stat, fixed2, plural } from './playerFormat';

// ------------------------------------------------------------------ building blocks

export const StatCard: React.FC<{ label: string; accent?: string; children: React.ReactNode }> = ({ label, accent = 'text-[#F6F6F3]', children }) => (
  <div className="bg-[#17181C] p-2.5 rounded-lg border border-white/5">
    <span className="text-[10px] uppercase text-[#8E8E88] font-bold">{label}</span>
    <p className={`text-base font-black ${accent}`}>{children}</p>
  </div>
);

interface TabItem { id: string; label: string }

/** Keyboard-operable tabs (arrow keys, Home, End) controlling one panel. */
export const Tabs: React.FC<{
  label: string;
  idPrefix: string;
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
  children: React.ReactNode;
}> = ({ label, idPrefix, tabs, active, onChange, children }) => {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const onKeyDown = (e: React.KeyboardEvent) => {
    const i = tabs.findIndex((t) => t.id === active);
    const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    const tab = tabs[(next + tabs.length) % tabs.length];
    onChange(tab.id);
    refs.current[tab.id]?.focus();
  };
  return (
    <div className="space-y-3">
      <div role="tablist" aria-label={label} className="flex flex-wrap gap-2" onKeyDown={onKeyDown}>
        {tabs.map((t) => (
          <button
            key={t.id}
            ref={(el) => { refs.current[t.id] = el; }}
            role="tab"
            id={`${idPrefix}-tab-${t.id}`}
            aria-selected={active === t.id}
            aria-controls={`${idPrefix}-panel`}
            tabIndex={active === t.id ? 0 : -1}
            onClick={() => onChange(t.id)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${FOCUS_RING} ${
              active === t.id
                ? 'bg-[#D9B15F] text-[#0D0E10] shadow-sm'
                : 'bg-[#101114] text-[#B9B9B3] hover:text-[#F6F6F3] border border-[#D9B15F]/15'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${idPrefix}-panel`} aria-labelledby={`${idPrefix}-tab-${active}`}>
        {children}
      </div>
    </div>
  );
};

export interface Column<T> {
  header: string;
  title?: string;
  cell: (row: T) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  // Lets long text wrap (e.g. "whitespace-normal min-w-[7rem]") instead of widening the table
  className?: string;
}

const ALIGN = { left: 'text-left', center: 'text-center', right: 'text-right' };

/** A table that scrolls inside its own container; the first column is the row header. */
export function DataTable<T>({ caption, columns, rows, rowKey, maxHeight, dense = false }: {
  caption: string;
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  maxHeight?: string;
  // Tighter cell padding for wide tables such as the match log
  dense?: boolean;
}) {
  const pad = dense ? 'py-2 px-2' : 'py-2 px-3';
  return (
    <ScrollRegion label={caption} className={maxHeight}>
      <table className="w-full text-left text-xs">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20 sticky top-0 z-10">
          <tr>
            {columns.map((c) => (
              <th key={c.header} scope="col" title={c.title} className={`${pad} whitespace-nowrap ${ALIGN[c.align ?? 'center']}`}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#D9B15F]/10">
          {rows.map((row) => (
            <tr key={rowKey(row)} className="hover:bg-[#1A1B1F]">
              {columns.map((c, i) =>
                i === 0 ? (
                  <th key={c.header} scope="row" className={`${pad} font-medium text-[#F6F6F3] ${c.className ?? 'whitespace-nowrap'} ${ALIGN[c.align ?? 'left']}`}>
                    {c.cell(row)}
                  </th>
                ) : (
                  <td key={c.header} className={`${pad} text-[#B9B9B3] ${c.className ?? 'whitespace-nowrap'} ${ALIGN[c.align ?? 'center']}`}>
                    {c.cell(row)}
                  </td>
                )
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollRegion>
  );
}

/** Focusable scroll container with a visible hint on narrow screens. */
export const ScrollRegion: React.FC<{ label: string; className?: string; children: React.ReactNode }> = ({ label, className = '', children }) => (
  <div>
    <div
      role="region"
      aria-label={label}
      tabIndex={0}
      className={`overflow-auto rounded-lg border border-[#D9B15F]/10 ${FOCUS_RING} ${className}`}
    >
      {children}
    </div>
    <p className="sm:hidden mt-1 text-[10px] text-[#8E8E88]" aria-hidden="true">Swipe the table sideways to see every column →</p>
  </div>
);

const CHART_TOOLTIP = {
  contentStyle: { backgroundColor: '#151619', borderColor: '#D9B15F', borderRadius: '0.75rem', fontSize: '12px' },
  labelStyle: { color: '#F6F6F3', fontWeight: 'bold' },
};

const SeasonChart: React.FC<{ data: { season: number; value: number }[]; label: string; color: string }> = ({ data, label, color }) => (
  <div className="h-56 w-full" role="img" aria-label={`${label} per season: ${data.map((d) => `${d.season} ${d.value}`).join(', ')}`}>
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#26272B" vertical={false} />
        <XAxis dataKey="season" stroke="#8E8E88" fontSize={11} tickLine={false} />
        <YAxis stroke="#8E8E88" fontSize={11} tickLine={false} allowDecimals={false} />
        <Tooltip {...CHART_TOOLTIP} formatter={(val: any) => [val, label]} cursor={{ fill: '#ffffff08' }} />
        <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  </div>
);

const Panel: React.FC<{ icon: React.ReactNode; title: string; tone?: 'gold' | 'green'; aside?: React.ReactNode; children: React.ReactNode }> = ({ icon, title, tone = 'gold', aside, children }) => (
  <div className={`bg-[#121316] border rounded-xl p-4 sm:p-5 space-y-4 ${tone === 'gold' ? 'border-[#D9B15F]/20' : 'border-emerald-500/20'}`}>
    <div className={`flex flex-wrap items-center justify-between gap-2 border-b pb-2 ${tone === 'gold' ? 'border-[#D9B15F]/10' : 'border-emerald-500/10'}`}>
      <h3 className={`text-xs font-bold uppercase tracking-wider flex items-center gap-2 ${tone === 'gold' ? 'text-[#D9B15F]' : 'text-emerald-400'}`}>
        {icon}
        {title}
      </h3>
      {aside}
    </div>
    {children}
  </div>
);

const SubHeading: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h4 className="text-[11px] font-bold uppercase tracking-wider text-[#B9B9B3]">{children}</h4>
);

const EmptyRecord: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="p-3 text-center text-xs text-[#8E8E88] italic bg-[#17181C] rounded-lg">{children}</div>
);

// ------------------------------------------------------------------ career summary

export const CareerSummary: React.FC<{ profile: PlayerProfileResponse; roleBadge: React.ReactNode }> = ({ profile, roleBadge }) => (
  <div className="space-y-4">
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <StatCard label={profile.season_filter != null ? 'Season' : 'First – last season'}>
        {profile.first_season === profile.last_season ? profile.first_season : `${profile.first_season}–${profile.last_season}`}
      </StatCard>
      <StatCard label="Seasons played">{profile.seasons_count}</StatCard>
      <StatCard label="Matches" accent="text-[#D9B15F]">{profile.matches.toLocaleString()}</StatCard>
      <StatCard label="Role">{roleBadge}</StatCard>
    </div>
    <div className="space-y-2">
      <SubHeading>Team history</SubHeading>
      <ul className="flex flex-wrap gap-2">
        {profile.team_history.map((t: PlayerTeamSpell) => (
          <li key={t.team} className="px-3 py-1.5 rounded-lg bg-[#101114] border border-[#D9B15F]/15 text-xs">
            <span className="font-semibold text-[#D9B15F]">{t.team}</span>
            <span className="text-[#B9B9B3]"> &middot; {t.seasons_label} &middot; {plural(t.matches, 'match', 'matches')}</span>
          </li>
        ))}
      </ul>
    </div>
  </div>
);

// ------------------------------------------------------------------ batting

const battingColumns = <T extends PlayerBattingSummary>(first: Column<T>, full: boolean): Column<T>[] => [
  first,
  { header: 'Inn', title: 'Innings', cell: (r) => r.innings },
  { header: 'Runs', cell: (r) => <span className="font-bold text-[#D9B15F]">{r.runs.toLocaleString()}</span> },
  { header: 'NO', title: 'Not outs', cell: (r) => r.not_outs },
  { header: 'Avg', title: 'Batting average', cell: (r) => <Stat value={fixed2(r.average)} state={r.average_state} /> },
  { header: 'SR', title: 'Strike rate', cell: (r) => <Stat value={fixed2(r.strike_rate)} state={r.strike_rate_state} /> },
  { header: 'HS', title: 'Highest score (* not out)', cell: (r) => r.highest_score },
  ...(full
    ? [
        { header: '4s', cell: (r: T) => r.fours },
        { header: '6s', cell: (r: T) => r.sixes },
        { header: 'Ducks', cell: (r: T) => r.ducks },
        { header: '30+', cell: (r: T) => r.scores_30_plus },
        { header: '50+', cell: (r: T) => r.scores_50_plus },
        { header: '100+', cell: (r: T) => r.scores_100_plus },
      ]
    : []),
];

const BATTING_SPLITS = [
  { id: 'team', label: 'By team' },
  { id: 'opposition', label: 'By opposition' },
  { id: 'venue', label: 'By venue' },
];

export const BattingSection: React.FC<{ profile: PlayerProfileResponse; scopeLabel: string }> = ({ profile, scopeLabel }) => {
  const [seasonView, setSeasonView] = useState('chart');
  const [split, setSplit] = useState('team');
  const b = profile.career_batting;
  const single = profile.season_filter != null;

  if (!b) {
    return (
      <Panel icon={<Flame className="w-4 h-4" />} title={`Batting · ${scopeLabel}`}>
        <EmptyRecord>
          {single ? `Did not bat in any recorded IPL match in ${profile.season_filter}.` : 'Did not bat in any recorded IPL match.'}
        </EmptyRecord>
      </Panel>
    );
  }

  const splitRows = { team: profile.batting_by_team, opposition: profile.batting_by_opposition, venue: profile.batting_by_venue };
  const splitHeader = { team: 'Team', opposition: 'Opposition', venue: 'Venue' }[split] ?? split;
  return (
    <Panel
      icon={<Flame className="w-4 h-4" />}
      title={`Batting · ${scopeLabel}`}
      aside={<span className="text-[11px] text-[#B9B9B3]">{plural(b.balls_faced, 'ball')} faced &middot; {plural(b.dismissals, 'dismissal')}</span>}
    >
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <StatCard label="Runs" accent="text-[#D9B15F]">{b.runs.toLocaleString()}</StatCard>
        <StatCard label="Innings">{b.innings}</StatCard>
        <StatCard label="Not outs">{b.not_outs}</StatCard>
        <StatCard label="Average"><Stat value={fixed2(b.average)} state={b.average_state} /></StatCard>
        <StatCard label="Strike rate"><Stat value={fixed2(b.strike_rate)} state={b.strike_rate_state} /></StatCard>
        <StatCard label="Highest score">{b.highest_score}</StatCard>
        <StatCard label="Fours">{b.fours}</StatCard>
        <StatCard label="Sixes">{b.sixes}</StatCard>
        <StatCard label="Ducks">{b.ducks}</StatCard>
        <StatCard label="30+">{b.scores_30_plus}</StatCard>
        <StatCard label="50+" accent="text-[#D9B15F]">{b.scores_50_plus}</StatCard>
        <StatCard label="100+" accent="text-[#D9B15F]">{b.scores_100_plus}</StatCard>
      </div>

      <div className="space-y-2">
        <SubHeading>Season by season</SubHeading>
        {single ? (
          <DataTable
            caption={`Batting in ${profile.season_filter}`}
            columns={battingColumns<PlayerBattingSeason>({ header: 'Season', cell: (r) => r.season }, true)}
            rows={profile.batting_by_season}
            rowKey={(r) => r.season}
          />
        ) : (
          <Tabs label="Batting season view" idPrefix="bat-season" tabs={[{ id: 'chart', label: 'Runs chart' }, { id: 'table', label: 'Table' }]} active={seasonView} onChange={setSeasonView}>
            {seasonView === 'chart' ? (
              <SeasonChart data={profile.batting_by_season.map((r) => ({ season: r.season, value: r.runs }))} label="Runs" color="#D9B15F" />
            ) : (
              <DataTable
                caption="Batting by season"
                columns={battingColumns<PlayerBattingSeason>({ header: 'Season', cell: (r) => r.season }, true)}
                rows={profile.batting_by_season}
                rowKey={(r) => r.season}
                maxHeight="max-h-80"
              />
            )}
          </Tabs>
        )}
      </div>

      <div className="space-y-2">
        <SubHeading>Splits</SubHeading>
        <Tabs label="Batting splits" idPrefix="bat-split" tabs={BATTING_SPLITS} active={split} onChange={setSplit}>
          <DataTable
            caption={`Batting ${BATTING_SPLITS.find((t) => t.id === split)?.label.toLowerCase()}, ${scopeLabel.toLowerCase()}`}
            columns={battingColumns<any>({ header: splitHeader, align: 'left', cell: (r) => r[split] }, false)}
            rows={splitRows[split as keyof typeof splitRows]}
            rowKey={(r: any) => r[split]}
            maxHeight="max-h-80"
          />
        </Tabs>
      </div>
    </Panel>
  );
};

// ------------------------------------------------------------------ bowling

const bowlingColumns = <T extends PlayerBowlingSummary>(first: Column<T>, full: boolean): Column<T>[] => [
  first,
  { header: 'Inn', title: 'Innings', cell: (r) => r.innings },
  { header: 'Overs', title: 'Overs (cricket notation)', cell: (r) => r.overs_bowled },
  { header: 'Wkts', title: 'Wickets', cell: (r) => <span className="font-bold text-emerald-400">{r.wickets}</span> },
  { header: 'Runs', title: 'Runs conceded', cell: (r) => r.runs_conceded.toLocaleString() },
  { header: 'Avg', title: 'Bowling average', cell: (r) => <Stat value={fixed2(r.bowling_average)} state={r.bowling_average_state} /> },
  ...(full ? [{ header: 'SR', title: 'Bowling strike rate', cell: (r: T) => <Stat value={fixed2(r.bowling_strike_rate)} state={r.bowling_strike_rate_state} /> }] : []),
  { header: 'Econ', title: 'Economy rate', cell: (r) => <Stat value={fixed2(r.economy_rate)} state={r.economy_rate_state} /> },
  { header: 'Best', title: 'Best figures (wickets/runs)', cell: (r) => r.best_bowling },
  ...(full ? [{ header: '3w/4w/5w', title: 'Innings with exactly 3, exactly 4, and 5 or more wickets', cell: (r: T) => `${r.three_wicket_hauls}/${r.four_wicket_hauls}/${r.five_wicket_hauls}` }] : []),
];

const BOWLING_SPLITS = [
  { id: 'opposition', label: 'By opposition' },
  { id: 'venue', label: 'By venue' },
];

export const BowlingSection: React.FC<{ profile: PlayerProfileResponse; scopeLabel: string }> = ({ profile, scopeLabel }) => {
  const [seasonView, setSeasonView] = useState('chart');
  const [split, setSplit] = useState('opposition');
  const w = profile.career_bowling;
  const single = profile.season_filter != null;

  if (!w) {
    return (
      <Panel icon={<Shield className="w-4 h-4" />} title={`Bowling · ${scopeLabel}`} tone="green">
        <EmptyRecord>
          {single ? `Did not bowl in any recorded IPL match in ${profile.season_filter}.` : 'Did not bowl in any recorded IPL match.'}
        </EmptyRecord>
      </Panel>
    );
  }

  const splitRows = { opposition: profile.bowling_by_opposition, venue: profile.bowling_by_venue };
  const splitHeader = split === 'venue' ? 'Venue' : 'Opposition';
  return (
    <Panel
      icon={<Shield className="w-4 h-4" />}
      title={`Bowling · ${scopeLabel}`}
      tone="green"
      aside={<span className="text-[11px] text-[#B9B9B3]">{plural(w.legal_deliveries, 'legal ball')}</span>}
    >
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <StatCard label="Wickets" accent="text-emerald-400">{w.wickets}</StatCard>
        <StatCard label="Innings">{w.innings}</StatCard>
        <StatCard label="Overs">{w.overs_bowled}</StatCard>
        <StatCard label="Runs conceded">{w.runs_conceded.toLocaleString()}</StatCard>
        <StatCard label="Average"><Stat value={fixed2(w.bowling_average)} state={w.bowling_average_state} /></StatCard>
        <StatCard label="Strike rate"><Stat value={fixed2(w.bowling_strike_rate)} state={w.bowling_strike_rate_state} /></StatCard>
        <StatCard label="Economy"><Stat value={fixed2(w.economy_rate)} state={w.economy_rate_state} /></StatCard>
        <StatCard label="Best" accent="text-emerald-300">{w.best_bowling}</StatCard>
        <StatCard label="3w / 4w / 5w" accent="text-emerald-300">{w.three_wicket_hauls} / {w.four_wicket_hauls} / {w.five_wicket_hauls}</StatCard>
      </div>

      <div className="space-y-2">
        <SubHeading>Season by season</SubHeading>
        {single ? (
          <DataTable
            caption={`Bowling in ${profile.season_filter}`}
            columns={bowlingColumns<PlayerBowlingSeason>({ header: 'Season', cell: (r) => r.season }, true)}
            rows={profile.bowling_by_season}
            rowKey={(r) => r.season}
          />
        ) : (
          <Tabs label="Bowling season view" idPrefix="bowl-season" tabs={[{ id: 'chart', label: 'Wickets chart' }, { id: 'table', label: 'Table' }]} active={seasonView} onChange={setSeasonView}>
            {seasonView === 'chart' ? (
              <SeasonChart data={profile.bowling_by_season.map((r) => ({ season: r.season, value: r.wickets }))} label="Wickets" color="#34D399" />
            ) : (
              <DataTable
                caption="Bowling by season"
                columns={bowlingColumns<PlayerBowlingSeason>({ header: 'Season', cell: (r) => r.season }, true)}
                rows={profile.bowling_by_season}
                rowKey={(r) => r.season}
                maxHeight="max-h-80"
              />
            )}
          </Tabs>
        )}
      </div>

      <div className="space-y-2">
        <SubHeading>Splits</SubHeading>
        <Tabs label="Bowling splits" idPrefix="bowl-split" tabs={BOWLING_SPLITS} active={split} onChange={setSplit}>
          <DataTable
            caption={`Bowling ${BOWLING_SPLITS.find((t) => t.id === split)?.label.toLowerCase()}, ${scopeLabel.toLowerCase()}`}
            columns={bowlingColumns<any>({ header: splitHeader, align: 'left', cell: (r) => r[split] }, false)}
            rows={splitRows[split as keyof typeof splitRows]}
            rowKey={(r: any) => r[split]}
            maxHeight="max-h-80"
          />
        </Tabs>
      </div>
    </Panel>
  );
};

// ------------------------------------------------------------------ definitions

const DEFINITION_LABELS: Record<string, string> = {
  fours_sixes: 'Fours and sixes',
  milestones: '30+ / 50+ / 100+',
  hauls: 'Hauls (3w / 4w / 5w)',
  splits: 'Team, opposition and venue',
  season_filter: 'Season selector',
};

const humanize = (key: string) => DEFINITION_LABELS[key] ?? key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');

export const DefinitionsDisclosure: React.FC<{ profile: PlayerProfileResponse }> = ({ profile }) => (
  <details className="group bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5">
    <summary className={`cursor-pointer list-none flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#D9B15F] rounded ${FOCUS_RING}`}>
      <BookOpen className="w-4 h-4" />
      Definitions
      <span className="ml-auto text-[10px] font-semibold normal-case tracking-normal text-[#8E8E88] group-open:hidden">Show how every number is counted</span>
    </summary>
    <dl className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-xs">
      {Object.entries(profile.metric_definitions).map(([key, text]) => (
        <div key={key}>
          <dt className="font-semibold text-[#F6F6F3]">{humanize(key)}</dt>
          <dd className="text-[#B9B9B3]">{text}</dd>
        </div>
      ))}
    </dl>
    <div className="mt-4 pt-3 border-t border-[#D9B15F]/10 space-y-1 text-xs">
      <p className="font-semibold text-[#F6F6F3] flex items-center gap-1.5"><Info className="w-3.5 h-3.5 text-[#D9B15F]" /> When a value shows "—"</p>
      <ul className="list-disc list-inside text-[#B9B9B3] space-y-0.5">
        {Object.keys(profile.state_definitions).map((code) => (
          <li key={code}><Stat value={null} state={code} /> {profile.state_definitions[code]}</li>
        ))}
      </ul>
      <p className="text-[#8E8E88] flex items-center gap-1.5 pt-1"><MapPin className="w-3.5 h-3.5" /> Source: Cricsheet ball-by-ball records; super overs are excluded from every statistic.</p>
    </div>
  </details>
);
