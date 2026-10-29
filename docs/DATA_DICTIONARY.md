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


### Stage 2 / Session 03 correction — match outcomes

- `winner`: ordinary source `outcome.winner`, blank on regulation ties decided by Super Over. Retained for provenance.
- `outcome_type`, `regulation_result`: ordinary regulation outcome, `win`, `tie` or `no result`.
- `super_over_winner`: normalized Cricsheet `outcome.eliminator` for tied games; otherwise blank.
- `final_winner`: ordinary winner or, if tied, Super Over winner. Blank for no-result matches. **Use this for final match win rate and winner-based toss statistics**.
- `decided_by`: `regulation`, `super_over` or `no_result`.
- `super_over_innings`: number of extra innings recorded as `super_over: true`. Excluded from normal innings/ball/player tables.
- `outcome_method`: raw method string such as `D/L`; denotes match-result annotation, not reliable shortened-innings indicator.


## `data/derived/` tables (website support)

Built from the raw Cricsheet JSON by `python -m cricketlens.derived_events --raw data/raw/ipl_json --output data/derived`.
They add what `deliveries.csv` does not carry (dismissal kind, player out, fielders, bowler registry IDs, the
non-boundary flag, squads and substitutions) and a registry-ID player table. `data/derived/README.md` is the
generated reference, with the SHA256 of each file; the rebuild reproduces the committed files exactly.

Delivery key: `match_id`, `innings` (1-based position in the file; super-over innings keep their position and
are flagged), `over_index` (0-based) and `delivery_index` (1-based, wides and no-balls included), the same
convention as `deliveries.csv`. `season` is the year of the first match date. Team names use Stage 1's
franchise mapping.

| Table | Rows | One row per | Columns |
|---|---:|---|---|
| `dismissals.csv` | 14,705 | Wicket event, super overs included (flagged) | delivery key, `season`, `date`, `is_super_over`, `batting_team`, `bowling_team`, `batter`/`batter_id`, `non_striker`/`non_striker_id`, `player_out`/`player_out_id`, `kind`, `bowler`/`bowler_id`, `fielders`/`fielder_ids` (semicolon-separated, substitutes included), `bowler_credited`, `counts_as_batting_dismissal` |
| `non_boundary_events.csv` | 29 | Delivery Cricsheet flags with `runs.non_boundary` (e.g. an all-run four) | delivery key, `season`, `date`, `is_super_over`, `batter`/`batter_id`, `bowler`/`bowler_id`, `runs_batter` |
| `batting_appearances.csv` | 19,111 | Player per ordinary innings at the crease as striker or non-striker (or dismissed) | `match_id`, `season`, `date`, `innings`, `batting_team`, `player_id`, `player_name`, `balls_faced` (wides excluded), `runs`, `dismissed`, `dismissal_kind`, `faced_a_ball`, `on_strike` |
| `match_players.csv` | 27,909 | Player per match in the official squad list (`info.players`), substitutes who came in included | `match_id`, `season`, `date`, `team`, `player_name`, `player_id` |
| `match_replacements.csv` | 563 | Match-level substitution in `replacements.match` (Impact Player or concussion substitute) | delivery key, `season`, `date`, `is_super_over`, `team`, `reason`, `player_in`/`player_in_id`, `player_out`/`player_out_id` |
| `people.csv` | 816 | Registry ID seen as a listed player or a fielder | `player_id`, `names` (every variant, semicolon-separated), `first_season`, `last_season`, `matches`, `teams` |

Rules:

- `bowler_credited` is True for bowled, caught, caught and bowled, lbw, stumped and hit wicket; False for run
  out, retired hurt, retired out, obstructing the field and any other kind.
- `counts_as_batting_dismissal` is True for every kind except retired hurt and retired not out, the same rule
  Stage 1 uses for team wickets, so retired out counts as a dismissal.
- In `batting_appearances.csv` a non-striker run out without facing a ball is an innings and a dismissal; the
  rows with `on_strike` True are exactly Stage 1's `batter_innings.csv` rows.
- `match_players.csv` holds each team's starting eleven plus every player who came in, so a team's list for a
  match is 11 plus its substitutions. Mid-over role changes are not substitutions.
- Substitute fielders who never appear in an official list have `matches` = 0 and empty seasons and teams in
  `people.csv`.
- Super-over rows are kept and flagged, never mixed into ordinary innings.
