# Stage 2 / Session 02 — Deeper exploratory analysis

**Status:** calculations and charts complete; Stage 2 overall **still in progress**.  
**Source:** audited Cricsheet men's IPL match/innings/delivery CSVs from Stage 1.  
**Strict analytical cutoff:** 2008–2025; first-innings and phase comparisons: 2018–2025. **No 2026 outcomes used.**  
**Reproduce:** `python -m cricketlens.stage02_deep_eda --data data/processed --output reports/stage_02/session_02 --figures reports/figures/stage_02`

## Research question 1 — Does innings duration distort score comparisons?

The 533 recorded first innings from 2018–2025 averaged **175.80** runs (median **175**). The **501** innings lasting all 120 legal deliveries averaged **178.88**; the **32** shorter ones averaged **127.50**. Short innings may result from dismissals or early stoppages, so the discrepancy does not isolate a single explanation. Report both overall and full-length scores; do not drop shortened innings from the archive. The 5% trimmed mean of all innings is **175.91**. There are **11** Tukey-fence statistical outliers (<89 or >265), retained unless determined invalid by the source audit.

## Research question 2 — Do within-innings scoring phases differ?

Among **937** innings with at least 30 Powerplay legal balls and at least 12 death-over legal balls, the mean Powerplay rate was **8.41** and the mean death-over rate **10.67** runs per six legal deliveries, a **paired mean difference of +2.26**. A match-clustered bootstrap yielded an approximate **95% interval of +2.02 to +2.51**. This is conditional on innings reaching late overs; the two innings from the same match are not fully independent, and a paired t-test's p-value is exploratory, not causal proof.

## Research question 3 — Do venue patterns remain after adjusting for the season mix?

Use **only 120-legal-ball first innings**, center each score on that season's full-length-innings mean, and report venues with >=20 qualifying innings. Twelve venues qualify. **Eden Gardens** averaged **+10.34** runs relative to its season-year baselines (37 innings) while **MA Chidambaram Stadium, Chepauk** averaged **-13.71** (38 innings); **Lucknow's Ekana stadium** averaged **-14.32** (21 innings). These are associations, not controlled venue effects: team, pitch, toss, weather, venue/season calendar, and selection can confound comparisons. Percentile bootstrap bands reflect variation in observations, not the uncertainty in all confounding controls.

## Research question 4 — Is toss decision associated with winning?

For completed, winner-recorded matches in 2018–2025, the toss-winning side also won **60/127 (47.24%)** of matches when choosing to bat, vs **209/393 (53.18%)** when choosing to field. Fisher's exact two-sided p ≈ **0.262**. No causal inference: choices and outcomes depend on conditions and team strength; this is exploratory, unadjusted and not enough to demonstrate an advantage from choosing to field.

## Research question 5 — What do missing fields tell us?

Of **1,169** matches before 2026, **51** have `city` missing, all from **Dubai International Cricket Stadium (33)** and **Sharjah Cricket Stadium (18)** in the observed data. Missingness clearly has a relationship with an observed field (venue) and is not well described as uniform across grounds. However, **MCAR vs MAR vs MNAR cannot be established conclusively from the observed sample alone**. `outcome_method` being absent for ordinary matches is a structural/not-applicable value, not necessarily lost information. For venue-level analysis use the recorded venue, not an invented city value.

## Statistical toolkit and measurements

| Variable | Measurement scale | Description |
|---|---|---|
| batting_team, venue, player_id | nominal | team/venue identifiers, not ordinal measurements |
| season / date | interval/calendar index | differences are meaningful; 'year 0' is arbitrary |
| runs, wickets, balls | ratio, discrete | nonnegative counts with meaningful zero |
| run rate | ratio, continuous-derived | runs per 6 legal balls |
| wicket-next-over outcome | binary nominal | either event occurs (1) or does not (0) |
| match phase | ordinal categorical | Powerplay, middle, death (in cricket order) |

Cricsheet coverage is not a random sample of all cricket; restricting to men's IPL and selecting 2018–2025 or only full 20-over innings changes the target population. Descriptive tables here do not claim randomized experiments. The dashboard can use complete history for historical queries, while Stage 3 model development must preserve the unseen 2026 test set.

## Output inventory

Session 02 summary and seven CSV tables: `reports/stage_02/session_02/`. Six new numbered figures `12`–`17` in `reports/figures/stage_02/`. Automated tests in `tests/test_stage02_deep_eda.py`. PDF report in `reports/Stage_02_Session_02_Deeper_EDA_Report.pdf`.

## Remaining Stage 2 work

Consolidate an EDA narrative spanning Sessions 01/02, add multiple-variable/confounder sensitivity where justified, and review results and figures against the course rubric before sign-off. **Stage 3 models have not yet been finalized or evaluated on 2026.**
