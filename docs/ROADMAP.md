# CricketLens development roadmap — canonical stage numbering

**Stage = project milestone; Session = date/number of work session.** These are not interchangeable.

| Stage | Goal | Status | Deliverables / acceptance criteria |
|---|---|---|---|
| **1: Dataset screening & cleaning** | Load Cricsheet IPL archive; create correct reproducible tables; audit exceptions | **COMPLETE FOR EDA** | Clean matches/innings/overs/deliveries/batting files; data dictionary; complete missingness + anomalies + venue/identity checks; reconciliation; signed-off Stage 1 report |
| **2: Systematic EDA** | Analyze IPL, team, venue, player patterns | **INTERNALLY COMPLETE (Sessions 01–03; professor review pending)** | Notebooks, descriptive stats, missingness, 20 EDA figures, regression/correlation, corrected outcome analysis and consolidated 7-page PDF |
| **3: Two ML models** | Develop and evaluate both probabilistic predictors | **COMPLETE: seven-algorithm benchmark; histogram gradient boosting selected and refitted through 2026** | Past-only features; tuning 2018–2020, ranking 2021–2025, retrospective 2026 test; Brier/log loss/calibration; assumption evidence; `docs/MODEL_METHODOLOGY.md` |
| **4: Dashboard website** | Seven interactive routes; no login | **COMPLETE** (see `docs/STAGE_04_WEBSITE.md`) | Responsive UI, filtering, real-data charts, player/team searches, forms, methodology page |
| **5: Integrate & test** | Connect FastAPI, predictions, local tracker, replay | **COMPLETE** (see `docs/STAGE_04_WEBSITE.md`) | Real model inference, original prediction saved, outcomes recorded, evaluation & historical replay; test cases |
| **6: Final report & presentation** | Integrate evidence from all stages | **Final submission prepared** (`reports/REPORT_DRAFT.md`, submission notebook) | Reproducible report, EDA and prediction-model notebook, graphs, data quality decisions, results, limitations, screenshots |

**Important:** The Stage 2 chapters and figures are now internally consolidated, with professor review still pending. Early wicket-model training remains a preliminary Stage 3 experiment and has not been tested on 2026.

**Stage 1 closure:** Source missingness, anomalous overs/D/L exceptions, conservative venue standardization, and player/innings accounting reviewed; 9 tests passed. See `docs/STAGE_01_STATUS.md` for the full sign-off and deferred ML sample policy.

**Stage 1 hand-off (2026-10-17):** Data inspection, conservative normalization, and exception logging completed for EDA. Read `docs/STAGE_01_STATUS.md`. Next is Stage 2: systematic descriptive, missingness, univariate, bivariate, time-trend and correlation analysis. Stage 3 will revisit candidate ML sample eligibility and temporal model validation.

**Stage 2 Session 01 (2026-10-18):** 11 statistical EDA charts, descriptive metrics, team/venue/player comparisons, correlations, descriptive regression and statistical caveats produced on seasons up to 2025. Stage 2 remains open pending deeper analysis and final EDA chapter. See `docs/STAGE_02_STATUS.md`.


## Stage 2 completion update — Session 03, October 2026

Stage 2 Sessions 01–03 have been completed and verified internally; the branch is ready for student review and a pull request. This includes an actual correction to Super Over outcome attribution, 20 numbered EDA figures, D/L sensitivity comparisons, no-result accounting, and the seven-page `reports/Stage_02_Consolidated_EDA_Report.pdf`. The professor's review is still pending. The next stage is the two-model ML pipeline, with IPL 2026 protected for one final unseen evaluation.


## Stages 4–5 completion update — October 2026

The six-tab React website and the FastAPI backend are complete: every statistic is computed from
`data/processed` and `data/derived`, the Prediction Arena serves the 2026 deployment models through the Stage 3
inference functions, and the Prediction Tracker stores predictions in the browser and replays the 2026 holdout.
The pytest suite verifies the API against independent calculations. Architecture, endpoints and prediction
guards are documented in `docs/STAGE_04_WEBSITE.md`. Stage 6 (final academic report and presentation)
remains in progress.


## Final submission update — November 2026

The prediction models were finalised: a chronological benchmark of seven algorithms (class-prior baseline,
logistic regression, decision tree, random forest, histogram gradient boosting, Gaussian naive Bayes and a
multilayer perceptron) selected histogram gradient boosting for both forecasts, under a rule fixed in
advance (lowest mean 2021–2025 validation Brier score). The final models in `models/final/` reproduce the
benchmark's 2026 forecasts exactly and serve the website; the Stage 3 models are kept as development
history. The full methodology, with evidence for every data and algorithm assumption, is in
`docs/MODEL_METHODOLOGY.md` and on the website's Methodology page. The single submission notebook
`notebooks/CricketLens_IPL_EDA_and_Prediction_Models.ipynb` reproduces the data preparation, EDA and
prediction models from the raw Cricsheet files.
