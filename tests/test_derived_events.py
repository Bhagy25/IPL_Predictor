"""Tests for the derived event tables built from raw Cricsheet JSON."""
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import pytest

from cricketlens.derived_events import build_tables, write_tables
from cricketlens.pipeline import extract

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw' / 'ipl_json'
PROCESSED = ROOT / 'data' / 'processed'
DERIVED = ROOT / 'data' / 'derived'
# Kept outside tests/fixtures/: Stage 1 tests read every *.json in that folder recursively.
FIXTURE = Path(__file__).parent / 'fixtures_derived' / 'derived_events_match.json'
KEY = ['match_id', 'innings', 'over_index', 'delivery_index']
CREDITED = {'bowled', 'caught', 'caught and bowled', 'lbw', 'stumped', 'hit wicket'}


@pytest.fixture
def fixture_dir(tmp_path):
    shutil.copy(FIXTURE, tmp_path / '900001.json')
    return tmp_path


# ------------------------------------------------------------------ synthetic fixture

def test_dismissal_rules_on_fixture(fixture_dir):
    rows = {(r['innings'], r['over_index'], r['delivery_index']): r for r in build_tables(fixture_dir)['dismissals']}
    assert len(rows) == 5

    caught = rows[(1, 0, 2)]  # the wide before it is delivery 1
    assert (caught['kind'], caught['player_out'], caught['fielders']) == ('caught', 'Batter A', 'Fielder F')
    assert caught['bowler_credited'] and caught['counts_as_batting_dismissal'] and not caught['is_super_over']
    assert (caught['batting_team'], caught['bowling_team']) == ('Delhi Capitals', 'Mumbai Indians')

    run_out = rows[(1, 0, 3)]
    assert run_out['player_out'] == run_out['non_striker'] == 'Batter B'
    assert run_out['batter'] == 'Batter C' and run_out['player_out_id'] == 'id_b'
    assert (run_out['fielders'], run_out['fielder_ids']) == ('Sub S', 'id_sub')
    assert not run_out['bowler_credited'] and run_out['counts_as_batting_dismissal']

    stumped = rows[(1, 1, 2)]
    assert stumped['kind'] == 'stumped' and stumped['fielder_ids'] == 'id_k'
    assert stumped['bowler_credited'] and stumped['bowler_id'] == 'id_y'

    retired = rows[(1, 1, 3)]
    assert retired['kind'] == 'retired hurt'
    assert not retired['bowler_credited'] and not retired['counts_as_batting_dismissal']

    super_over = rows[(3, 0, 1)]
    assert super_over['is_super_over'] and super_over['kind'] == 'bowled'
    assert super_over['bowler_credited'] and super_over['batting_team'] == 'Delhi Capitals'


def test_non_boundary_players_and_people_on_fixture(fixture_dir):
    tables = build_tables(fixture_dir)
    assert [(r['innings'], r['over_index'], r['delivery_index'], r['batter_id'], r['runs_batter'])
            for r in tables['non_boundary_events']] == [(1, 1, 1, 'id_c', 4)]

    players = tables['match_players']
    assert len(players) == 8
    assert {r['team'] for r in players} == {'Delhi Capitals', 'Mumbai Indians'}

    people = {r['player_id']: r for r in tables['people']}
    assert len(people) == 9
    assert people['id_a']['matches'] == 1 and people['id_a']['teams'] == 'Delhi Capitals'
    # The substitute fielder is not in the squad lists but still has a registry row.
    assert people['id_sub']['names'] == 'Sub S' and people['id_sub']['matches'] == 0


