"""Reproduce Stage 3 / Session 01 calibration figures and match-bootstrap context."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def run(results:Path,figures:Path,n_boot=2000):
    results=Path(results);figures=Path(figures)
    figures.mkdir(parents=True,exist_ok=True)
    comparison=pd.read_csv(results/'validation_comparison_2025.csv')
    forecast=pd.read_csv(results/'validation_forecasts_2025.csv')
    metrics=json.loads((results/'stage03_session01_validation.json').read_text())
    selected=metrics['selected_candidate']
    reliability=pd.read_csv(results/'calibration_2025.csv')
    phase=pd.read_csv(results/'by_phase_2025.csv')
    baseline='constant_rate_since_2018'

    fig,ax=plt.subplots(figsize=(9,4.4))
    labels=comparison.model.str.replace('_',' ',regex=False)
    bars=ax.barh(labels[::-1],comparison.brier_score.iloc[::-1])
    ax.set_xlabel('Brier Score (lower is better)');ax.set_title('Next-over wicket: 2025 validation models')
    ax.set_xlim(0,max(comparison.brier_score)*1.18)
    for b in bars:
        ax.annotate(f'{b.get_width():.4f}',(b.get_width(),b.get_y()+b.get_height()/2),
                    xytext=(5,0),textcoords='offset points',va='center',fontsize=9)
    fig.tight_layout()
    fig.savefig(figures/'01_validation_brier_comparison.png',dpi=170)
    plt.close(fig)

    fig,ax=plt.subplots(figsize=(6,5.5))
    ax.plot([0,1],[0,1],'--',color='#8e98a6',label='Ideal calibration')
    ax.plot(reliability.avg_predicted,reliability.observed_frequency,'o-',label='Development model')
    for r in reliability.itertuples():
        ax.annotate(str(int(r.n)),(r.avg_predicted,r.observed_frequency),xytext=(4,5),textcoords='offset points',fontsize=8)
    ax.set_xlim(0,0.75);ax.set_ylim(0,0.75)
    ax.set_xlabel('Mean predicted wicket probability')
    ax.set_ylabel('Observed wicket frequency')
    ax.set_title('2025 reliability by probability bin (labels = n)')
    ax.legend(loc='upper left');ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(figures/'02_validation_calibration.png',dpi=170);plt.close(fig)

    phase_order=['powerplay','middle','death'];ph=phase.set_index('phase').reindex(phase_order)
    fig,ax=plt.subplots(figsize=(7.4,4.2));x=np.arange(len(phase_order));w=.35
    ax.bar(x-w/2,ph.observed_rate,w,label='Observed')
    ax.bar(x+w/2,ph.avg_forecast,w,label='Average forecast')
    ax.set_xticks(x,labels=[p.title() for p in phase_order]);ax.set_ylim(0,.52)
    ax.set_ylabel('Chance of at least one wicket')
    ax.set_title('2025 wicket rate versus model forecasts by phase')
    ax.legend();ax.grid(axis='y',alpha=.18)
    fig.tight_layout();fig.savefig(figures/'03_validation_by_phase.png',dpi=170);plt.close(fig)

    f=forecast.copy()
    f['gain']=(f[baseline]-f.wicket_next_over)**2-(f[selected]-f.wicket_next_over)**2
    groups=f.groupby('match_id').gain.agg(['sum','count'])
    rng=np.random.default_rng(42); idx=rng.integers(0,len(groups),(n_boot,len(groups)))
    score=groups['sum'].to_numpy()[idx].sum(axis=1)/groups['count'].to_numpy()[idx].sum(axis=1)
    audit={'comparison':'positive values mean model beats constant-rate reference',
           'validation_matches':len(groups),'bootstrap_samples':n_boot,
           'point_brier_improvement':round(float(f.gain.mean()),6),
           'cluster_bootstrap_95_percent_interval':[round(float(z),6) for z in np.quantile(score,[.025,.975])],
           'caution':'Descriptive uncertainty on validation data used for model selection; not an independent test or guarantee.'}
    (results/'bootstrap_gain_2025.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    return audit


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--results',type=Path,default=Path('reports/stage_03/session_01'))
    p.add_argument('--figures',type=Path,default=Path('reports/figures/stage_03'))
    args=p.parse_args()
    print(json.dumps(run(args.results,args.figures),indent=2))

if __name__=='__main__':main()
