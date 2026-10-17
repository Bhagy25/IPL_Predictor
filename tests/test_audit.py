from pathlib import Path
from cricketlens.pipeline import extract, write_csvs
from cricketlens.data_audit import audit


def test_synthetic_extraction_reconciles(tmp_path):
    fixture = Path(__file__).parent / 'fixtures'
    write_csvs(extract(fixture), tmp_path / 'data')
    result = audit(tmp_path / 'data', tmp_path / 'report')
    assert result['counts']['matches'] == 1
    assert result['reconciliation_failures'] == 0
    assert (tmp_path / 'report' / 'season_summary.csv').exists()


def test_next_over_anomaly_does_not_create_training_example(tmp_path):
    # Extend fixture with an extra legal delivery in the future over.
    import json
    fixture = Path(__file__).parent / 'fixtures' / 'example_match.json'
    match = json.loads(fixture.read_text())
    future_over = match['innings'][0]['overs'][1]
    future_over['deliveries'].append({'batter':'Batter B', 'bowler':'Bowler X', 'runs':{'batter':0,'extras':0,'total':0}})
    p = tmp_path / 'anomalous.json'; p.write_text(json.dumps(match))
    result = extract(tmp_path)
    assert any(r['issue'] == 'more_than_six_legal_balls' for r in result['screening_issues'])
    assert any(r['issue'] == 'invalid_next_over_length' for r in result['screening_issues'])
    assert all(r['completed_overs'] != 1 for r in result['next_over_samples'])
