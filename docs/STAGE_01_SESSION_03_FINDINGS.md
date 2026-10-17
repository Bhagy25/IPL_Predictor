# Stage 1 / Session 03 - Source-level audit and corrections

## Purpose
Finish the dataset screening and cleaning phase before systematic EDA. Inspect original JSON files, not just CSV totals.

## Implementation
- Added `src/cricketlens/stage01_review.py`: reviews outcome types, incomplete matches, anomalous overs, extras and dismissals; writes named audit CSVs and summary JSON.
- Added `src/cricketlens/venues.py`: transparent exact-string venue aliases. Kept original `venue` plus a new `venue_canonical` column in match, innings, batter and next-over tables. No unverified stadium mergers.
- Strengthened the next-over sample generator: if an over records over six legal deliveries, that and later checkpoints in the same innings cannot be used as reliable learning examples.
- Added three tests for venue identity, reporting outputs and contaminated checkpoints.
- Re-ran source audit, CSV extraction, derived audit/reconciliation and automated tests on the user-provided raw ZIP.

## Results
- 1,243 matches (all male Indian Premier League), 2,480 ordinary innings and 295,557 deliveries.
- 60 raw venue names -> 38 canonical names; 22 names mapped, affecting 461 match records.
- 51 missing city fields: Dubai 33, Sharjah 18; kept missing.
- 16 ties, 9 no-results, 23 D/L-affected matches, six single-ordinary-innings matches, and 34 additional Super Over innings.
- Eight unusual over records: four with seven legal deliveries and four with zero legal deliveries.
- 1 player name (`Harmeet Singh`) appears with two distinct registry IDs, so IDs are needed for player identity.
- 0 duplicate match IDs, 0 run-total discrepancies and 0 innings reconciliation failures.
- Regenerated 44,706 **candidate** next-over snapshots, down from earlier preliminary 44,714.
- 9 synthetic automated tests passed; verified corrected outputs against source data.

## Interpretation, risks and limits
- 'Missing' metadata can be structural and cannot be indiscriminately imputed. MCAR/MAR/MNAR classification cannot be established solely from descriptive counts.
- The 7-legal-ball overs are *not* silently reinterpreted as 6-ball overs; their affected future training snapshots are omitted.
- Incomplete next-over horizons are censored rather than presumed negative.
- 608 candidate checkpoint rows occurred in matches with D/L methods; defining the final model's target population and eligibility will happen in Stage 3.
- Previously reported baseline scores are exploratory results for an older provisional cohort. Re-evaluate from scratch with the corrected cohort and hold 2026 out.

## Sign-off
**Stage 1 completed for EDA with known limitations disclosed.** Stage 2 is now ready. Final ML sample selection is explicitly reserved for Stage 3.
