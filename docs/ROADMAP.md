# CricketLens development roadmap — canonical stage numbering

**Stage = project milestone; Session = date/number of work session.** These are not interchangeable.

| Stage | Goal | Status | Deliverables / acceptance criteria |
|---|---|---|---|
| **1: Dataset screening & cleaning** | Load Cricsheet IPL archive; create correct reproducible tables; audit exceptions | **IN PROGRESS** | Clean matches/innings/overs/deliveries/batting files; data dictionary; complete missingness + anomalies + venue/identity checks; reconciliation; signed-off Stage 1 report |
| **2: Systematic EDA** | Analyze IPL, team, venue, player patterns | Not formally started | Notebook, descriptive stats (mean, median, SD, IQR, MAD), missingness interpretation, 10–12 well-chosen visualizations, correlations/regression, substantive written findings |
| **3: Two ML models** | Develop and evaluate both probabilistic predictors | Preliminary wicket-baseline only | Past-only features, train through 2024, validation on 2025, once-only held-out test on 2026; Brier/log loss/calibration; trained models and documentation |
| **4: Dashboard website** | Six interactive tabs; no login | Not started | Responsive UI, filtering, real-data charts, player/team searches, forms |
| **5: Integrate & test** | Connect FastAPI, predictions, local tracker, replay | Not started | Real model inference, original prediction saved, outcomes recorded, evaluation & historical replay; test cases |
| **6: Final report & presentation** | Integrate evidence from all stages | Ongoing notes, not complete | Reproducible academic PDF, graphs, data quality decisions, results, limitations, screenshots, walkthrough |

**Important:** Early charts in `reports/figures` belong to **preliminary Stage 2**. Early wicket model training is a **preliminary Stage 3 experiment**, not Stage 3 completion. Neither changes the current status of Stage 1.

**Next work:** complete Stage 1 missingness analysis, anomalous overs/DLS checks, venue standardization, player/innings accounting, and archive completeness; rerun all tests; write acceptance summary; only then mark Stage 1 done.
