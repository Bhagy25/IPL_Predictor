# Stage 2 - Exploratory Data Analysis

**Current stage:** Stage 2 in progress. Stage 1 data quality is signed off for descriptive EDA; Stage 3 model training sample filtering is pending.

**Session 01 completed:**
- Verified data imports and enforced `season <= 2025` to protect the held-out 2026 ML test.
- Computed five-number summaries, mean, median, mode, sample variance, SD, IQR, median absolute deviation, CV and Tukey outliers.
- Investigated season trends, innings distributions, batting phase patterns, venue and team comparisons, player performance, and next-over outcome frequencies.
- Produced Pearson and Spearman matrices, descriptive multiple regression, explanatory VIF values and missingness table.
- Generated 11 reproducible charts, CSV aggregates, a JSON summary, Session 01 EDA report, and documented caveats.
- Expanded automated unit tests.

**Stage 2 NOT yet completed:** deeper stratified/bivariate analysis, written advanced EDA interpretation, integration into a complete chapter, professor review.

**Next:** Stage 2 / Session 02, then formal Stage 2 sign-off. No final ML algorithm or test result yet.

**Run:** `python -m cricketlens.stage02_eda --data data/processed --output reports/stage_02/session_01 --figures reports/figures/stage_02`

**Session 02 completed:** length-stratified scores, outlier sensitivity, within-innings paired Powerplay vs death-over scoring, season-centered venue associations, toss-outcome crosstabs, venue-linked city missingness, measurement scale/sampling interpretation, six additional charts and tested code.

**Next:** combine Session 01 and 02 into a coherent final EDA chapter, select key figures for the dashboard and complete Stage 2 review. Continue on `feature/stage-02-eda`; do NOT merge this branch until Stage 2 is reviewed.

**Session 02 run:** `python -m cricketlens.stage02_deep_eda --data data/processed --output reports/stage_02/session_02 --figures reports/figures/stage_02`
