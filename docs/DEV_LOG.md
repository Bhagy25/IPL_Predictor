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
