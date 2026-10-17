"""Compute honest first-pass descriptive statistics from extracted CSVs."""
import argparse
import json
from pathlib import Path
import pandas as pd


def run(directory: Path):
    matches = pd.read_csv(directory / 'matches.csv')
    deliveries = pd.read_csv(directory / 'deliveries.csv')
    batter_innings = pd.read_csv(directory / 'batter_innings.csv')
    output = {
        'match_count': int(len(matches)),
        'seasons': sorted(int(x) for x in matches.season.unique()),
        'total_runs': int(deliveries.runs_total.sum()),
        'total_team_wickets': int(deliveries.team_wickets_on_ball.sum()),
        'total_legal_deliveries': int(deliveries.legal_delivery.sum()),
        'player_innings_count': int(len(batter_innings)),
        'player_innings_30plus_rate': round(float(batter_innings.reached_30.mean()), 4),
        'player_innings_50plus_rate': round(float(batter_innings.reached_50.mean()), 4),
        'note': 'Milestone rates conditional on recorded batting appearances; not predictions.',
    }
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data', type=Path, default=Path('data/processed'))
    p.add_argument('--output', type=Path, default=Path('reports/first_eda_numbers.json'))
    a = p.parse_args()
    result = run(a.data)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
