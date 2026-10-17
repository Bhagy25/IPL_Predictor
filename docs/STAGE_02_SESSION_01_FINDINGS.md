# Stage 2 / Session 01 - Structured IPL EDA findings

**Status:** Initial Stage 2 analysis complete; **Stage 2 overall is still in progress**. All reported observations were computed from the Stage 1 audited `data/processed/*.csv`. Execute `python -m cricketlens.stage02_eda` to regenerate charts and tables. The `2026` season is deliberately excluded from all these analytical computations to protect its ML test role.

## Research questions and results

| Question | Reproducible answer | Scope and caution |
|---|---|---|
| How have first-innings totals changed? | 2008-2025 seasonal mean score trend has a descriptive unweighted slope **+1.71 runs/season**, R² **0.663**. 2008 season average **160.97**, 2025 **188.84**. | 18 annual mean observations; uneven season coverage, changing laws/teams/venues. Not causal. |
| What is the distribution of scores? | 2018-2025, **n=533** first innings: mean **175.80**, median **175**, sample SD **33.93**, Q1 **155**, Q3 **199**, IQR **44**, median absolute deviation **22**, CV **19.30%**. | Includes reduced overs, D/L, early all-outs; not a standardized 20-over score. |
| Are there extreme innings? | Using Tukey's 1.5×IQR rule on 2018-25 first-innings totals: thresholds **below 89 or above 265**, **11 flagged**. | Statistical outliers, not incorrect records; do not delete them automatically. |
| Which match phase scores faster? | 2018-2025 run rates: **Powerplay 8.49**, **Middle 8.32**, **Death 10.73** runs per six legal balls. | Phase rates based on innings that reach each phase; selection/survivor effects apply. |
| How do current franchises compare? | For **2022-2025 decided matches**, Gujarat Titans had **37 wins in 60** (**61.67%**); Mumbai Indians **26 in 60** (**43.33%**). | Ties and no-results excluded from denominator. Descriptive only. |
| How do grounds differ? | Eden Gardens first-innings mean **191.31 (n=39)**; Chepauk **161.47 (n=43)** during 2018-25. | Grounds differ in teams, climate and conditions; do not interpret as a causal ground effect. Venues shown only if ≥20 first innings. |
| What is the milestone base rate? | 2018-2025 observed batter appearances **n=8,123**: 30+ in **27.03%**, 50+ in **12.22%**. | Conditional on a batter appearing in a recorded innings, not unconditional before playing XI confirmation. |
| What is historical next-over wicket frequency? | **27.85%** across **19,290** eligible 2018-2025 checkpoint windows. | Stage 1 inclusion rules censor some windows; not representative of every match checkpoint; not a calibrated prediction. |
| Which quantitative variables associate with total? | 2018-2025 first-innings **runs vs final wickets r=-0.507**, **runs vs legal balls r=+0.337** (Pearson). | Final innings quantities contain future info; not permissible features for a live/pre-match predictor. |
| What does simple data-fitting show? | In-sample descriptive OLS association of innings runs with final wickets, final legal balls, season: **R²=0.398**, MAE=**20.47 runs**. | Explanatory demonstration for IT462, **NOT an innings-score prediction model**. Final-only variables make it inapplicable for pre-match inference. |

## Missingness and bias notes

- Among 1,169 development-season matches, match-level `city` is missing 51 times (4.36%). Earlier Stage 1 source audit located these in Dubai/Sharjah records. Do not assert MCAR/MAR/MNAR without evidence.
- `winner` is missing in 23 development matches because ties and no-results are recorded separately. `outcome_method` is normally empty and is **structural optional information**, not something to impute.
- The archive is observational rather than a random sample of future events. Franchises, venues, schedules, pitches and scoring environments have changed.
- Both selection and survivor bias affect innings-phase and next-over calculations. Stage 3 must handle interrupted innings and censored event windows before final training.
- **The 2026 IPL outcomes are not examined here for feature selection or model evaluation.**

## Associated deliverables

- `reports/stage_02/session_01/stage02_session01_summary.json`
- 11 chart PNGs in `reports/figures/stage_02/`
- Descriptive summaries, season trends, team/venue/player tables, correlation matrices, missingness summary, and historical wicket-rate aggregates in `reports/stage_02/session_01/`
- `src/cricketlens/stage02_eda.py` and `tests/test_stage02_eda.py` (reproducible code and unit tests).

## Still needed before Stage 2 completion

1. **More systematic bivariate work:** team/venue stratification controlling for seasons, crosstabs, and season-adjusted comparisons.
2. **Statistical interpretations:** examine uncertainty, sample sizes, possible outliers and confounders with suitable tests; include Spearman analysis interpretation.
3. **Advanced EDA:** multicollinearity and potential PCA as descriptive exploration (not forced if unjustified), correlations/regression explanation; missingness interpretation consistent with MCAR/MAR/MNAR limits.
4. Consolidate figures into a full Stage 2 EDA chapter and map to IT462 topics. The final website will implement selected views in Tabs 1-4.
