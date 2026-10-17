"""Stage 2 / Session 02 - careful, descriptive men's IPL EDA.

Data cutoff is ALWAYS 2025; never use 2026 (held out for Stage 3).
Calculations use audited Stage 1 CSV tables; no new ML model is trained here.

Run: python -m cricketlens.stage02_deep_eda
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
from scipy import stats

from cricketlens.stage02_eda import development_only, standardized_phase, describe

CUTOFF = 2025
SEED = 42


def bootstrap_mean_ci(values: np.ndarray | pd.Series, n_boot: int = 3000, seed: int = SEED) -> tuple[float, float]:
    """Percentile bootstrap of the sample mean; not an adjustment for confounders."""
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if not len(a):
        raise ValueError('Need at least one finite value')
    if len(a) == 1:
        return float(a[0]), float(a[0])
    gen = np.random.default_rng(seed)
    # batches avoid large temporary arrays for production-sized datasets
    means = np.empty(n_boot, dtype=float)
    for k in range(0, n_boot, 250):
        k_end = min(k + 250, n_boot)
        draw = gen.integers(0, len(a), size=(k_end-k, len(a)))
        means[k:k_end] = a[draw].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(lo), float(hi)


def clustered_mean_ci(values: np.ndarray | pd.Series, clusters: np.ndarray | pd.Series,
                      n_boot: int = 3000, seed: int = SEED) -> tuple[float, float]:
    """Match-clustered percentile bootstrap; both innings from a match resample together."""
    df = pd.DataFrame({'value': np.asarray(values, dtype=float),
                       'cluster': np.asarray(clusters)}).dropna()
    if df.empty:
        raise ValueError('Need observations')
    agg = df.groupby('cluster')['value'].agg(['sum','count'])
    sums = agg['sum'].to_numpy(dtype=float)
    counts = agg['count'].to_numpy(dtype=float)
    gen = np.random.default_rng(seed)
    draws = gen.integers(0, len(sums), size=(n_boot, len(sums)))
    bootstrap_means = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    return tuple(float(x) for x in np.quantile(bootstrap_means, [0.025, 0.975]))


def season_centered_scores(first: pd.DataFrame) -> pd.DataFrame:
    """Within-season centering controls the year's overall average, NOT causal venue effects."""
    needed = {'season', 'runs', 'venue_canonical', 'legal_balls'}
    if not needed.issubset(first.columns):
        raise KeyError(f'Missing columns: {needed - set(first.columns)}')
    f = first.copy()
    season_mean = f.groupby('season')['runs'].transform('mean')
    f['runs_above_season_mean'] = f['runs'] - season_mean
    return f


def make_venue_comparison(first: pd.DataFrame, min_n: int = 20) -> pd.DataFrame:
    """Venue comparison on 20-over first innings; requires multiple sample records."""
    f = first.loc[(first.legal_balls == 120) & first.venue_canonical.notna()].copy()
    f = season_centered_scores(f)
    out = []
    for venue, g in f.groupby('venue_canonical'):
        if len(g) < min_n:
            continue
        lower, upper = bootstrap_mean_ci(g.runs_above_season_mean.to_numpy(), seed=SEED)
        out.append({'venue_canonical': venue, 'n_full_first_innings': len(g),
                    'seasons_represented': int(g.season.nunique()),
                    'mean_runs': float(g.runs.mean()),
                    'season_adjusted_difference_runs': float(g.runs_above_season_mean.mean()),
                    'ci95_low': lower, 'ci95_high': upper})
    return pd.DataFrame(out).sort_values('season_adjusted_difference_runs', ascending=False).reset_index(drop=True)


