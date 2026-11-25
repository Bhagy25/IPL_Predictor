import React from 'react';
import { Lightbulb } from 'lucide-react';
import { EDAAreas, EDAFiltersEcho, TeamResultSummary } from '../../types';
import { fmtCount } from '../../utils/format';

const pct = (v: number | null | undefined) => (v == null ? null : `${v.toFixed(1)}%`);
const rate = (v: number | null | undefined) => (v == null ? null : v.toFixed(2));

/**
 * Key findings for the current selection, each written from the numbers the charts below show (no value is
 * typed in): scoring change across the seasons, phases, innings order, toss, dismissals and boundaries.
 * A finding is left out when its numbers are unavailable for the selection.
 */
export const EDATakeaways: React.FC<{ areas: EDAAreas; filters: EDAFiltersEcho }> = ({ areas, filters }) => {
  const items: { title: string; text: string }[] = [];
  const seasons = areas.scoring_trends.data?.by_season.filter((s) => s.run_rate != null) ?? [];
  if (seasons.length >= 2) {
    const first = seasons[0];
    const last = seasons[seasons.length - 1];
    const peak = seasons.reduce((a, b) => (b.runs_per_innings > a.runs_per_innings ? b : a));
    items.push({
      title: 'Scoring across the seasons',
      text: `The run rate went from ${rate(first.run_rate)} runs per over in ${first.season} to ${rate(last.run_rate)} in ${last.season}; the highest mean innings total was ${peak.runs_per_innings.toFixed(1)} runs in ${peak.season}.`,
    });
  }
  const phases = areas.phases.data?.overall ?? [];
  if (phases.length === 3 && phases.every((p) => p.batting_run_rate != null)) {
    const [pp, mid, death] = ['powerplay', 'middle', 'death'].map((k) => phases.find((p) => p.phase === k)!);
    const fastest = [pp, mid, death].reduce((a, b) => (b.batting_run_rate! > a.batting_run_rate! ? b : a));
    items.push({
      title: `Fastest scoring: the ${fastest.phase === 'middle' ? 'middle overs' : fastest.phase === 'death' ? 'death overs' : 'powerplay'}`,
      text: `Runs per over: ${rate(pp.batting_run_rate)} in the powerplay (overs ${pp.overs}), ${rate(mid.batting_run_rate)} in the middle overs (${mid.overs}) and ${rate(death.batting_run_rate)} at the death (${death.overs}).`,
    });
  }
  const teamView = Boolean(areas.innings_order.data?.team_view && filters.team);
  const subject = teamView && filters.team ? filters.team.name : 'Teams';
  const order = areas.innings_order.data?.overall;
  const winText = (r: TeamResultSummary) => (r.win_pct == null ? null : `${pct(r.win_pct)} of ${fmtCount(r.win_pct_denominator)}`);
  if (order && winText(order.batting_first) && winText(order.chasing)) {
    const first = order.batting_first.win_pct!;
    const chase = order.chasing.win_pct!;
    items.push({
      title: chase > first ? 'Chasing has won more often' : chase < first ? 'Batting first has won more often' : 'Batting first and chasing are level',
      text: `${subject} batting first won ${winText(order.batting_first)} decided matches; chasing, ${teamView ? 'they' : 'teams'} won ${winText(order.chasing)}.`,
    });
  }
  const toss = areas.toss.data?.overall;
  if (toss && toss.tosses_won > 0 && toss.after_winning_toss.win_pct != null) {
    items.push({
      title: 'The toss and the result',
      text: `${areas.toss.data?.team_view && filters.team ? `After winning the toss, ${filters.team.name}` : 'Toss winners'} chose to field ${pct((100 * toss.elected_to_field) / toss.tosses_won)} of the time and won ${pct(toss.after_winning_toss.win_pct)} of their decided matches. This is an association, not proof that the toss causes wins.`,
    });
  }
  const dismissals = areas.dismissals.data?.kinds ?? [];
  if (dismissals.length) {
    const top = dismissals.reduce((a, b) => (b.count > a.count ? b : a));
    if (top.pct != null) items.push({ title: 'How batters get out', text: `"${top.kind}" is the most common dismissal: ${fmtCount(top.count)} times, ${pct(top.pct)} of all dismissals.` });
  }
  const b = areas.boundaries.data?.totals;
  if (b && b.boundary_run_pct != null && b.dot_ball_pct != null) {
    items.push({
      title: 'Boundaries and dot balls',
      text: `${pct(b.boundary_run_pct)} of runs came from fours and sixes (${fmtCount(b.fours)} fours, ${fmtCount(b.sixes)} sixes), while ${pct(b.dot_ball_pct)} of legal balls were dot balls.`,
    });
  }
  if (!items.length) return null;
  const range = filters.season_from === filters.season_to ? `${filters.season_from}` : `${filters.season_from}–${filters.season_to}`;
  return (
    <section aria-labelledby="eda-takeaways" className="bg-gradient-to-br from-[#D9B15F]/[0.10] to-[#151619] border border-[#D9B15F]/35 rounded-2xl p-4 sm:p-5 space-y-3">
      <h2 id="eda-takeaways" className="text-sm sm:text-base font-bold text-[#F6F6F3] flex items-center gap-2">
        <Lightbulb className="w-4 h-4 text-[#D9B15F]" aria-hidden="true" /> Key takeaways for {range}
        {filters.team && <span className="text-[#B9B9B3] font-normal">· {filters.team.name}</span>}
        {filters.venue && <span className="text-[#B9B9B3] font-normal">· {filters.venue}</span>}
      </h2>
      <ul className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {items.map((i) => (
          <li key={i.title} className="bg-[#101114] border border-white/5 rounded-xl p-3">
            <p className="text-sm font-semibold text-[#F6F6F3]">{i.title}</p>
            <p className="text-xs text-[#B9B9B3] mt-1">{i.text}</p>
          </li>
        ))}
      </ul>
      <p className="text-[11px] text-[#8E8E88]">Computed from the charts below for the current selection; they update with the filters. Observational patterns, not causes.</p>
    </section>
  );
};
