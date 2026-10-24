# GitHub Desktop handoff - Stage 3, Session 3

**Work branch:** `feature/stage-03-ml`. Do not create a separate repository or a `CricketLens` folder inside `IPL_Predictor`.

1. **GitHub ZIP:** Extract `CricketLens_Stage03_Session03_GitHub_Update.zip`. Copy the *contents* of the included `CricketLens/` into your existing local `IPL_Predictor/` repository. Review changed files before replacing.
2. **Local ZIP:** Extract `CricketLens_Stage03_Session03_Local_Model_Data.zip` into that same repository root. This populates `data/processed/` and `models/` with large generated CSVs and pretrained artifacts, plus local-only 2026 predictions/diagnostics. These locations are `.gitignore`-excluded.
3. In GitHub Desktop verify you are on `feature/stage-03-ml`. Commit `feat(ml): evaluate full-history models on 2026 and refit for deployment`. Click **Push origin**.
4. Reproduce locally from the project root: `pip install -e '.[dev]'`, `pytest -q`. Full dataset extraction/retraining: `python -m cricketlens.stage03_full_history`; diagnostics: `python -m cricketlens.stage03_full_history_diagnostics`.
5. Review the report and test metrics. After that, create PR `feature/stage-03-ml` -> `main`. This merge records internally complete ML Stage 3; Stage 4 dashboard still awaits implementation.

**IMPORTANT**: We tested 2026 using pre-2026 model weights, then refitted separate copies through 2026. **Do not report the latter as independent 2026-tested models.** No manual user feedback is used for auto-training.
