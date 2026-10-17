# Stage 1 - Dataset Screening & Cleaning

**Status: COMPLETE FOR EDA (with documented exceptions)**  
**Reviewed:** 2026-10-17  
**Dataset:** User-supplied Cricsheet men's IPL JSON archive, 1,243 matches / 2008-2026.

## What passed

- All 1,243 matches are men's Indian Premier League; dates, events and teams parsed.
- 2,480 regular innings; Super Overs remain excluded from ordinary innings/ML samples.
- 295,557 regular delivery records reconcile exactly with innings runs, wickets and legal balls.
- Zero duplicate match IDs, negative run fields or ball-level total-run mismatches in raw inspection.
- 9 automated tests passed against synthetic edge cases; real-data screening is separate.
- Venue names are now standardized conservatively: 60 raw strings -> 38 canonical strings, original preserved.
- Person IDs are retained, including the two distinct IDs associated with the name "Harmeet Singh".
- Structural missingness, weird overs, and rain interruptions are documented in audit CSVs.

## Decisions, not silent 'fixes'

- `city`: 51 blanks, all at Dubai International Cricket Stadium (33) or Sharjah Cricket Stadium (18). Left blank in source table; no unsupported inference or statistical imputation.
- `winner`: 25 blanks correspond to 16 tied and 9 no-result matches. Retain their outcomes instead of imputing a winner.
- `outcome_method`: 1,220 blanks mean no D/L method was recorded, rather than necessarily damaged data; 23 explicit D/L cases.
- Four 7-legal-ball overs in original source: flagged as anomalous, left unmodified. Training checkpoint samples at/after the flawed over in those innings are excluded.
- Four 0-legal-ball final overs ended with a wide during successful chases. The zero legal-ball count is explainable, not a reason to invent an extra ball.
- Six matches have only one regular innings; this is a source property, not automatically a parse failure.
- 34 Super Over innings excluded from standard innings records.
- Source penalty extras are retained in team totals; only named extras selected in delivery CSV are separate columns.

## Scope boundary: not yet final ML-ready

- **44,706 next-over rows are candidate snapshots, not a final training cohort.**
- **608 candidate snapshots** belong to the 23 matches with D/L outcome method, so Stage 3 should establish an explicit exclusion/handling rule.
- Incomplete future overs with no team all-out are excluded (censored). This can change the population whose wicket probabilities are calibrated; assess selection bias in Stage 3.
- Player milestone features still require past-only aggregates and clear eligibility (announced lineup / batting appearance).
- Pre-existing 2025 validation numbers in `reports/preliminary_stage_03` predate this revised pipeline and must **not** be presented as final model performance.
- The IPL 2026 season remains unseen for ML development; descriptive data-quality summaries across all seasons are permitted.

## Outputs

Source code: `src/cricketlens/pipeline.py`, `venues.py`, `stage01_review.py`, `data_audit.py`  
Quality outputs: `reports/stage_01/source_audit_summary.json`, `venue_alias_review.csv`, `missing_city_cases.csv`, `raw_over_anomalies.csv`, `player_name_id_collisions.csv`, `missingness.csv`, `audit_summary.json`  
Derived local tables: `data/processed/*.csv` (gitignored)

## Stage 1 -> Stage 2 hand-off

EDA can begin on these curated tables. Report the known limitations alongside any statistics. Keep predictive feature construction and final eligibility decisions for Stage 3.
