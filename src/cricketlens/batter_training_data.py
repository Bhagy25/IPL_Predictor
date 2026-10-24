"""Leakage-safe pre-match batter milestone features (Stage 3, Session 2).

Targets: >=30 and >=50 runs conditional on an observed batting innings.
One feature snapshot per batter/match, computed from matches dated STRICTLY before
that match. Same-calendar-date matches never inform one another.

In the initial development cohort, D/L-marked and no-result matches are excluded
from both examples and form histories. The raw/EDA tables are not modified.
No data from the 2026 held-out season is read when running the development CLI.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
import json
import numpy as np
import pandas as pd

NEEDED_BAT = {'match_id','date','season','innings','batting_team','bowling_team',
              'venue_canonical','batter','batter_id','runs','reached_30','reached_50'}
NEEDED_MATCH = {'match_id','outcome_method','outcome_type'}


def _average(values):
    return float(np.mean(values)) if len(values) else 0.0


def _rate(values, threshold):
    return _average([v>=threshold for v in values])


def _features(history: list[tuple], current_date: pd.Timestamp,
              opponent: str, venue: str) -> dict:
    # History: (date, runs, opponent, venue). Only strictly earlier dates.
    past = [r[1] for r in history]
    recent = past[-5:]
    recent10 = past[-10:]
    vs_opponent = [r[1] for r in history if r[2] == opponent]
    at_venue = [r[1] for r in history if r[3] == venue]
    return {
        'prior_innings': len(past),
        'career_avg_runs': _average(past),
        'career_30_rate': _rate(past,30),
        'career_50_rate': _rate(past,50),
        'recent5_avg_runs': _average(recent),
        'recent5_30_rate': _rate(recent,30),
        'recent5_50_rate': _rate(recent,50),
        'recent10_avg_runs': _average(recent10),
        'recent10_30_rate': _rate(recent10,30),
        'recent10_50_rate': _rate(recent10,50),
        'opposition_prior_innings': len(vs_opponent),
        'opposition_avg_runs': _average(vs_opponent),
        'opposition_30_rate': _rate(vs_opponent,30),
        'venue_prior_innings': len(at_venue),
        'venue_avg_runs': _average(at_venue),
        'venue_30_rate': _rate(at_venue,30),
        'days_since_previous_innings': (
            min((current_date-history[-1][0]).days,3650) if history else 3650
        ),
    }


def build(batters: pd.DataFrame, matches: pd.DataFrame, max_development_season: int=2025, *, allow_2026: bool=False):
    if NEEDED_BAT-set(batters.columns):
        raise ValueError(f'Missing batter columns: {sorted(NEEDED_BAT-set(batters.columns))}')
    if NEEDED_MATCH-set(matches.columns):
        raise ValueError(f'Missing match columns: {sorted(NEEDED_MATCH-set(matches.columns))}')
    if matches.match_id.duplicated().any():
        raise ValueError('Duplicate match IDs in match metadata')
    if max_development_season > 2025 and not (allow_2026 and max_development_season == 2026):
        raise ValueError('2026 is a locked holdout during Session 2 unless explicitly unlocked for final evaluation')

    # Filter first: the held-out 2026 season is never used even for form building.
    raw = batters.loc[batters.season<=max_development_season].copy()
    meta = matches.loc[:,['match_id','outcome_method','outcome_type']].copy()
    raw = raw.merge(meta, on='match_id',validate='many_to_one',indicator=True)
    if (raw._merge!='both').any():
        raise ValueError('Batter innings missing match metadata')
    if raw.batter_id.isna().any() or (raw.batter_id.astype(str).str.strip()=='').any():
        raise ValueError('Batter IDs missing; cannot safely merge same-named players')
    if raw.duplicated(['match_id','innings','batter_id']).any():
        raise ValueError('Duplicate batter match-innings')
    raw['date'] = pd.to_datetime(raw['date'], errors='raise')
    dls = raw.outcome_method.fillna('').astype(str).str.strip().str.upper().isin(['D/L','DLS','D/L METHOD','DLS METHOD'])
    no_result = raw.outcome_type.fillna('').astype(str).str.lower().str.contains('no result',regex=False)
    eligible=raw.loc[~(dls|no_result)].copy()
    if eligible.empty:
        raise ValueError('No eligible batting innings')
    if not ((eligible.runs>=0).all() and eligible.reached_30.isin([0,1]).all() and eligible.reached_50.isin([0,1]).all()):
        raise ValueError('Invalid batter runs or milestone flags')
    if not ((eligible.reached_30==(eligible.runs>=30)).all() and (eligible.reached_50==(eligible.runs>=50)).all()):
        raise ValueError('Milestone targets do not match actual runs')
    # 3 exclusive outcomes -> one coherent probability distribution after fitting.
    eligible['milestone_class'] = np.select([eligible.runs>=50,eligible.runs>=30],[2,1],default=0).astype(int)
    history: dict[str,list[tuple]] = defaultdict(list)
    rows=[]
    # Every batter playing on the same date sees the SAME historical cutoff.
    for day, dated in eligible.sort_values(['date','match_id','innings','batter_id']).groupby('date',sort=True):
        for row in dated.itertuples(index=False):
            h=history[row.batter_id]
            record={
                'match_id':row.match_id,'date':day.strftime('%Y-%m-%d'),
                'season':int(row.season),'innings':int(row.innings),
                'batter_id':row.batter_id,'batter':row.batter,
                'batting_team':row.batting_team,'bowling_team':row.bowling_team,
                'venue_canonical':row.venue_canonical,
                **_features(h,day,row.bowling_team,row.venue_canonical),
                'milestone_class':int(row.milestone_class),
                'reached_30':int(row.reached_30),'reached_50':int(row.reached_50),
                'actual_runs':int(row.runs), # AUDIT ONLY - never a model feature
            }
            rows.append(record)
        # Only after computing all of today's features do we learn today's runs.
        for row in dated.itertuples(index=False):
            history[row.batter_id].append((day,int(row.runs),row.bowling_team,row.venue_canonical))
    result=pd.DataFrame.from_records(rows)
    if result.duplicated(['match_id','innings','batter_id']).any():
        raise ValueError('Repeated player/match prediction records')
    summary={
      'all_rows_in_pre2026_raw':int(len(raw)),
      'excluded_dls_batter_innings':int(dls.sum()),
      'excluded_no_result_batter_innings':int((~dls&no_result).sum()),
      'eligible_pre2026_batter_innings':int(len(result)),
      'development_train_rows_through_2024':int((result.season<=2024).sum()),
      'development_validation_rows_2025':int((result.season==2025).sum()),
      'cold_start_rows_no_prior_innings':int((result.prior_innings==0).sum()),
      'unique_batters':int(result.batter_id.nunique()),
      'target_class_counts':{str(k):int(v) for k,v in result.milestone_class.value_counts().sort_index().items()},
      'policy': 'exclude D/L and no-result matches in this first model cohort; same-date history excluded; batting appearance conditioned',
      'holdout': ('2026 unlocked for one-time final testing and later refit' if allow_2026 else
                  '2026 never accessed for feature building, tuning or validation'),
    }
    return result,summary


def main():
    p=argparse.ArgumentParser(description='Construct pre-match historical batter form with no future leakage')
    p.add_argument('--batters',type=Path,default=Path('data/processed/batter_innings.csv'))
    p.add_argument('--matches',type=Path,default=Path('data/processed/matches.csv'))
    p.add_argument('--output',type=Path,default=Path('data/processed/stage03_batter_training_pre2026.csv'))
    p.add_argument('--audit',type=Path,default=Path('reports/stage_03/session_02/batter_eligibility.json'))
    args=p.parse_args()
    rows,summary=build(pd.read_csv(args.batters),pd.read_csv(args.matches))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    rows.to_csv(args.output,index=False)
    args.audit.parent.mkdir(parents=True,exist_ok=True)
    args.audit.write_text(json.dumps(summary,indent=2),encoding='utf8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
