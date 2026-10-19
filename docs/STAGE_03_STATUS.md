# Stage 3 — Machine Learning: current status

**Session 01 is complete for development validation, not final deployment.** The Next-Over Wicket Predictor has been trained using historic pre-2025 matches, and validated exclusively on 2025. **2026 has not been evaluated or used for feature/model selection.** The Batter Milestone Predictor is scheduled for Session 02.

## Session 01: auditable wicket labels

- Build `data/processed/stage03_next_over_training.csv` from Stage 1 `overs.csv` and `matches.csv` using `python -m cricketlens.wicket_training_data`.
- The predictor is asked **after a fully completed over**, whether **at least one batting-team wicket will occur in the upcoming over**.
- Include following six-legal-ball overs with Yes/No labels; include next overs that end early if a wicket was already witnessed (known Yes); **exclude** early-ending overs without a witnessed wicket (censored outcome). Record audit-only `label_evidence` and `next_over_legal_balls`, neither of which enters model features.
- Exclude 23 D/L-marked matches from this first model cohort; keep those matches in raw/EDA data. Ignore Super Over deliveries (Stage 1 parser already excludes them); ordinary innings of tied games remain eligible.
- Exclude checkpoints affected by invalid 7-ball overs, broken sequencing or 10 wickets already down.

### Eligibility counts (full archival extract, **not** model-development results for 2026)

- 2,480 ordinary innings considered; 45,268 completed checkpoints reviewed.
- 619 D/L-marked checkpoints excluded; 14 anomalous/gapped checkpoints excluded; 474 shortened following overs without a wicket censored and excluded.
- 237 short following overs with a witnessed wicket included as known positives; 43,924 full following overs included.
- **44,161 eligible records** exported in the entire archive (2008–2026), **41,580 pre-2026**. The 2026 outcome labels are not accessed by training, tuning, plots, or validation reports.

## Session 01: actual development experiments

- Train through 2024; validate on 2025; do not touch 2026 for model performance until both model designs are frozen.
- Training: 39,019 checkpoint examples from 1,074 matches (2008–2024), with 16,575 examples when using 2018–2024 only.
- Validation: 2,561 checkpoint examples from 73 matches (2025), with observed wicket-event rate of **28.2702%**.
- Candidate algorithms: Logistic Regression with basic features (all history and 2018+); Logistic Regression with recent-over momentum, venue, and phase (2018+). Compare against constant historical wicket-rate baselines.
- Best validated candidate, **logistic_context_since_2018**: **Brier 0.197195**, **log loss 0.582958**, **ROC-AUC 0.596101**.
- Constant 2018–2024 event-rate reference: Brier **0.202796**, log loss **0.595524**; improvement in Brier **0.005601** (modest). 2,000-match-cluster resamples yielded a descriptive 95% interval **[0.002358, 0.008731]** for this comparison; note **selection on the same validation set** makes this not an independent confidence guarantee.
- The best model includes 11 **checkpoint-known** inputs: innings, completed overs, runs, wickets, run rate, last over runs, last over wickets, batting team, bowling team, innings phase, venue name. It does **not** use the future next-over event, label evidence, last legal-ball count or actual next bowler.
- Development artifact `models/wicket_development_pre2025.joblib` is local / ignored by Git. Run `python -m cricketlens.predict_wicket --help` to enter a hypothetical scenario. Do not describe it as the final 2027 model.

### 2025 performance by innings phase (observational)

| Upcoming-over phase | Validation n | Observed wicket rate | Mean forecast | Brier |
|---|---:|---:|---:|---:|
| Powerplay | 715 | 0.2336 | 0.2335 | 0.1813 |
| Middle overs | 1,266 | 0.2504 | 0.2560 | 0.1872 |
| Death overs | 580 | 0.4138 | 0.4254 | 0.2386 |

The event is much more frequent late in innings; higher Brier there is partially attributable to inherent uncertainty/class prevalence, not necessarily just a bad model. Calibration is uneven in sparsely populated high-probability bins; see reliability plot.

## Open limitations and next sessions

1. Session 02: Before-match batter milestone prediction using historical player form computed strictly before the chosen match. DNB/playing-XI handling and 30+/50+ coherence need design and tests.
2. Session 03: Freeze both model specifications, evaluate on the **unseen 2026 season once**, present calibration and performance, then separately refit on verified data through 2026 for future predictions.
3. Explicit runtime inputs should include previous-over runs and wickets for this preferred wicket model; update the Prediction Arena form accordingly. An unknown venue can be tolerated by one-hot encoding, but new teams and varying conditions require testing.
4. D/L excluded for initial model; censoring from shortened chases or interruptions is handled conservatively but can change the target population, causing selection bias. Explain at viva.
5. The reference event label is a **batting-team wicket**, excluding retired hurt and other non-wicket departures. We are predicting a *probability*, not a certain Yes/No result.
6. Model performance may be modest; we must not claim superiority on the 2026 holdout yet. We also must never train automatically on unverified browser feedback.

## Reproduce from repository root

```bash
pip install -e '.[dev]'
python -m cricketlens.wicket_training_data
python -m cricketlens.fit_wicket_models
python -m cricketlens.stage03_diagnostics
pytest -q
```

Required local inputs: `data/processed/overs.csv`, `matches.csv` generated from the Cricsheet archive (ignored by Git). Outputs: `data/processed/stage03_next_over_training.csv` and local `models/...joblib` (both ignored), tracked summary CSVs/JSONs and `reports/figures/stage_03/*.png`.
