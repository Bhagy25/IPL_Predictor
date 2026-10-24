"""Validation-only diagnostics for 2025 pre-match batter milestone predictions."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss


def run(forecast_csv:Path, comparisons_csv:Path, training_csv:Path,
        output_dir:Path, figures_dir:Path, resamples:int=1200):
    f=pd.read_csv(forecast_csv)
    t=pd.read_csv(training_csv)
    cmp=pd.read_csv(comparisons_csv)
    if set(f.season)!={2025}:
        raise ValueError('Diagnostics accept only 2025 validation forecasts')
    earlier=t.loc[(t.season>=2018)&(t.season<=2024)]
    if earlier.empty:
        raise ValueError('No pre-2025 training history')
    output_dir.mkdir(parents=True,exist_ok=True)
    figures_dir.mkdir(parents=True,exist_ok=True)
    # Coherent prior baseline from same information available pre-match.
    train_probs=np.array([(earlier.milestone_class==i).mean() for i in range(3)])
    n=np.asarray(f.prior_innings,dtype=float)
    # Needed historical career-rate columns from pre-computed chronological features.
    historic=t.loc[(t.season==2025),['match_id','batter_id','career_30_rate','career_50_rate']]
    f=f.merge(historic,on=['match_id','batter_id'],validate='one_to_one')
    base50=(n*f.career_50_rate.to_numpy()+10*train_probs[2])/(n+10)
    base30=(n*f.career_30_rate.to_numpy()+10*(train_probs[1]+train_probs[2]))/(n+10)
    model_score=0.5*((f.actual_30-f.predicted_30)**2+(f.actual_50-f.predicted_50)**2)
    base_score=0.5*((f.actual_30-base30)**2+(f.actual_50-base50)**2)
    f['model_brier_per_innings']=model_score
    f['baseline_brier_per_innings']=base_score
    gain=float(np.mean(base_score-model_score))
    # vectorized per-match sums for efficient bootstrap.
    g=f.assign(gain=base_score-model_score).groupby('match_id').agg(
        sum_gain=('gain','sum'),n=('gain','size'))
    rng=np.random.default_rng(42)
    sampled=rng.integers(0,len(g),size=(resamples,len(g)))
    gg=g.sum_gain.to_numpy(); nn=g.n.to_numpy()
    bootstrap=gg[sampled].sum(axis=1)/nn[sampled].sum(axis=1)
    ci=np.quantile(bootstrap,[0.025,0.975])
    summary={'validation_year':2025,'validation_examples':int(len(f)),
             'validation_matches':int(f.match_id.nunique()),
             'brier_gain_over_smoothed_player_baseline':round(gain,6),
             'match_cluster_bootstrap_95_percentile_interval':[round(float(q),6) for q in ci],
             'bootstrap_resamples':resamples,
             'caution':'Descriptive interval, optimistic for selection: best candidate selected on same 2025 validation season, NOT independent confirmation.'}
    (output_dir/'batter_bootstrap_gain_2025.json').write_text(json.dumps(summary,indent=2))
    # Model comparisons; smaller is better.
    subset=cmp[['model','avg_milestone_brier']].copy()
    fig,ax=plt.subplots(figsize=(10,4.8))
    short=[s.replace('_full_form',' full form').replace('_2018plus',' 2018+')
           .replace('_all_history',' all history').replace('_three_class',' 3-class')
           .replace('_history_baseline',' history base') for s in subset.model]
    ax.barh(short,subset.avg_milestone_brier)
    ax.set(xlabel='Average Brier score of 30+ and 50+ (lower is better)',
           title='2025 validation: batter milestone candidate models')
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(figures_dir/'batter_model_comparison_2025.png',dpi=165)
    plt.close(fig)
    cal=pd.read_csv(output_dir/'batter_calibration_2025.csv')
    fig,axs=plt.subplots(1,2,figsize=(10,4.4),sharex=True,sharey=True)
    for ax,label in zip(axs,['30+','50+']):
        x=cal[cal.milestone==label]
        ax.plot([0,1],[0,1],linestyle='--',linewidth=1,label='Perfect calibration')
        ax.scatter(x.predicted,x.actual_rate,s=np.maximum(35,x.n/2),label='Observed bins')
        ax.set(xlim=(0,1),ylim=(0,1),xlabel='Average predicted probability',
               title=f'2025 validation: {label}')
        ax.grid(alpha=.2)
    axs[0].set_ylabel('Observed event frequency')
    fig.tight_layout()
    fig.savefig(figures_dir/'batter_milestone_calibration_2025.png',dpi=165)
    plt.close(fig)
    f['experience']=pd.cut(f.prior_innings,bins=[-1,0,4,19,np.inf],
                           labels=['First recorded innings','1-4 prior','5-19 prior','20+ prior'])
    cold=f.groupby('experience',observed=True).agg(
        n=('match_id','size'),observed_30=('actual_30','mean'),
        predicted_30=('predicted_30','mean'),observed_50=('actual_50','mean'),
        predicted_50=('predicted_50','mean')).reset_index()
    cold.to_csv(output_dir/'batter_by_player_experience_2025.csv',index=False)
    fig,ax=plt.subplots(figsize=(9,4.1))
    ax.bar(range(len(cold)),cold.n)
    ax.set(xticks=range(len(cold)),xticklabels=cold.experience,
           xlabel='Batter history available before each match',ylabel='Number of 2025 predictions',
           title='Cold-start and historical sample support')
    fig.tight_layout()
    fig.savefig(figures_dir/'batter_prior_history_2025.png',dpi=165)
    plt.close(fig)
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--forecasts',type=Path,default=Path('reports/stage_03/session_02/batter_validation_forecasts_2025.csv'))
    p.add_argument('--comparisons',type=Path,default=Path('reports/stage_03/session_02/batter_validation_comparison_2025.csv'))
    p.add_argument('--training',type=Path,default=Path('data/processed/stage03_batter_training_pre2026.csv'))
    p.add_argument('--output',type=Path,default=Path('reports/stage_03/session_02'))
    p.add_argument('--figures',type=Path,default=Path('reports/figures/stage_03'))
    args=p.parse_args()
    print(json.dumps(run(args.forecasts,args.comparisons,args.training,args.output,args.figures),indent=2))

if __name__=='__main__':main()
