from pathlib import Path
from cricketlens.pipeline import extract, franchise, write_csvs

FIXTURE = Path(__file__).parent / 'fixtures'


def test_franchise_names_do_not_merge_unrelated_clubs():
    assert franchise('Delhi Daredevils') == 'Delhi Capitals'
    assert franchise('Rising Pune Supergiants') == 'Rising Pune Supergiant'
    assert franchise('Gujarat Lions') == 'Gujarat Lions'
    assert franchise('Gujarat Titans') == 'Gujarat Titans'


def test_balls_and_wicket_definition():
    data = extract(FIXTURE)
    assert len(data['matches']) == 1
    assert data['matches'][0]['team1'] == 'Delhi Capitals'
    assert len(data['next_over_samples']) == 2
    first = data['next_over_samples'][0]
    assert first['completed_overs'] == 1
    assert first['runs'] == 10
    assert first['wickets'] == 0
    assert first['wicket_next_over'] == 1
    second = data['next_over_samples'][1]
    assert second['wicket_next_over'] == 0
    a = next(x for x in data['batter_innings'] if x['batter'] == 'Batter A')
    assert a['runs'] == 8
    assert a['balls_faced'] == 10  # one wide excluded; no-ball is counted
    assert a['dismissed'] == 1
    assert sum(x['legal_delivery'] for x in data['deliveries'] if x['over_index'] == 0) == 6
    assert sum(x['team_wickets_on_ball'] for x in data['deliveries']) == 1


def test_write_csvs(tmp_path):
    tables = extract(FIXTURE)
    counts = write_csvs(tables, tmp_path)
    assert counts['next_over_samples'] == 2
    assert (tmp_path / 'batter_innings.csv').exists()
