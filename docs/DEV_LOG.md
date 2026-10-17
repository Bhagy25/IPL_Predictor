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
