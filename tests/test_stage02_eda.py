import numpy as np
import pandas as pd
from cricketlens.stage02_eda import describe, standardized_phase, variance_inflation_factors, development_only


def test_describe_five_number_and_mad():
    d = describe(pd.Series([1, 2, 2, 4, 7]))
    assert d['count'] == 5
    assert d['median'] == 2
    assert d['mode_smallest'] == 2
    assert d['min'] == 1 and d['max'] == 7
    assert d['iqr'] == 2  # Q1=2, Q3=4
    assert d['median_abs_deviation'] == 1
    assert np.isclose(d['mean'],3.2)


def test_phase_mapping():
    actual = standardized_phase(pd.Series([0,5,6,15,16,19,20])).astype(str).tolist()
    assert actual == ['Powerplay (1-6)','Powerplay (1-6)','Middle (7-16)',
                      'Middle (7-16)','Death (17-20)','Death (17-20)','nan']


def test_vif_independent():
    a = pd.DataFrame({'x':[0,1,2,3,4,5], 'y':[1,4,0,2,5,3]})
    v = variance_inflation_factors(a)
    assert 1 <= v['x'] < 5 and 1 <= v['y'] < 5


def test_holdout_2026_is_excluded():
    df=pd.DataFrame({"season":[2024,2025,2026], "outcome":[1,0,1]})
    assert development_only(df).season.tolist()==[2024,2025]
