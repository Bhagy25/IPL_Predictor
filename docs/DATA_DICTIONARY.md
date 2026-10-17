# Initial data dictionary (Stage 1 - preliminary)

## `matches.csv`

- `match_id` string: Cricsheet source filename stem.
- `date` ISO date and `season` calendar year (audit any competition-specific season anomaly).
- `team1`, `team2`: normalized franchise strings; rename-only normalization.
- `venue`, `city`, `event`: strings as supplied or blank if missing.
- `gender`, `winner`, `outcome_type`, `outcome_method`, `toss_winner`, `toss_decision`: match metadata for descriptive analysis, **not eligible** as pre-match model features when only known afterward (e.g. winner).

## `deliveries.csv`

- `match_id`, `date`, `season`, `innings`: match identifiers and number of ordinary innings.
- `batting_team`, `bowling_team`: normalized strings.
- `over_index`: 0-based Cricsheet over number, `delivery_index`: observed event index within over (includes illegals).
- `batter`, `batter_id`, `bowler`: names and Cricsheet person ID when available.
- `runs_batter`, `runs_extras`, `runs_total`: credited batter, extras and team runs for the event.
- `wides`, `noballs`, `byes`, `legbyes`: extra-type contributions.
- `legal_delivery`: 0 on wides/no-balls, 1 otherwise.
- `team_wickets_on_ball`: team wickets taken on event; retired hurt is not a team wicket.
- `innings_runs_after`, `innings_wickets_after`: accumulated within same ordinary innings.

## `next_over_samples.csv`

One eligible snapshot immediately after an over is fully completed, *before the next over starts*.

- Context: `match_id`, `date`, `season`, `innings`, `batting_team`, `bowling_team`, `venue`.
- Training features: `completed_overs`, `runs`, `wickets`, `run_rate` plus team/innings context.
- Label: `wicket_next_over`: 1 if at least one team wicket falls in following over, 0 otherwise.
- Quality: `next_over_legal_balls` records horizon length. A shortened next over is only labeled when the batting side is all out (known positive). Other partial-over outcomes are censored/omitted.

## `batter_innings.csv`

- `runs`, `balls_faced`, `dismissed`, `reached_30`, `reached_50`: per observed batter innings.
- `balls_faced`: wides excluded; no-balls faced included, per cricket notation.
- These are **raw outcomes**, not yet leakage-free pre-match features. Rollings/lagging must be computed for batter ML.

## `screening_issues.csv`

- `match_id`, `issue`: entries excluded/skipped due to malformed dates/teams or unusual overs. If empty, the CSV is empty with no header. Later data audit will add structured counts and treatment notes.


## `innings.csv`

- One regular batting innings per row, excluding Super Overs. Includes date, season, team/opposition/venue, team runs, team wickets, legal-ball count, and number of recorded overs.

## `overs.csv`

- One recorded regular-innings over per row (including partial last overs).
- `legal_balls`, `runs_after`, `wickets_after`: legal deliveries within that over and cumulative innings totals at its end.
- `complete_standard_over`: 1 exactly when there are six legal deliveries; >6 or 0 triggers screening issues.

## `reports/stage_01/` and `reports/figures/`

- `audit_summary.json`: computed archive counts, date coverage, missingness, reconciliation and screening summaries.
- `season_summary.csv`: match/inning counts, first-inning means and eligible wicket-event frequencies by season.
- `missingness.csv`: fields with blank or NA counts; absence may be *structural* rather than corrupted data.
- `wickets_by_over.csv` and `wicket_event_by_checkpoint.csv`: descriptive event rates; affected by the selection of eligible windows.
- Visualizations are descriptive (not causal, not proof of ML calibration).

## Stage 1 / Session 03 audited additions

- `venue` is the exact raw string from the source, **not overwritten**.
- `venue_canonical` is an additional, conservative canonical label in `matches.csv`, `innings.csv`, `batter_innings.csv` and `next_over_samples.csv`; specific mappings live in `src/cricketlens/venues.py` and are reviewable in `reports/stage_01/venue_alias_review.csv`.
- `reports/stage_01/source_audit_summary.json` summarizes raw-source exception classes, distinct player-ID name collisions, rain methods, tie/no-results, and Super Over innings.
- `reports/stage_01/raw_over_anomalies.csv` records four seven-legal-ball and four zero-legal-ball over records; zero-legal-ball innings endings are preserved as observed.
- `next_over_samples.csv` remains a *candidate* ML table: Stage 3 must apply policy for D/L matches and event censoring and reconstruct all pre-checkpoint features without leakage. Known over-length anomalies contaminate later runs and wickets; checkpoint rows after the anomaly are excluded.
- ML 2026 holdout rule is unchanged. CSVs contain 2026 rows for EDA, **not for training/tuning**.
