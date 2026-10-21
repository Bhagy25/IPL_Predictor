import pandas as pd
import numpy as np
from cricketlens.wicket_training_data import build,phase_for_next_over
from cricketlens.fit_wicket_models import measure


def sample_overs():
    def row(mid,over,legal,runs,wickets):
        return dict(match_id=mid,date='2025-04-01',season=2025,innings=1,
                    batting_team='Mumbai Indians',bowling_team='Chennai Super Kings',
                    over_index=over,legal_balls=legal,runs_after=runs,wickets_after=wickets)
    return pd.DataFrame([
        row('a',0,6,7,0),row('a',1,6,13,1),row('a',2,3,15,2),
        row('b',0,6,5,0),row('b',1,3,12,0),
        row('c',0,6,12,0),row('c',1,6,17,0),
        row('d',0,7,14,0),row('d',1,6,18,1),row('d',2,6,20,1),
        row('e',0,6,11,0),row('e',1,6,16,0),
    ])

def sample_matches():
    return pd.DataFrame({'match_id':['a','b','c','d','e'],
       'venue_canonical':['Wankhede']*5,'outcome_method':[None,None,None,None,'D/L']})

def test_short_positive_counted_and_short_negative_censored():
    data,stats=build(sample_overs(),sample_matches())
    a=data[data.match_id=='a'].sort_values('completed_overs')
    assert list(a.wicket_next_over)==[1,1]
    assert list(a.next_over_legal_balls)==[6,3]
    assert a.iloc[-1].label_evidence=='observed_wicket_before_short_over_ended'
    assert 'b' not in data.match_id.values
    assert stats['censored_no_wicket_short_next_over']==1


def test_dls_removed_anomaly_not_propagated_and_features_past_only():
    data,stats=build(sample_overs(),sample_matches())
    assert set(data.match_id)=={'a','c'}
    assert data[data.match_id=='c'].iloc[0].last_over_runs==12
    assert data[data.match_id=='a'].iloc[1].last_over_runs==6
    assert stats['excluded_dls_checkpoints']>0


def test_next_phase():
    assert phase_for_next_over(5)=='powerplay'
    assert phase_for_next_over(6)=='middle'
    assert phase_for_next_over(14)=='middle'
    assert phase_for_next_over(15)=='death'


def test_metric_reference():
    r=measure(np.array([0,1]),np.array([0.1,0.8]))
    assert abs(r['brier_score']-0.025)<1e-6


def test_predict_rejects_invalid_checkpoint_without_loading_file():
    import pytest
    from pathlib import Path
    from cricketlens.predict_wicket import forecast
    with pytest.raises(ValueError,match='1–19'):
        forecast(Path('not_saved.joblib'),batting_team='MI',bowling_team='CSK',
                 venue='Ground',innings=1,completed_overs=20,runs=100,wickets=4,
                 last_over_runs=7,last_over_wickets=1)


def test_2026_rows_do_not_change_2025_validation(tmp_path,monkeypatch):
    from cricketlens.fit_wicket_models import fit_and_validate
    monkeypatch.chdir(tmp_path)
    records=[]
    for year in (2018,2024,2025):
        for i in range(12):
            records.append({'match_id':f'{year}-{i//3}','season':year,
                            'date':f'{year}-04-01','innings':1,'completed_overs':i%9+1,
                            'runs':i*9+6,'wickets':i%6,'run_rate':float(i+1),
                            'last_over_runs':i%12,'last_over_wickets':i%3,
                            'batting_team':'Mumbai Indians','bowling_team':'Chennai Super Kings',
                            'phase':phase_for_next_over(i%9+1),'venue_canonical':'Wankhede',
                            'wicket_next_over':int(i%4==0)})
    earlier=pd.DataFrame(records)
    a=fit_and_validate(earlier,tmp_path/'result_a')
    # Change the 2026 outcomes drastically: model choice and metrics must remain identical.
    extra=earlier[earlier.season==2025].copy()
    extra['season']=2026
    extra['match_id']=extra['match_id'].str.replace('2025','2026')
    extra['wicket_next_over']=1-extra['wicket_next_over']
    b=fit_and_validate(pd.concat([earlier,extra],ignore_index=True),tmp_path/'result_b')
    assert a['candidate_ranking']==b['candidate_ranking']
    assert a['selected_candidate']==b['selected_candidate']
