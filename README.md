# CricketLens

**Men's IPL exploratory analysis and probability prediction** - IT462 EDA project.

Status: **Phase 1 starter code**. No real IPL data has been processed or any trained/tested model results claimed yet.

## Confirmed scope

- **Dashboard:** IPL Overview, Team Analysis, Player Explorer, Statistics & EDA Lab, Prediction Arena, Prediction Tracker.
- **Model 1:** Pre-match probabilities a selected batter scores **30+** and **50+** runs, conditional on actually batting; build after wicket baseline.
- **Model 2:** After a completed over, probability of **at least one team wicket in the next over (6 legal deliveries)**.
- **No login**; predictions and actual outcomes saved in browser local storage in the first version. User entries are **not used for automatic retraining**.
- **No real-money betting**; no live cricket API is required.

## Get started (Python 3.10+)

```bash
python -m venv .venv
# macOS / Linux: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -e '.[dev]'
pytest -q
```

Download the **IPL JSON** from https://cricsheet.org/downloads/ (`ipl_json.zip`) and place it at `data/raw/ipl_json.zip`. This ZIP is *not* included in the repo.

```bash
python -m cricketlens.pipeline data/raw/ipl_json.zip --output data/processed
python -m cricketlens.overview --data data/processed --output reports/first_eda_numbers.json
python -m cricketlens.train_wicket_baseline --input data/processed/next_over_samples.csv --output models
```

For an introduction, read [`docs/ML_FOR_BEGINNERS.md`](docs/ML_FOR_BEGINNERS.md) first.

The wicket baseline **validates on 2025 only by default**. Once design/feature decisions are frozen, use `--evaluate-test-2026` for one final evaluation; this refits on data through 2025 before testing 2026. Do **not** tune repeatedly on the 2026 holdout.

## What's actually implemented so far?

- Data extraction of match, delivery, next-over training checkpoint, and batter-innings tables.
- Legal-ball, wide/no-ball, team-wicket and selected censoring handling.
- Simple pre-2025 logistic-regression wicket baseline + 2025 comparison against constant-rate baseline (requires real data).
- First descriptive-statistics generator (requires real data).
- Automated tests based on a tiny *synthetic* fixture.
- Transparent ongoing report notes (`reports/`) and dated work log (`docs/DEV_LOG.md`).

**Not yet implemented:** the batter milestone ML pipeline, verified IPL EDA results, frontend, FastAPI inference, prediction tracker and historical replay. These are tracked in `docs/ROADMAP.md`.

## Repository layout

```text
src/cricketlens/    Extractor, descriptive stats, first ML baseline
scripts/            Additional utilities to come
tests/              Synthetic fixtures and tests
data/raw/            Place downloaded Cricsheet ZIP here (gitignored)
data/processed/      Generated clean CSV files (gitignored)
models/             Model artifacts, excluded from Git
notebooks/          EDA exploration and reporting later
reports/            Academic evidence, definitions and progress
docs/               Roadmap, evaluation design, work log
web/                React interface later
```

## Academic integrity / credits

Data: [Cricsheet](https://cricsheet.org/). Code will cite relevant packages and document AI assistance. Author(s) must independently review outputs and cite any AI support as required by IT462. See `reports/REPORT_DRAFT.md`.
