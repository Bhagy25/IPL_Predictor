# GitHub repository setup

Recommendation: use a **private** repository named `CricketLens` initially. You can make it public after reviewing data licenses, credits, and secrets.

1. Create a new empty GitHub repo (do not initialize it with a README, because this project already has one).
2. Extract `CricketLens_starter.zip` into a local `CricketLens` folder (or copy the `CricketLens/` folder into your GitHub workspace).
3. Run the commands below in that project folder:

```bash
git init
git add .
git commit -m "chore: initialize CricketLens EDA and ML project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/CricketLens.git
git push -u origin main
```

Then for each development session:

```bash
git status
git add .
git commit -m "data: add audited IPL match extraction" # example
 git push
```

Prefer small commits for each milestone. Do not commit raw datasets, `.env` secrets, generated model binaries, or personal information. Each meaningful milestone should update `docs/DEV_LOG.md` and `reports/REPORT_DRAFT.md`. Do not claim a model is trained unless metrics and reproducible evidence exist.

GitHub issue ideas: Data import/audit, Next-over model baseline, Batter milestone feature engineering, EDA report, FastAPI inference, React dashboard, Tracker, Historical replay, QA.
