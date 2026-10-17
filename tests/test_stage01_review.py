import json
from pathlib import Path
from cricketlens.stage01_review import review
from cricketlens.venues import canonical_venue
from cricketlens.pipeline import extract


def test_exact_venue_aliases_and_distinct_stadiums():
    assert canonical_venue('Wankhede Stadium, Mumbai') == 'Wankhede Stadium'
    assert canonical_venue('Feroz Shah Kotla') == 'Arun Jaitley Stadium'
    assert canonical_venue('Sardar Patel Stadium, Motera') != canonical_venue('Narendra Modi Stadium, Ahmedabad')
    assert canonical_venue('Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur') != canonical_venue('Punjab Cricket Association IS Bindra Stadium, Mohali')


def test_review_fixture_outputs_expected_reports(tmp_path):
    root = Path(__file__).parent / 'fixtures'
    r = review(root, tmp_path)
    assert r['archive_matches'] == 1
    assert r['delivery_run_total_mismatches'] == 0
    assert (tmp_path / 'raw_over_anomalies.csv').exists()
    assert (tmp_path / 'venue_alias_review.csv').exists()


def test_invalid_seven_ball_over_blocks_downstream_training_windows(tmp_path):
    fixture = Path(__file__).parent / 'fixtures' / 'example_match.json'
    match = json.loads(fixture.read_text())
    # Corrupt the first over (which contains six valid balls) with another legal ball.
    first = match['innings'][0]['overs'][0]
    first['deliveries'].append({'batter':'Batter A','bowler':'Bowler X',
                                'runs':{'batter':0,'extras':0,'total':0}})
    (tmp_path / 'bad.json').write_text(json.dumps(match))
    rows = extract(tmp_path)
    assert any(x['issue'] == 'more_than_six_legal_balls' for x in rows['screening_issues'])
    assert not rows['next_over_samples']
