"""Stage 1 screening and preliminary Stage 2 EDA tables.

All summaries are derived from parsed real Cricsheet records; no ML is fitted here.
2026 is described for EDA only, not used to train/tune the future holdout model.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd

TABLES = ('matches', 'innings', 'overs', 'deliveries', 'batter_innings', 'next_over_samples', 'screening_issues')


def audit(data_dir: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = {k: pd.read_csv(data_dir / f'{k}.csv') for k in TABLES}
    matches = frames['matches']
    innings = frames['innings']
    balls = frames['deliveries']
    batters = frames['batter_innings']
    windows = frames['next_over_samples']
    overs = frames['overs']
    issues = frames['screening_issues']

    # Missingness counts *blank/NA* fields; some empty cities are structural.
    missingness = []
    for name, df in frames.items():
        for column in df.columns:
            column_values = df[column]
            missing = column_values.isna() | (column_values.astype('string').str.strip() == '').fillna(False)
            if missing.any():
                missingness.append({'table': name, 'column': column, 'missing_count': int(missing.sum()),
                                    'total_rows': len(df), 'missing_pct': round(100 * missing.mean(), 3)})
    pd.DataFrame(missingness, columns=['table', 'column', 'missing_count', 'total_rows', 'missing_pct']).to_csv(
        out_dir / 'missingness.csv', index=False)

    # Check additive invariants against complete inning totals, without relying on file order.
    ix = ['match_id', 'innings']
    by_ball = balls.groupby(ix, as_index=False).agg(
        runs_from_balls=('runs_total', 'sum'), wickets_from_balls=('team_wickets_on_ball', 'sum'),
        legal_balls_from_balls=('legal_delivery', 'sum'))
    reconciled = innings.merge(by_ball, on=ix, how='left', validate='one_to_one')
    mismatched = (reconciled['runs'] != reconciled['runs_from_balls']) | (reconciled['wickets'] != reconciled['wickets_from_balls']) | (reconciled['legal_balls'] != reconciled['legal_balls_from_balls'])
    bad = int(mismatched.sum())
    if bad:
        reconciled.loc[mismatched].to_csv(out_dir / 'reconciliation_failures.csv', index=False)

    # Match/season descriptions (not time-safe features for ML).
    seasons = matches.groupby('season', as_index=False).agg(matches=('match_id', 'size'))
    innings_a = innings.groupby('season', as_index=False).agg(innings=('match_id', 'size'),
                                                              runs=('runs', 'sum'), wickets=('wickets', 'sum'))
    first = innings[innings.innings == 1].groupby('season', as_index=False).agg(
        avg_first_innings_runs=('runs', 'mean'), median_first_innings_runs=('runs', 'median'))
    windows_a = windows.groupby('season', as_index=False).agg(
        eligible_wicket_windows=('wicket_next_over', 'size'), wicket_next_over_rate=('wicket_next_over', 'mean'))
    seasons = seasons.merge(innings_a, on='season').merge(first, on='season').merge(windows_a, on='season')
    seasons = seasons.round(3)
    seasons.to_csv(out_dir / 'season_summary.csv', index=False)

    wickets_by_over = balls.groupby('over_index', as_index=False).agg(
        wickets=('team_wickets_on_ball', 'sum'), legal_balls=('legal_delivery', 'sum'))
    wickets_by_over['wickets_per_legal_ball'] = (wickets_by_over.wickets / wickets_by_over.legal_balls).round(4)
    wickets_by_over.to_csv(out_dir / 'wickets_by_over.csv', index=False)

    over_event = windows.groupby('completed_overs', as_index=False).agg(
        eligible_windows=('wicket_next_over', 'size'), next_over_wicket_rate=('wicket_next_over', 'mean'))
    over_event.round(4).to_csv(out_dir / 'wicket_event_by_checkpoint.csv', index=False)

    result = {
        'coverage': {'first_match_date': str(matches.date.min()), 'last_match_date': str(matches.date.max()),
                     'seasons': sorted(int(s) for s in matches.season.unique()),
                     'matches_by_season': {str(int(k)): int(v) for k, v in matches.season.value_counts().sort_index().items()}},
        'counts': {k: int(len(df)) for k, df in frames.items()},
        'totals': {'team_runs': int(balls.runs_total.sum()), 'team_wickets': int(balls.team_wickets_on_ball.sum()),
                   'legal_deliveries': int(balls.legal_delivery.sum()), 'wide_events': int((balls.wides > 0).sum()),
                   'noball_events': int((balls.noballs > 0).sum())},
        'screening_issue_counts': {str(k): int(v) for k,v in issues.issue.value_counts().items()},
        'gender_values': {str(k): int(v) for k,v in matches.gender.value_counts(dropna=False).items()},
        'event_values': {str(k): int(v) for k,v in matches.event.value_counts(dropna=False).items()},
        'teams_in_archive': sorted(set(matches.team1) | set(matches.team2)),
        'distinct_teams': int(len(set(matches.team1) | set(matches.team2))),
        'reconciliation_failures': bad,
        'first_innings_mean': round(float(innings[innings.innings == 1].runs.mean()), 2),
        'first_innings_median': round(float(innings[innings.innings == 1].runs.median()), 2),
        'batter_milestone_30_rate': round(float(batters.reached_30.mean()), 4),
        'batter_milestone_50_rate': round(float(batters.reached_50.mean()), 4),
        'next_over_event_rate': round(float(windows.wicket_next_over.mean()), 4),
        'notices': [
            'Recorded batter milestone rates are conditional on batting appearances; pre-match features must be past-only.',
            'Retired hurt is excluded from team wickets; super overs are not part of ordinary innings tables.',
            'Next-over examples exclude non-wicket incomplete horizons; truncated chases create censoring.',
            'Matches involving discontinued franchises are kept distinct; dashboard selectors will focus on current franchises.',
            '2026 data included in EDA descriptions but reserved from model fitting/tuning until final holdout evaluation.',
        ],
    }
    (out_dir / 'audit_summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def make_figures(data_dir: Path, out_dir: Path) -> None:
    """Four basic descriptive charts; intentionally not predictive model evaluations."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out_dir.mkdir(parents=True, exist_ok=True)
    matches = pd.read_csv(data_dir / 'matches.csv')
    innings = pd.read_csv(data_dir / 'innings.csv')
    balls = pd.read_csv(data_dir / 'deliveries.csv')
    wicket = pd.read_csv(data_dir / 'next_over_samples.csv')

    def finish(path):
        plt.tight_layout()
        plt.savefig(out_dir / path, dpi=160)
        plt.close()

    ax = matches.groupby('season').size().plot(kind='bar', figsize=(10, 4))
    ax.set(title='IPL matches recorded by season', xlabel='Season', ylabel='Matches')
    finish('matches_by_season.png')

    first = innings[innings.innings == 1]
    ax = first.groupby('season').runs.mean().plot(marker='o', figsize=(10, 4))
    ax.set(title='Average first-innings team total by season', xlabel='Season', ylabel='Average runs')
    ax.set_xticks(sorted(matches.season.unique())[::2])
    finish('average_first_innings_runs.png')

    ax = first.runs.hist(bins=28, figsize=(9, 4))
    ax.set(title='Distribution of recorded first-innings team totals', xlabel='Runs', ylabel='Innings')
    finish('first_innings_distribution.png')

    bycheckpoint = wicket.groupby('completed_overs').wicket_next_over.mean()
    ax = bycheckpoint.plot(kind='bar', figsize=(9, 4))
    ax.set(title='Share of eligible next overs with at least one wicket',
           xlabel='Completed overs at prediction checkpoint', ylabel='Observed event rate')
    finish('wicket_next_over_by_checkpoint.png')


def main():
    p = argparse.ArgumentParser(description='Stage 1 data quality and preliminary EDA plots')
    p.add_argument('--data', type=Path, default=Path('data/processed'))
    p.add_argument('--output', type=Path, default=Path('reports/stage_01'))
    p.add_argument('--figures', type=Path, default=Path('reports/figures'))
    args = p.parse_args()
    result = audit(args.data, args.output)
    make_figures(args.data, args.figures)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