def test_batting_appearances_on_fixture(fixture_dir):
    rows = {(r['innings'], r['player_name']): r for r in build_tables(fixture_dir)['batting_appearances']}
    # Ordinary innings only, in order of first appearance; super overs are excluded
    assert list(rows) == [(1, 'Batter A'), (1, 'Batter B'), (1, 'Batter C'), (1, 'Batter D'),
                          (2, 'Keeper K'), (2, 'Fielder F')]

    a = rows[(1, 'Batter A')]  # a wide, then caught: one ball faced
    assert (a['balls_faced'], a['runs'], a['dismissed'], a['dismissal_kind']) == (1, 0, True, 'caught')
    b = rows[(1, 'Batter B')]  # run out at the non-striker's end without facing
    assert (b['balls_faced'], b['dismissed'], b['dismissal_kind'], b['faced_a_ball'], b['on_strike']) == \
        (0, True, 'run out', False, False)
    c = rows[(1, 'Batter C')]  # the non-boundary four still counts as runs off the bat
    assert (c['balls_faced'], c['runs'], c['dismissed'], c['dismissal_kind']) == (3, 4, True, 'stumped')
    d = rows[(1, 'Batter D')]  # retired hurt is not a dismissal
    assert (d['balls_faced'], d['runs'], d['dismissed'], d['dismissal_kind']) == (1, 1, False, 'retired hurt')
    f = rows[(2, 'Fielder F')]
    assert (f['balls_faced'], f['dismissed'], f['on_strike']) == (0, False, False)


def test_match_replacements_on_fixture(fixture_dir):
    rows = build_tables(fixture_dir)['match_replacements']
    # The Impact Player substitution only; the mid-over role replacement does not change the squad
    assert [(r['innings'], r['over_index'], r['delivery_index'], r['is_super_over'], r['team'], r['reason'],
             r['player_in'], r['player_in_id'], r['player_out'], r['player_out_id']) for r in rows] == \
        [(2, 0, 1, False, 'Mumbai Indians', 'impact_player', 'Fielder F', 'id_f', 'Bowler Y', 'id_y')]


def test_fixture_keys_align_with_stage1_deliveries(fixture_dir):
    deliveries = extract(fixture_dir)['deliveries']
    team_wickets = {tuple(str(d[k]) for k in KEY): d['team_wickets_on_ball'] for d in deliveries}
    ordinary = [r for r in build_tables(fixture_dir)['dismissals'] if not r['is_super_over']]
    per_key = Counter(tuple(str(r[k]) for k in KEY) for r in ordinary if r['counts_as_batting_dismissal'])

    assert all(tuple(str(r[k]) for k in KEY) in team_wickets for r in ordinary)
    assert {k: v for k, v in team_wickets.items() if v} == dict(per_key)


def test_written_csv_is_lf_and_hash_matches(fixture_dir, tmp_path):
    out = tmp_path / 'derived'
    summary = write_tables(build_tables(fixture_dir), out)
    for name, (rows, size, sha) in summary.items():
        data = (out / f'{name}.csv').read_bytes()
        assert b'\r' not in data
        assert (len(data), hashlib.sha256(data).hexdigest()) == (size, sha)
        with (out / f'{name}.csv').open(encoding='utf-8', newline='') as f:
            assert len(list(csv.DictReader(f))) == rows


# ------------------------------------------------------------------ real data

needs_raw = pytest.mark.skipif(
    not RAW.is_dir() or not any(RAW.glob('*.json')) or not (PROCESSED / 'deliveries.csv').exists(),
    reason='raw Cricsheet JSON or processed deliveries not available',
)


