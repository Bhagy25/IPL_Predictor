import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from cricketlens.pipeline import extract
from cricketlens.stage02_final_eda import check_match_outcomes, team_win_comparison


@pytest.fixture
def scenarios(tmp_path):
    root=Path(__file__).parent/'fixtures'/'example_match.json'
    base=json.loads(root.read_text())
    outcomes={
        'tie': {'result':'tie','eliminator':'Delhi Daredevils'},
        'rain': {'winner':'Delhi Daredevils','method':'D/L'},
        'abandoned': {'result':'no result'},
    }
    dest=tmp_path/'cases.zip'
    with ZipFile(dest,'w') as z:
        for i,(name,outcome) in enumerate(outcomes.items()):
            case=json.loads(json.dumps(base))
            case['info']['outcome']=outcome
            case['info']['dates']=['2025-04-%02d'%(i+1)]
            if name=='tie':
                second=json.loads(json.dumps(case['innings'][0]))
                second['team']='Mumbai Indians'
                case['innings'].append(second)
                case['innings'].extend([
                    {'team':'Delhi Daredevils','super_over':True,'overs':[]},
                    {'team':'Mumbai Indians','super_over':True,'overs':[]},
                ])
            z.writestr(name+'.json',json.dumps(case))
    return dest


def test_tie_final_winner_separate_from_regulation_result(scenarios):
    rows=extract(scenarios)
    m={r['match_id']:r for r in rows['matches']}
    assert m['tie']['winner']==''
    assert m['tie']['final_winner']=='Delhi Capitals'
    assert m['tie']['super_over_winner']=='Delhi Capitals'
    assert m['tie']['outcome_type']=='tie'
    assert m['tie']['regulation_result']=='tie'
    assert m['tie']['super_over_innings']==2
    assert m['tie']['decided_by']=='super_over'
    assert m['rain']['final_winner']=='Delhi Capitals'
    assert m['rain']['outcome_method']=='D/L'
    assert m['abandoned']['final_winner']==''
    assert m['abandoned']['regulation_result']=='no result'
    # Super Over deliveries/innings are not part of ordinary batting and bowling.
    assert len([x for x in rows['innings'] if x['match_id']=='tie']) == 2


def test_quality_check_rejects_wrong_superover_winner():
    df=pd.DataFrame([dict(season=2025,team1='A',team2='B',winner=None,
          final_winner='A',regulation_result='tie',outcome_type='tie',
          super_over_winner='B',super_over_innings=2,decided_by='super_over',outcome_method=None)])
    with pytest.raises(ValueError,match='Final winner'):
        check_match_outcomes(df)


def test_team_win_comparison_includes_super_over_win():
    df=pd.DataFrame([
        dict(season=2025,match_id='a',team1='Delhi Capitals',team2='Mumbai Indians',
             outcome_type='tie',winner=None,final_winner='Delhi Capitals'),
        dict(season=2025,match_id='b',team1='Delhi Capitals',team2='Mumbai Indians',
             outcome_type='win',winner='Mumbai Indians',final_winner='Mumbai Indians'),
    ])
    g=team_win_comparison(df).set_index('team')
    assert g.loc['Delhi Capitals','wins_regulation_only']==0
    assert g.loc['Delhi Capitals','wins_including_super_overs']==1
    assert g.loc['Mumbai Indians','wins_including_super_overs']==1
