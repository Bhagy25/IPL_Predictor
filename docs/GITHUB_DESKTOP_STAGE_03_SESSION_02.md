# GitHub Desktop - Stage 3, Session 02

1. Check out `feature/stage-03-ml`, which should already contain Session 01 after pushing.
2. Extract `CricketLens_Stage03_Session02_GitHub_Update.zip` and copy its **CricketLens folder contents** into the local repository. Do not nest another `CricketLens` folder.
3. Review Python scripts, tests, report notes, charts and report updates. Preserve any personal edits before replacing files.
4. Extract `CricketLens_Stage03_Session02_Local_Model_Data.zip` into the repository root so its `data/processed/` and `models/` land in those existing folders. They are ignored by `.gitignore` and should **not** appear in the GitHub commit.
5. Commit the tracked changes with the summary `feat(ml): build and validate batter milestone predictor` and **Push origin**.
6. Do **not** merge Stage 3 into `main` yet. Session 03 is the final 2026 holdout evaluation and refit decision.

**Important:** Never add the raw IPL ZIP, generated processed CSVs, `.joblib` files, or validation secrets to version control. Preserve the corrected matches.csv with Super Over final winner fields from Stage 2.
