# Your first ML model - CricketLens explanation

The next-over predictor is a **binary classification** problem: **1** means at least one team wicket falls in the upcoming completed over; **0** means no team wicket falls. We predict the probability of 1, not a guarantee.

- **One row (`X`)**: an observed match checkpoint, e.g. 110 runs, 3 wickets after 13 completed overs, batting team, bowling team.
- **The target (`y`)**: whether a team wicket fell in the next over (made from later deliveries solely for training labels, never input features).
- **`fit()`**: learns relationships from past checkpoints and outcomes.
- **`predict_proba()`**: returns model-estimated probabilities. A value of 0.35 = 35% chance of a wicket.
- **Validation**: compare candidate models on 2025 without leaking 2026 outcomes.
- **Evaluation**: Brier Score and log loss reward reliable probabilities rather than exact yes/no guesses.
- **Baseline**: predict the overall historical wicket frequency for every checkpoint. Our trained model should ideally beat this simple reference out of sample.
- **Feedback**: save all predictions and actual outcomes for the tracker; verify new match data before planned retraining. No model changes automatically.

## Learning plan

1. Extract Cricsheet ZIP and visually inspect 10 checkpoint rows.
2. Understand how `wicket_next_over` is made by looking at the following over.
3. Count how many examples are 0 versus 1 and chart the frequency by over number.
4. Run a logistic regression on years through 2024, validate on 2025.
5. Compare its Brier Score with the constant-rate baseline; plot calibration.
6. Only then consider boosted trees or the more complex batter milestones model.

## Beware of leakage

The model cannot know the next over's bowler before he is announced. It may only use information known at the completed-over checkpoint. Historical `wicket_next_over` is a label, never an input. The future match's score or final outcome cannot be fed into a pre-match batter predictor.
