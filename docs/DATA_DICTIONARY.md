# Initial data dictionary (Stage II)

## `matches.csv`

- `match_id` string: Cricsheet source filename stem.
- `date` ISO date and `season` calendar year (audit any competition-specific season anomaly).
- `team1`, `team2`: normalized franchise strings; rename-only normalization.
- `venue`, `city`, `event`: strings as supplied or blank if missing.

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
