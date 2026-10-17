"""Session 02 EDA: synthetic examples, including holdout protection."""
import numpy as np
import pandas as pd
import pytest

from cricketlens.stage02_deep_eda import (
    bootstrap_mean_ci, clustered_mean_ci, season_centered_scores, make_venue_comparison,
    paired_innings_phase, toss_decision_crosstab,
)


def test_bootstrap_mean_constant_and_missing():
    assert bootstrap_mean_ci([5.,5.,5.]) == (5.,5.)
    with pytest.raises(ValueError): bootstrap_mean_ci([])


def test_season_centered_without_peeking_other_seasons():
    df = pd.DataFrame({'season':[2024,2024,2025,2025],
                       'runs':[100,200,180,220],
                       'venue_canonical':['A','B','A','B'],
                       'legal_balls':[120]*4})
    out = season_centered_scores(df)
    assert out.runs_above_season_mean.tolist()==[-50,50,-20,20]
    venues = make_venue_comparison(df,min_n=2)
    assert venues.loc[venues.venue_canonical=='A','season_adjusted_difference_runs'].iat[0]==-35
    assert venues.loc[venues.venue_canonical=='B','season_adjusted_difference_runs'].iat[0]==35


def test_paired_phase_uses_only_innings_reaching_death():
    rows=[]
    for mi, phases in [('x',[(0,6,42),(16,6,70),(17,6,6)]),('y',[(0,6,42)])]:
        for ov,balls,runs in phases:
            rows.append({'match_id':mi,'innings':1,'season':2025,'over_index':ov,
                         'legal_delivery':balls,'runs_total':runs})
    # Using batch totals in this synthetic test (6 legal balls in a row)
    d=pd.DataFrame(rows)
    assert paired_innings_phase(d,min_powerplay_balls=6,min_death_balls=12).match_id.tolist()==['x']
    assert np.isclose(paired_innings_phase(d,min_powerplay_balls=6,min_death_balls=12).death_minus_powerplay.iat[0],-4)


def test_toss_crosstab_excludes_no_result_and_2026():
    df=pd.DataFrame({'season':[2024,2025,2025,2026],
                     'outcome_type':['win','win','no result','win'],
                     'winner':['A','B',None,'A'],
                     'toss_winner':['A','A','A','A'],
                     'toss_decision':['bat','field','bat','bat']})
    t=toss_decision_crosstab(df)
    assert t.matches_with_result.sum()==2
    assert t.loc[t.toss_decision=='bat','toss_winner_won'].iat[0]==1
    assert t.loc[t.toss_decision=='field','toss_winner_lost'].iat[0]==1


def test_cluster_bootstrap_constant_and_shape():
    assert clustered_mean_ci([2, 2, 2], ['a', 'a', 'b']) == (2.0, 2.0)
    with pytest.raises(ValueError): clustered_mean_ci([], [])
