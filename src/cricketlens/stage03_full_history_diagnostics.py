"""Regenerate Stage 3 Session 3 diagnostics from locked 2026 test forecasts."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def one_reliability(df, truth, pred, title, output):
    value=pd.DataFrame({'truth':df[truth].astype(int),'pred':df[pred].astype(float)})
    edges=np.linspace(0,1,11)
    value['bin']=pd.cut(value.pred,edges,labels=False,include_lowest=True)
    summary=value.groupby('bin',observed=True).agg(observed=('truth','mean'),predicted=('pred','mean'),n=('truth','size')).reset_index()
    fig,ax=plt.subplots(figsize=(6.9,4.1))
    ax.plot([0,1],[0,1],linestyle='--',linewidth=1,label='Perfect calibration')
    ax.scatter(summary.predicted,summary.observed,s=np.sqrt(summary.n)*9,label='2026 test bins')
    ax.plot(summary.predicted,summary.observed,linewidth=1)
    ax.set_xlim(0,1);ax.set_ylim(0,1)
    ax.set_xlabel('Mean predicted probability');ax.set_ylabel('Observed event frequency')
    ax.set_title(title);ax.grid(alpha=.25);ax.legend(loc='upper left')
    fig.tight_layout();output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(output,dpi=155);plt.close(fig)


def run(root:Path):
    result_dir=root/'reports/stage_03/session_03'
    figures=root/'reports/figures/stage_03'
    data=json.loads((result_dir/'stage03_session03_final_results.json').read_text())
    wk=pd.read_csv(result_dir/'wicket/wicket_holdout_forecasts_2026.csv')
    bt=pd.read_csv(result_dir/'batter/batter_holdout_forecasts_2026.csv')
    one_reliability(wk,'wicket_next_over','predicted_wicket_probability',
        '2026 wicket probability calibration',figures/'full_history_wicket_calibration_2026.png')
    one_reliability(bt,'actual_30_plus','probability_30_plus',
        '2026 batter 30+ probability calibration',figures/'full_history_batter30_calibration_2026.png')
    one_reliability(bt,'actual_50_plus','probability_50_plus',
        '2026 batter 50+ probability calibration',figures/'full_history_batter50_calibration_2026.png')
    labels=['Wicket next over','Batter scores 30+','Batter scores 50+']
    values=[data['wicket']['holdout_2026']['brier_score'],data['batter']['holdout_2026']['brier_30'],data['batter']['holdout_2026']['brier_50']]
    bases=[data['wicket']['holdout_constant']['brier_score'],data['batter']['holdout_constant']['brier_30'],data['batter']['holdout_constant']['brier_50']]
    x=np.arange(len(labels));fig,ax=plt.subplots(figsize=(7.2,4.4))
    ax.bar(x-.18,values,width=.35,label='Full-history ML model')
    ax.bar(x+.18,bases,width=.35,label='Constant-rate baseline')
    ax.set_xticks(x,labels);ax.set_ylabel('Brier score (lower is better)')
    ax.set_ylim(0,.26);ax.set_title('One-time holdout: IPL 2026')
    ax.legend(loc='upper right');ax.grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(figures/'full_history_2026_brier_comparison.png',dpi=155);plt.close(fig)
    return figures

if __name__=='__main__':
    print(run(Path('.')))