def paired_innings_phase(deliveries: pd.DataFrame, min_powerplay_balls: int = 30,
                         min_death_balls: int = 12) -> pd.DataFrame:
    """Compare phases within the SAME innings that reaches the late phase.

    Does not claim that death overs are intrinsically causally faster; the selected
    sample necessarily contains innings that lasted long enough to have death balls.
    """
    d = deliveries.loc[(deliveries.season >= 2018) & (deliveries.season <= CUTOFF)].copy()
    d['phase'] = standardized_phase(d.over_index)
    g = (d.groupby(['match_id', 'innings', 'season', 'phase'], observed=True)
          .agg(runs=('runs_total', 'sum'), legal_balls=('legal_delivery', 'sum'))
          .reset_index())
    # Pair PP and death rates after verifying reasonable exposure in both phases
    p = g[g.phase == 'Powerplay (1-6)'].set_index(['match_id', 'innings', 'season'])
    z = g[g.phase == 'Death (17-20)'].set_index(['match_id', 'innings', 'season'])
    pair = p[['runs', 'legal_balls']].join(z[['runs', 'legal_balls']], how='inner', lsuffix='_pp', rsuffix='_death')
    pair = pair.loc[(pair.legal_balls_pp >= min_powerplay_balls) &
                    (pair.legal_balls_death >= min_death_balls)].copy()
    pair['powerplay_runs_per_six_legal'] = 6 * pair.runs_pp / pair.legal_balls_pp
    pair['death_runs_per_six_legal'] = 6 * pair.runs_death / pair.legal_balls_death
    pair['death_minus_powerplay'] = pair.death_runs_per_six_legal - pair.powerplay_runs_per_six_legal
    return pair.reset_index()


def toss_decision_crosstab(matches: pd.DataFrame) -> pd.DataFrame:
    """Descriptive association, not an effect of choosing to bat/field."""
    if 'final_winner' not in matches:
        raise ValueError('Regenerate Stage 1 match table with final_winner field')
    m = matches.loc[(matches.season >= 2018) & (matches.season <= CUTOFF) &
                    matches.final_winner.notna()].copy()
    m['toss_winner_won_match'] = m.toss_winner == m.final_winner
    c = (m.groupby(['toss_decision', 'toss_winner_won_match'])
         .size().unstack(fill_value=0))
    c = c.reindex(index=['bat', 'field'], columns=[False, True], fill_value=0)
    c.index.name = 'toss_decision'
    c.columns = ['toss_winner_lost', 'toss_winner_won']
    c = c.reset_index()
    c['matches_with_result'] = c.toss_winner_lost + c.toss_winner_won
    c['win_rate_toss_winner'] = c.toss_winner_won / c.matches_with_result.replace(0, np.nan)
    return c


