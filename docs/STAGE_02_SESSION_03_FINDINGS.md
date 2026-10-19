# Stage 2 / Session 03 — Exceptional match outcomes and final EDA synthesis

**Development branch:** `feature/stage-02-eda`  
**Source:** Cricsheet men's IPL JSON archive, processed locally.  
**Analysis:** seasons **2008–2025** only; IPL 2026 remains the **unseen ML holdout**.  
**Status:** Stage 2 numerical sign-off complete internally; professor feedback and final project presentation remain pending.

## Research question — How should Super Overs change team win rates?

Cricsheet outcome fields distinguish a `result: tie` in regulation play from an `eliminator` (the Super Over winner). Previously we preserved the tie but **did not credit the Super Over winner** in the regular team win-rate calculations. The source and parser are now reconciled using the following fields:

- `regulation_result`: `win`, `tie`, or `no result` as the ordinary result.
- `winner`: the source's ordinary-winner field, kept for traceability (blank on Super Over ties).
- `super_over_winner`: normalized `outcome.eliminator`, if present.
- `final_winner`: ordinary winner, otherwise Super Over eliminator, otherwise missing.
- `decided_by`: `regulation`, `super_over`, or `no_result`.
- `super_over_innings`: number of separately recorded Super Over innings. **These are not added to regular batting, bowling, wicket or over totals.**

Across the complete archive (2008–2026) the match-level QA counts **1,218 ordinary wins, 16 regulation ties decided by Super Over (34 Super Over innings), 9 no-results, and 23 D/L-marked matches**. This entire-archive audit checks parsing coverage and **must not be used to tune the 2026 holdout model**.

All statistical EDA remains restricted to **2008–2025**: **1,169 matches; 1,146 ordinary wins, 15 Super Over-decided ties (32 Super Over innings), 8 no-results and 22 D/L-marked outcomes**. All 15 ties have a final Super Over winner in the source. Decided matches = 1,161; the remaining 8 are no-results.

### Measured correction to team comparisons

Among the 10 current franchises in **2022–2025**, the corrected head-to-head style match-win summaries include Super Over decisions and exclude no-result games. **Delhi Capitals increases from 25/54 (46.30%) to 26/55 (47.27%)** because the 2025 Super Over victory against Rajasthan Royals is now credited. The Rajasthan Royals denominator also increases (30/59 becomes 30/60), reducing their rate from 50.85% to 50.00%. Other current-team counts in this period are unchanged. The 2022–2025 10-team comparison now has **289** decided matches in total.

### Toss findings corrected

When counting the final match winner, **2018–2025** toss winners won **62/130 (47.69%)** after choosing bat versus **210/398 (52.76%)** after choosing field. The exploratory Fisher two-sided p-value is approximately **0.363**. Do **not** use the earlier Session 02 PDF's now-superseded 60/127 and 209/393 totals; use the regenerated CSVs and the consolidated report. No causal advantage is established.

## Research question — How should D/L games be treated in scoring comparisons?

`outcome.method == 'D/L'` flags a match decided using the recorded rain-adjustment method. It does **not** identify whether an interruption affected the first innings, the second innings, or when it occurred. Preserve the real ball events and actual recorded match winner. Do **not** transform scores into fabricated 20-over equivalents.

For **2018–2025**, 533 first innings are recorded: 6 belong to D/L-marked matches (4 still have 120 legal deliveries, 2 have <120). Thirty of the 527 non-D/L first innings lasted <120 legal deliveries, which shows that **short innings are not synonymous with D/L** (all-out and other match endings matter). There are too few D/L-marked first innings in this recent window for a stable separate scoring estimate. Report stratified descriptive values, not a causal D/L impact.

The fact that the source labels 23 matches D/L across all archive seasons does not prove every other game experienced no interruption. Stage 3 must define an eligibility rule for interrupted games and next-over windows using known-at-checkpoint information and censoring.

## Research question — What about no-result matches?

