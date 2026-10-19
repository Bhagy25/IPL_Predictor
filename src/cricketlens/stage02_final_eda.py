"""CricketLens Stage 2 / Session 03 — exceptional outcomes and EDA synthesis.

Only development seasons <=2025 are included in the statistical outputs.
The raw 2026 IPL season remains untouched for the final ML evaluation.

The session separates ordinary regulation result, eventual match winner,
D/L annotations, and Super Over innings. Figures are descriptive, not causal.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cricketlens.stage02_eda import CURRENT_TEAMS, development_only


def check_match_outcomes(matches: pd.DataFrame) -> dict:
    """Validate final-winner consistency without guessing missing outcomes."""
    required = {'season', 'team1', 'team2', 'winner', 'final_winner',
                'regulation_result', 'outcome_type', 'super_over_winner',
                'super_over_innings', 'decided_by', 'outcome_method'}
    missing = required - set(matches.columns)
    if missing:
        raise ValueError(f'Processed match table is outdated: missing {sorted(missing)}. Re-run IPL parser.')
    is_tie = matches.regulation_result.eq('tie')
    is_super = matches.decided_by.eq('super_over')
    is_no_result = matches.regulation_result.eq('no result')
    if not (matches.outcome_type == matches.regulation_result).all():
        raise ValueError('Mismatch between legacy outcome_type and regulation_result')
    if (is_super & ~is_tie).any() or (is_tie & ~is_super).any():
        raise ValueError('Unexpected tied match without Super Over winner, or conflicting category')
    if (is_super & (matches.super_over_innings < 2)).any():
        raise ValueError('Super Over result without two recorded Super Over innings')
    if (matches.loc[is_super, 'final_winner'] != matches.loc[is_super, 'super_over_winner']).any():
        raise ValueError('Final winner not equal to Super Over eliminator')
    if matches.loc[is_no_result, 'final_winner'].notna().any():
        raise ValueError('No-result match must not have final winner')
    if matches.loc[~is_no_result, 'final_winner'].isna().any():
        raise ValueError('Decided match unexpectedly has no final winner')
    if not ((matches.final_winner.isna()) | (matches.final_winner == matches.team1) |
            (matches.final_winner == matches.team2)).all():
        raise ValueError('Winning side is not among the two participants')
    return {
        'matches': int(len(matches)),
        'regulation_wins': int(matches.regulation_result.eq('win').sum()),
        'regulation_ties': int(is_tie.sum()),
        'super_over_matches': int(is_super.sum()),
        'super_over_innings': int(matches.super_over_innings.sum()),
        'no_results': int(is_no_result.sum()),
        'dl_method_matches': int(matches.outcome_method.eq('D/L').sum()),
        'decided_matches': int(matches.final_winner.notna().sum()),
    }


def team_win_comparison(matches: pd.DataFrame) -> pd.DataFrame:
    """Show old vs corrected winner accounting, among current teams, 2022-2025."""
    m = development_only(matches).loc[lambda t: t.season >= 2022]
    long = pd.concat([m.assign(team=m.team1),m.assign(team=m.team2)], ignore_index=True)
    long = long.loc[long.team.isin(CURRENT_TEAMS)].copy()
    long['winner_regulation_only'] = long.outcome_type.eq('win') & long.winner.eq(long.team)
    long['eligible_regulation_only'] = long.outcome_type.eq('win') & long.winner.notna()
    long['winner_corrected'] = long.final_winner.eq(long.team)
    long['eligible_corrected'] = long.final_winner.notna()
    g = (long.groupby('team', as_index=False).agg(
        played=('match_id','nunique'),
        wins_regulation_only=('winner_regulation_only','sum'),
        matches_with_regulation_winner=('eligible_regulation_only','sum'),
        wins_including_super_overs=('winner_corrected','sum'),
        decided_matches_including_super_overs=('eligible_corrected','sum')))
    g['old_win_pct'] = (100 * g.wins_regulation_only /
                        g.matches_with_regulation_winner.replace(0,np.nan))
    g['corrected_win_pct'] = (100 * g.wins_including_super_overs /
                              g.decided_matches_including_super_overs.replace(0,np.nan))
    g['win_count_change'] = g.wins_including_super_overs - g.wins_regulation_only
    g['pct_point_change'] = g.corrected_win_pct - g.old_win_pct
    return g.sort_values('corrected_win_pct',ascending=False).reset_index(drop=True)


def run(data: Path, output: Path, figures: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    matches = pd.read_csv(data/'matches.csv')
    innings = pd.read_csv(data/'innings.csv')
    if matches.match_id.duplicated().any():
        raise ValueError('Duplicate match IDs')
    if matches.season.min() != 2008 or matches.season.max() != 2026:
        raise ValueError('Expected the uploaded Cricsheet archive covering 2008-2026')
    audit_full = check_match_outcomes(matches)
    dev = development_only(matches)
    audit_dev = check_match_outcomes(dev)
    i = development_only(innings)

    # Keep raw outcomes and eventual winner separate, and D/L as a flag,
    # not a new win/loss category.
    outcomes = (dev.groupby(['regulation_result','decided_by'],dropna=False)
                .agg(matches=('match_id','size'),d_l_matches=('outcome_method',lambda x:x.eq('D/L').sum()))
                .reset_index())
    outcomes.to_csv(output/'match_outcomes_2008_2025.csv', index=False)
    exceptions = dev.loc[dev.regulation_result.ne('win') | dev.outcome_method.eq('D/L'),
                         ['match_id','date','season','team1','team2','regulation_result',
                          'final_winner','super_over_winner','super_over_innings',
                          'decided_by','outcome_method','venue_canonical']].copy()
    exceptions.to_csv(output/'exceptional_matches_2008_2025.csv',index=False)

    # For scoring summaries use a recognized first innings. D/L result is a
    # match-level annotation and does not establish which innings was affected.
    first = i.loc[(i.innings == 1) & (i.season >= 2018)].copy()
    first = first.merge(dev[['match_id','outcome_method','regulation_result','decided_by']],
                        on='match_id',how='left',validate='many_to_one')
    first['d_l_annotated'] = first.outcome_method.eq('D/L')
    first['full_120_legal'] = first.legal_balls.eq(120)
    groups = (first.groupby(['d_l_annotated','full_120_legal'],dropna=False)
              .agg(innings=('match_id','size'),mean_recorded_runs=('runs','mean'),
                   median_recorded_runs=('runs','median'),mean_legal_balls=('legal_balls','mean'))
              .reset_index())
    groups.to_csv(output/'first_innings_by_d_l_and_length_2018_2025.csv',index=False)

    team = team_win_comparison(matches)
    team.to_csv(output/'team_wins_before_after_super_over_fix_2022_2025.csv',index=False)
    corrected_toss = dev.loc[(dev.season >= 2018) & dev.final_winner.notna()].copy()
    corrected_toss['toss_winner_won'] = corrected_toss.toss_winner.eq(corrected_toss.final_winner)
    toss = (corrected_toss.groupby('toss_decision').agg(matches=('match_id','size'),
             toss_winner_wins=('toss_winner_won','sum')).reset_index())
    toss['pct'] = 100 * toss.toss_winner_wins/toss.matches
    toss.to_csv(output/'toss_results_with_super_overs_2018_2025.csv',index=False)

    # Comparison plots. All inputs are measured through 2025; no holdout plots.
    fig,ax=plt.subplots(figsize=(8.4,4.6))
    names=['Ordinary win','Regulation tie\n(Super Over)','No result']
    n=[audit_dev['regulation_wins'],audit_dev['regulation_ties'],audit_dev['no_results']]
    bars=ax.bar(names,n)
    for bar,v in zip(bars,n): ax.text(bar.get_x()+bar.get_width()/2,v+4,str(v),ha='center',size=10)
    ax.set(ylabel='Matches', title='Ordinary results vs Super Over ties vs no results (2008–2025)')
    ax.set_ylim(0,max(n)*1.17)
    fig.tight_layout();fig.savefig(figures/'18_match_outcomes.png',dpi=150);plt.close(fig)

    fig,ax=plt.subplots(figsize=(8.8,5.4))
    g=team.sort_values('pct_point_change').copy()
    y=np.arange(len(g))
    ax.scatter(g.old_win_pct,y,label='Original (ties excluded)',s=40)
    ax.scatter(g.corrected_win_pct,y,label='Corrected (Super Over included)',s=40,marker='s')
    for k,row in enumerate(g.itertuples()):
        ax.plot([row.old_win_pct,row.corrected_win_pct],[k,k],linewidth=1,alpha=.6)
    ax.set_yticks(y,g.team.to_list())
    ax.set(xlabel='Win rate among decided matches (%)',
           title='Correction to team win rate, 2022–2025')
    ax.legend(loc='lower right',fontsize=8)
    fig.tight_layout();fig.savefig(figures/'19_win_rate_super_over_fix.png',dpi=150);plt.close(fig)

    fig,ax=plt.subplots(figsize=(8.5,4.7))
    plot=groups.loc[groups.innings > 0].copy()
    plot['group']=[('D/L' if x else 'Other')+' · '+('120 balls' if y else '<120 balls')
                   for x,y in zip(plot.d_l_annotated,plot.full_120_legal)]
    bars=ax.bar(plot.group,plot.mean_recorded_runs)
    for bar,x in zip(bars,plot.itertuples()):
        ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,f'n={x.innings}',ha='center',size=9)
    ax.set(xlabel='Match-method annotation / innings length', ylabel='Mean first-innings runs',
           title='Short innings vs D/L result annotation (2018–2025)')
    ax.tick_params(axis='x', labelrotation=14)
    fig.tight_layout();fig.savefig(figures/'20_dl_innings_sensitivity.png',dpi=150);plt.close(fig)

    summary = {
        'status':'Stage 2 Session 03 complete: numerical review ready; professor review remains external',
        'analysis_season_cutoff':2025,
        'all_archive_quality_audit_only':audit_full,
        'eda_development_period':audit_dev,
        'dl_flag_pre2026_match_count':audit_dev['dl_method_matches'],
        'dl_2018_2025_first_innings_count':int(first.d_l_annotated.sum()),
        'recent_first_innings_n':int(len(first)),
        'team_win_rate_corrections':team.loc[team.win_count_change>0,
                        ['team','wins_regulation_only','wins_including_super_overs',
                         'old_win_pct','corrected_win_pct']].to_dict('records'),
        'toss_results':toss.to_dict('records'),
        'method_limitations':[
            'D/L identifies a match outcome method, not precisely the shortened innings or interruption timing.',
            'Super Over innings excluded from ordinary batting, bowling, scoring-phase and wicket samples.',
            'Regulation ties and final Super Over winners are separately recorded.',
            'No-result matches are retained; no winner is imputed.',
            'Only season<=2025 used for descriptive development; 2026 left for unseen ML test.',
            'Preliminary next-over candidate cohort still needs interrupted-innings/censoring rules in Stage 3.',
        ],
    }
    (output/'stage02_session03_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=Path('data/processed'))
    p.add_argument('--output',type=Path,default=Path('reports/stage_02/session_03'))
    p.add_argument('--figures',type=Path,default=Path('reports/figures/stage_02'))
    args=p.parse_args()
    out=run(args.data,args.output,args.figures)
    print(json.dumps({k:out[k] for k in ('status','analysis_season_cutoff','eda_development_period','dl_2018_2025_first_innings_count')},indent=2))

if __name__=='__main__': main()
