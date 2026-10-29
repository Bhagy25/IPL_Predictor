"""Supplementary event tables derived directly from raw Cricsheet IPL JSON.

Stage 1's deliveries.csv carries no dismissal kind, player_out, bowler ID or
non-boundary flag, and identifies players by name. This module writes small
companion tables keyed exactly like deliveries.csv (match_id, innings,
over_index, delivery_index) plus a registry-ID player table. It reads the raw
JSON only and never writes into data/processed.

Usage: python -m cricketlens.derived_events --raw data/raw/ipl_json --output data/derived
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from cricketlens.pipeline import NO_TEAM_WICKET, franchise, read_matches

# Dismissals credited to the bowler; run outs, retirements, obstruction etc. are not.
BOWLER_CREDITED = frozenset({'bowled', 'caught', 'caught and bowled', 'lbw', 'stumped', 'hit wicket'})

DISMISSAL_COLUMNS = [
    'match_id', 'season', 'date', 'innings', 'is_super_over', 'over_index', 'delivery_index',
    'batting_team', 'bowling_team', 'batter', 'batter_id', 'non_striker', 'non_striker_id',
    'player_out', 'player_out_id', 'kind', 'bowler', 'bowler_id', 'fielders', 'fielder_ids',
    'bowler_credited', 'counts_as_batting_dismissal',
]
NON_BOUNDARY_COLUMNS = [
    'match_id', 'season', 'date', 'innings', 'is_super_over', 'over_index', 'delivery_index',
    'batter', 'batter_id', 'bowler', 'bowler_id', 'runs_batter',
]
BATTING_APPEARANCE_COLUMNS = [
    'match_id', 'season', 'date', 'innings', 'batting_team', 'player_id', 'player_name',
    'balls_faced', 'runs', 'dismissed', 'dismissal_kind', 'faced_a_ball', 'on_strike',
]
MATCH_PLAYER_COLUMNS = ['match_id', 'season', 'date', 'team', 'player_name', 'player_id']
MATCH_REPLACEMENT_COLUMNS = [
    'match_id', 'season', 'date', 'innings', 'is_super_over', 'over_index', 'delivery_index',
    'team', 'reason', 'player_in', 'player_in_id', 'player_out', 'player_out_id',
]
PEOPLE_COLUMNS = ['player_id', 'names', 'first_season', 'last_season', 'matches', 'teams']


def new_appearance() -> dict:
    return {'balls_faced': 0, 'runs': 0, 'on_strike': False, 'kinds': []}


def appearance_rows(base: dict, innings_pos: int, batting_team: str, registry: dict, crease: dict) -> list:
    """One row per player at the crease in an ordinary innings, in order of first appearance."""
    rows = []
    for name, a in crease.items():
        # A batter is out if any wicket event for them counts as a dismissal (not retired hurt).
        counting = [k for k in a['kinds'] if k not in NO_TEAM_WICKET]
        rows.append({
            **base, 'innings': innings_pos, 'batting_team': batting_team,
            'player_id': registry.get(name, ''), 'player_name': name,
            'balls_faced': a['balls_faced'], 'runs': a['runs'],
            'dismissed': bool(counting),
            'dismissal_kind': counting[-1] if counting else (a['kinds'][-1] if a['kinds'] else ''),
            'faced_a_ball': a['balls_faced'] > 0, 'on_strike': a['on_strike'],
        })
    return rows


def build_tables(source: Path) -> dict:
    """Extract dismissals, non-boundary events, batting appearances, match players, replacements and people."""
    dismissals, non_boundary, batting_appearances, match_players, replacements = [], [], [], [], []
    for filename, match in read_matches(source):
        info = match.get('info', {})
        # Skip exactly the matches, innings and overs pipeline.extract skips, so keys stay aligned.
        try:
            match_date = date.fromisoformat(str((info.get('dates') or [''])[0])[:10])
        except ValueError:
            continue
        teams = [franchise(t) for t in info.get('teams') or []]
        if len(teams) != 2:
            continue
        match_id = Path(filename).stem
        registry = (info.get('registry') or {}).get('people') or {}
        base = {'match_id': match_id, 'season': match_date.year, 'date': match_date.isoformat()}

        for raw_team, names in (info.get('players') or {}).items():
            for name in names:
                match_players.append({
                    **base, 'team': franchise(raw_team), 'player_name': name,
                    'player_id': registry.get(name, ''),
                })

        # Innings are numbered by position, as in deliveries.csv; super overs keep theirs (3, 4, ...).
        for innings_pos, innings in enumerate(match.get('innings') or [], start=1):
            is_super_over = innings.get('super_over') is True
            batting_team = franchise(innings.get('team', ''))
            if (not is_super_over and innings_pos > 2) or batting_team not in teams:
                continue
            bowling_team = teams[1] if batting_team == teams[0] else teams[0]
            crease = {}  # ordinary innings only: striker, non-striker and dismissed players
            for over in innings.get('overs') or []:
                over_index = over.get('over')
                if not isinstance(over_index, int) or over_index < 0:
                    continue
                for delivery_index, ball in enumerate(over.get('deliveries') or [], start=1):
                    key = {
                        **base, 'innings': innings_pos, 'is_super_over': is_super_over,
                        'over_index': over_index, 'delivery_index': delivery_index,
                    }
                    batter, bowler = ball.get('batter', ''), ball.get('bowler', '')
                    non_striker = ball.get('non_striker', '')
                    runs = ball.get('runs') or {}
                    if not is_super_over:
                        striker = crease.setdefault(batter, new_appearance())
                        crease.setdefault(non_striker, new_appearance())
                        striker['on_strike'] = True
                        striker['runs'] += int(runs.get('batter', 0))
                        # A no-ball is faced by the batter; a wide is not (as in Stage 1).
                        striker['balls_faced'] += int('wides' not in (ball.get('extras') or {}))
                    if runs.get('non_boundary'):
                        non_boundary.append({
                            **key, 'batter': batter, 'batter_id': registry.get(batter, ''),
                            'bowler': bowler, 'bowler_id': registry.get(bowler, ''),
                            'runs_batter': int(runs.get('batter', 0)),
                        })
                    # Match-level substitutions (Impact Player, concussion); mid-over role changes are not.
                    for sub in (ball.get('replacements') or {}).get('match') or []:
                        player_in, player_out = sub.get('in', ''), sub.get('out', '')
                        replacements.append({
                            **key, 'team': franchise(sub.get('team', '')), 'reason': sub.get('reason', ''),
                            'player_in': player_in, 'player_in_id': registry.get(player_in, ''),
                            'player_out': player_out, 'player_out_id': registry.get(player_out, ''),
                        })
                    for wicket in ball.get('wickets') or []:
                        kind = wicket.get('kind', '').lower()
                        player_out = wicket.get('player_out', '')
                        fielders = [f['name'] for f in wicket.get('fielders') or [] if f.get('name')]
                        if not is_super_over:
                            crease.setdefault(player_out, new_appearance())['kinds'].append(kind)
                        dismissals.append({
                            **key, 'batting_team': batting_team, 'bowling_team': bowling_team,
                            'batter': batter, 'batter_id': registry.get(batter, ''),
                            'non_striker': non_striker, 'non_striker_id': registry.get(non_striker, ''),
                            'player_out': player_out, 'player_out_id': registry.get(player_out, ''),
                            'kind': kind, 'bowler': bowler, 'bowler_id': registry.get(bowler, ''),
                            'fielders': ';'.join(fielders),
                            'fielder_ids': ';'.join(registry.get(f, '') for f in fielders),
                            'bowler_credited': kind in BOWLER_CREDITED,
                            'counts_as_batting_dismissal': kind not in NO_TEAM_WICKET,
                        })
            if not is_super_over:
                batting_appearances.extend(appearance_rows(base, innings_pos, batting_team, registry, crease))
    return {
        'dismissals': dismissals,
        'non_boundary_events': non_boundary,
        'batting_appearances': batting_appearances,
        'match_players': match_players,
        'match_replacements': replacements,
        'people': build_people(match_players, dismissals),
    }


def build_people(match_players: list, dismissals: list) -> list:
    """One row per registry ID with every name variant, seasons, matches and teams."""
    people = defaultdict(lambda: {'names': set(), 'matches': set(), 'seasons': set(), 'teams': set()})
    for row in match_players:
        person = people[row['player_id']]
        person['names'].add(row['player_name'])
        person['matches'].add(row['match_id'])
        person['seasons'].add(row['season'])
        person['teams'].add(row['team'])
    # Substitute fielders are not in the official player lists but are still registry people.
    for row in dismissals:
        if row['fielders']:
            for name, pid in zip(row['fielders'].split(';'), row['fielder_ids'].split(';')):
                people[pid]['names'].add(name)
    return [
        {
            'player_id': pid,
            'names': ';'.join(sorted(p['names'])),
            'first_season': min(p['seasons']) if p['seasons'] else '',
            'last_season': max(p['seasons']) if p['seasons'] else '',
            'matches': len(p['matches']),
            'teams': ';'.join(sorted(p['teams'])),
        }
        for pid, p in sorted(people.items())
    ]


def write_tables(tables: dict, output: Path) -> dict:
    """Write each table as LF-terminated UTF-8 CSV; return {name: (rows, bytes, sha256)}."""
    columns = {
        'dismissals': DISMISSAL_COLUMNS, 'non_boundary_events': NON_BOUNDARY_COLUMNS,
        'batting_appearances': BATTING_APPEARANCE_COLUMNS,
        'match_players': MATCH_PLAYER_COLUMNS, 'match_replacements': MATCH_REPLACEMENT_COLUMNS,
        'people': PEOPLE_COLUMNS,
    }
    output.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, rows in tables.items():
        path = output / f'{name}.csv'
        with path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns[name], lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        data = path.read_bytes()
        summary[name] = (len(rows), len(data), hashlib.sha256(data).hexdigest())
    return summary


README_TEMPLATE = """# Derived event tables