Eight matches before 2026 are `no result` and have no invented winner. Retain recorded deliveries in descriptive tables where an innings actually occurred, but exclude them from denominators for **win percentage among matches with a final winner**. Provide separate total matches and decided matches to keep denominators auditable.

## Stage 2 consolidated evidence (pre-2026 only)

- **Data source/quality:** 1,169 matches before 2026; 51 missing cities (33 Dubai, 18 Sharjah), treated as missing, not fabricated. Player IDs identify homonymous players; venue names are conservatively standardized.
- **Scores:** 533 first innings (2018–2025), mean **175.80**, median **175**. Of these, 501 full 120-ball innings average **178.88**, and 32 shorter ones average **127.50**. Real extremes are retained and checked against the source.
- **Phases:** within 937 qualifying innings, mean death minus Powerplay runs per 6 legal deliveries is **+2.26** (approx. 95% match-clustered bootstrap interval **[+2.02, +2.51]**); this conditional comparison is observational.
- **Venues:** season-centered 120-legal-ball first-innings analysis puts Eden Gardens at **+10.34 runs** (37 innings) and Chepauk at **-13.71 runs** (38 innings) relative to each selected season's mean, **not causal ground effects**.
- **Player outcomes:** in 8,123 recorded batter appearances (2018–2025), **27.03%** reached 30+ and **12.22%** reached 50+; these are historical base rates, not model forecasts.
- **Wicket event:** in 19,290 provisional eligible next-over windows (2018–2025), **27.85%** had a wicket; final censoring and D/L eligibility decisions remain **Stage 3**.
- **Statistics:** five-number summaries, mean/median/mode, SD, variance, MAD, CV, Tukey outliers, Pearson/Spearman, unweighted season trend, descriptive multiple linear regression and VIF have been computed and documented. Regression uses final wickets/balls: *not permissible as pre-match prediction features*.

## Final figure selection for website

| Proposed tab | Best stage 2 visual | Source figure |
|---|---|---|
| IPL Overview | scoring trend by season; phase run rate; first-innings histogram | 01, 04, 02 |
| Teams | corrected final-winner win rates; season comparisons | 05 (regenerated), 19 |
| Player Explorer | top batter runs; runs-vs-balls scatter | 09, 10 |
| Statistics & EDA Lab | innings-duration split, correlations, venue adjusted comparison, missingness and exceptions | 12, 08, 13, 17, 18, 20 |
| Prediction Arena | historical next-over wicket frequencies only as context | 07 (candidate cohort only) |
| Prediction Tracker | calibration and Brier plots to be built after Stage 3 | Not available yet |

## Academic integrity and limitations

This is observational analysis, not a controlled experiment. Selection into full-length or death-phase samples can bias group comparisons. Cricsheet coverage and team-era changes limit generalization. The 2026 holdout was **not examined for exploratory outcome comparisons** here; all 2026-level counts above are mechanical archive completeness checks. Instructor approval of the data source and acknowledgment of AI assistance remain important.

## Reproduce

```bash
python -m cricketlens.pipeline data/raw/ipl_json.zip --output data/processed
python -m cricketlens.stage02_eda --data data/processed --output reports/stage_02/session_01 --figures reports/figures/stage_02
python -m cricketlens.stage02_deep_eda --data data/processed --output reports/stage_02/session_02 --figures reports/figures/stage_02
python -m cricketlens.stage02_final_eda --data data/processed --output reports/stage_02/session_03 --figures reports/figures/stage_02
pytest -q
```

**Stage 2 sign-off checklist:** classic descriptive statistics, missingness, variable scales, sampling limits, plotted distributions, bivariate analyses, correlation, regression, time trend, outcome exception analysis, and narrative interpretations. The final 2026 ML holdout remains untouched for development. Optional PCA and third-party profiling tools are not claimed as implemented. Next: create Stage 3 branch from updated main **only after review and merging this Stage 2 branch**.