@pytest.fixture(scope='module')
def raw_facts():
    """One independent pass over the raw JSON, sharing no code with derived_events."""
    credited = Counter()
    batting_outs = Counter()
    boundaries = Counter()
    ids_by_name = defaultdict(set)
    substitutions = []
    squad_sizes = {}
    for path in RAW.glob('*.json'):
        match = json.loads(path.read_text(encoding='utf-8'))
        registry = match['info']['registry']['people']
        for team, names in match['info']['players'].items():
            squad_sizes[(int(path.stem), team)] = len(names)
            for name in names:
                ids_by_name[name].add(registry[name])
        for innings in match['innings']:
            for over in innings['overs']:
                for ball in over['deliveries']:
                    for sub in ball.get('replacements', {}).get('match', []):
                        substitutions.append((int(path.stem), sub['team'], sub['reason'],
                                              registry[sub['in']], registry[sub['out']]))
                    if innings.get('super_over'):
                        continue
                    runs = ball['runs']
                    if runs['batter'] in (4, 6) and not runs.get('non_boundary'):
                        boundaries[(registry[ball['batter']], runs['batter'])] += 1
                    for wicket in ball.get('wickets', []):
                        if wicket['kind'] in CREDITED:
                            credited[registry[ball['bowler']]] += 1
                        if wicket['kind'] not in ('retired hurt', 'retired not out'):
                            batting_outs[registry[wicket['player_out']]] += 1
    return {'credited': credited, 'batting_outs': batting_outs, 'boundaries': boundaries, 'ids_by_name': ids_by_name,
            'substitutions': substitutions, 'squad_sizes': squad_sizes}


@pytest.fixture(scope='module')
def derived():
    return {
        name: pd.read_csv(DERIVED / f'{name}.csv', dtype={'fielders': str, 'fielder_ids': str})
        for name in ('dismissals', 'non_boundary_events', 'match_players', 'match_replacements', 'people')
    }


def player_id(derived, name):
    ids = derived['match_players'].loc[derived['match_players']['player_name'] == name, 'player_id'].unique()
    assert len(ids) == 1, (name, ids)
    return ids[0]


@needs_raw
def test_committed_tables_match_a_fresh_build(tmp_path):
    summary = write_tables(build_tables(RAW), tmp_path)
    for name in summary:
        assert (tmp_path / f'{name}.csv').read_bytes() == (DERIVED / f'{name}.csv').read_bytes(), name


@needs_raw
def test_keys_align_with_processed_deliveries(derived):
    deliveries = pd.read_csv(PROCESSED / 'deliveries.csv', usecols=KEY + ['batter', 'bowler', 'team_wickets_on_ball'])
    for name in ('dismissals', 'non_boundary_events'):
        rows = derived[name][~derived[name]['is_super_over']]
        joined = rows.merge(deliveries, on=KEY, how='left', suffixes=('', '_d'), indicator=True)
        assert (joined['_merge'] == 'both').all(), name
        assert (joined['batter'] == joined['batter_d']).all() and (joined['bowler'] == joined['bowler_d']).all()

    ordinary = derived['dismissals'][~derived['dismissals']['is_super_over']]
    per_key = ordinary[ordinary['counts_as_batting_dismissal']].groupby(KEY).size()
    team_wickets = deliveries[deliveries['team_wickets_on_ball'] > 0].set_index(KEY)['team_wickets_on_ball']
    assert per_key.sort_index().equals(team_wickets.sort_index())


@needs_raw
def test_batting_appearances_extend_stage1_batter_innings(derived):
    appearances = pd.read_csv(DERIVED / 'batting_appearances.csv')
    stage1 = pd.read_csv(PROCESSED / 'batter_innings.csv').rename(columns={'batter_id': 'player_id'})
    key = ['match_id', 'innings', 'player_id']
    joined = appearances.merge(stage1[key + ['runs', 'balls_faced', 'dismissed']], on=key, how='outer',
                               suffixes=('', '_s1'), indicator=True)
    assert not (joined['_merge'] == 'right_only').any()
    # Rows Stage 1 has are exactly the on-strike rows, with identical runs, balls and dismissals
    both = joined[joined['_merge'] == 'both']
    assert both['on_strike'].all() and len(both) == len(stage1)
    assert (both['runs'] == both['runs_s1']).all() and (both['balls_faced'] == both['balls_faced_s1']).all()
    assert (both['dismissed'].astype(int) == both['dismissed_s1']).all()
    # The extra rows are non-striker-only appearances with no runs or balls
    extra = joined[joined['_merge'] == 'left_only']
    assert (~extra['on_strike']).all() and (extra['runs'] == 0).all() and (extra['balls_faced'] == 0).all()
    # Every batting dismissal in dismissals.csv appears exactly once
    ordinary = derived['dismissals'][~derived['dismissals']['is_super_over']]
    assert int(appearances['dismissed'].sum()) == int(ordinary['counts_as_batting_dismissal'].sum())


