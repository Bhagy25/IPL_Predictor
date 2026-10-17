# CricketLens — Living IT462 EDA project report

**Status as of 17 October 2026:** real Cricsheet dataset imported and development Stage 1 screening begun. All numbers below were computed from the supplied men's IPL JSON ZIP. Sections for advanced EDA, both final ML models and website are incomplete. No IPL 2026 held-out ML test has been performed.

## 1. Project definition and scope (agreed)

Analyze men's Indian Premier League data, season-by-season and across players/venues/teams, using statistical EDA. Provide two eventual ML tools: (A) pre-match probability of 30+ and 50+ batter runs, and (B) the probability at least one batting-team wicket falls during the next six-legal-delivery over. The final website will present six sections (Overview, Teams, Players, Statistics & EDA Lab, Prediction Arena, Prediction Tracker), with no login and no automatic retraining.

**Data source:** [Cricsheet](https://cricsheet.org/), match-by-match structured JSON, supplied locally as `ipl_json (1).zip`, 1,243 match files, 2008–2026. Cite Cricsheet according to its dataset license; see `LICENSE_NOTES.md`. Confirm with the professor how the syllabus's `data.gov.in` collection clause applies to a Cricsheet-based project.

## 2. Stage 1 — Dataset screening and cleaning: measured findings (provisional)

### 2.1 Data structure and dimensions

| Cleaned table | Rows | Meaning |
|---|---:|---|
| `matches.csv` | 1,243 | One men's IPL match each |
| `innings.csv` | 2,480 | Ordinary team batting innings (not Super Overs) |
| `overs.csv` | 47,756 | Recorded regular innings overs, including partial overs |
| `deliveries.csv` | 295,557 | Recorded ball events including wides and no-balls |
| `batter_innings.csv` | 18,768 | One player batting appearance per innings |
| `next_over_samples.csv` | 44,714 | Eligible checkpoint-known next-over outcomes |
| `screening_issues.csv` | 562 | Issue *records*, including censored windows and anomalies |

Date coverage is 2008-04-18 to 2026-05-31. The JSON is entirely labeled `male` and `Indian Premier League`. Runs are ratio/discrete; team/venue are nominal; over number is an ordered match-progress variable. Match/date and season are necessary to enforce chronological ML training.

### 2.2 Cricket-specific cleaning decisions

1. Standardize genuine franchise renames: Delhi Daredevils -> Delhi Capitals, Kings XI Punjab -> Punjab Kings, Royal Challengers Bangalore -> Royal Challengers Bengaluru, and Rising Pune Supergiants -> Rising Pune Supergiant. Do not falsely merge unrelated discontinued teams with current ones.
2. A wide or no-ball is an *illegal* delivery; a no-ball can still count as a ball faced by the batter, while a wide does not. Batting runs differ from total innings runs because of extras.
3. Wickets count batting-team losses, excluding `retired hurt`; `retired out` counts as a wicket. Ordinary innings exclude Super Overs.
4. Eligible next-over samples require a full 6-legal-ball **current** over. Label the next over only if it has exactly six legal balls, or if it finishes early with a confirmed all-out causing a known positive. Other shortened future overs are censored and omitted. Anomalous future overs with >6 legal balls are excluded.
5. The archive has 550 censored next-over windows, 4 over records with >6 legal balls, 4 with zero legal balls, and 4 rejected future-over windows; these issue categories overlap. Further investigation into anomalies and D/L matches is needed before a final dataset is frozen.
6. Aggregated per-innings team runs, wickets and legal-ball counts reconcile perfectly to delivery-level sums for all 2,480 ordinary innings.

### 2.3 Missingness and limitations

`city` is missing in 51 matches (4.10%). `winner` is empty in 25 records because 16 matches are ties and 9 are no-results—not all missing values indicate error. `outcome_method` is ordinarily blank except for the 23 recorded D/L outcomes and is structurally optional. All records include a venue, though venue aliases are not fully standardized yet. The MCAR/MAR/MNAR mechanisms cannot be established merely from these counts; they require careful contextual investigation and remain unproven.

**Sampling:** The dataset is an archive of available historical IPL matches, not a random sample of all possible future IPL match situations. Historical eras, changing franchise composition, venue conditions, and censored innings may bias conclusions.

## 3. Preliminary Stage 2 — First descriptive EDA (measured, not inferential)

- **401,423** total team runs and **14,655** batting-team wickets appear in ordinary delivery records; **284,465** legal deliveries.
- Recorded first-innings totals have **mean 168.57 runs** and **median 168 runs** across archive history. This is descriptive, not adjusted for changing eras, reduced overs, venues or D/L.
- Among **18,768 observed batting appearances**, **25.53%** scored 30+ and **11.27%** scored 50+. These are historical frequencies, not calibrated pre-match forecasts.
- Of **44,714** eligible next-over windows, roughly **27.70%** include at least one team wicket. The conditional definition excludes censored future overs, and is not necessarily representative of all match states.
- Early EDA figures: `figures/matches_by_season.png`, `figures/average_first_innings_runs.png`, `figures/first_innings_distribution.png`, `figures/wicket_next_over_by_checkpoint.png`. Supporting CSVs and audit JSON are in `reports/stage_01/`.

**Interpretation pending:** Add exact distribution summary (IQR, MAD, SD, outliers), team/venue differences, uncertainty and season-trend controls before making substantive cricket claims.

## 4. Preliminary Stage 3 — First next-over wicket ML baseline (2025 validation only)

Initial logistic-regression classifier uses checkpoint-known runs, wickets, completed overs, run rate, innings number, batting team and bowling team. Training uses match seasons **2008–2024** (39,503 windows) and development validation uses **2025** (2,596 windows). It does not use 2026 outcomes for training, tuning, or model performance assessment.

| Evaluation on 2025 | Logistic regression | Constant historical event-rate baseline |
|---|---:|---:|
| Brier Score (lower better) | 0.19831 | 0.20319 |
| Log loss (lower better) | 0.58561 | 0.59638 |
| ROC-AUC | 0.59223 | 0.50000 |

The model shows **only a modest improvement** on this validation year. These metrics do not imply accurate forecasts for every over, and no final algorithm has yet been selected. Further feature engineering must use information known only before each corresponding checkpoint. The **2026 holdout** will be scored once after model design is fixed; only afterward may the selected model be refitted through 2026 for future use. The batter milestone model has not been developed yet.

## 5. Syllabus alignment and planned EDA (not yet completed)

- Explicit measurement scales, sampling biases, missingness and MCAR/MAR/MNAR treatment.
- Five-number summaries, central tendency, variance, standard deviation, IQR, MAD and coefficient of variation.
- Histograms, box/violin plots, team comparisons, wicket phase trends, venue effects, crosstabs, heatmaps.
- Pearson/Spearman correlations, multiple linear regression/goodness of fit, potential multicollinearity/VIF, time trends and optional PCA/profiling.
- Statistical interpretations and caveats in both report and dashboard, not just charts.

## 6. Dashboard plan (not yet implemented)

1. **IPL Overview** — totals, scoring distributions, season trends, filters.
2. **Teams** — selected-franchise performance, opposition head-to-head, venue/phase comparisons.
3. **Players** — batting/bowling explorer, milestones and recent form.
4. **Statistics & EDA Lab** — IPL-wide distributions with team/venue/season filters, correlations and variability.
5. **Prediction Arena** — two model forms and probability outputs.
6. **Prediction Tracker** — store original probability, context, model version and actual outcome; Brier/calibration across both successful and unsuccessful events; manual optional later retraining of verified data.

## 7. Integrity, attribution and next actions

Source: Cricsheet JSON. Source code/scripts, raw match records and generated reports must not be confused. Cite external libraries and disclose AI assistance in coursework per IT462 requirements. Manual actual-result submissions are unverified until checked against authoritative match data and must not blindly retrain a model.

**Next:** finish Stage 1 venue/roster/data audit; then systematic Stage 2 EDA notebook and plots, improved wicket model features and calibration; then pre-match batter model; only then FastAPI and six-tab website.

## Stage 1 / Session 03 - Source quality audit (2026-10-17)

We inspected the original Cricsheet men's IPL archive of 1,243 matches (2008-2026), producing 2,480 ordinary innings and 295,557 delivery records. All ball-level team runs/wickets/legal deliveries reconciled with innings summaries. No duplicate match IDs or negative ball-run fields were found. Venue names were standardized conservatively from 60 raw labels to 38 canonical labels, preserving raw strings. The source contains 51 missing `city` values (33 Dubai, 18 Sharjah), 16 ties and 9 no-results (hence missing winner), and 23 D/L match outcomes. Missingness is described by pattern, not unproven MCAR/MAR/MNAR labels. Four seven-legal-ball overs are retained as anomalies and affected downstream checkpoint rows excluded; four zero-legal-ball final overs are consistent with successful chases ending on wides. Player identities use Cricsheet IDs because "Harmeet Singh" maps to two IDs. Data preprocessing is complete for EDA, but final ML training eligibility remains to be established in Stage 3. The recalculated candidate next-over dataset has 44,706 rows; 608 of those occur in D/L matches. No 2026 data has been used for training or tuning. Figures and data-quality evidence are in `reports/stage_01/`.


## Stage 2 / Session 01 - Systematic EDA findings (2026-10-18)

All numbers below come from `python -m cricketlens.stage02_eda` applied to the audited IPL data, **excluding 2026 (reserved for final ML testing)**. Full numerical summaries and supporting plots are in `reports/stage_02/session_01/` and `reports/figures/stage_02/`.

- First-innings score distribution, 2018-2025 (n=533): mean 175.80, median 175, sample standard deviation 33.93, Q1 155, Q3 199, IQR 44, median absolute deviation 22. Tukey's fences are <89 and >265: 11 statistical outliers, which remain valid match observations unless separately investigated.
- First-innings seasonal means rise in the historical sample. A simple unweighted 2008-2025 linear trend on annual means gives +1.71 runs/season and R² 0.663. This is an observational pattern, not proof of a cause.
- From 2018-2025 deliveries, the observed Powerplay, middle and death phase scoring rates were 8.49, 8.32 and 10.73 runs per six legal balls respectively. Death overs only occur in innings that reach that phase.
- For 2022-2025 matches with winners, Gujarat Titans won 37/60 (61.67%); Mumbai Indians won 26/60 (43.33%). Exclude tied and no-result matches in these denominators.
- On grounds with >=20 recorded first innings in 2018-2025, Eden Gardens averaged 191.31 (n=39) and Chepauk 161.47 (n=43), but the different teams/seasons/rain conditions confound any causal venue comparison.
- Among 8,123 observed batter appearances from 2018-2025, 27.03% scored 30+ and 12.22% scored 50+. These **are not** future-game predicted probabilities.
- Among 19,290 Stage 1 candidate complete next-over windows from 2018-2025, 27.85% contained at least one wicket. Window exclusions may introduce selection bias; final model cohort is deferred to Stage 3.
- First-innings runs correlated with final wickets lost (Pearson r=-0.507) and final legal balls (r=+0.337) in 2018-2025. A descriptive multiple regression using final innings quantities and season achieved in-sample R²~0.398; **it is not a forecasting model** and the final quantities cannot be used as known inputs before the innings ends.
- Match-level missing `city` records (51/1169) and structurally absent `winner`/`outcome_method` are documented; no MCAR/MAR/MNAR mechanism is claimed as proven.

This is the **first EDA session, not Stage 2 completion**. Subsequent sessions will deepen bivariate tests, confounding/stratification and interpretation.
