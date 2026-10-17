# Development roadmap

| Stage | Work | Status | Evidence |
|---|---|---|---|
| 0 | Scope, no-login decision, six dashboard tabs, two targets | Agreed | README.md |
| 1A | Create reproducible Python project and tests | **Implemented** | `src/`, `tests/` |
| 1B | Load and screen full Cricsheet IPL ZIP | **Blocked: source archive not available in this runtime** | Await upload/download |
| 2 | Data-quality audit, missingness, data dictionary, EDA | Planned | `reports/REPORT_DRAFT.md` |
| 3A | Next-over wicket baseline (code) | **Implemented, not trained on real data** | `train_wicket_baseline.py` |
| 3B | Batter milestone model with temporal features | Planned | — |
| 3C | Validation on 2025, one-time 2026 holdout test | Planned | Metrics logs |
| 4 | FastAPI model inference / validation | Planned | — |
| 5 | React six-tab website; no login; local tracker | Planned | — |
| 6 | Historical replay, report, screenshots, final presentation | Planned | — |

Definition of complete: working code + test evidence + documented data decisions + reproducible outputs.
