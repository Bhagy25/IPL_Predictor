# CricketLens - Session 02 handoff for GitHub Desktop

**Date:** 17 October 2026. **Current state:** real IPL dataset screened, descriptive EDA and initial wicket baseline complete. No website, batter predictor or final 2026 ML evaluation yet.

## 1. Bring this update into your GitHub Desktop clone

1. Extract `CricketLens_Stage02_GitHub_Update.zip`.
2. Open the existing local repository folder from **Repository > Show in Explorer/Finder** in GitHub Desktop.
3. Copy the *contents inside* the extracted `CricketLens/` folder into the local repository root, allowing the starter files to be updated. Do **not** create an extra nested `CricketLens/CricketLens` folder.
4. GitHub Desktop **Changes** should show updated Python sources, new tests, EDA reports/figures and docs. Verify no `data/raw/`, `data/processed/`, `.joblib` or `.zip` data archives appear in Changes.
5. Commit message: `Stage II: screen IPL archive and validate wicket baseline` then **Push origin**.

## 2. Run locally (Python 3.10+)

```bash
python -m venv .venv
# Activate .venv on your operating system
pip install -e '.[dev]'
pytest -q
```

Put your supplied Cricsheet IPL JSON ZIP in the local `data/raw/ipl_json.zip` directory, then:

```bash
python -m cricketlens.pipeline data/raw/ipl_json.zip --output data/processed
python -m cricketlens.data_audit --data data/processed --output reports/stage_ii --figures reports/figures
python -m cricketlens.overview --data data/processed --output reports/stage_ii/first_eda_numbers.json
python -m cricketlens.train_wicket_baseline --input data/processed/next_over_samples.csv --output models
```

The last command validates on 2025. **Do not add `--evaluate-test-2026` now.** We are preserving 2026 as the held-out test after the model-selection process is fixed.

## 3. Files updated

- `src/cricketlens/pipeline.py`: cleaned extracted tables, toss/outcome fields, genuine rename, handling anomalous overs, playable 6-ball wicket labels.
- `src/cricketlens/data_audit.py`: new real-data diagnostic/audit and descriptive graphs.
- `src/cricketlens/train_wicket_baseline.py`: output path is created before save.
- `tests/test_pipeline.py` and `tests/test_audit.py`: synthetic tests, 6 passed.
- `reports/REPORT_DRAFT.md` and `docs/DEV_LOG.md`: real measurements, caveats, and 2025 validation only.
- `reports/stage_ii/*`: checked report tables, missingness and model validation JSON, source-generated with scripts.
- `reports/figures/*.png`: four first EDA charts.
- `reports/Session_02_Real_IPL_Data_Audit.pdf`: intermediate 3-page development report.

## 4. Report notes

- Recorded IPL archives can contain discontinued teams; current-team dropdowns will be built later and must not rewrite historical identity.
- The 2025 wicket-model validation demonstrates a small improvement over a constant-frequency baseline, not a robust production predictor.
- Browser tracker, feedback verification and optional manual retraining are future features, not built yet.
- Maintain citations to Cricsheet and disclosure of AI support according to your course rules.
