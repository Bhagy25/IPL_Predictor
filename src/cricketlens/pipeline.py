"""Auditable Cricsheet IPL JSON extraction; no model fitting happens here.

Inputs: directory of .json files or Cricsheet JSON .zip. Outputs: CSVs.
Delivery facts are normalized without using information from future overs.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from zipfile import ZipFile

# Only genuine franchise renames; DO NOT merge Gujarat Lions with Gujarat Titans.
RENAMES = {
    'Delhi Daredevils': 'Delhi Capitals',
    'Kings XI Punjab': 'Punjab Kings',
    'Royal Challengers Bangalore': 'Royal Challengers Bengaluru',
    'Rising Pune Supergiants': 'Rising Pune Supergiant',  # Same discontinued franchise, genuine name change.
}
NO_TEAM_WICKET = {'retired hurt', 'retired not out'}


def franchise(name: str) -> str:
    return RENAMES.get(name, name)


def read_matches(source: Path):
    """Yield (filename, decoded match), streaming zip members one by one."""
    if source.is_dir():
        for file in sorted(source.rglob('*.json')):
            yield file.name, json.loads(file.read_text(encoding='utf-8'))
    elif source.suffix.lower() == '.zip':
        with ZipFile(source) as archive:
            for filename in sorted(archive.namelist()):
                if filename.lower().endswith('.json') and not filename.startswith('__MACOSX/'):
                    try:
                        with archive.open(filename) as f:
                            match = json.load(f)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        raise ValueError(f'Invalid JSON in {filename}') from None
                    if isinstance(match, dict) and 'innings' in match and 'info' in match:
                        yield Path(filename).name, match
    else:
        raise ValueError('Source must be a directory of Cricsheet JSON files or a .zip')


def extract(source: Path):
    matches, deliveries, checkpoints, batters, issues = [], [], [], [], []
    innings_rows, over_rows_all = [], []
    seen_ids = set()
    for filename, match in read_matches(source):
        info = match.get('info', {})
        # Cricsheet competition is usually info.event.name; zip is already IPL-only.
        raw_dates = info.get('dates') or []
        if not raw_dates:
            issues.append({'match_id': Path(filename).stem, 'issue': 'missing_dates'})
            continue
        try:
            match_date = date.fromisoformat(str(raw_dates[0])[:10])
        except ValueError:
            issues.append({'match_id': Path(filename).stem, 'issue': 'invalid_date'})
            continue
        match_id = Path(filename).stem
        if match_id in seen_ids:
            issues.append({'match_id': match_id, 'issue': 'duplicate_match_id'})
            continue
        seen_ids.add(match_id)
        raw_teams = info.get('teams') or []
        if len(raw_teams) != 2:
            issues.append({'match_id': match_id, 'issue': 'invalid_team_list'})
            continue
        teams = list(map(franchise, raw_teams))
        player_registry = ((info.get('registry') or {}).get('people') or {})
        outcome = info.get('outcome') or {}
        matches.append({
            'match_id': match_id, 'date': match_date.isoformat(),
            'season': match_date.year, 'team1': teams[0], 'team2': teams[1],
            'venue': info.get('venue') or '', 'city': info.get('city') or '',
            'event': (info.get('event') or {}).get('name', ''),
            'gender': info.get('gender', ''),
            'winner': franchise(outcome.get('winner', '')) if outcome.get('winner') else '',
            'outcome_type': ('tie' if 'eliminator' in outcome or outcome.get('result') == 'tie'
                             else outcome.get('result', 'win' if outcome.get('winner') else 'unknown')),
            'outcome_method': outcome.get('method', ''),
            'toss_winner': franchise((info.get('toss') or {}).get('winner', ''))
                           if (info.get('toss') or {}).get('winner') else '',
            'toss_decision': (info.get('toss') or {}).get('decision', ''),
        })
        for innings_pos, innings in enumerate(match.get('innings') or [], start=1):
            if innings.get('super_over') is True:
                continue
            # IPL's ordinary match has two batting innings; no super-over replay.
            if innings_pos > 2:
                issues.append({'match_id': match_id, 'issue': 'unusual_extra_innings'})
                continue
            batting_team = franchise(innings.get('team', ''))
            if batting_team not in teams:
                issues.append({'match_id': match_id, 'issue': 'innings_team_not_in_match'})
                continue
            bowling_team = teams[1] if batting_team == teams[0] else teams[0]
            total_runs, wickets, innings_legal = 0, 0, 0
            batter_runs = defaultdict(int)
            batter_balls = defaultdict(int)
            batter_dismissed = defaultdict(int)
            over_rows = []
            for over in innings.get('overs') or []:
                over_number = over.get('over')
                if not isinstance(over_number, int) or over_number < 0:
                    issues.append({'match_id': match_id, 'issue': 'invalid_over'})
                    continue
                legal = 0
                for delivery_position, ball in enumerate(over.get('deliveries') or [], start=1):
                    r = ball.get('runs') or {}
                    extras = ball.get('extras') or {}
                    is_legal = 'wides' not in extras and 'noballs' not in extras
                    legal += int(is_legal)
                    innings_legal += int(is_legal)
                    total_runs += int(r.get('total', 0))
                    batter_name = ball.get('batter', '')
                    if batter_name:
                        batter_runs[batter_name] += int(r.get('batter', 0))
                        # A no-ball is faced by the batter; wides are not faced.
                        batter_balls[batter_name] += int('wides' not in extras)
                    team_wickets = 0
                    for wicket in ball.get('wickets') or []:
                        if wicket.get('kind', '').lower() not in NO_TEAM_WICKET:
                            team_wickets += 1
                            batter_dismissed[wicket.get('player_out', '')] += 1
                    wickets += team_wickets
                    deliveries.append({
                        'match_id': match_id, 'date': match_date.isoformat(),
                        'season': match_date.year, 'innings': innings_pos,
                        'batting_team': batting_team, 'bowling_team': bowling_team,
                        'over_index': over_number, 'delivery_index': delivery_position,
                        'batter': batter_name, 'batter_id': player_registry.get(batter_name, ''),
                        'bowler': ball.get('bowler', ''), 'runs_batter': int(r.get('batter', 0)),
                        'runs_extras': int(r.get('extras', 0)), 'runs_total': int(r.get('total', 0)),
                        'wides': int(extras.get('wides', 0)), 'noballs': int(extras.get('noballs', 0)),
                        'byes': int(extras.get('byes', 0)), 'legbyes': int(extras.get('legbyes', 0)),
                        'legal_delivery': int(is_legal), 'team_wickets_on_ball': team_wickets,
                        'innings_runs_after': total_runs, 'innings_wickets_after': wickets,
                    })
                over_rows.append({
                    'over_index': over_number, 'legal_balls': legal, 'runs_after': total_runs,
                    'wickets_after': wickets,
                })
                over_rows_all.append({
                    'match_id': match_id, 'date': match_date.isoformat(), 'season': match_date.year,
                    'innings': innings_pos, 'batting_team': batting_team,
                    'bowling_team': bowling_team, 'over_index': over_number,
                    'legal_balls': legal, 'runs_after': total_runs, 'wickets_after': wickets,
                    'complete_standard_over': int(legal == 6),
                })
                if legal > 6:
                    issues.append({'match_id': match_id, 'issue': 'more_than_six_legal_balls'})
                elif legal == 0:
                    issues.append({'match_id': match_id, 'issue': 'zero_legal_balls_in_recorded_over'})
            innings_rows.append({
                'match_id': match_id, 'date': match_date.isoformat(), 'season': match_date.year,
                'innings': innings_pos, 'batting_team': batting_team, 'bowling_team': bowling_team,
                'venue': info.get('venue') or '', 'runs': total_runs, 'wickets': wickets,
                'legal_balls': innings_legal, 'overs_recorded': len(over_rows),
            })
            for bname, bruns in batter_runs.items():
                batters.append({
                    'match_id': match_id, 'date': match_date.isoformat(), 'season': match_date.year,
                    'innings': innings_pos, 'batting_team': batting_team,
                    'bowling_team': bowling_team, 'venue': info.get('venue') or '',
                    'batter': bname, 'batter_id': player_registry.get(bname, ''),
                    'runs': bruns, 'balls_faced': batter_balls[bname],
                    'dismissed': int(bool(batter_dismissed[bname])),
                    'reached_30': int(bruns >= 30), 'reached_50': int(bruns >= 50),
                })
            # Training snapshots are produced only at FULLY COMPLETED overs.
            # If the following over ends early because all 10 wickets fell, outcome is
            # known to be positive; otherwise the shortened horizon is censored.
            for current, future in zip(over_rows, over_rows[1:]):
                if current['legal_balls'] != 6:
                    continue
                if future['over_index'] != current['over_index'] + 1:
                    issues.append({'match_id': match_id, 'issue': 'nonconsecutive_overs'})
                    continue
                if future['legal_balls'] > 6:
                    issues.append({'match_id': match_id, 'issue': 'invalid_next_over_length'})
                    continue
                positive = int(future['wickets_after'] > current['wickets_after'])
                full_horizon = future['legal_balls'] == 6
                terminal_all_out = future['wickets_after'] >= 10 and positive
                if not full_horizon and not terminal_all_out:
                    issues.append({'match_id': match_id, 'issue': 'censored_next_over'})
                    continue
                completed_overs = current['over_index'] + 1
                checkpoints.append({
                    'match_id': match_id, 'date': match_date.isoformat(), 'season': match_date.year,
                    'innings': innings_pos, 'batting_team': batting_team,
                    'bowling_team': bowling_team, 'venue': info.get('venue') or '',
                    'completed_overs': completed_overs,
                    'runs': current['runs_after'], 'wickets': current['wickets_after'],
                    'run_rate': round(current['runs_after'] / completed_overs, 4),
                    'wicket_next_over': positive,
                    'next_over_legal_balls': future['legal_balls'],
                })
    return {'matches': matches, 'innings': innings_rows, 'overs': over_rows_all,
            'deliveries': deliveries,
            'next_over_samples': checkpoints, 'batter_innings': batters,
            'screening_issues': issues}


def write_csvs(tables: dict, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    for name, records in tables.items():
        if not records:
            # Keep issue table readable when the source has zero flagged records.
            schema = ['match_id', 'issue'] if name == 'screening_issues' else []
            (output / f'{name}.csv').write_text(','.join(schema) + ('\n' if schema else ''), encoding='utf-8')
            continue
        with (output / f'{name}.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    return {name: len(rows) for name, rows in tables.items()}


def main():
    parser = argparse.ArgumentParser(description='CricketLens Stage 1: parse Cricsheet IPL JSON')
    parser.add_argument('source', type=Path, help='Cricsheet IPL JSON ZIP or directory')
    parser.add_argument('--output', type=Path, default=Path('data/processed'))
    args = parser.parse_args()
    print(json.dumps(write_csvs(extract(args.source), args.output), indent=2))


if __name__ == '__main__':
    main()
