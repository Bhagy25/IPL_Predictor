# CricketLens — Living EDA project report

**Status:** working academic report, not a completed results report. Add *measured* numerical results and figures as soon as IPL JSON extraction is available.

## Stage I — Problem and scope

Men's Indian Premier League match and delivery data. Objectives: (a) descriptive/univariate/bivariate/multivariate IPL EDA, (b) pre-match batter milestone probabilities of 30+ and 50+ runs, and (c) in-match probability at least one wicket falls in the next completed over. User-facing dashboard has six tabs; feedback is evaluated but never auto-trains models.

**Dataset candidate:** Cricsheet's IPL JSON archive, nominal coverage 2008–2026; the precise number of usable matches, seasons and files will be documented after import. The data source must be credited. Ask the instructor if the syllabus note about data.gov.in collection is a strict requirement.

## Stage II — Screening / cleaning (work started)

The extractor builds four primary tables: `matches.csv`, `deliveries.csv`, `next_over_samples.csv`, `batter_innings.csv`, plus `screening_issues.csv`. Relevant definitions:
- Nominal: team, opposition, batter, venue. Ratio/discrete: runs and wickets. Ordered time: dates, overs.
- Wides and no-balls are *not legal deliveries*. Batter balls faced exclude wides but include no-balls.
- Exclude a non-wicket retirement (`retired hurt`) from the batting side's team wicket count.
- Maintain franchise rename mappings, not unrelated franchise mergers.
- Super overs excluded from base innings modeling.
- A next-over outcome after an interrupted or prematurely completed over can be censored; labels are admitted only when the next over is complete or a known wicket-driven all-out ends early.

**Pending actual data inspection:** match count/date range, duplicates, missingness by field, unusual innings, venue variations, team rename counts, outliers and censoring counts; distinguish structural missingness from data errors; discuss MCAR/MAR/MNAR carefully.

## Stage III — EDA and statistical investigation (planned)

- Descriptives: five-number summary, mean, median, mode, variance, SD, MAD, IQR, CV.
- Univariate: innings totals and player runs histograms/densities/boxplots.
- Bivariate: team comparison, phases vs run rate, venue vs totals; scatterplot, crosstab, covariance and heatmap.
- Pearson/Spearman comparisons, multicollinearity and an interpretable linear/multiple-regression analysis with goodness-of-fit.
- Advanced EDA: season trends, time drift, optional profiling and PCA experiment where suitable.
- Explain *why* the visible patterns matter, data limitations and confounders. No invented findings.

## Stage IV — ML design and evaluation (code started)

Model A: batter innings -> 30+/50+ milestone probabilities from rolling, past-only statistics (not yet built).

Model B: situation after completed over -> next-over team wicket yes/no, scored with Brier and log loss. Logistic regression baseline is coded but not trained on real IPL data yet.

Development train <=2024, validation 2025; holdout 2026 for one unbiased final evaluation; planned later refit through 2026 for prospective forecasts. No leakage from future data.

## Stage V — Dashboard and evidence (planned)

1. IPL Overview; 2. Team Analysis; 3. Player Explorer; 4. Statistics & EDA Lab; 5. Prediction Arena; 6. Prediction Tracker.

No login. Browser-local saving of forecasts and actual results, with model version, event probability, match context and time. Tracker shows all predictions, proper scores and calibration over many events. No auto-retraining. Historical replay from held-out matches for demonstration.

## Academic integrity and limitations

Use official Cricsheet attribution, attribute Python libraries and disclose AI assistance in coursework according to IT462 rules. The user must review any generated material, run experiments and write genuine interpretations. The accuracy of all future ML models is unknown until evaluated.

## Results table (fill only after execution)

| Item | Observed result | Evidence |
|---|---|---|
| Match count and seasonal coverage | Not yet measured | `matches.csv` |
| Screening issues | Not yet measured | `screening_issues.csv` |
| Next-over eligible training cases | Not yet measured | `next_over_samples.csv` |
| 2025 validation Brier (baseline/model) | Not yet measured | model metrics JSON |
| 2026 held-out Brier | Not yet measured | final one-time evaluation |
