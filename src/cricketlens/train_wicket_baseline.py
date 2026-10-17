"""Train first understandable baseline; hold out 2026 until model choice is frozen.

The fixed chronological split is explicitly stated in docs/EVALUATION_PLAN.md.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

NUMERICAL = ['runs', 'wickets', 'completed_overs', 'run_rate', 'innings']
CATEGORICAL = ['batting_team', 'bowling_team']
TARGET = 'wicket_next_over'


def metrics(actual, probabilities):
    output = {'n': len(actual), 'event_rate': round(float(actual.mean()), 5),
              'brier': round(float(brier_score_loss(actual, probabilities)), 5),
              'log_loss': round(float(log_loss(actual, probabilities, labels=[0, 1])), 5)}
    if actual.nunique() == 2:
        output['roc_auc'] = round(float(roc_auc_score(actual, probabilities)), 5)
    return output


def run(input_csv: Path, output_dir: Path, evaluate_test: bool = False):
    df = pd.read_csv(input_csv)
    df = df.dropna(subset=NUMERICAL + CATEGORICAL + [TARGET, 'season'])
    train = df[df.season <= 2024]
    val = df[df.season == 2025]
    test = df[df.season == 2026]
    if train.empty or val.empty:
        raise ValueError('Need both pre-2025 and 2025 samples to train/validate. Inspect archive coverage.')
    if train[TARGET].nunique() < 2:
        raise ValueError('Training data must include both wicket and no-wicket cases.')
    processor = ColumnTransformer([
        ('num', Pipeline([('impute', SimpleImputer(strategy='median')),
                           ('scale', StandardScaler())]), NUMERICAL),
        ('cat', OneHotEncoder(handle_unknown='ignore'), CATEGORICAL),
    ])
    model = Pipeline([('preprocess', processor),
                      ('classifier', LogisticRegression(max_iter=2000, random_state=42))])
    model.fit(train[NUMERICAL + CATEGORICAL], train[TARGET])
    p = model.predict_proba(val[NUMERICAL + CATEGORICAL])[:, 1]
    base_p = [float(train[TARGET].mean())] * len(val)
    results = {
        'status': 'validation_only' if not evaluate_test else 'one_time_holdout_evaluation',
        'development_seasons': '<=2024', 'validation_season': 2025,
        'holdout_season': 2026, 'training_rows': len(train),
        'validation_model': metrics(val[TARGET], p),
        'validation_constant_baseline': metrics(val[TARGET], base_p),
        'note': 'Do not tune repeatedly on the 2026 holdout. Features are checkpoint-known only.',
    }
    if evaluate_test:
        if test.empty:
            raise ValueError('No 2026 matches for final holdout evaluation.')
        # After choosing the model with 2025 validation, refit on *all* pre-2026
        # history before touching the held-out 2026 season.
        development = df[df.season <= 2025]
        refitted = Pipeline([('preprocess', processor),
                             ('classifier', LogisticRegression(max_iter=2000, random_state=42))])
        refitted.fit(development[NUMERICAL + CATEGORICAL], development[TARGET])
        results['holdout_train_rows'] = len(development)
        results['test_2026'] = metrics(
            test[TARGET], refitted.predict_proba(test[NUMERICAL + CATEGORICAL])[:, 1])
        joblib.dump(refitted, output_dir / 'next_over_baseline_pre2026_holdout.joblib')
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / 'next_over_baseline_pre2025.joblib')
    (output_dir / 'next_over_baseline_metrics.json').write_text(json.dumps(results, indent=2))
    return results


def main():
    p = argparse.ArgumentParser(description='First next-over wicket baseline; no automatic deployment')
    p.add_argument('--input', type=Path, default=Path('data/processed/next_over_samples.csv'))
    p.add_argument('--output', type=Path, default=Path('models'))
    p.add_argument('--evaluate-test-2026', action='store_true', help='One-time held-out test, after model design is frozen')
    a = p.parse_args()
    print(json.dumps(run(a.input, a.output, a.evaluate_test_2026), indent=2))


if __name__ == '__main__':
    main()
