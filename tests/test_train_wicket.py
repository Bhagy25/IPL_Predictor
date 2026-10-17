from pathlib import Path
import pandas as pd
from cricketlens.train_wicket_baseline import run


def test_model_training_respects_time_split(tmp_path):
    # SYNTHETIC DATA: tests training plumbing, not predictive validity.
    rows = []
    for season in (2023, 2024, 2025, 2026):
        for over in range(1, 51):
            rows.append({
                'season': season, 'runs': over * 4, 'wickets': over % 6,
                'completed_overs': (over % 17) + 1,
                'run_rate': round((over*4)/((over%17)+1), 2),
                'innings': (over % 2) + 1,
                'batting_team': 'Mumbai Indians' if over % 2 else 'Chennai Super Kings',
                'bowling_team': 'Chennai Super Kings' if over % 2 else 'Mumbai Indians',
                'wicket_next_over': int(over % 4 == 0),
            })
    csv_path = tmp_path / 'samples.csv'
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    output = tmp_path / 'models'
    validation = run(csv_path, output)
    assert validation['training_rows'] == 100
    assert validation['validation_model']['n'] == 50
    assert 'test_2026' not in validation
    assert (output / 'next_over_baseline_pre2025.joblib').exists()
    final = run(csv_path, output, evaluate_test=True)
    assert final['holdout_train_rows'] == 150
    assert final['test_2026']['n'] == 50
    assert (output / 'next_over_baseline_pre2026_holdout.joblib').exists()
