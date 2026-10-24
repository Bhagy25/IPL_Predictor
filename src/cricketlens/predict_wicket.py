"""Manual next-over forecast from chosen saved development or deployment model."""
from __future__ import annotations
import argparse
from pathlib import Path
import joblib
import pandas as pd
from cricketlens.wicket_training_data import phase_for_next_over


def forecast(model_path:Path, *,batting_team:str,bowling_team:str,venue:str,
             innings:int,completed_overs:int,runs:int,wickets:int,
             last_over_runs:int,last_over_wickets:int) -> dict:
    if not 1<=completed_overs<=19:
        raise ValueError('Predictions require 1–19 completed overs')
    if innings not in (1,2) or not 0<=wickets<10 or runs<0:
        raise ValueError('Invalid innings, wickets or runs')
    if not 0<=last_over_runs<=runs or not 0<=last_over_wickets<=wickets:
        raise ValueError('Invalid most-recent-over runs / wickets')
    if not batting_team or not bowling_team or batting_team==bowling_team or not venue:
        raise ValueError('Please supply distinct teams and a venue')
    # Accept a development or explicitly refitted deployment artifact.
    saved=joblib.load(model_path)
    x=pd.DataFrame([{
        'batting_team':batting_team,'bowling_team':bowling_team,
        'venue_canonical':venue,'innings':innings,
        'completed_overs':completed_overs,'runs':runs,'wickets':wickets,
        'run_rate':runs/completed_overs,
        'last_over_runs':last_over_runs,'last_over_wickets':last_over_wickets,
        'phase':phase_for_next_over(completed_overs)}])
    prob=float(saved['model'].predict_proba(x[saved['columns']])[:,1][0])
    version=saved.get('version','development')
    return {'event':'at least one team wicket in the next scheduled over',
            'probability':round(prob,4),'model':saved['name'],
            'training_end':saved['training_end'],
            'status':('deployment_refit' if version=='deployment_refit_2008_2026' else
                      'development_or_holdout_demo'),
            'notice':'Manual score input; not a live-data feed'}


def main():
    p=argparse.ArgumentParser(description='Demo prediction: one wicket next over')
    p.add_argument('--model',type=Path,default=Path('models/wicket_development_pre2025.joblib'))
    p.add_argument('--batting-team',required=True)
    p.add_argument('--bowling-team',required=True)
    p.add_argument('--venue',required=True)
    p.add_argument('--innings',type=int,choices=[1,2],required=True)
    p.add_argument('--completed-overs',type=int,required=True)
    p.add_argument('--runs',type=int,required=True)
    p.add_argument('--wickets',type=int,required=True)
    p.add_argument('--last-over-runs',type=int,required=True)
    p.add_argument('--last-over-wickets',type=int,required=True)
    args=p.parse_args()
    import json
    print(json.dumps(forecast(args.model,batting_team=args.batting_team,
        bowling_team=args.bowling_team,venue=args.venue,
        innings=args.innings,completed_overs=args.completed_overs,
        runs=args.runs,wickets=args.wickets,
        last_over_runs=args.last_over_runs,last_over_wickets=args.last_over_wickets),indent=2))

if __name__=='__main__':main()
