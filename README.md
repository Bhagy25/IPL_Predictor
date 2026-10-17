# CricketLens — Men’s IPL Analytics & Prediction

**IT462 Exploratory Data Analysis college project.** Development **Stage 2: Systematic EDA (IN PROGRESS)**; Stage 1 dataset screening and cleaning is complete for EDA with documented exceptions. Files here also include explicitly labelled *preliminary* Stage 2 EDA and Stage 3 ML experiments. No completed dashboard or final trained model yet.

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
| **1** | Screen, clean, standardize and audit IPL data | **Complete for EDA; candidate ML labels require Stage 3 selection** |
| **2** | Systematic EDA, descriptive statistics, plots and interpretations | **In progress**; Session 01 generated 11 evidence-based charts and numeric tables |
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

## Stage 1 audited evidence (2026-10-17)

- 1,243 men’s IPL JSON matches, dates 2008–2026.
- 295,557 recorded delivery events; 18,768 batter-innings records.
- 44,706 **candidate** next-over windows; 548 flagged censored windows under the revised anomaly policy. Final ML eligibility is not yet decided.
- 2,480 ordinary innings reconciled against delivery-level runs, wickets and legal-ball counts.
- 9 synthetic-fixture software tests passed; raw source audit also completed.
- **Preliminary** 2025-only wicket baseline: Brier score 0.19831 versus 0.20319 for a constant-rate baseline. No held-out 2026 results.

Data source: [Cricsheet](https://cricsheet.org/). Credit Cricsheet and disclose any AI assistance in assessed work, consistent with your syllabus. Data is signed off for descriptive EDA; ML eligibility and leakage-safe player features remain Stage 3 work.

### Stage 1 source-quality audit (completed for EDA)

From project root after `pip install -e '.[dev]'`:

```bash
python -m cricketlens.stage01_review "data/raw/ipl_json.zip" --output reports/stage_01
python -m cricketlens.pipeline "data/raw/ipl_json.zip" --output data/processed
python -m cricketlens.data_audit --data data/processed --output reports/stage_01 --figures reports/figures
pytest -q
```

Details, exclusions and limits: `docs/STAGE_01_STATUS.md` and `docs/STAGE_01_SESSION_03_FINDINGS.md`. The `data/processed` outputs are local and ignored by Git. No final trained model is claimed.

## Stage 2 / Session 01 - Run reproducible EDA

Following the completed Stage 1 audit, ensure the seven CSV files are stored locally in `data/processed/`. Then run:

```bash
python -m cricketlens.stage02_eda --data data/processed --output reports/stage_02/session_01 --figures reports/figures/stage_02
pytest -q
```

The results are 11 real-data figures, comparison tables, and statistical summaries for 2008-2025; **2026 is intentionally kept out of development EDA** so it can remain the final ML test season. No ML model was retrained in this session. See `docs/STAGE_02_SESSION_01_FINDINGS.md` and `docs/STAGE_02_STATUS.md`.
