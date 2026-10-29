# data/processed

Tables built from the Cricsheet IPL ball-by-ball JSON in `data/raw/ipl_json/` (1,243 men's IPL matches,
2008–2026). They are committed so the analysis, the API and the tests run from a fresh clone without
rebuilding anything, and every table can be regenerated with the commands below.

| File | Rows | Columns | Produced by | Contents |
|---|---:|---:|---|---|
| `matches.csv` | 1,243 | 20 | Stage 1 pipeline | One row per match: date, season, teams, venue (raw and canonical), toss, result, winner (including Super Overs), method |
| `innings.csv` | 2,480 | 12 | Stage 1 pipeline | One row per ordinary innings: batting and bowling team, runs, wickets, legal balls, overs recorded |
| `deliveries.csv` | 295,557 | 22 | Stage 1 pipeline | One row per ball event in ordinary innings (Super Over balls excluded), with extras and legality |
| `overs.csv` | 47,756 | 11 | Stage 1 pipeline | One row per over per innings with its runs and wickets |
| `batter_innings.csv` | 18,768 | 15 | Stage 1 pipeline | One row per batter who faced a ball in an innings: runs, balls, dismissal flag, 30+/50+ flags |
| `next_over_samples.csv` | 44,706 | 14 | Stage 1 pipeline | Next-over checkpoints used by the Stage 1 baseline (state after each completed over and whether the next over had a wicket) |
| `screening_issues.csv` | 574 | 2 | Stage 1 pipeline | Data-screening findings logged while parsing (for audit, not used by the app) |
| `stage03_wicket_full_history_2008_2026.csv` | 44,161 | 17 | Stage 3 Session 3 | Eligible next-over training rows for the wicket model (D/L-marked matches excluded) |
| `stage03_batter_full_history_2008_2026.csv` | 18,429 | 30 | Stage 3 Session 3 | Eligible batter-innings rows with past-only form features for the milestone model (D/L and no-result matches excluded) |

Row counts exclude the header line. The two Stage 3 tables are the exact training data of the deployment
models; the API also reads `stage03_wicket_full_history_2008_2026.csv` to show the observed range of each
input in the Prediction Arena.

## Rebuilding

```bash
# Stage 1: the seven base tables from the raw JSON
python -m cricketlens.pipeline data/raw/ipl_json --output data/processed

# Stage 3 Session 3: the two training tables (this also refits and re-saves the models in models/,
# so run it only to reproduce Stage 3, not as part of normal use)
python -m cricketlens.stage03_full_history
```

The bowler-credited dismissals, squads, registry IDs and other tables the website needs are in
`data/derived/` (see `data/derived/README.md`).