Small supplementary tables built directly from the committed raw Cricsheet JSON in
`data/raw/ipl_json/`. They add facts that Stage 1's `data/processed/deliveries.csv`
does not carry (dismissal kind, player out, fielders, bowler registry IDs, the
non-boundary flag) and a registry-ID player table. Stage 1 code and outputs are
unchanged. This file is generated; do not edit it by hand.

Build (from the repository root):

    python -m cricketlens.derived_events --raw data/raw/ipl_json --output data/derived

## Keys

`match_id`, `innings`, `over_index`, `delivery_index` use the same convention as
`deliveries.csv`: `match_id` is the JSON file name, `innings` is the 1-based
position of the innings in the file, `over_index` is Cricsheet's 0-based `over`,
and `delivery_index` is the 1-based position in that over's delivery list
(wides and no-balls included). Ordinary innings are 1 and 2; super-over innings
keep their position (3, 4, ...) and are flagged `is_super_over`. `season` is the
year of the first match date, as in Stage 1. Team names use Stage 1's franchise
mapping (`pipeline.RENAMES`).

## dismissals.csv

One row per wicket event, including super overs.

- `match_id`, `season`, `date`, `innings`, `over_index`, `delivery_index`: delivery key (see above)
- `is_super_over`: True for super-over innings; exclude these rows for career statistics
- `batting_team`, `bowling_team`: canonical franchise names
- `batter`, `batter_id`: striker on the delivery and Cricsheet registry ID
- `non_striker`, `non_striker_id`: non-striker and registry ID
- `player_out`, `player_out_id`: dismissed player (may be the non-striker) and registry ID
- `kind`: Cricsheet dismissal kind, lower case
- `bowler`, `bowler_id`: bowler of the delivery and registry ID
- `fielders`, `fielder_ids`: fielders involved, semicolon-separated, in matching order (substitutes included)
- `bowler_credited`: True when the wicket counts for the bowler
- `counts_as_batting_dismissal`: True when the batter's innings ends as a dismissal

