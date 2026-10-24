# Stage 3 / Session 02 - Beginner's guide to training the batter model

## What is being learned?

We ask: **Assuming this player has a batting innings in the upcoming IPL match, what is the chance of scoring 30+ runs and 50+ runs?** The model does not know the innings score in advance. It only sees their historical form and opponent/venue/team context.

Think of every historical batter inning as one study example.

| Term | Simple definition | CricketLens instance |
|---|---|---|
| Feature, X | Information we would know before a match | Previous five innings average, past opposition record |
| Target, y | What actually happened afterward | 0 = <30, 1 = 30-49, 2 = 50+ |
| Training | Let the algorithm learn historical relationships | Player innings through 2024 |
| Validation | Measure model quality on later data and choose a candidate | 2025 innings |
| Testing | Final independent evaluation after choices are frozen | 2026 (not done yet) |
| Inference | Make a probability forecast using already-trained weights | Show P30+ and P50+ |

## Step-by-step flow

1. **Load** `batter_innings.csv` and the corrected `matches.csv` from Stage 1/2.
2. **Screen** for invalid labels, blank player IDs, D/L-marked and no-result matches; filter out 2026 entirely.
3. **Build snapshots**: at each match date, compute player form using strictly *earlier* match dates, even when there are multiple matches on a day.
4. **Create categories**: <30, 30-49, 50+ from the actual runs, stored for training only.
5. **Split by year**: train through 2024, validate on 2025. We do not randomly mix rows.
6. **Train models**: Logistic Regression and Random Forest. The library's `.fit(X_train, y_train)` is the central operation; input preparation takes more code.
7. **Generate probabilities** with `.predict_proba(X_valid)`. Add class 1 + class 2 to get P30+, and use class 2 for P50+.
8. **Compare baselines**: if our model cannot beat simply using a player's past milestone frequency, adding complexity may not be justified.
9. **Save the model** as `.joblib` locally, generate plots and record the limitations.

## Why not call 2025 "the test"?

We are selecting models using its performance, so **2025 is validation**. We keep 2026 fully unseen until we freeze our choices, then evaluate it exactly once. If we change the model based on 2026, 2026 would no longer be an unbiased final test.

## What does a Brier score mean?

For an event with predicted chance `p`, the realized outcome is `y=1` if it happened and `y=0` otherwise. The Brier score is the average `(p-y)^2` across examples. **Lower is better.** The batters model uses separate 30+ and 50+ Brier scores and averages them to rank candidates.

A 70% forecast is not a promise: if an event doesn't happen, it contributes `(0.70-0)^2 = 0.49` to the Brier score. A model should be judged across a large sample and by how well forecasts align with empirical event frequencies.

## Current limitations you should say out loud at the viva

- **No appearance model**: someone outside the XI or who does not bat is not a 0-run failure; our task is conditional on a recorded innings.
- **No future batting position feature**: actual batting order is known only later and would leak information.
- **No automatic retraining from browser feedback**: only verified IPL outcomes can be used in a later explicit retraining step.
- **No claimed 2027 model**: the saved development model is trained through 2024, and 2026 is still unseen.
- **Modest improvement**: Random Forest beat the smoothed player-history baseline on 2025 average Brier by about 0.00224; a small advantage that needs independent holdout evaluation.

See `docs/STAGE_03_SESSION_02_BATTER_MODEL.md` for the auditable numerical report.
