# CricketLens development log

## 2026-10-17 - Session 01: repository foundation

**Decisions confirmed:** Men's IPL only; 2008-2026 as candidate history; team rename normalization; six-tab EDA-first website; Model 1 batter 30+/50+; Model 2 next-over wicket; no login; record every forecast and verified actual outcome; retraining optional and manual only.

**Built:**
- Initialized version-control-ready structure with `.gitignore`, `pyproject.toml`, and setup guide.
- Cricsheet JSON extractor with match/delivery/batter-innings/over-checkpoint exports.
- Starter next-over wicket logistic-regression training/validation script (not trained yet).
- Basic descriptive statistics script, synthetic match fixture, automated tests.

**Why these choices:**
- EDA must precede modeling in IT462.
- Wicket labels must use team wickets and account for illegal balls and incomplete overs.
- Temporal validation prevents future match information leakage.
- No login reduces unnecessary backend complexity; browser localStorage will retain tracker entries per browser.

**Blockers:** Official Cricsheet raw IPL JSON archive is not accessible in the current session's mounted files; direct download attempt failed. Actual dataset measurements, algorithm accuracy, deployed model, and website remain pending.

**Next action:** Add `ipl_json.zip` under `data/raw/`, run extraction, inspect screening issues, and add a data dictionary + quality findings to report.

**Academic report evidence:** Stage I scope; Stage II extraction design, audit rules, synthetic test cases. No observational results are claimed.

**Verification at end of Session 01:** `PYTHONPATH=src pytest -q` -> **4 passed**. The synthetic match extraction produced one synthetic match, 20 recorded delivery events, two eligible next-over checkpoints and three batter-innings rows. The trainer passed an additional *synthetic-only* season-split smoke test; these are engineering tests, not IPL model results.

## 2026-10-17 - Session 02: real IPL archive screening, initial EDA and wicket baseline

