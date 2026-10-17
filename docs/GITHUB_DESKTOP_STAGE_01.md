# Update the existing GitHub Desktop repository — Stage 1

1. Download and extract `CricketLens_Stage01_GitHub_Update.zip`.
2. In GitHub Desktop select **Repository > Show in Explorer/Finder** to open the *local repository root*.
3. Copy the **contents** of the extracted `CricketLens/` directory to that root. Do not create an extra nested `CricketLens` folder.
4. Review the **Changes** tab. If old `reports/stage_ii/` files exist, remove that outdated folder after confirming the contents have moved to `reports/stage_01/` and `reports/preliminary_stage_03/`. Previously pushed session PDFs can stay, but are now archival.
5. **Do not commit** `data/raw/`, `data/processed/`, model `.joblib` files or ZIP datasets. These are ignored by `.gitignore`.
6. Commit as `Stage 1: IPL parsing and initial data quality audit`. Click **Push origin**.

**Stage 1 was completed for EDA in Session 03.** The word Session in prior filenames does not mean Stage. The next phase is Stage 2 (EDA).
