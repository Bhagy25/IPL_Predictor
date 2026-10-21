# CricketLens Stage 3: questions to understand, not memorize

These are **current implementation** questions based on Stage 3 Session 01. Answers will be revised if training design changes.

1. **What are X and y?** X: features observed at the end of a completed over; y: indicator of at least one team wicket in the following over.
2. **Why predict a probability?** Cricket events are uncertain; calibrated probabilities can be evaluated over many examples with Brier/log loss.
3. **Why not call a 70% forecast wrong if no wicket?** An event assigned 70% probability still fails to occur about 30% of the time in a well-calibrated system.
4. **Why is 2026 excluded now?** It is the final chronological unseen holdout, reserved until feature/algorithm choices are frozen.
5. **Why no random train-test split?** The same match contributes many similar over checkpoints, and cricket changes over time; random splitting would mix match contexts and future conditions.
6. **What is the meaning of a censored target?** If the following over stops after only a few balls and no wicket has occurred, we cannot assert what would have happened over all six balls.
7. **Why retain a wicket in a shortened next over?** The event has already happened, so the Yes label is known even if the over ended early.
8. **How are D/L cases handled?** Excluded from this first ML cohort; preserved for EDA. This is a simplifying modeling policy with possible selection effects.
9. **How are Super Overs handled?** Ordinary innings preceding the tie can be used, but the special Super Over innings is not included in the standard-innings predictor.
10. **Why choose the 2018+ training window?** The 2025 validation Brier score was better for the enhanced candidate; cricket playing styles have changed, but this is a validated selection, not a proof older seasons are always bad.
11. **Why Logistic Regression?** It is understandable, yields class probabilities, and establishes a reproducible benchmark before trying more complex models.
12. **Which features are known at prediction time?** Current score/wickets/overs, previous-over runs/wickets, teams, innings, phase, and venue. The future over's events are withheld as the target.
13. **Why does the website need last-over values now?** The best validated model uses recent momentum, so the manual UI must collect those two numbers (or clearly implement a validated alternative).
14. **What does Brier 0.197 mean?** It is the average squared error between probabilities and Yes/No outcomes; lower is better. Compare to 0.2028 constant rate on the **same 2025 observations**.
15. **Why isn't 0.197 a 80.3% accuracy score?** Brier Score is not classification accuracy; it evaluates probabilistic error and has a different interpretation.
16. **What do we do with user feedback?** Store both forecasts and verified outcomes; evaluate performance; any retraining happens later in a controlled offline process.
17. **What are the remaining model limitations?** Dependence between checkpoints, different era conditions, unequal phase event rates, censored-match selection effects, and need for final 2026 holdout evidence.
18. **What if the selected model is weak on the holdout?** Report it transparently; don't repeatedly tune on 2026 and keep claiming 2026 as an unbiased test.
