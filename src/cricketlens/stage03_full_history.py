"""Stage 3 Session 3: full-history 2008-2025 -> 2026 HOLDOUT -> refit 2008-2026.

The 2025 validation selects a full-history configuration without inspecting 2026.
A single held-out 2026 evaluation is recorded; the 2026 outcomes are only used
for training after those metrics and per-example forecasts have been saved.
Past-only player form allows 2026 results from *earlier dates* at later 2026
checkpoints, simulating continuously updated information during the season.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from cricketlens.wicket_training_data import build as build_wicket
from cricketlens.batter_training_data import build as build_batter
from cricketlens.fit_wicket_models import (BASIC_NUM, BASIC_CAT, ADDED_NUM,
    ENHANCED_CAT, make_logistic as wicket_logistic, measure as wicket_measure,
    reliability as wicket_reliability)
from cricketlens.fit_batter_models import (FORM_NUM, CONTEXT_CAT,
    make_logistic as batter_logistic, make_forest as batter_forest,
    metrics as batter_measure, positive_probability_three_class,
    calibration_table)

WICKET_TARGET='wicket_next_over'
BATTER_TARGET='milestone_class'


def _triple(model, data, columns):
    p=model.predict_proba(data[columns]); classes=model.named_steps['model'].classes_.astype(int)
    result=np.zeros((len(data),3),dtype=float)
    result[:,classes]=p
    if not np.allclose(result.sum(axis=1),1):
        raise ValueError('Milestone class probabilities must sum to one')
    return result


def _class_rate(y):
    values=np.asarray(y,dtype=int)
    return np.array([(values==c).mean() for c in (0,1,2)])


def _assert_date_splits(df):
    for yr in [2025,2026]:
        if (df.season==yr).sum()==0:
            raise ValueError(f'Missing required IPL {yr} examples')
    if set(df[df.season<=2025].match_id).intersection(set(df[df.season==2026].match_id)):
        raise AssertionError('2026 match appears in pre-2026 training')
    if df.duplicated(['match_id','innings','completed_overs']).any() and 'completed_overs' in df:
        raise ValueError('Duplicated wicket examples')


def run_wicket(data, out_dir, model_dir):
    cols_basic=BASIC_NUM+BASIC_CAT
    cols_context=BASIC_NUM+ADDED_NUM+BASIC_CAT+ENHANCED_CAT
    required=set(cols_context+['season','date','match_id','innings','completed_overs',WICKET_TARGET])
    if missing:=required-set(data.columns): raise ValueError(f'Wicket missing: {sorted(missing)}')
    _assert_date_splits(data)
    train=data[data.season<=2024].copy()
    valid=data[data.season==2025].copy()
    pretest=data[data.season<=2025].copy()
    test=data[data.season==2026].copy()
    assert len(train)>5000 and len(valid)>100 and len(test)>100
    # Candidate family + hyperparameters frozen BEFORE opening 2026.
    configs={'logistic_basic_all_history':cols_basic,
             'logistic_context_all_history':cols_context}
    evaluated=[]
    for name,cols in configs.items():
        model=wicket_logistic(cols[:len(BASIC_NUM)] if name=='logistic_basic_all_history' else BASIC_NUM+ADDED_NUM,
                              BASIC_CAT if name=='logistic_basic_all_history' else BASIC_CAT+ENHANCED_CAT)
        model.fit(train[cols],train[WICKET_TARGET])
        p=model.predict_proba(valid[cols])[:,1]
        evaluated.append({'model':name,'training_rows':len(train),**wicket_measure(valid[WICKET_TARGET],p)})
    base=float(train[WICKET_TARGET].mean())
    base_scores=wicket_measure(valid[WICKET_TARGET],np.full(len(valid),base))
    select=min(evaluated,key=lambda x:(x['brier_score'],x['log_loss']))
    selected_name=select['model']; selected_cols=configs[selected_name]
    num=BASIC_NUM if selected_name=='logistic_basic_all_history' else BASIC_NUM+ADDED_NUM
    cat=BASIC_CAT if selected_name=='logistic_basic_all_history' else BASIC_CAT+ENHANCED_CAT

    def factory(): return wicket_logistic(num,cat)
    # This is the important boundary: selected_name is locked by 2025 only.
    holdout_model=factory();holdout_model.fit(pretest[selected_cols],pretest[WICKET_TARGET])
    test_p=holdout_model.predict_proba(test[selected_cols])[:,1]
    test_base=np.repeat(float(pretest[WICKET_TARGET].mean()),len(test))
    model_scores=wicket_measure(test[WICKET_TARGET],test_p)
    baseline_scores=wicket_measure(test[WICKET_TARGET],test_base)
    out_dir.mkdir(parents=True,exist_ok=True);model_dir.mkdir(parents=True,exist_ok=True)
    forecasts=test[['match_id','date','season','innings','completed_overs','phase',WICKET_TARGET]].copy()
    forecasts['predicted_wicket_probability']=test_p
    forecasts.to_csv(out_dir/'wicket_holdout_forecasts_2026.csv',index=False)
    wicket_reliability(test[WICKET_TARGET],test_p).to_csv(out_dir/'wicket_holdout_calibration_2026.csv',index=False)
    artifact_hold={'model':holdout_model,'columns':selected_cols,'name':selected_name,
                   'training_end':2025,'test_year':2026,'version':'holdout_eval_pre2026',
                   'outcome':WICKET_TARGET,'horizon':'one upcoming over'}
    joblib.dump(artifact_hold,model_dir/'wicket_holdout_train_through_2025.joblib')
    # Only now, after 2026 holdout is scored and saved, fit through 2026.
    deployment_model=factory();deployment_model.fit(data[selected_cols],data[WICKET_TARGET])
    joblib.dump({'model':deployment_model,'columns':selected_cols,'name':selected_name,
                 'training_end':2026,'version':'deployment_refit_2008_2026',
                 'outcome':WICKET_TARGET,'horizon':'one upcoming over',
                 'notice':'No automatic retraining, manual score/wickets input'},
                model_dir/'wicket_deployment_through_2026.joblib')
    return {'model':'next_over_wicket','selected_name_from_2025_only':selected_name,
            'candidate_validation_2025':evaluated,'constant_validation_2025':base_scores,
            'selection_metric':'lowest 2025 Brier, tie break log loss',
            'train_2008_2024':len(train),'validate_2025':len(valid),
            'refit_2008_2025_for_holdout':len(pretest),
            'test_2026_rows':len(test),'test_2026_matches':int(test.match_id.nunique()),
            'holdout_2026':model_scores,'holdout_constant':baseline_scores,
            'final_refit_2008_2026':len(data),'final_trained_through':2026,
            'selected_features':selected_cols,
            'exclusions':'D/L-marked matches excluded; unusual/censored overs excluded unless a wicket observed',
            'limitation':'Model performance on a future season is not guaranteed'}


def run_batter(data,out_dir,model_dir):
    cols=FORM_NUM+CONTEXT_CAT
    required=set(cols+['season','date','match_id','innings','batter_id','batter',BATTER_TARGET])
    if missing:=required-set(data.columns):raise ValueError(f'Batter missing: {sorted(missing)}')
    assert (data.season==2026).sum()>100
    assert not data.duplicated(['match_id','innings','batter_id']).any()
    train=data[data.season<=2024].copy()
    valid=data[data.season==2025].copy()
    pretest=data[data.season<=2025].copy()
    test=data[data.season==2026].copy()
    assert len(train)>1000 and len(valid)>100
    constructors={'logistic_full_history':lambda:batter_logistic(FORM_NUM,CONTEXT_CAT),
                  'forest_full_history':lambda:batter_forest(FORM_NUM,CONTEXT_CAT)}
    validation=[]
    for name,make in constructors.items():
        model=make();model.fit(train[cols],train[BATTER_TARGET])
        prob=_triple(model,valid,cols)
        validation.append({'model':name,'training_rows':len(train),**batter_measure(valid[BATTER_TARGET],prob)})
    val_constant=np.tile(_class_rate(train[BATTER_TARGET]),(len(valid),1))
    val_baseline=batter_measure(valid[BATTER_TARGET],val_constant)
    selected=min(validation,key=lambda x:(x['avg_milestone_brier'],x['multiclass_log_loss']))
    selected_name=selected['model'];factory=constructors[selected_name]
    holdout_model=factory();holdout_model.fit(pretest[cols],pretest[BATTER_TARGET])
    test_prob=_triple(holdout_model,test,cols)
    p30,p50=positive_probability_three_class(test_prob)
    assert np.all(p50<=p30) and np.all((0<=p30)&(p30<=1))
    baseline=np.tile(_class_rate(pretest[BATTER_TARGET]),(len(test),1))
    test_scores=batter_measure(test[BATTER_TARGET],test_prob)
    baseline_scores=batter_measure(test[BATTER_TARGET],baseline)
    out_dir.mkdir(parents=True,exist_ok=True);model_dir.mkdir(parents=True,exist_ok=True)
    forecast=test[['match_id','date','season','innings','batter_id','batter','actual_runs',
                   BATTER_TARGET,'prior_innings']].copy()
    forecast['probability_30_plus']=p30
    forecast['probability_50_plus']=p50
    forecast['actual_30_plus']=(test[BATTER_TARGET]>=1).astype(int)
    forecast['actual_50_plus']=(test[BATTER_TARGET]==2).astype(int)
    forecast.to_csv(out_dir/'batter_holdout_forecasts_2026.csv',index=False)
    pd.concat([calibration_table(test[BATTER_TARGET]>=1,p30,'30+'),
               calibration_table(test[BATTER_TARGET]==2,p50,'50+')],ignore_index=True).to_csv(
                out_dir/'batter_holdout_calibration_2026.csv',index=False)
    joblib.dump({'model':holdout_model,'columns':cols,'name':selected_name,
                 'train_end':2025,'test_year':2026,'version':'holdout_eval_pre2026',
                 'condition':'batter has recorded batting innings'},
                model_dir/'batter_holdout_train_through_2025.joblib')
    # After scoring 2026, fit FINAL deployment artifact on whole eligible history.
    final_model=factory();final_model.fit(data[cols],data[BATTER_TARGET])
    joblib.dump({'model':final_model,'columns':cols,'name':selected_name,
                 'train_end':2026,'version':'deployment_refit_2008_2026',
                 'condition':'batter has recorded batting innings','milestones':[30,50]},
                model_dir/'batter_deployment_through_2026.joblib')
    return {'model':'batter_milestones_30_50','selected_name_from_2025_only':selected_name,
            'candidate_validation_2025':validation,'constant_validation_2025':val_baseline,
            'selection_metric':'lowest 2025 avg milestone Brier, tie break multiclass log loss',
            'train_2008_2024':len(train),'validate_2025':len(valid),
            'refit_2008_2025_for_holdout':len(pretest),
            'test_2026_rows':len(test),'test_2026_matches':int(test.match_id.nunique()),
            'holdout_2026':test_scores,'holdout_constant':baseline_scores,
            'final_refit_2008_2026':len(data),'final_trained_through':2026,
            'selected_features':cols,
            'assumption':'conditional on batting appearance; batting selection / did-not-bat not predicted',
            'exclusions':'D/L-marked and no-result matches initially excluded',
            'temporal_feature_policy':'2026 model weights frozen at 2025; feature snapshot only uses strictly prior-date player innings'}


def execute(batters_csv:Path,matches_csv:Path,overs_csv:Path,output:Path,model_dir:Path,processed:Path):
    # There is no model selection using 2026: each run fixes the candidate family,
    # feature schema and training split up front (code audited/reproducible).
    matches=pd.read_csv(matches_csv)
    bats=pd.read_csv(batters_csv)
    ovs=pd.read_csv(overs_csv)
    # Wicket labels generated from eligible next overs, with no future score as a feature.
    wk,wk_audit=build_wicket(ovs,matches)
    # Critical: allow building 2026 features explicitly, but only use 2026
    # earlier-date innings to inform LATER 2026 features, never the current match.
    bt,bt_audit=build_batter(bats,matches,max_development_season=2026,allow_2026=True)
    processed.mkdir(parents=True,exist_ok=True)
    wk.to_csv(processed/'stage03_wicket_full_history_2008_2026.csv',index=False)
    bt.to_csv(processed/'stage03_batter_full_history_2008_2026.csv',index=False)
    out_w=output/'wicket';out_b=output/'batter'
    wicket_result=run_wicket(wk,out_w,model_dir)
    batter_result=run_batter(bt,out_b,model_dir)
    result={'stage':'3','session':'03','purpose':'2008-2025 train/validate, 2026 one-time holdout, refit through 2026',
            'created_utc':datetime.now(timezone.utc).isoformat(),
            'archive_matches':int(len(matches)),
            'eligible_wicket_examples':wk_audit,'eligible_batter_examples':bt_audit,
            'wicket':wicket_result,'batter':batter_result,
            'important_caveats':[
                'Full history is used for both models; selection among predeclared algorithms made using 2025 only.',
                'Holdout models use 2008-2025 records and never train on 2026 outcomes.',
                '2026 labels used solely for the one-time test, then deployment refit through 2026.',
                '2026 test batter recent-form features can use earlier 2026 innings, which would have been known chronologically.',
                'D/L exclusions and censored next-over labeling affect representativeness; scores depend on eligibility choices.',
                '2027 deployment requires updated player-roster checks and feature construction at requested dates.']}
    output.mkdir(parents=True,exist_ok=True)
    (output/'stage03_session03_final_results.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--batters',type=Path,default=Path('data/processed/batter_innings.csv'))
    p.add_argument('--matches',type=Path,default=Path('data/processed/matches.csv'))
    p.add_argument('--overs',type=Path,default=Path('data/processed/overs.csv'))
    p.add_argument('--output',type=Path,default=Path('reports/stage_03/session_03'))
    p.add_argument('--model-dir',type=Path,default=Path('models'))
    p.add_argument('--processed',type=Path,default=Path('data/processed'))
    a=p.parse_args()
    summary=execute(a.batters,a.matches,a.overs,a.output,a.model_dir,a.processed)
    print(json.dumps({'wicket':summary['wicket']['holdout_2026'],
                      'batter':summary['batter']['holdout_2026'],
                      'chosen_wicket':summary['wicket']['selected_name_from_2025_only'],
                      'chosen_batter':summary['batter']['selected_name_from_2025_only']},indent=2))

if __name__=='__main__':main()
