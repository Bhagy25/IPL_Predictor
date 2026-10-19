"""Stage 3: leak-free, auditable next-over wicket training records.

Use completed over checkpoints only. A full following over yields a known Yes/No;
a shortened following over with a witnessed wicket yields a known Yes. A shortened
following over without a wicket is censored (unknown for six-ball horizon).
Outcomes from D/L-marked matches are excluded from this FIRST predictive cohort,
not deleted from the source or Stage 2 dashboard.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd

REQUIRED_OVER = {'match_id','date','season','innings','batting_team','bowling_team',
                 'over_index','legal_balls','runs_after','wickets_after'}
REQUIRED_MATCH = {'match_id','outcome_method','venue_canonical'}


def phase_for_next_over(completed: int) -> str:
    if completed <= 5:
        return 'powerplay'
    if completed <= 14:
        return 'middle'
    return 'death'


def build(overs: pd.DataFrame, matches: pd.DataFrame) -> tuple[pd.DataFrame,dict]:
    if REQUIRED_OVER - set(overs.columns):
        raise ValueError(f'Missing overs columns: {sorted(REQUIRED_OVER-set(overs.columns))}')
    if REQUIRED_MATCH - set(matches.columns):
        raise ValueError(f'Missing match columns: {sorted(REQUIRED_MATCH-set(matches.columns))}')
    if matches.match_id.duplicated().any():
        raise ValueError('Duplicate match IDs')
    match_lookup = matches.set_index('match_id')
    if (~overs.match_id.isin(match_lookup.index)).any():
        raise ValueError('Over references missing match ID')
    rows = []
    count = {'innings_seen':0,'considered_completed_checkpoints':0,
             'excluded_dls_checkpoints':0,'excluded_anomalous_or_gapped':0,
             'censored_no_wicket_short_next_over':0,
             'witnessed_wicket_short_next_over':0,'full_next_over_examples':0}
    # Do not condition on anything from future overs when constructing FEATURES.
    for (mid, inn), group in overs.groupby(['match_id','innings'],sort=False):
        count['innings_seen']+=1
        group=group.sort_values('over_index')
        metadata=match_lookup.loc[mid]
        dls = str(metadata['outcome_method']).strip().upper() in {'D/L','DLS','D/L METHOD','DLS METHOD'}
        previous_total=0
        previous_wickets=0
        previous_index=None
        invalid_history=False
        sequence = list(group.itertuples(index=False))
        for j, cur in enumerate(sequence[:-1]):
            nex=sequence[j+1]
            # An erroneous completed-over length contaminates future time features.
            if cur.legal_balls > 6 or cur.legal_balls < 0:
                invalid_history=True
            adjacent = (nex.over_index==cur.over_index+1 and
                        (previous_index is None or cur.over_index==previous_index+1))
            if not adjacent:
                invalid_history=True
            if cur.legal_balls==6:
                count['considered_completed_checkpoints']+=1
                if dls:
                    count['excluded_dls_checkpoints']+=1
                elif invalid_history or nex.legal_balls>6 or nex.legal_balls<0 or cur.wickets_after>=10 or cur.over_index>=19:
                    count['excluded_anomalous_or_gapped']+=1
                else:
                    witnessed=int(nex.wickets_after>cur.wickets_after)
                    if nex.legal_balls<6 and not witnessed:
                        count['censored_no_wicket_short_next_over']+=1
                    else:
                        if nex.legal_balls<6:
                            count['witnessed_wicket_short_next_over']+=1
                            evidence='observed_wicket_before_short_over_ended'
                        else:
                            count['full_next_over_examples']+=1
                            evidence='complete_six_legal_deliveries'
                        completed=cur.over_index+1
                        rows.append({
                            'match_id':mid,'date':cur.date,'season':int(cur.season),
                            'innings':int(inn),'batting_team':cur.batting_team,
                            'bowling_team':cur.bowling_team,
                            'venue_canonical':metadata['venue_canonical'],
                            'completed_overs':completed,'runs':int(cur.runs_after),
                            'wickets':int(cur.wickets_after),
                            'run_rate':float(cur.runs_after)/completed,
                            'last_over_runs':int(cur.runs_after-previous_total),
                            'last_over_wickets':int(cur.wickets_after-previous_wickets),
                            'phase':phase_for_next_over(completed),
                            'wicket_next_over':witnessed,
                            # These fields exist for AUDIT only; never features!
                            'next_over_legal_balls':int(nex.legal_balls),
                            'label_evidence':evidence,
                        })
            previous_total=int(cur.runs_after)
            previous_wickets=int(cur.wickets_after)
            previous_index=cur.over_index
    result=pd.DataFrame.from_records(rows)
    if result.empty:
        raise ValueError('No eligible next-over examples')
    key=['match_id','innings','completed_overs']
    if result.duplicated(key).any():
        raise ValueError('Duplicated prediction checkpoint')
    if not (result.wicket_next_over.isin([0,1]).all() and result.completed_overs.between(1,19).all()):
        raise ValueError('Invalid labels / checkpoint times')
    if (result.last_over_runs < 0).any() or (result.last_over_wickets<0).any():
        raise ValueError('Negative current-over delta')
    return result, {**count,'eligible_rows':len(result),
                    'eligible_before_2026':int((result.season<2026).sum()),
                    'policy':'exclude D/L-marked matches; observed short-over positives retained; censored negatives excluded'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--overs',type=Path,default=Path('data/processed/overs.csv'))
    p.add_argument('--matches',type=Path,default=Path('data/processed/matches.csv'))
    p.add_argument('--output',type=Path,default=Path('data/processed/stage03_next_over_training.csv'))
    p.add_argument('--audit',type=Path,default=Path('reports/stage_03/session_01/eligibility_summary.json'))
    args=p.parse_args()
    result,summary=build(pd.read_csv(args.overs),pd.read_csv(args.matches))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result.to_csv(args.output,index=False)
    args.audit.parent.mkdir(parents=True,exist_ok=True)
    args.audit.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main()
