# Model evaluation and leakage rules

1. For model **development**, train on historical IPL seasons through **2024** and validate on **2025**.
2. Freeze feature definitions, model family and settings using validation, then refit on all **<=2025** matches and evaluate on **2026** exactly once as the **held-out final test**.
3. For eventual 2027 deployment, **refit the selected model using verified historical data through 2026**. That is a separate model artifact, not the held-out evaluation model.
4. Compare against simple baselines: constant previous-season event rate, logistic regression; compare stronger models only if warranted.
5. Report event frequency, Brier Score, log loss and reliability/calibration plots (ROC-AUC secondary).
6. Model 2 uses *completed over* checkpoints and predicts at least one **team wicket in the next six legal deliveries of the upcoming over**. A future over that terminates early without all-out is censored; a shortened over ending in a tenth wicket is a known positive. Audit exceptional innings carefully.
7. Model 1 uses information strictly known *before* a match, including historical rolling form computed using earlier matches only. Predict milestone conditional on the batter appearing; playing XI confirmation and DNB must be handled in UI.
8. Compare using the same 2026 holdout whether a recent (2018+) history window or longer (2008+) window generalizes better; do NOT choose window based on holdout performance. Make this selection with 2025 validation.
9. Archive the exact feature schema, training period, random seed, dependencies and model version.
10. Do not blindly retrain on crowdsourced browser feedback. Use verified match scorecards/Cricsheet and preserve model version of each prediction.
