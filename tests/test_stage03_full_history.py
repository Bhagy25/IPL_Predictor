"""Stage 3 Session 3 regression tests for chronological features and deployment."""
import pandas as pd
import numpy as np
import joblib
import pytest
from cricketlens.batter_training_data import build
from cricketlens.fit_batter_models import positive_probability_three_class
from cricketlens.stage03_full_history import _triple


def test_holdout_2026_explicit_unlock_and_no_2025_feature_leakage():
    matches=pd.DataFrame({'match_id':['a','b','c'],
        'outcome_method':['','',''],'outcome_type':['win']*3})
    def rec(mid,yr,run):
        return {'match_id':mid,'date':f'{yr}-04-01','season':yr,'innings':1,
                'batting_team':'CSK','bowling_team':'MI','venue_canonical':'Wankhede',
                'batter':'A','batter_id':'p1','runs':run,
                'reached_30':int(run>=30),'reached_50':int(run>=50)}
    bats=pd.DataFrame([rec('a',2024,50),rec('b',2025,40),rec('c',2026,70)])
    with pytest.raises(ValueError,match='locked'):
        build(bats,matches,max_development_season=2026)
    all_rows,_=build(bats,matches,max_development_season=2026,allow_2026=True)
    pre,_=build(bats,matches,max_development_season=2025)
    pd.testing.assert_frame_equal(all_rows[all_rows.season<=2025].reset_index(drop=True),
                                  pre.reset_index(drop=True))
    assert all_rows.loc[all_rows.season==2026,'prior_innings'].iloc[0]==2
    bats.loc[bats.season==2026,'runs']=1
    bats.loc[bats.season==2026,'reached_30']=0
    bats.loc[bats.season==2026,'reached_50']=0
    changed,_=build(bats,matches,max_development_season=2026,allow_2026=True)
    assert all_rows.loc[all_rows.season==2026,'career_avg_runs'].iloc[0]==changed.loc[changed.season==2026,'career_avg_runs'].iloc[0]


def test_p50_never_exceeds_p30():
    p=np.array([[0.6,0.25,0.15],[0.1,0.3,0.6]])
    p30,p50=positive_probability_three_class(p)
    assert (p50<=p30).all()


def test_final_serialized_models_are_2026_refits_if_available():
    from pathlib import Path
    folder=Path(__file__).parents[1]/'models'
    a=folder/'batter_deployment_through_2026.joblib'
    b=folder/'wicket_deployment_through_2026.joblib'
    if not (a.exists() and b.exists()):
        pytest.skip('Local generated model artifacts not present; ignored by git')
    ma=joblib.load(a);mw=joblib.load(b)
    assert ma['train_end']==2026
    assert mw['training_end']==2026
    assert ma['version']==mw['version']=='deployment_refit_2008_2026'
    assert 'actual_runs' not in ma['columns']
    assert 'wicket_next_over' not in mw['columns']
