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


## Session 02 - Batter Milestone Predictor (extra viva preparation)

**Q19. What exactly does the batter model predict?**  The conditional chances of a recorded batter innings scoring at least 30 or at least 50 runs; it does not forecast exact runs or playing-XI selection.

**Q20. Why don't we simply train two independent binary models?**  Independent probabilities could contradict P(50+) <= P(30+). One 3-class model for <30 / 30–49 / >=50 automatically respects that ordering.

**Q21. How are our historical features calculated without looking into the future?**  They are computed only from player innings on strictly earlier calendar dates. Rows from the current match or the same date cannot influence them.

**Q22. How do we identify a player who changes teams?**  By their stable Cricsheet batter ID, not their displayed name or previous franchise.

**Q23. Why are player name and player ID not necessarily features?**  The ID organizes histories; our selected model uses numerical prior form and contextual team/venue features, enabling more principled cold starts.

**Q24. Why exclude D/L and no-result matches for model training?**  To start with relatively consistent innings contexts. We keep them for EDA and may revisit the cohort; exclusions may themselves induce bias.

**Q25. Do we exclude regular innings of matches decided by Super Over?**  No. Only Super Over deliveries are excluded; ordinary batting performances remain eligible if the match is otherwise eligible.

**Q26. If a player is absent from the XI or never bats, how do we handle the prediction?**  This model assumes a recorded batting innings. Do not mark a DNB as a 0-run failure. The UI must state the condition and mark absence as ineligible / not settled unless a separate participation model is built.

**Q27. Is actual batting position used?**  No. It would generally only be known during the match. An expected pre-match position would need separate historically available data to use safely.

**Q28. What is a cold start?**  A player with no historical eligible batting innings. The model sees zeros/counts and may be less reliable; we need an uncertainty warning and group-specific analysis.

**Q29. Why split by time rather than randomly?**  Random splitting lets future matches influence training and leads to optimistic results. Train through 2024, validate 2025, test 2026 once.

**Q30. How can the model use earlier 2025 matches in a later 2025 forecast?**  Those earlier results were already known at prediction time. Model parameters remain frozen after training through 2024; only past-form inputs update.

**Q31. Why compare with simple historical baselines?**  A complex model only adds value if it improves probabilistic scoring relative to easy-to-compute statistics.

**Q32. Why select a Random Forest?**  It achieved the lowest 2025 average milestone Brier among predeclared candidate classifiers, but the advantage is small and selection was on that same validation set.

**Q33. Does a 15% chance of 50+ mean a player's half-century is impossible?**  No. It assigns roughly a 15-in-100 long-run frequency for similar situations; outcomes are stochastic.

**Q34. What is the most important unresolved task?**  Freeze choices, perform one-time 2026 holdout evaluation, assess calibration/cold starts and then refit for future use. Do not claim the development artifact is 2027-ready.


### Full-history training and 2026 temporal holdout: additional questions
**Why not test 2026 after refitting through 2026?** That would be in-sample testing, not an independent test. 2026 metrics refer to the pre-2026 models only.

**Did you use 2026 information anywhere when predicting later 2026 matches?** Only previously played 2026 innings were permitted in time-ordered player-form features; model weights were fixed using data through 2025. No current-day or future innings enter features.

**Were both models trained with older IPL data?** Yes, eligible 2008 onward, following the explicit full-history plan. Age of data may make patterns less current; the 2025 validation can compare historical windows if needed, but 2026 is not repeatedly tuned on.

**Why does the wicket model only slightly beat a constant rate?** Ball-level wickets contain substantial randomness; Brier and calibration must be interpreted relative to event frequency, not marketed as guaranteed prediction.

**Is the 2027 app ready?** Model inference functions are ready locally; live fixture data, roster checks, and dashboard integration are not yet implemented.