**Input:** User-supplied `ipl_json (1).zip` (Cricsheet men's IPL JSON). ZIP integrity checked; 1,243 match JSON files plus README/LICENSE, covering 2008-04-18 through 2026-05-31. Archive itself remains out of Git via `.gitignore`.

**Implemented / checked:**
- Ran actual JSON extraction, yielding 1,243 matches, 2,480 ordinary innings, 47,756 recorded overs, 295,557 delivery events, and 18,768 observed batter innings. Super-overs are excluded.
- Created 44,714 eligible next-over wicket examples (complete prior over; next over contains six legal deliveries OR ends with confirmed all-out), of which ~27.70% were positive. Incomplete censored future overs are not labeled as zeros.
- Added `innings.csv` and `overs.csv`, winner/toss/outcome metadata, and audit/plot generator `python -m cricketlens.data_audit`.
- Standardized the *same* discontinued Rising Pune Supergiants / Supergiant franchise; kept Deccan Chargers, SRH, Gujarat Lions and Gujarat Titans distinct.
- Source quality: 550 censored next-over windows, 4 overs with >6 legal balls, 4 zero-legal-ball recorded overs, and 4 invalid future-over windows. These are **562 issue rows**, not 562 uniquely bad matches; multiple issue codes can apply to one match. The 4 invalid future-over windows were removed, versus the first-pass parser.
- Inning run/wicket/legal-ball reconciliation succeeded for **all 2,480 ordinary innings** (zero mismatches).
- Missing `city`: 51/1,243 (4.10%); missing match `winner`: 25/1,243 (16 ties, 9 no-results); missing `outcome_method` indicates ordinary matches, not 98.15% corrupt fields. Venue is populated in all 1,243 match records.
- Actual descriptive EDA: 401,423 recorded runs, 14,655 team wickets, 284,465 legal deliveries; mean/median first-innings totals 168.57 / 168.0; 30+ milestone rate 25.53%, 50+ rate 11.27% among recorded batting innings (conditional on batting).
- Generated season and missingness summaries and four charts into `reports/stage_ii/` and `reports/figures/`.
- Trained **simple logistic-regression wicket baseline** on pre-2025 examples (39,503 rows) and evaluated **2025 only** (2,596 windows). 2025 Brier: model 0.19831 vs constant-rate baseline 0.20319, log loss 0.58561 vs 0.59638, ROC-AUC 0.59223. Modest improvement; do not overclaim effectiveness. The 2026 ML test is deliberately not run.
- Automated tests now **6 passed**, including audit reconciliation and an anomalous seven-legal-ball over case. Tests are engineering checks, not accuracy guarantees.

**Limitations / follow-ups:** More EDA needed on venue aliasing, team performance bias, rain/DLS, missingness mechanisms, uncertainty and chronological player form features. No pre-match batter predictor or website exists yet. The next-over classifier remains a simple validation baseline; 2026 stays the held-out period for a later one-time evaluation after model selection. User feedback will only evaluate predictions; retraining is optional and manual using verified original outcomes.

**GitHub Desktop instructions:** Copy updated code/docs/reports into local repo, review Changes, Commit to main, Push origin. Do not commit `data/raw`, `data/processed`, or `models`.

## 2026-10-17 — Stage labeling clarification (documentation only)

Canonical development stages: Stage 1 = cleaning; Stage 2 = systematic EDA; Stage 3 = two prediction models; Stage 4 = dashboard; Stage 5 = integration; Stage 6 = final report. Prior use of “Stage II” in generated code and report paths referred to academic screening conventions and did not mean our development Stage 2 was finished. The original sessions are preserved for audit; this package labels datasets and audit as Stage 1, with charts and baseline clearly identified as preliminary later-stage experiments. No new IPL data cleaning or ML evaluation is claimed by this documentation correction.

## 2026-10-17 - Stage 1 / Session 03: final source audit

- Audited all 1,243 original men's IPL match JSON files, not just processed CSVs.
- Confirmed 0 team-runs/innings reconciliation discrepancies, 0 duplicate IDs and 0 negative ball run fields.
- Added source-level anomaly reporting, venue alias maps, identifier collision reporting, and 3 new tests (9 passing in total).
- Preserved 51 missing city fields (Dubai/Sharjah); documented 16 tied and 9 no-result games and 23 D/L matches.
- Flagged four 7-legal-ball overs; corrected candidate next-over sample selection to exclude contaminated future checkpoints (44,706 rows now).
- Kept four legitimate 0-legal-ball final overs (winning wides) as observed.
- **Stage 1 signed off for EDA with exceptions.** Important model eligibility rules (D/L and censored windows) are deferred to Stage 3.
- Next: Stage 2 systematic statistical EDA. Prior experimental model metrics are superseded, not final results.


## Stage 2 / Session 01 - First systematic EDA (18 Oct 2026)

- Loaded Stage 1 audited local CSV tables; no raw-data cleaning changes.
- Enforced seasons <=2025 for development-stage findings to preserve 2026 ML test outcomes.
- Added `src/cricketlens/stage02_eda.py` and unit tests; generated 11 analytical charts and CSV/JSON data evidence.
- Recorded real results and caveats in `docs/STAGE_02_SESSION_01_FINDINGS.md` and `docs/STAGE_02_STATUS.md`.
- No ML retraining or 2026 holdout assessment performed.
- Stage 2 remains in progress. Next: stratified EDA, missingness mechanism reasoning, cross-tab/hypothesis work, finalize academic EDA chapter.

## Stage 2 / Session 02 — Deeper EDA (2026-10-18)

- Added `stage02_deep_eda.py`: length-stratified first-innings distributions, 5% trimmed mean and Tukey outlier review, within-innings Powerplay/death paired analysis, season-centered full-innings venue comparisons with bootstrap bands, toss-decision/outcome crosstab, and observed-field missingness review.
- Reproducible figures `12`–`17`, data tables under `reports/stage_02/session_02/`, markdown findings and PDF report.
- Preserved all 2026 matches as future test-set data (not queried for statistics or model fitting).
- These analyses are exploratory/associational, not a third ML model or a causal experiment.
- Tests: see automated `pytest` run (synthetic edge cases added) and accompanying Session 02 report.
- Stage 2 remains in progress pending synthesis and academic review.


## Stage 2 / Session 03 — Exceptional outcomes and EDA consolidation (2026-10-18)

- Audited the raw Cricsheet `outcome.eliminator`, `outcome.result`, `outcome.winner`, and D/L outcome.method fields. Verified 16 Super Over ties and 9 no-results in 2008–2026 (counts for input integrity only).
- Updated `pipeline.py` match schema with `regulation_result`, `final_winner`, `super_over_winner`, `super_over_innings`, `decided_by`, retaining original `winner`/`outcome_type`. Kept Super Over deliveries out of ordinary innings.
- Re-ran cleaned table extraction and regenerated affected Stage 2 Session 01 and Session 02 team/toss tables. Corrected 2022–2025 DC wins from 25 to 26 and the pre-2026 toss table.
- Added `stage02_final_eda.py`, exceptional-match summary outputs, 3 charts, and synthetic match tests.
- Consolidated core descriptive EDA and remaining ML limitations; no 2026 model evaluation or final model fitting.
- **Next:** Stage 2 feature branch review and PR; then Stage 3 model design (one-over censoring + batter 30/50 milestones).