## non_boundary_events.csv

Deliveries Cricsheet flags with `runs.non_boundary` (for example an all-run four).
The flag is the only source; nothing is inferred from run values.

- delivery key columns and `is_super_over`, as above
- `batter`, `batter_id`, `bowler`, `bowler_id`: players on the delivery
- `runs_batter`: runs credited to the batter, which are not a boundary

## batting_appearances.csv

One row per player per ordinary innings in which they were at the crease, as
striker or non-striker (or dismissed), in order of first appearance. A batting
innings is one row, so a non-striker run out without facing a ball still counts
as an innings and a dismissal. Super overs are excluded.

- `match_id`, `season`, `date`, `innings`: innings key (see above)
- `batting_team`: canonical franchise name
- `player_id`, `player_name`: registry ID and the name used in that match
- `balls_faced`: deliveries faced as striker, excluding wides (no-balls count)
- `runs`: runs off the bat
- `dismissed`: True when a wicket event for this player counts as a batting dismissal
- `dismissal_kind`: kind of that dismissal, or of a non-dismissal event such as retired hurt; empty if none
- `faced_a_ball`: True when `balls_faced` > 0
- `on_strike`: True when the player was the striker on at least one delivery
  (including wides); these rows are exactly Stage 1's `batter_innings.csv` rows

