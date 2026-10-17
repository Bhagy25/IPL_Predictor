# Stage 01 — Dataset Screening & Cleaning

**Status: IN PROGRESS** | Last updated: 2026-10-17 | Source: user-supplied Cricsheet men's IPL JSON archive.

## Stage 1 scope
Understand raw data, parse JSON correctly, standardize identities, define legal deliveries, count runs and team wickets, inspect missing fields and anomalies, and build reproducible analysis tables. Stage 1 does **not** mean EDA or model development is complete.

### Completed initial implementation
- Checked ZIP and parsed 1,243 men's IPL match JSON files (2008–2026).
- Created 7 CSV tables: matches, innings, overs, deliveries, batter_innings, next_over_samples, screening_issues.
- Reconciled runs, wickets and legal deliveries for 2,480 ordinary innings.
- Identified 51 missing `city` fields, 25 matches without declared winner (including ties/no-results), 550 censored windows, and other anomalous overs.
- Created tests for parsing and cricket-specific accounting (6 synthetic tests previously passed).
- Produced an initial data dictionary, audit tables and documented decisions.

### Still required before Stage 1 sign-off
- Investigate anomalous overs and rain/DLS/shortened innings, not just count them.
- Resolve/flag venue naming aliases; re-check player identities/transfers and franchise renames.
- Create final missingness table, justified treatment and limits on MCAR/MAR/MNAR claims.
- Check duplicate/invalid entries and file/record consistency; record exclusions clearly.
- Check wicket target selection bias due to censored innings and define final eligibility.
- Rerun parser, tests, reconciliation and data dictionary; review Stage 1 audit report.

### Stage 1 outputs / separation from later stages
- `data/processed/*.csv` — derived outputs, local and **gitignored**, NOT final audited data.
- `reports/stage_01/*` — data quality summaries and counts.
- `reports/figures/*` — exploratory plots made early (preliminary **Stage 2**, not stage completion).
- `reports/preliminary_stage_03/*` — experimental wicket validation record (preliminary **Stage 3**, not final model).
- `reports/archive/` — older session reports whose historical labels should not be mistaken for current development stages.

**GitHub Desktop commit suggestion:** `Stage 1: IPL parsing and initial data quality audit`.
