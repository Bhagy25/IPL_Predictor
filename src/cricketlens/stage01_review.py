"""Stage 1 *source-level* quality audit: no predictive fitting, no 2026 leakage.

Run against the original Cricsheet JSON ZIP, not previously produced CSV files.
Keeps anomalies for transparent review rather than deleting match data.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from cricketlens.pipeline import read_matches
from cricketlens.venues import canonical_venue


def write_rows(path: Path, records: list[dict], columns: list[str]):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)


def review(source: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    defects, cities, extra_samples = [], [], []
    venue_usage, gender, competitions, dismissal, extra_types, innings_count = (Counter() for _ in range(6))
    name_ids = defaultdict(set)
    match_count = 0
    zero_ball_overs = seven_ball_overs = super_over_count = dls_count = 0
    win_tie_no_result = Counter()
    extra_events = Counter()
    records_with_invalid_delivery_totals = 0
    records_with_negative_runs = 0
    duplicate_match_ids = 0
    seen_ids = set()
    for fname, match in read_matches(source):
        match_count += 1
        mid = Path(fname).stem
        if mid in seen_ids:
            duplicate_match_ids += 1
        seen_ids.add(mid)
        info = match['info']
        gender[str(info.get('gender', ''))] += 1
        competitions[str((info.get('event') or {}).get('name', ''))] += 1
        venue_usage[info.get('venue') or ''] += 1
        outcome = info.get('outcome') or {}
        win_tie_no_result['no_result' if outcome.get('result') == 'no result' else
                          'tie' if outcome.get('result') == 'tie' or 'eliminator' in outcome else
                          'winner_recorded' if outcome.get('winner') else 'other'] += 1
        if (outcome.get('method') or '').upper() in {'D/L', 'DLS'}:
            dls_count += 1
        if not info.get('city'):
            cities.append({'match_id': mid, 'venue': info.get('venue') or '', 'reason': 'city_missing_in_source'})
        for person, pid in ((info.get('registry') or {}).get('people') or {}).items():
            name_ids[person].add(pid)
        ordinary = [inn for inn in match.get('innings', []) if not inn.get('super_over')]
        super_over_count += len(match.get('innings', [])) - len(ordinary)
        innings_count[len(ordinary)] += 1
        for inn_idx, inn in enumerate(ordinary, 1):
            overs = inn.get('overs') or []
            numbers = [o.get('over') for o in overs]
            if numbers != list(range(len(numbers))):
                defects.append({'match_id': mid, 'innings': inn_idx, 'over_index': '',
                                'issue': 'nonsequential_over_indices', 'detail': repr(numbers)})
            for over in overs:
                legal = 0
                for ball in over.get('deliveries') or []:
                    runs = ball.get('runs') or {}
                    extras = ball.get('extras') or {}
                    extra_types.update(extras)  # Counter totals: numeric runs, NOT event counts.
                    extra_events.update(extras.keys())
                    legal += int('wides' not in extras and 'noballs' not in extras)
                    for w in ball.get('wickets') or []:
                        dismissal[w.get('kind', '')] += 1
                    if int(runs.get('batter', 0)) + int(runs.get('extras', 0)) != int(runs.get('total', 0)):
                        records_with_invalid_delivery_totals += 1
                    if any(int(v) < 0 for v in runs.values()):
                        records_with_negative_runs += 1
                    if 'penalty' in extras:
                        extra_samples.append({'match_id': mid, 'innings': inn_idx,
                                              'over_index': over.get('over'), 'penalty_runs': extras['penalty']})
                if legal == 0 or legal > 6:
                    defect = {'match_id': mid, 'innings': inn_idx, 'over_index': over.get('over'),
                              'issue': 'zero_legal_balls' if legal == 0 else 'over_six_legal_balls',
                              'detail': f'legal={legal}; deliveries={len(over.get("deliveries") or [])}'}
                    defects.append(defect)
                    if legal == 0:
                        zero_ball_overs += 1
                    else:
                        seven_ball_overs += 1
    collisions = [{'name': name, 'id_count': len(ids), 'ids': ' | '.join(sorted(ids))}
                  for name, ids in sorted(name_ids.items()) if len(ids) > 1]
    venues = [{'venue_raw': key, 'venue_canonical': canonical_venue(key), 'match_count': cnt,
               'changed': int(key != canonical_venue(key))} for key, cnt in sorted(venue_usage.items())]
    write_rows(out / 'raw_over_anomalies.csv', defects, ['match_id', 'innings', 'over_index', 'issue', 'detail'])
    write_rows(out / 'missing_city_cases.csv', cities, ['match_id', 'venue', 'reason'])
    write_rows(out / 'venue_alias_review.csv', venues, ['venue_raw', 'venue_canonical', 'match_count', 'changed'])
    write_rows(out / 'player_name_id_collisions.csv', collisions, ['name', 'id_count', 'ids'])
    write_rows(out / 'penalty_extras.csv', extra_samples, ['match_id', 'innings', 'over_index', 'penalty_runs'])
    result = {
        'archive_matches': match_count,
        'gender': dict(gender), 'competition': dict(competitions),
        'ordinary_innings_by_match': {str(k): v for k, v in sorted(innings_count.items())},
        'super_over_innings': super_over_count,
        'match_outcome_types': dict(win_tie_no_result), 'matches_with_DLS_or_DL': dls_count,
        'distinct_raw_venue_strings': len(venue_usage),
        'distinct_canonical_venue_strings': len({v['venue_canonical'] for v in venues}),
        'raw_venue_aliases_rewritten': sum(v['changed'] for v in venues),
        'matches_with_venue_aliases': sum(v['match_count'] for v in venues if v['changed']),
        'missing_city_match_count': len(cities),
        'missing_city_by_venue': dict(Counter(x['venue'] for x in cities)),
        'overs_with_zero_legal_balls': zero_ball_overs,
        'overs_with_more_than_six_legal_balls': seven_ball_overs,
        'duplicate_match_ids': duplicate_match_ids,
        'nonconsecutive_over_sequences': sum(x['issue'] == 'nonsequential_over_indices' for x in defects),
        'delivery_run_total_mismatches': records_with_invalid_delivery_totals,
        'negative_run_fields': records_with_negative_runs,
        'extra_runs_by_type': dict(extra_types), 'extra_events_by_type': dict(extra_events),
        'dismissal_kinds': dict(dismissal),
        'player_names_with_multiple_ids': collisions,
        'notes': [
            'Source missing city for Dubai and Sharjah is not filled without evidence. Treat as source missingness, not automatically MCAR.',
            'A seven-legal-ball over indicates a source coding anomaly requiring investigation; do not force it to six.',
            'Zero-legal-ball final over can legitimately occur when a chase ends on a wide.',
            'Canonical venue aliases use exact documented mappings while raw values are preserved.',
            'Name ambiguity requires batter_id (person registry) for consistent player features.',
            'DLS matches and censored over horizons need explicit eligibility decisions before final ML training.',
            'This report is a source-quality review; no attempt to claim missingness mechanisms are identifiable from data alone.',
        ],
    }
    (out / 'source_audit_summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main():
    p = argparse.ArgumentParser(description='Review original Cricsheet IPL match JSON quality')
    p.add_argument('source', type=Path)
    p.add_argument('--output', type=Path, default=Path('reports/stage_01'))
    args = p.parse_args()
    print(json.dumps(review(args.source, args.output), indent=2))


if __name__ == '__main__':
    main()
