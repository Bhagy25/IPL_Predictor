# Stage 2 — Exploratory Data Analysis — Internally complete

**Sessions 01–03 completed.** Stage 2's code, statistics and exceptions have been consolidated and verified for development seasons **2008–2025**; academic review by the professor remains external. Do not claim predictive-model accuracy or 2026 holdout findings from this stage.

- **Session 01:** classical descriptive statistics, 11 plots, correlation/regression, player/team/venue trends.
- **Session 02:** duration-stratified scores, paired scoring-phase uncertainty, adjusted-venue comparisons, toss associations and missingness, 6 additional figures.
- **Session 03:** corrected Super Over final winner attribution, D/L-stratified sensitivity checks, no-result accounting, 3 additional figures, integrated EDA narrative and corrected previously stated toss/team metrics.

**Canonical EDA narrative:** `docs/STAGE_02_SESSION_03_FINDINGS.md` and `reports/Stage_02_Consolidated_EDA_Report.pdf`.
Earlier Session 02 PDF toss figures are superseded because those calculations previously excluded Super Over winners. New CSV summaries and consolidated PDF contain corrected outcomes. The match parser must be rerun to add `final_winner` and other outcome columns.

Run `pytest -q` and all three EDA modules before merging `feature/stage-02-eda` into `main`. **Next development stage:** Stage 3 ML with temporal splits, proper censored-window handling and two probabilistic predictors. No automatic retraining from feedback.