## match_players.csv

One row per player per match from `info.players` (official squad lists, including
listed impact or replacement players) and `info.registry.people`.

- `match_id`, `season`, `date`: match key
- `team`: canonical franchise name
- `player_name`: name as listed for that match
- `player_id`: Cricsheet registry ID

## match_replacements.csv

One row per match-level substitution recorded in a delivery's
`replacements.match` list: Impact Player substitutions and concussion
substitutes. Both players are in `info.players`, so both have a
match_players.csv row for that match: a team's list is its starting eleven
plus every player who came in. Mid-over bowler or batter changes
(`replacements.role`) do not change the squad and are not included.

- `match_id`, `season`, `date`, `innings`, `over_index`, `delivery_index`: the
  delivery where the substitution is recorded (see Keys)
- `is_super_over`: True when it is recorded in a super-over innings
- `team`: canonical franchise name
- `reason`: Cricsheet reason, e.g. `impact_player` or `concussion_substitute`
- `player_in`, `player_in_id`: player who came into the match and registry ID
- `player_out`, `player_out_id`: player replaced and registry ID

## people.csv

One row per registry ID seen as a listed player or as a fielder.

- `player_id`: Cricsheet registry ID
- `names`: every name variant seen for this ID, semicolon-separated
- `first_season`, `last_season`: first and last season in an official player list
- `matches`: matches in an official player list
- `teams`: canonical franchises in those lists, semicolon-separated

Substitute fielders who never appear in an official player list have
`matches` = 0 and empty season and team fields.

## Rules

- `bowler_credited` is True for: bowled, caught, caught and bowled, lbw, stumped,
  hit wicket. It is False for run out, retired hurt, retired out, obstructing the
  field and any other kind (handled the ball, timed out).
- `counts_as_batting_dismissal` is True for every kind except retired hurt and
  retired not out. This is the same rule Stage 1 uses for team wickets
  (`pipeline.NO_TEAM_WICKET`), so retired out counts as a dismissal.
- Super overs: rows are kept and flagged, never mixed into ordinary innings.

## Files

CSV files are UTF-8 with LF line endings; `.gitattributes` keeps git from
converting them, so the hashes below match a checkout.

| File | Rows | Bytes | SHA256 |
|---|---:|---:|---|
{file_rows}
"""


def write_readme(summary: dict, output: Path) -> None:
    file_rows = '\n'.join(
        f'| {name}.csv | {rows:,} | {size:,} | `{sha}` |' for name, (rows, size, sha) in summary.items()
    )
    (output / 'README.md').write_text(README_TEMPLATE.format(file_rows=file_rows), encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description='Build supplementary event tables from raw Cricsheet JSON')
    parser.add_argument('--raw', type=Path, default=Path('data/raw/ipl_json'), help='Cricsheet JSON directory or zip')
    parser.add_argument('--output', type=Path, default=Path('data/derived'))
    args = parser.parse_args()
    summary = write_tables(build_tables(args.raw), args.output)
    write_readme(summary, args.output)
    print(json.dumps({name: {'rows': r, 'bytes': b, 'sha256': s} for name, (r, b, s) in summary.items()}, indent=2))


if __name__ == '__main__':
    main()