@needs_raw
def test_bumrah_bowler_credited_wickets(derived, raw_facts):
    bumrah = player_id(derived, 'JJ Bumrah')
    dismissals = derived['dismissals']
    table = int((dismissals['bowler_credited'] & ~dismissals['is_super_over'] & (dismissals['bowler_id'] == bumrah)).sum())
    assert table == raw_facts['credited'][bumrah]
    assert table == 187  # baseline sanity check (Stage 1 heuristic gave 199)


@needs_raw
def test_kohli_boundaries_after_non_boundary_correction(derived, raw_facts):
    kohli = player_id(derived, 'V Kohli')
    deliveries = pd.read_csv(PROCESSED / 'deliveries.csv', usecols=['batter_id', 'runs_batter'])
    nb = derived['non_boundary_events']
    nb = nb[(nb['batter_id'] == kohli) & ~nb['is_super_over']]
    for runs in (4, 6):
        corrected = int(((deliveries['batter_id'] == kohli) & (deliveries['runs_batter'] == runs)).sum()
                        - (nb['runs_batter'] == runs).sum())
        assert corrected == raw_facts['boundaries'][(kohli, runs)]
    assert (raw_facts['boundaries'][(kohli, 4)], raw_facts['boundaries'][(kohli, 6)]) == (844, 316)  # baseline


@needs_raw
def test_bumrah_batting_dismissals_include_non_striker_run_out(derived, raw_facts):
    bumrah = player_id(derived, 'JJ Bumrah')
    d = derived['dismissals']
    outs = d[~d['is_super_over'] & d['counts_as_batting_dismissal'] & (d['player_out_id'] == bumrah)]
    assert len(outs) == raw_facts['batting_outs'][bumrah] == 8  # baseline: batter_innings.csv has 7
    assert (outs['player_out'] != outs['batter']).any()


@needs_raw
def test_registry_ids_resolve_name_variants(derived, raw_facts):
    people = derived['people'].set_index('player_id')
    ids = raw_facts['ids_by_name']
    # Same person listed under two names: one registry ID, both variants recorded.
    for a, b in (('Arshad Khan', 'Arshad Khan (2)'), ('S Arora', 'Salil Arora')):
        assert ids[a] == ids[b] and len(ids[a]) == 1
        assert set(people.loc[next(iter(ids[a])), 'names'].split(';')) == {a, b}
    # Two different people sharing one name: two registry IDs.
    assert len(ids['Harmeet Singh']) == 2
    assert set(ids['Harmeet Singh']) <= set(people.index)


@needs_raw
def test_match_replacements_match_raw_and_squad_lists(derived, raw_facts):
    table = derived['match_replacements']
    rows = sorted(zip(table['match_id'], table['reason'], table['player_in_id'], table['player_out_id']))
    assert rows == sorted((m, reason, pin, pout) for m, _, reason, pin, pout in raw_facts['substitutions'])
    assert len(rows) == len(set(rows))

    # Both players of every substitution are in that match's squad list, on the substituting team
    squads = derived['match_players']
    listed = set(zip(squads['match_id'], squads['team'], squads['player_id']))
    for side in ('player_in_id', 'player_out_id'):
        assert all(key in listed for key in zip(table['match_id'], table['team'], table[side])), side

    # Each listed team is its starting eleven plus every player who came in
    came_in = Counter((m, team) for m, team, *_ in raw_facts['substitutions'])
    assert all(size == 11 + came_in[key] for key, size in raw_facts['squad_sizes'].items())
