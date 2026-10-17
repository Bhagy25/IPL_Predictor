# CricketLens — Men’s IPL Analytics & Prediction

**IT462 Exploratory Data Analysis college project.** Development **Stage 1: Dataset screening and cleaning (IN PROGRESS)**. Files here also include explicitly labelled *preliminary* Stage 2 EDA and Stage 3 ML experiments. No completed dashboard or final trained model yet.

## Agreed scope
- Men's IPL matches 2008–2026; Cricsheet ball-by-ball JSON as source.
- Six website tabs: IPL Overview; Team Analysis; Player Explorer; Statistics & EDA Lab; Prediction Arena; Prediction Tracker.
- Model A: probability a batter scores 30+ and 50+ runs *before the match* (with suitable qualification for batting participation).
- Model B: probability of at least one team wicket in the *next over* after a completed over.
- No login/signup. First version stores predictions and user-entered outcomes in the browser; no automatic model retraining.
- Development uses pre-2026 seasons; **2026 is reserved as an unseen test**, then a final model can be refit through 2026 for future predictions.

## Stage definitions
| Stage | Work | Status |
|---|---|---|
| **1** | Screen, clean, standardize and audit IPL data | **In progress; initial data tables generated** |
| **2** | Systematic EDA, descriptive statistics, plots and interpretations | Not formally complete; early exploratory charts exist |
| **3** | Train/validate/test both ML models | Not formally complete; early next-over baseline validated on 2025 |
| **4** | Build six-tab React dashboard | Not started |
| **5** | FastAPI integration, tracker and historical replay | Not started |
| **6** | Consolidate final academic report and demonstrate | Ongoing notes; final report not complete |

For deliverables and completion criteria see [`docs/ROADMAP.md`](docs/ROADMAP.md), [`docs/STAGE_01_STATUS.md`](docs/STAGE_01_STATUS.md), and [`reports/REPORT_DRAFT.md`](reports/REPORT_DRAFT.md).

## Run the project locally (Python 3.10+)

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

Place your copy of the official `ipl_json.zip` in `data/raw/ipl_json.zip` (excluded from GitHub), then:

```bash
python -m cricketlens.pipeline data/raw/ipl_json.zip --output data/processed
python -m cricketlens.data_audit --data data/processed --output reports/stage_01 --figures reports/figures
python -m cricketlens.overview --data data/processed --output reports/stage_01/first_eda_numbers.json
```

These commands create initial clean tables and audit outputs. The `reports/figures` charts are **preliminary Stage 2** work. If experimenting separately with the Stage 3 wicket baseline, run:

```bash
python -m cricketlens.train_wicket_baseline --input data/processed/next_over_samples.csv --output models
```

Do **not** evaluate or tune on the 2026 holdout while still selecting models. Code, tests, and reproducible summaries may go to GitHub; `data/raw/`, `data/processed/`, and `models/` are ignored.

## Evidence so far (initial processing, not Stage 1 sign-off)

- 1,243 men’s IPL JSON matches, dates 2008–2026.
- 295,557 recorded delivery events; 18,768 batter-innings records.
- 44,714 eligible provisional next-over samples; 550 censored next-over windows.
- 2,480 ordinary innings reconciled against delivery-level runs, wickets and legal-ball counts.
- 6 synthetic-fixture software tests previously passed. Run `pytest` again after updating the code.
- **Preliminary** 2025-only wicket baseline: Brier score 0.19831 versus 0.20319 for a constant-rate baseline. No held-out 2026 results.

Data source: [Cricsheet](https://cricsheet.org/). Credit Cricsheet and disclose any AI assistance in assessed work, consistent with your syllabus. Further data auditing is required before the cleaned dataset is frozen.
