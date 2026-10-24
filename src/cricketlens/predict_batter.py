"""Run the saved DEVELOPMENT batter model on a 2025 validation match only.

This script does not forecast 2027; that requires a model refit after the 2026 test.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import joblib
import pandas as pd
from cricketlens.fit_batter_models import positive_probability_three_class


def preview(match_id:str, player_id:str, training_csv:Path,artifact_path:Path):
    data=pd.read_csv(training_csv)
    matched=data.loc[(data.match_id.astype(str)==str(match_id)) &
                     (data.batter_id==player_id)]
    if len(matched)!=1:
        raise ValueError('Expected exactly one match/batter pair; check player ID')
    record=matched.iloc[0]
    if int(record.season)!=2025:
        raise ValueError('This development demo is limited to 2025 validation matches')
    art=joblib.load(artifact_path)
    if art.get('version')!='development' or art.get('train_end')!=2024:
        raise ValueError('Unexpected model artifact version')
    p=art['model'].predict_proba(matched[art['columns']])
    proba=pd.DataFrame(p,columns=art['model'].named_steps['model'].classes_)
    p3=proba.reindex(columns=[0,1,2],fill_value=0).to_numpy()
    p30,p50=positive_probability_three_class(p3)
    return {'batter':record.batter,'date':record.date,'match_id':str(record.match_id),
            'probability_30_plus':round(float(p30[0]),4),
            'probability_50_plus':round(float(p50[0]),4),
            'actual_30':bool(record.reached_30),'actual_50':bool(record.reached_50),
            'actual_runs':int(record.actual_runs),
            'note':'2025 historical out-of-sample validation replay, not a future 2027 forecast'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--match-id',required=True)
    p.add_argument('--player-id',required=True)
    p.add_argument('--input',type=Path,default=Path('data/processed/stage03_batter_training_pre2026.csv'))
    p.add_argument('--model',type=Path,default=Path('models/batter_development_pre2025.joblib'))
    args=p.parse_args()
    import json
    print(json.dumps(preview(args.match_id,args.player_id,args.input,args.model),indent=2))

if __name__=='__main__':main()
