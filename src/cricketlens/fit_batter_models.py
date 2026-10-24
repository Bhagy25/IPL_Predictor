"""Stage 3/Session 2: one three-class model for coherent P(30+) and P(50+).

Development only: train <=2024, validate 2025; do not evaluate 2026 yet.
All model feature columns are explicitly whitelisted (no current-match runs).
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
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FORM_NUM=['prior_innings','career_avg_runs','career_30_rate','career_50_rate',
          'recent5_avg_runs','recent5_30_rate','recent5_50_rate',
          'recent10_avg_runs','recent10_30_rate','recent10_50_rate',
          'opposition_prior_innings','opposition_avg_runs','opposition_30_rate',
          'venue_prior_innings','venue_avg_runs','venue_30_rate',
          'days_since_previous_innings']
TEAM_CAT=['batting_team','bowling_team']
CONTEXT_CAT=TEAM_CAT+['venue_canonical']
Y='milestone_class'


def make_logistic(num,cat):
    return Pipeline([
      ('features',ColumnTransformer([
          ('numerics',Pipeline([('impute',SimpleImputer(strategy='median')),
                                ('scale',StandardScaler())]),num),
          ('categoricals',OneHotEncoder(handle_unknown='ignore'),cat),
      ])),
      ('model',LogisticRegression(max_iter=1800, C=0.25, random_state=42))
    ])


def make_forest(num,cat):
    return Pipeline([
      ('features',ColumnTransformer([
          ('numerics',SimpleImputer(strategy='median'),num),
          ('categoricals',OneHotEncoder(handle_unknown='ignore'),cat),
      ])),
      ('model',RandomForestClassifier(n_estimators=160,max_depth=8,
                   min_samples_leaf=30,n_jobs=-1,random_state=42))
    ])


def positive_probability_three_class(proba, classes=(0,1,2)):
    prob = np.asarray(proba,dtype=float)
    mapping={int(c):i for i,c in enumerate(classes)}
    if set(mapping)!={0,1,2}:
        raise ValueError('Expected three categories <30,30-49,>=50')
    p50=prob[:,mapping[2]]
    p30=p50+prob[:,mapping[1]]
    if np.any(p50>p30+1e-12):
        raise AssertionError('Invalid milestone probability ordering')
    return p30,p50


def metrics(yclass,proba):
    y=np.asarray(yclass,dtype=int)
    p30,p50=positive_probability_three_class(proba)
    out={'rows':len(y),
         'observed_30_rate':round(float(np.mean(y>=1)),6),
         'observed_50_rate':round(float(np.mean(y==2)),6),
         'brier_30':round(float(brier_score_loss(y>=1,p30)),6),
         'brier_50':round(float(brier_score_loss(y==2,p50)),6),
         'avg_milestone_brier':round(float((brier_score_loss(y>=1,p30)+brier_score_loss(y==2,p50))/2),6),
         'multiclass_log_loss':round(float(log_loss(y,np.clip(proba,1e-8,1),labels=[0,1,2])),6)}
    for milestone,label,events in [(30,'roc_auc_30',y>=1),(50,'roc_auc_50',y==2)]:
        if len(set(events))==2:
            out[label]=round(float(roc_auc_score(events,p30 if milestone==30 else p50)),6)
    return out


def calibration_table(y, probabilities, label, bins=8):
    df=pd.DataFrame({'actual':np.asarray(y,dtype=int),'forecast':np.asarray(probabilities,dtype=float)})
    df['bin']=pd.cut(df.forecast,bins=np.linspace(0,1,bins+1),labels=False,include_lowest=True)
    table=(df.groupby('bin',observed=True)
           .agg(n=('actual','size'),predicted=('forecast','mean'),actual_rate=('actual','mean'))
           .reset_index())
    table['milestone']=label
    return table


def fit_and_validate(data:pd.DataFrame,output:Path,model_path:Path|None=None):
    needed=set(FORM_NUM+CONTEXT_CAT+[Y,'match_id','batter_id','batter','date','season','reached_30','reached_50'])
    if needed-set(data.columns):
        raise ValueError(f'Missing training columns: {sorted(needed-set(data.columns))}')
    # Explicitly block 2026 rows from all development operations and candidate tuning.
    data=data.loc[data.season<=2025].copy()
    if data.duplicated(['match_id','innings','batter_id']).any():
        raise ValueError('Duplicate batter innings')
    train=data.loc[data.season<=2024]
    valid=data.loc[data.season==2025]
    if len(train)<100 or len(valid)<25 or len(set(train[Y]))!=3:
        raise ValueError('Not enough eligible training/validation observations for all classes')
    if not ((data.reached_30==(data[Y]>=1)).all() and (data.reached_50==(data[Y]==2)).all()):
        raise ValueError('Labels contradict milestone class')
    # Two chronological-history windows, two algorithms, and baselines.
    train_recent=train.loc[train.season>=2018]
    candidates={
      'logistic_team_context_2018plus':(train_recent,make_logistic(['prior_innings','career_avg_runs','career_30_rate',
                                         'career_50_rate'],TEAM_CAT),
                                      ['prior_innings','career_avg_runs','career_30_rate','career_50_rate']+TEAM_CAT),
      'logistic_full_form_2018plus':(train_recent,make_logistic(FORM_NUM,CONTEXT_CAT),FORM_NUM+CONTEXT_CAT),
      'logistic_full_form_all_history':(train,make_logistic(FORM_NUM,CONTEXT_CAT),FORM_NUM+CONTEXT_CAT),
      'forest_full_form_2018plus':(train_recent,make_forest(FORM_NUM,CONTEXT_CAT),FORM_NUM+CONTEXT_CAT),
    }
    rows=[]; fore={}; fitted={}
    y=valid[Y].to_numpy(dtype=int)
    for name,(subset,model,cols) in candidates.items():
        model.fit(subset[cols],subset[Y].astype(int))
        p=model.predict_proba(valid[cols])
        # Classes explicitly normalized to [0,1,2] for defensiveness.
        prob=np.zeros((len(valid),3),dtype=float)
        prob[:,model.named_steps['model'].classes_.astype(int)]=p
        fore[name]=prob
        rows.append({'model':name,'trained_rows':len(subset),'validation_year':2025,**metrics(y,prob)})
        fitted[name]=(model,cols)
    # Global class proportions and player-specific prior rate baselines.
    for reference,subset in [('all_history',train),('since_2018',train_recent)]:
        fractions=np.array([(subset[Y]==i).mean() for i in range(3)])
        p=np.tile(fractions,(len(valid),1))
        fore['constant_three_class_'+reference]=p
        rows.append({'model':'constant_three_class_'+reference,
                     'trained_rows':len(subset),'validation_year':2025,**metrics(y,p)})
    # Player's prior career milestone rates, with Laplace-style smoothing toward
    # pre-2025 global classes. Uses only player history from before match date.
    global_probs=np.array([(train_recent[Y]==i).mean() for i in range(3)])
    n=np.asarray(valid.prior_innings,dtype=float)
    p50=(n*np.asarray(valid.career_50_rate,dtype=float)+10*global_probs[2])/(n+10)
    p30=(n*np.asarray(valid.career_30_rate,dtype=float)+10*(global_probs[1]+global_probs[2]))/(n+10)
    p=np.stack([1-p30,p30-p50,p50],axis=1)
    if np.any(p< -1e-9):
        raise ValueError('Inconsistent prior milestone rates')
    fore['smoothed_player_history_baseline']=p
    rows.append({'model':'smoothed_player_history_baseline','trained_rows':len(train_recent),
                 'validation_year':2025,**metrics(y,p)})
    ranking=pd.DataFrame(rows).sort_values(['avg_milestone_brier','multiclass_log_loss']).reset_index(drop=True)
    best_name=ranking.loc[ranking.model.isin(candidates),'model'].iloc[0]
    best,cols=fitted[best_name]
    best_probs=fore[best_name]
    p30,p50=positive_probability_three_class(best_probs)
    if np.any(p50>p30) or np.any(p30>1) or np.any(p50<0):
        raise AssertionError('Invalid coherent forecasts')
    output.mkdir(parents=True,exist_ok=True)
    ranking.to_csv(output/'batter_validation_comparison_2025.csv',index=False)
    forecasts=valid[['match_id','date','season','batter_id','batter','batting_team','bowling_team',
                     'venue_canonical','milestone_class','actual_runs','prior_innings']].copy()
    forecasts['predicted_30']=p30
    forecasts['predicted_50']=p50
    forecasts['actual_30']=(valid[Y]>=1).astype(int)
    forecasts['actual_50']=(valid[Y]==2).astype(int)
    forecasts.to_csv(output/'batter_validation_forecasts_2025.csv',index=False)
    pd.concat([calibration_table(valid[Y]>=1,p30,'30+'),
               calibration_table(valid[Y]==2,p50,'50+')],ignore_index=True).to_csv(
                   output/'batter_calibration_2025.csv',index=False)
    stats={'stage':'3, session 2','status':'development validation only',
           'training_end_year':2024,'validation_year':2025,'holdout_2026':'unopened',
           'training_rows':int(len(train)),'validation_rows':int(len(valid)),
           'training_matches':int(train.match_id.nunique()),'validation_matches':int(valid.match_id.nunique()),
           'training_player_ids':int(train.batter_id.nunique()),
           'validation_cold_starts':int((valid.prior_innings==0).sum()),
           'selected_candidate':best_name,'selected_features':cols,
           'selected_validation_scores':ranking.loc[ranking.model==best_name].to_dict(orient='records')[0],
           'comparison':ranking.to_dict(orient='records'),
           'caveats':['Forecasts assume batter has a recorded batting innings; selection and DNB not modeled.',
                      'Realized batting position, toss, playing XI, and match score are not used as pre-match inputs.',
                      'D/L-marked and no-result matches excluded from development cohort.',
                      'Features from earlier 2025 matches are allowed for later 2025 dates; model weights fixed after 2024.',
                      'Year 2026 unused for candidate selection or reporting.',
                      'Performance depends on player prior history; unseen players have cold-start uncertainty.']}
    (output/'stage03_session02_validation.json').write_text(json.dumps(stats,indent=2),encoding='utf8')
    artifact=model_path or Path('models/batter_development_pre2025.joblib')
    artifact.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump({'model':best,'columns':cols,'name':best_name,'train_end':2024,
                 'validation_year':2025,'milestones':[30,50],
                 'condition':'batter has an observed batting innings','version':'development'},artifact)
    return stats


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,default=Path('data/processed/stage03_batter_training_pre2026.csv'))
    p.add_argument('--output',type=Path,default=Path('reports/stage_03/session_02'))
    p.add_argument('--model',type=Path,default=Path('models/batter_development_pre2025.joblib'))
    args=p.parse_args()
    summary=fit_and_validate(pd.read_csv(args.input),args.output,args.model)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
