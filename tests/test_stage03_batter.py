"""Stage 3 session 2: leakage, eligibility and coherent milestone guarantees."""
from __future__ import annotations
import numpy as np
import pandas as pd
import pytest
from cricketlens.batter_training_data import build
from cricketlens.fit_batter_models import (positive_probability_three_class,
                                            fit_and_validate)


def two_day_data():
    m=pd.DataFrame([
        {'match_id':'A','outcome_method':'','outcome_type':'win'},
        {'match_id':'B','outcome_method':'','outcome_type':'win'},
        {'match_id':'C','outcome_method':'D/L','outcome_type':'win'},
        {'match_id':'D','outcome_method':'','outcome_type':'no result'},
    ])
    def batter(mid,dt,player,pid,runs,op='MI',venue='Wankhede'):
        return {'match_id':mid,'date':dt,'season':2024,'innings':1,
                'batting_team':'CSK','bowling_team':op,'venue_canonical':venue,
                'batter':player,'batter_id':pid,'runs':runs,
                'reached_30':int(runs>=30),'reached_50':int(runs>=50)}
    b=pd.DataFrame([batter('A','2024-01-01','A Name','p1',60),
                    batter('B','2024-01-01','A Name','p1',10),
                    batter('C','2024-01-02','A Name','p1',100),
                    batter('D','2024-01-03','A Name','p1',99)])
    return b,m


def test_same_day_matches_do_not_leak_across_one_another():
    b,m=two_day_data()
    x,_=build(b,m)
    assert len(x)==2
    assert x.prior_innings.tolist()==[0,0]
    changed=b.copy()
    changed.loc[changed.match_id=='A','runs']=15
    changed.loc[changed.match_id=='A','reached_30']=0
    changed.loc[changed.match_id=='A','reached_50']=0
    y,_=build(changed,m)
    # Changes to today's results cannot alter features for another match TODAY.
    features=['prior_innings','career_avg_runs','career_50_rate','recent5_avg_runs']
    assert x.loc[x.match_id=='B',features].reset_index(drop=True).equals(
           y.loc[y.match_id=='B',features].reset_index(drop=True))


def test_dls_no_results_excluded_and_identity_stable():
    b,m=two_day_data()
    x,summary=build(b,m)
    assert summary['excluded_dls_batter_innings']==1
    assert summary['excluded_no_result_batter_innings']==1
    assert summary['eligible_pre2026_batter_innings']==2
    # The player's identity is their stable ID, not just a display name.
    b2=b.iloc[:2].copy()
    b2.loc[b2.match_id=='B','batter_id']='different-person'
    x2,_=build(b2,m)
    assert x2.prior_innings.eq(0).all()


def test_only_past_dates_used_not_future_results():
    b,m=two_day_data()
    b=pd.concat([b, pd.DataFrame([{**b.iloc[0].to_dict(), 'match_id':'F',
                        'date':'2026-04-01','season':2026,'runs':200,
                        'reached_30':1,'reached_50':1}])],ignore_index=True)
    m=pd.concat([m,pd.DataFrame([{'match_id':'F','outcome_method':'','outcome_type':'win'}])],ignore_index=True)
    x,_=build(b,m)
    b.loc[b.match_id=='F','runs']=0
    b.loc[b.match_id=='F','reached_30']=0
    b.loc[b.match_id=='F','reached_50']=0
    y,_=build(b,m)
    pd.testing.assert_frame_equal(x,y)
    assert 2026 not in set(x.season)
    with pytest.raises(ValueError,match='locked holdout'):
        build(b,m,max_development_season=2026)


def test_future_innings_cannot_modify_pre_match_form():
    b,m=two_day_data()
    b=b.iloc[:2].copy()
    b.loc[1,'date']='2024-02-01'
    x,_=build(b,m)
    assert list(x.prior_innings)==[0,1]
    assert x.iloc[1].career_avg_runs==60
    assert x.iloc[1].recent5_50_rate==1
    b.loc[1,'runs']=150
    b.loc[1,'reached_30']=1
    b.loc[1,'reached_50']=1
    y,_=build(b,m)
    assert y.iloc[1].career_avg_runs==60
    assert y.iloc[1].recent5_50_rate==1


def test_milestone_probabilities_monotonic_and_valid():
    arr=np.array([[0.2,0.5,0.3],[0.4,0.6,0.0],[1.0,0,0]])
    p30,p50=positive_probability_three_class(arr)
    np.testing.assert_allclose(p30,[.8,.6,0])
    np.testing.assert_allclose(p50,[.3,0,0])
    assert np.all(p50<=p30)
    with pytest.raises(ValueError,match='three categories'):
        positive_probability_three_class([[.5,.5]],classes=[0,1])


def test_model_rejects_duplicate_match_batter(tmp_path):
    x,_=build(*two_day_data())
    bad=pd.concat([x,x.iloc[:1]],ignore_index=True)
    with pytest.raises(ValueError,match='Duplicate'):
        fit_and_validate(bad,tmp_path)


def test_training_feature_whitelist_has_no_current_match_result():
    from cricketlens.fit_batter_models import FORM_NUM,CONTEXT_CAT
    prohibited={'runs','actual_runs','reached_30','reached_50','milestone_class',
                'balls_faced','dismissed','batting_position_actual'}
    assert not prohibited.intersection(FORM_NUM+CONTEXT_CAT)


def test_actual_outcome_consistency_checked():
    b,m=two_day_data()
    b.loc[0,'reached_50']=0
    with pytest.raises(ValueError,match='do not match'):
        build(b,m)
