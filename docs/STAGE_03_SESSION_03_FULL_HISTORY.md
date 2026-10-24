# Stage 3 / Session 03 — FULL historical IPL training (2008–2026)

**Status: one-time holdout evaluation performed, deployment artifacts refitted through 2026.**

## Exact experimental sequence

1. **2008–2024:** Fit candidate model specifications using full historical data (not only 2018 onward).
2. **2025:** Validate on eligible 2025 records; choose by lowest Brier score using 2025 only. The wicket model uses a binary event; the batter model uses three mutually exclusive classes (<30, 30–49, >=50) to ensure P(50+) <= P(30+).
3. **2008–2025:** Refit those selected specifications using all eligible pre-2026 examples.
4. **2026:** Run a *single held-out* evaluation without fitting model weights to 2026 targets. Preserve outputs and baseline comparisons.
5. **2008–2026:** Refit the same specifications on all eligible data and save separate deployment artifacts for future forecasting. **The 2026 holdout performance does not independently validate the new 2026-refitted artifacts**, because 2026 is now in their training set.

2026 batter features may use results from **earlier matches in 2026** (strictly earlier dates), because those results would have been available before the later 2026 match. Future-day and same-day batting results cannot influence a prediction feature. The model weights were frozen at the end of 2025 for this evaluation. Wicket context is available at the completed-over checkpoint only.

## 2025 algorithm selection (full-history training)

- Wicket candidates: simple Logistic Regression and context-rich Logistic Regression. Chosen: `logistic_context_all_history`. 2025 Brier score: 0.1971.
- Batter candidates: multinomial Logistic Regression and Random Forest. Chosen: `forest_full_history`. 2025 averaged 30+/50+ Brier: 0.1531.
- 2026 was NOT used to pick the selected candidates. Full-history training was an explicit user requirement; more history does not necessarily outperform shorter history on every validation metric.

## Final independent 2026 scores

| Model / event | 2026 observations | Model Brier | Constant-rate baseline Brier | Log loss | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Next-over wicket | 2,581 | 0.200519 | 0.204936 | 0.589813 | 0.589476 |
| Batter 30+ | 1,113 | 0.185299 | 0.209614 | n/a (see multiclass) | 0.708762 |
| Batter 50+ | 1,113 | 0.117947 | 0.129097 | n/a (see multiclass) | 0.728988 |

Milestone multiclass log loss: **0.743083**; constant baseline: 0.818114. All ML scores are lower-better for Brier/log loss, higher-better for ROC-AUC. Predictions are probabilistic—not guaranteed correct for each event.

## Sample sizes & artifact separation

| Model | Train 2008–2024 | 2025 validate | Fit 2008–2025 | 2026 holdout | Final fit 2008–2026 |
|---|---:|---:|---:|---:|---:|
| Wicket | 39,019 | 2,561 | 41,580 | 2,581 | 44,161 |
| Batter | 16,231 | 1,085 | 17,316 | 1,113 | 18,429 |

### Saved local models (not committed to GitHub)

- `models/wicket_holdout_train_through_2025.joblib` — testable 2026 *holdout* model.
- `models/batter_holdout_train_through_2025.joblib` — testable 2026 *holdout* model.
- `models/wicket_deployment_through_2026.joblib` — future-score manually entered.
- `models/batter_deployment_through_2026.joblib` — future-date player milestone forecasts.

The model scripts do **not** auto-update weights from browser feedback. All records used for future retraining must be verified first.

## Assumptions / limitations

- D/L-marked matches excluded from initial ML cohort; no-result batting excluded; regular innings of Super Over matches retained, Super Over deliveries excluded.
- Next-over observations ending early without a witnessed wicket are censored/excluded; early-ending positive observations are retained; this definition can introduce selection bias.
- Batter result is **conditional on batting appearance**; absence/DNB and batting position are not predicted; future player rosters must be checked separately.
- Source player IDs are stable and may differ from displayed names. Venue labels must use canonical normalization.
- A simple constant baseline was beaten on the 2026 holdout, but the wicket model's gain is **modest**. Does not guarantee future performance; 2027 cannot be measured until matches occur.
- Final models are reproducible, but a web API, interactive UI, actual-match verification and deployment are **Stage 4/5 tasks**, not completed here.

## Run from repository root

```bash
pip install -e '.[dev]'
python -m cricketlens.stage03_full_history
python -m cricketlens.stage03_full_history_diagnostics
pytest -q
```

Requires local `data/processed/matches.csv`, `overs.csv`, `batter_innings.csv`. Generated CSVs and .joblib are ignored by Git; the tracked code and aggregate reports reproduce them. See `reports/stage_03/session_03/stage03_session03_final_results.json`.

## Questions to defend in the viva

1. Why are model selection and holdout performance measured in different seasons?
2. Can earlier 2026 matches be used as batter-form features for later 2026 matches? Under what conditions?
3. Why is the 2026-refitted model not evaluated on 2026 again?
4. What does a Brier score of 0.2005 tell you compared with 0.2049?
5. Does including all 2008–2017 matches necessarily improve future predictions?
6. What happens if a selected batter is not in the playing XI or never bats?
7. How are D/L, Super Over and short next-over events handled?
8. Why might a next-over model predict a low chance of wicket despite a wicket actually falling?
