# Stage 3 / Session 02 - Pre-match Batter Milestone Predictor

**Status:** Development model trained and validated on 2025. **2026 holdout unopened.** The full Stage 3 ML stage is **not complete**: one-time 2026 testing and final refit remain for Session 03.

## Problem statement and unit

Before an IPL match, estimate **P(batter scores >=30)** and **P(batter scores >=50)**, **conditional on that batter having a recorded batting innings**. The initial model does not predict playing-XI membership, whether a named player will get to bat, or DNB cases. It does not use actual batting position from the future match, in-match information, toss outcome, innings position, or the match's actual runs as features. Use only confirmed/expected participants when the final website is implemented.

Each example is one **player innings** identified by stable `batter_id` plus match/innings, not a ball-level example. The player does not change identity when their team changes. We distinguish historical innings from the availability of a player for a new season.

## Eligibility from verified Cricsheet extract

- Initial raw batter-innings rows from seasons <=2025: **17,638**.
- D/L (or DLS) match-level flagged rows excluded from this first ML cohort: **263**.
- Additional no-result match rows excluded: **59**. Some legitimate batting innings may therefore be lost; this is a conservative initial choice.
- Eligible player innings through 2025: **17,316**; distinct players **702**.
- Target classes: `<30` **12,940**; `30-49` **2,463**; `50+` **1,913**.
- Cold starts (zero earlier eligible batting innings) **702** across 2008–2025. Includes first observed innings for each player.

Crucially, these ML exclusions do **not** delete D/L matches, Super Over final winners, or no-result records from the EDA dataset. Normal innings of matches later decided in a Super Over may be used; the super-over innings themselves were excluded by Stage 1 parsing.

## Preventing information leakage

1. `batter_training_data.py` first filters out season 2026, then excludes flagged D/L/no-result match records.
2. For every calendar date `d`, compute all player form features using batting innings on dates **strictly earlier than `d`**. Only then update history with that date's runs. Players in two records on the same date cannot leak outcomes between them.
3. Past-player features: career average and historical 30+/50+ frequencies; last 5/10 innings run averages and event rates; previous appearances vs the *current* opposition and at the *current* standardized venue; history counts and days since previous appearance.
4. Current match context available before play: the selected batting team, the opponent and venue.
5. Training features are a **hardcoded whitelist** in `fit_batter_models.py`. `actual_runs`, current-match class/targets, balls faced, toss and actual batting position are NEVER included.
6. Feature histories for later 2025 matches may include actual earlier 2025 innings (known before those later matches), but fitted model parameters never learn from 2025 outcomes. Train only through 2024, validate on 2025.

**Important interpretation:** Models trained using the 2018–2024 rows can still use pre-2018 innings in the historical player-form features at those dates. The training window refers to labeled examples used for fitting, not necessarily the span of permissible past form.

## Why one three-category classifier?

We fit **one multiclass classifier** with mutually exclusive targets:

- class 0: fewer than 30 runs;
- class 1: 30–49 runs;
- class 2: 50 or more runs.

At inference, `P(30+) = P(class1) + P(class2)` and `P(50+) = P(class2)`. This mathematically guarantees `P(50+) <= P(30+)`, avoiding conflicting independent binary models. Do not use the 2025 achieved outcome to predict the same match.

## Training and 2025 validation

- Fitting: eligible **16,231 player innings** across **1,069 matches** through 2024; 2018+ comparisons also included.
- Validation: **1,085 player innings** across **70 matches** in 2025; **30** first-time recorded players in validation.
- Model candidates: simple Logistic Regression, feature-rich Logistic Regression (2018+ and all-history training), and a constrained Random Forest (2018+). Baselines: two constant historical milestone frequency distributions and a smoothed individual prior-player form baseline.
- Selection metric: average of 30+ and 50+ Brier scores, with three-class log loss also reported.

| 2025 validation measure | Selected model (`forest_full_form_2018plus`) | Smoothed player-history baseline | Constant recent-history baseline |
|---|---:|---:|---:|
| 30+ Brier (lower better) | 0.194459 | 0.197376 | 0.217188 |
| 50+ Brier (lower better) | 0.109510 | 0.111076 | 0.118775 |
| Mean milestone Brier | **0.151985** | 0.154226 | 0.167981 |
| Three-class log loss | 0.772682 | 0.793569 | 0.841330 |
| ROC-AUC 30+/50+ | 0.6954 / 0.7319 | 0.6770 / 0.7062 | 0.5000 / 0.5000 |

- Descriptive improvement in mean Brier vs smoothed player baseline: **0.002241**, clustered bootstrap (by match) percentile interval **[0.000397, 0.003978]** from 1,200 resamples. The best model was selected on the same 2025 data; this **is not** an independent confidence statement or final generalization guarantee.
- Even a good Brier or AUC does not prove that the model is well calibrated at all probability levels, players, grounds or new IPL eras; check reliability plots and small-bin support.

## Known limitations and next steps

- The outcome is conditional on a **recorded batting innings**. The system cannot claim an unconditional pre-match milestone probability if a player might not play or may not bat. The final UI must explain this.
- We do not yet use expected batting order; it is an optional future input only if we can construct an equally known-before-match feature historically. Actual batting position leaks if substituted naively.
- First-appearance players have no historical form and forecasts are uncertain; evaluate separately or display a cold-start warning.
- D/L/no-results excluded conservatively; testing whether excluding them biases who appears in the cohort is important.
- 2025 is used for model selection, so differences may be optimistic. **Freeze choices and evaluate exactly once on 2026** in Session 03; then refit through 2026 for potential 2027 use, without calling refit scores test metrics.
- Browser user feedback is not automatically trustworthy training data. Retrain only after matching recorded forecasts to verified historical match outcomes.

## Reproducible commands (repo root)

```bash
pip install -e '.[dev]'
python -m cricketlens.batter_training_data
python -m cricketlens.fit_batter_models
python -m cricketlens.stage03_batter_diagnostics
pytest -q

# 2025 historical held-out replay (NOT a 2027 match prediction)
python -m cricketlens.predict_batter --match-id 1473438 --player-id 29e95537
```

Inputs must exist **locally** at `data/processed/batter_innings.csv` and `data/processed/matches.csv` (corrected outcome schema). No large data/model artifacts go into GitHub. Generated training CSV: `data/processed/stage03_batter_training_pre2026.csv`; serialized model: `models/batter_development_pre2025.joblib` (ignored by Git). Reports + figures + these notes are tracked.
