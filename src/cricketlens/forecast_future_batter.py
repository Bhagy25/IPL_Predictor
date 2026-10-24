"""Manual future pre-match batter forecasts from final 2008-2026 artifact.

Only historical completed innings STRICTLY before the supplied match date inform
features; the model is conditional on the chosen batter recording an innings.
This script does NOT check announced playing XI or fetch live fixtures.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import joblib
import pandas as pd
from cricketlens.batter_training_data import _features
from cricketlens.fit_batter_models import positive_probability_three_class


def forecast(*,model_path:Path,batters_path:Path,matches_path:Path,
             batter_id:str,opponent:str,venue:str,batting_team:str,match_date:str):
    target=pd.Timestamp(match_date)
    if not batter_id.strip() or not opponent.strip() or not venue.strip() or not batting_team.strip():
        raise ValueError('A player ID, opponent, batting team and venue are required')
    if opponent==batting_team:
        raise ValueError('Batting team and opponent must differ')
    saved=joblib.load(model_path)
    if saved.get('version')!='deployment_refit_2008_2026' or saved.get('train_end')!=2026:
        raise ValueError('Expected final model refitted on eligible data through 2026')
    bats=pd.read_csv(batters_path)
    matches=pd.read_csv(matches_path)
    needed={'match_id','batter_id','date','runs','bowling_team','venue_canonical'}
    if missing:=needed-set(bats.columns):raise ValueError(f'Missing batting columns: {sorted(missing)}')
    info=matches[['match_id','outcome_method','outcome_type']].copy()
    hist=bats.merge(info,on='match_id',validate='many_to_one')
    bad_dls=hist.outcome_method.fillna('').str.strip().str.upper().isin(['D/L','DLS','D/L METHOD','DLS METHOD'])
    bad_nr=hist.outcome_type.fillna('').str.lower().str.contains('no result',regex=False)
    hist=hist.loc[~bad_dls&~bad_nr & (hist.batter_id.astype(str)==str(batter_id))].copy()
    hist.date=pd.to_datetime(hist.date,errors='raise')
    if hist.empty: raise ValueError('No recorded eligible history for this player ID')
    if target<=hist.date.max():
        raise ValueError('Future-match date must follow the latest eligible innings for this player')
    hist=hist.loc[hist.date<target].sort_values(['date','match_id','innings'])
    history=[(row.date,int(row.runs),row.bowling_team,row.venue_canonical)
             for row in hist.itertuples(index=False)]
    features=_features(history,target,opponent,venue)
    sample=pd.DataFrame([{**features,'batting_team':batting_team,'bowling_team':opponent,
                          'venue_canonical':venue}])
    mdl=saved['model'];classes=mdl.named_steps['model'].classes_
    p=mdl.predict_proba(sample[saved['columns']])
    import numpy as np
    p3=np.zeros((1,3));p3[:,classes.astype(int)]=p
    p30,p50=positive_probability_three_class(p3)
    return {'player_id':batter_id,'player_name':str(hist.batter.iloc[-1]),
            'batting_team':batting_team,'opponent':opponent,'venue':venue,
            'date':target.date().isoformat(),'prior_eligible_innings':len(history),
            'chance_30_plus':round(float(p30[0]),6),
            'chance_50_plus':round(float(p50[0]),6),
            'model_train_end':2026,'version':saved['version'],
            'scope':'conditional on player having a batting innings; playing XI not forecast',
            'warning':'No live data; venue/team inputs must match standardized data values'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model',type=Path,default=Path('models/batter_deployment_through_2026.joblib'))
    p.add_argument('--batters',type=Path,default=Path('data/processed/batter_innings.csv'))
    p.add_argument('--matches',type=Path,default=Path('data/processed/matches.csv'))
    p.add_argument('--player-id',required=True)
    p.add_argument('--batting-team',required=True)
    p.add_argument('--opponent',required=True)
    p.add_argument('--venue',required=True)
    p.add_argument('--date',required=True)
    x=p.parse_args()
    result=forecast(model_path=x.model,batters_path=x.batters,matches_path=x.matches,
                    batter_id=x.player_id,opponent=x.opponent,venue=x.venue,
                    batting_team=x.batting_team,match_date=x.date)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