def savefig(fig, path: Path) -> None:
    fig.tight_layout(pad=1.5)
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def generate(data_dir: Path, output_dir: Path, figure_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    matches_raw = pd.read_csv(data_dir / 'matches.csv')
    innings_raw = pd.read_csv(data_dir / 'innings.csv')
    deliveries_raw = pd.read_csv(data_dir / 'deliveries.csv')
    if int(matches_raw.season.max()) != 2026:
        raise ValueError('Expected 2008-2026 archive; verify data directory')
    m = development_only(matches_raw)
    inn = development_only(innings_raw)
    d = development_only(deliveries_raw)
    assert (m.season <= CUTOFF).all() and (d.season <= CUTOFF).all()

    first = inn.loc[(inn.innings == 1) & (inn.season >= 2018)].copy()
    full = first.loc[first.legal_balls == 120].copy()
    full_vs_short = []
    for label, f in [('all_recorded', first), ('full_120_legal_balls', full),
                     ('fewer_than_120_legal_balls', first.loc[first.legal_balls < 120])]:
        if len(f):
            lo, hi = bootstrap_mean_ci(f.runs.to_numpy())
            full_vs_short.append({'scope': label, 'n': len(f), 'mean_runs': float(f.runs.mean()),
                                  'median_runs': float(f.runs.median()), 'sd_runs': float(f.runs.std(ddof=1)),
                                  'boot_mean_ci95_low': lo, 'boot_mean_ci95_high': hi})
    pd.DataFrame(full_vs_short).round(3).to_csv(output_dir / 'first_innings_full_vs_short_2018_2025.csv', index=False)

    venues = make_venue_comparison(first)
    venues.round(3).to_csv(output_dir / 'venues_full_20_season_adjusted_2018_2025.csv', index=False)
    paired = paired_innings_phase(d)
    paired.round(4).to_csv(output_dir / 'paired_powerplay_death_per_innings_2018_2025.csv', index=False)
    paired_diff = paired.death_minus_powerplay.to_numpy()
    diff_ci = clustered_mean_ci(paired_diff, paired.match_id.to_numpy())
    # Paired t-test treats innings as independent; same match sometimes contributes 2 innings.
    paired_t = stats.ttest_rel(paired.death_runs_per_six_legal, paired.powerplay_runs_per_six_legal)
    phase_by_year = (paired.groupby('season', as_index=False).agg(
        n_innings=('match_id', 'size'), mean_powerplay=('powerplay_runs_per_six_legal', 'mean'),
        mean_death=('death_runs_per_six_legal', 'mean'),
        mean_difference=('death_minus_powerplay', 'mean')))
    phase_by_year.round(4).to_csv(output_dir / 'paired_phase_by_season_2018_2025.csv', index=False)

    toss = toss_decision_crosstab(m)
    toss.to_csv(output_dir / 'toss_decision_match_result_crosstab_2018_2025.csv', index=False)
    fisher = stats.fisher_exact(toss[['toss_winner_lost','toss_winner_won']].to_numpy()) if toss.matches_with_result.min() > 0 else None

    # Missing city: the absence is real; its mechanism (MCAR/MAR/MNAR) is NOT identified.
    miss = m[['match_id','season','venue_canonical','city']].copy()
    miss['city_is_missing'] = miss.city.isna()
    city = (miss.groupby('venue_canonical', as_index=False)
            .agg(matches=('match_id', 'size'), missing_city=('city_is_missing', 'sum')))
    city['missing_city_pct'] = 100 * city.missing_city / city.matches
    city = city.loc[city.missing_city > 0].sort_values('missing_city', ascending=False)
    city.to_csv(output_dir / 'missing_city_by_venue_pre2026.csv', index=False)

    # Outlier sensitivity: Tukey outliers are retained in main analysis.
    dist = describe(first.runs)
    lower_fence = dist['q1'] - 1.5 * dist['iqr']
    upper_fence = dist['q3'] + 1.5 * dist['iqr']
    outliers = first.loc[(first.runs < lower_fence) | (first.runs > upper_fence),
                         ['match_id','season','batting_team','venue_canonical','runs','wickets','legal_balls']]
    outliers.to_csv(output_dir / 'first_innings_tukey_outliers_2018_2025.csv', index=False)
    trimmed_mean = float(stats.trim_mean(first.runs, proportiontocut=0.05))

    # Measured figure A: distributions by full-length vs shorter innings.
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.hist(full.runs, bins=np.arange(30, 301, 15), alpha=.75, label=f'120 legal balls (n={len(full)})')
    short = first.loc[first.legal_balls < 120]
    ax.hist(short.runs, bins=np.arange(30, 301, 15), alpha=.7, label=f'<120 legal balls (n={len(short)})')
    ax.legend(); ax.set(xlabel='Recorded first-innings runs', ylabel='Innings',title='Recorded innings length matters (2018-2025)')
    savefig(fig, figure_dir / '12_full_vs_short_innings.png')

    # Figure B: season-centered venue differences, with within-venue bootstrap bands.
    if len(venues):
        v = venues.sort_values('season_adjusted_difference_runs')
        y = np.arange(len(v))
        fig, ax = plt.subplots(figsize=(9.5, max(4.7, .55*len(v)+1)))
        x = v.season_adjusted_difference_runs.to_numpy()
        ax.errorbar(x, y, xerr=[x-v.ci95_low.to_numpy(),v.ci95_high.to_numpy()-x], fmt='o', capsize=2)
        ax.set_yticks(y, v.venue_canonical.to_list()); ax.axvline(0, ls='--', lw=1, color='grey')
        ax.set(xlabel='Runs above/below the same-season full-innings mean',
               title='Venue associations, 120-ball first innings (2018-2025)')
        savefig(fig, figure_dir / '13_venue_season_centered.png')

    # Figure C: paired phase difference with histogram.
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.hist(paired_diff, bins=28, edgecolor='white')
    ax.axvline(float(paired_diff.mean()), linestyle='--', color='black', label=f'Mean difference {paired_diff.mean():+.2f}')
    ax.axvline(0, color='grey', lw=1); ax.legend()
    ax.set(xlabel='Death - Powerplay runs per six legal balls',ylabel='Paired innings',
           title='Within-innings late-over acceleration (2018-2025)')
    savefig(fig, figure_dir / '14_paired_phase_differences.png')

    # Figure D: by-season paired phase differences.
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    ax.plot(phase_by_year.season, phase_by_year.mean_powerplay, marker='o', label='Powerplay')
    ax.plot(phase_by_year.season, phase_by_year.mean_death, marker='o', label='Death')
    ax.legend(); ax.set(xlabel='Season',ylabel='Runs per six legal balls',
                         title='Within-innings paired phase means (2018-2025)')
    savefig(fig, figure_dir / '15_phase_year_matched.png')

    # Figure E: toss association descriptive only.
    fig, ax = plt.subplots(figsize=(7.3, 4.5))
    ax.bar(toss.toss_decision, 100*toss.win_rate_toss_winner)
    for ind, r in toss.iterrows():
        ax.text(ind, r.win_rate_toss_winner*100+1, f"{r.toss_winner_won}/{r.matches_with_result}", ha='center')
    ax.set(ylim=(0, 80), xlabel='Toss-winner choice', ylabel='Toss winner also won match (%)',
           title='Toss decision and outcome (2018-2025): association only')
    savefig(fig, figure_dir / '16_toss_decision_association.png')

    # Figure F: missing city by venue (exclude zero-missing locations from visualization).
    if len(city):
        fig, ax = plt.subplots(figsize=(8.5, max(3.3, .7*len(city)+1)))
        ax.barh(city.venue_canonical, city.missing_city)
        ax.set(xlabel='Number of matches with missing city',title='Where missing city fields occur (2008-2025)')
        savefig(fig, figure_dir / '17_city_missingness_by_venue.png')

    summary = {
        'status': 'Stage 2 Session 02 complete; Stage 2 sign-off pending research narrative/review',
        'data_cutoff': CUTOFF,
        'development_matches': len(m),
        'recent_2018_2025_first_innings': len(first),
        'full_first_innings_120_balls': len(full),
        'shorter_first_innings': len(short),
        'all_innings_mean_runs': float(first.runs.mean()),
        'full_first_innings_mean_runs': float(full.runs.mean()),
        'shorter_first_innings_mean_runs': float(short.runs.mean()),
        'all_innings_5pct_trimmed_mean_runs': trimmed_mean,
        'tukey_bounds': [float(lower_fence),float(upper_fence)],
        'n_tukey_outliers': len(outliers),
        'venue_comparison_min_n':20,
        'n_venues_full_innings':len(venues),
        'venue_extremes':venues.iloc[np.r_[0,-1]][['venue_canonical','n_full_first_innings','season_adjusted_difference_runs']].to_dict('records') if len(venues) else [],
        'paired_phase_sample_innings':len(paired),
        'paired_phase_mean_powerplay':float(paired.powerplay_runs_per_six_legal.mean()),
        'paired_phase_mean_death':float(paired.death_runs_per_six_legal.mean()),
        'paired_phase_difference_mean':float(paired_diff.mean()),
        'paired_phase_difference_ci95_match_clustered':list(diff_ci),
        'paired_t_statistic_exploratory':float(paired_t.statistic),
        'paired_t_p_exploratory':float(paired_t.pvalue),
        'toss_table':toss.to_dict('records'),
        'toss_decision_fisher_p_exploratory':float(fisher.pvalue) if fisher else None,
        'missing_city_matches_pre2026':int(m.city.isna().sum()),
        'missing_city_venues':city[['venue_canonical','missing_city']].to_dict('records'),
        'interpretation_notes':[
            'Full vs shorter is observational: fewer than 120 legal balls may mean all-out, chase/rain truncation or other situations; score comparisons are not causal.',
            'Venue year-centering removes each year overall mean but cannot account for team, pitch, toss, weather, calendar composition, or all other confounders.',
            'Bootstrap uncertainty intervals are descriptive and conditional on these samples; they do not fix confounding or sampling bias.',
            'Paired phase analysis selects innings that reach at least 12 death-over legal balls; cannot generalize to early-ending innings.',
            'Bootstrap phase-difference uncertainty resamples whole matches; paired t-test separately treats innings as independent and its p-value is exploratory only.',
            'Toss choice vs toss-winner victory is an association in completed result matches, not evidence of a causal advantage.',
            '2026 held out completely. Do not use any of these statistical summaries as future-match features without computing historical snapshots.',
            'Missing city is concentrated by observed venue; MCAR/MAR/MNAR cannot be proven from observed data alone.',
        ],
    }
    (output_dir / 'stage02_session02_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False), encoding='utf-8')
    return summary


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data', type=Path, default=Path('data/processed'))
    ap.add_argument('--output', type=Path, default=Path('reports/stage_02/session_02'))
    ap.add_argument('--figures', type=Path, default=Path('reports/figures/stage_02'))
    args=ap.parse_args()
    result=generate(args.data,args.output,args.figures)
    print(json.dumps({k: result[k] for k in ['recent_2018_2025_first_innings','full_first_innings_120_balls','paired_phase_sample_innings','n_venues_full_innings','missing_city_matches_pre2026']}, indent=2))

if __name__ == '__main__':
    main()
