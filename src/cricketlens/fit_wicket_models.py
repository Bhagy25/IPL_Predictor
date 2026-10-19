"""Stage 3 / Session 1: compare wicket-risk models using 2025 only.

No 2026 observations are evaluated or used for feature selection here.
Model artifacts are DEVELOPMENT ONLY. The 2026 test is a later, one-time step.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASIC_NUM = ['innings','completed_overs','runs','wickets','run_rate']
BASIC_CAT = ['batting_team','bowling_team']
ADDED_NUM = ['last_over_runs','last_over_wickets']
ENHANCED_CAT=['phase','venue_canonical']
TARGET='wicket_next_over'


def make_logistic(num,cat):
    return Pipeline([
        ('features', ColumnTransformer([
            ('numbers',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]), num),
            ('categories',OneHotEncoder(handle_unknown='ignore'),cat),
        ])),
        ('model',LogisticRegression(max_iter=2500,C=1.0,random_state=42))
    ])


def measure(y, p):
    p=np.clip(np.asarray(p,dtype=float),1e-6,1-1e-6)
    out={'rows':int(len(y)), 'event_rate':round(float(np.mean(y)),6),
         'brier_score':round(float(brier_score_loss(y,p)),6),
         'log_loss':round(float(log_loss(y,p,labels=[0,1])),6)}
    if len(set(y))==2: out['roc_auc']=round(float(roc_auc_score(y,p)),6)
    return out


def reliability(y,p,bins=10):
    tbl=pd.DataFrame({'actual':np.asarray(y,dtype=int),'pred':np.asarray(p,dtype=float)})
    tbl['bin']=pd.cut(tbl.pred,bins=np.linspace(0,1,bins+1),labels=False,include_lowest=True)
    return tbl.groupby('bin',observed=True).agg(n=('actual','size'),
            avg_predicted=('pred','mean'), observed_frequency=('actual','mean')).reset_index()


def fit_and_validate(data:pd.DataFrame, output:Path,seed=42):
    needed=set(BASIC_NUM+BASIC_CAT+ADDED_NUM+ENHANCED_CAT+[TARGET,'season','match_id','phase'])
    if needed-set(data.columns): raise ValueError(f'Missing: {sorted(needed-set(data.columns))}')
    # We may read a file with 2026 rows, but they are discarded before modeling,
    # scoring, plotting, or model selection. 2026 remains locked.
    eligible=data[data.season<=2025].copy()
    if eligible.empty: raise ValueError('No development rows')
    if eligible.duplicated(['match_id','innings','completed_overs']).any():
        raise ValueError('Duplicate examples')
    # Explicitly keep ALL checkpoints from each match within its own season.
    train=eligible[eligible.season<=2024].copy()
    val=eligible[eligible.season==2025].copy()
    if val.empty or train.empty or train[TARGET].nunique()!=2:
        raise ValueError('Train through 2024 and validate 2025 must both exist')
    configs={
        'logistic_basic_all_history':(train, make_logistic(BASIC_NUM,BASIC_CAT),BASIC_NUM+BASIC_CAT),
        'logistic_basic_since_2018':(train[train.season>=2018],make_logistic(BASIC_NUM,BASIC_CAT),BASIC_NUM+BASIC_CAT),
        'logistic_context_since_2018':(train[train.season>=2018],make_logistic(BASIC_NUM+ADDED_NUM,BASIC_CAT+ENHANCED_CAT),BASIC_NUM+ADDED_NUM+BASIC_CAT+ENHANCED_CAT),
    }
    results=[]; forecasts={}; fitted={}
    y=val[TARGET].astype(int).to_numpy()
    for name,(training,model,cols) in configs.items():
        model.fit(training[cols],training[TARGET].astype(int))
        p=model.predict_proba(val[cols])[:,1]
        results.append({'model':name,'trained_rows':len(training),'validation_year':2025,**measure(y,p)})
        forecasts[name]=p
        fitted[name]=(model,cols)
    # A constant-rate reference is a rigorous honest comparator.
    for window_name,subset in [('all_history',train),('since_2018',train[train.season>=2018])]:
        p=np.repeat(float(subset[TARGET].mean()),len(val))
        results.append({'model':'constant_rate_'+window_name,'trained_rows':len(subset),
                        'validation_year':2025,**measure(y,p)})
        forecasts['constant_rate_'+window_name]=p
    ranking=pd.DataFrame(results).sort_values(['brier_score','log_loss']).reset_index(drop=True)
    # Select only among ML candidates and ONLY using validation (not 2026).
    best_name=ranking.loc[ranking.model.isin(configs),'model'].iloc[0]
    best,cols=fitted[best_name]
    prediction_table=val[['match_id','date','season','innings','completed_overs','phase',TARGET]].copy()
    for name,p in forecasts.items():prediction_table[name]=p
    # Auditable models, values, and metrics, no artifact uses 2026.
    output.mkdir(parents=True,exist_ok=True)
    ranking.to_csv(output/'validation_comparison_2025.csv',index=False)
    prediction_table.to_csv(output/'validation_forecasts_2025.csv',index=False)
    reliability(y,forecasts[best_name]).to_csv(output/'calibration_2025.csv',index=False)
    by_phase=(prediction_table.groupby('phase',observed=True)
              .apply(lambda g:pd.Series({'n':len(g),'observed_rate':g[TARGET].mean(),
                             'avg_forecast':g[best_name].mean(),
                             'brier':brier_score_loss(g[TARGET],g[best_name])}),include_groups=False)
              .reset_index())
    by_phase.to_csv(output/'by_phase_2025.csv',index=False)
    # Don't persist very large serialized model in git; only local models/.
    model_path=Path('models')/'wicket_development_pre2025.joblib'
    model_path.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump({'model':best,'columns':cols,'name':best_name,'training_end':2024,
                 'validation_year':2025,'outcome':'wicket_next_over','horizon':'next over'},model_path)
    report={'stage':'3, session 1', 'status':'validation_only',
            'train_end_year':2024,'validation_year':2025,'holdout_year_unopened':2026,
            'training_matches':int(train.match_id.nunique()),
            'validation_matches':int(val.match_id.nunique()),
            'training_eligible_rows':len(train),'validation_eligible_rows':len(val),
            'selected_candidate':best_name,'features':cols,
            'candidate_ranking':ranking.to_dict(orient='records'),
            'notes':['All match checkpoints remain grouped by season.','D/L-marked matches excluded from initial cohort.',
                     'Validation improvements may be small. No 2026 results inspected.',
                     'No player milestone model trained yet.']}
    (output/'stage03_session01_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,default=Path('data/processed/stage03_next_over_training.csv'))
    p.add_argument('--output',type=Path,default=Path('reports/stage_03/session_01'))
    args=p.parse_args()
    summary=fit_and_validate(pd.read_csv(args.input),args.output)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
