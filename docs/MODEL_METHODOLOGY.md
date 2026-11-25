# CricketLens prediction-model methodology

This document describes the whole prediction workflow behind the two CricketLens forecasts: the questions,
the data and its eligibility rules, the features and how leakage is prevented, the assumptions the data and
each algorithm make and the evidence on whether they hold, the evaluation design and metrics, the seven
algorithms compared, the learning-curve (convergence) evidence, the final model, what the website serves,
and the limitations. Every number below is read from `reports/model_benchmark/` (the benchmark,
the 2026 test, the final models and the assumption evidence). `tests/test_methodology_doc.py` checks the
key numbers in this document against those files.

**Final decision.** Both forecasts use **Histogram gradient boosting** with the frozen settings
`max_leaf_nodes=7`, `max_iter=60`, `l2_regularization=2.0` (plus the benchmark's fixed `learning_rate=0.06`,
`min_samples_leaf=50`, no early stopping, seed 42). It had the lowest mean validation Brier score of the
seven algorithms over 2021–2025 for both tasks, which is the selection rule fixed before any 2026 score was
computed. The leading three algorithms are close, and the evidence below says exactly how close.

---

## 1. Prediction questions and targets

| | Next-over wicket | Batter milestones |
|---|---|---|
| Question | After a completed over, will at least one team wicket fall in the next over? | Before a match, will this batter score 30+ and 50+, given that they bat? |
| Target | `wicket_next_over`: 1 if a wicket falls in the next over, else 0 | `milestone_class`: 0 (<30), 1 (30–49), 2 (50+) |
| Output | P(wicket) | P(30+) = P(class 1) + P(class 2); P(50+) = P(class 2) |
| Rows | One per completed-over checkpoint (overs 1–19) | One per eligible batting innings |

One three-class batter model gives both milestones, so P(50+) ≤ P(30+) always holds.

## 2. Data and eligibility

Source: Cricsheet ball-by-ball JSON for men's IPL, 1,243 matches from 2008-04-18 to 2026-05-31
(19 seasons; 295,557 delivery records). The eligibility counts come from
`reports/model_benchmark/assumptions/eligibility.csv`:

| Scope | Rule | Count |
|---|---|---:|
| Archive | Super-over innings, left out of the ordinary innings tables | 34 |
| Archive | D/L-marked matches | 23 |
| Archive | No-result matches | 9 |
| Wicket | Completed-over checkpoints considered | 45,268 |
| Wicket | Excluded: in D/L-marked matches | 619 |
| Wicket | Excluded: anomalous or gapped overs | 14 |
| Wicket | Excluded: next over cut short with no wicket (censored) | 474 |
| Wicket | Kept: complete six-ball next over | 43,924 |
| Wicket | Kept: next over cut short by a wicket | 237 |
| Wicket | **Eligible rows** (1,220 matches) | **44,161** |
| Wicket | Eligible rows from no-result matches (kept: the next over was observed) | 123 |
| Batter | Batting innings in the source | 18,768 |
| Batter | Excluded: in D/L-marked matches | 276 |
| Batter | Excluded: in no-result matches | 63 |
| Batter | **Eligible rows** (1,211 matches) | **18,429** |

An over cut short with no wicket is censored: the wicket might have fallen had the over finished, so it is
dropped rather than labelled 0. An over cut short *by* a wicket has an observed positive and is kept.

## 3. Features and leakage prevention

**Wicket (11 inputs).** Known at the checkpoint: `innings`, `completed_overs`, `runs`, `wickets`,
`run_rate`, `last_over_runs`, `last_over_wickets` (numeric) and `batting_team`, `bowling_team`, `phase`
of the next over, `venue_canonical` (categorical).

**Batter (20 inputs).** Form from earlier innings only: `prior_innings`, career, last-5 and last-10 average
runs and 30+/50+ rates, record against this opponent and at this venue, and days since the previous innings
(17 numeric), plus `batting_team`, `bowling_team` and `venue_canonical`.

**Leakage controls.**
- Every split trains on seasons strictly before the evaluation season. In all 9 folds per task (tuning
  2018–2020, validation 2021–2025, test 2026) every training date precedes every evaluation date (the
  smallest gap is 150 days) and no match appears on both sides (`assumptions/folds.csv`).
- Batter form uses only innings on strictly earlier calendar dates; all 18,429 rows were rebuilt
  independently from that rule (`reports/model_benchmark/data_audit.json`). Innings earlier in the
  evaluation season may inform later forecasts in that season (a forecaster would know them), but model
  weights stay fixed for the whole season.
- No current-match runs, the toss, the playing XI or the final result are inputs.
- Preprocessing (median imputation, one-hot encoding, scaling) is fitted inside each training fold.

## 4. Data assumptions and evidence

Verdicts and evidence from `reports/model_benchmark/assumptions/summary.json` (the rules are stated in
`src/cricketlens/model_assumptions.py`):

| Assumption | Verdict | Evidence | Consequence |
|---|---|---|---|
| Chronological order, no leakage | Holds | 9 folds per task; smallest train-to-evaluation gap 150 days; 0 shared matches | Scores are not inflated by future information |
| Independent rows | Partially holds | 36.2 wicket rows and 15.22 batter rows per match. Wicket events show no clustering (ICC −0.00089 within innings, p = 0.71); batter outcomes cluster slightly (30+ ICC 0.02207 within innings, p = 7.8e-08; 50+ ICC 0.0131 within match, p = 3.3e-06) | Whole matches and seasons stay together in every split; uncertainty is reported across seasons, not rows |
| Stationary seasons | Violated | Wicket `run_rate` shifts by SMD 0.842 in 2026 against all earlier seasons (PSI 0.791); in 3 (wicket) and 6 (batter) of the six 2021–2026 seasons some feature has PSI ≥ 0.25. The wicket rate is stable (26.0%–28.9%, χ² p = 0.47) but the batter 30+ rate is not (21.4%–31.2%, χ² p = 1.3e-07) | Expanding-window training and season-by-season evaluation measure the effect of drift instead of assuming it away |
| Classes adequately represented | Partially holds | Wicket 72.18% / 27.82%; batter 74.48% / 14.24% / 11.29%. Always predicting the majority class gives 71.65% (wicket) and 72.87% (batter) accuracy over 2021–2025 | Accuracy hardly separates models; Brier score and log loss do |
| Complete inputs; sensible defaults | Partially holds | 0 missing model inputs; 736 batter rows have no earlier innings (34 in 2026) and use default values (0.0 rates, 3,650 days) | A debutant's 0.0 rates code "no history"; `prior_innings = 0` lets trees separate the two |
| Category levels seen in training | Partially holds | Rows with a level unseen in training: 2021: 253, 2022: 1,620 (the two new franchises), 2023: 455, 2024: 279; none in 2026 | Unseen levels are all-zero after one-hot encoding, so those rows rely on the other inputs |
| Measurement scales respected | Holds | Counts, runs, rates and days are ratio scale; teams and venues nominal (one-hot); `phase` ordinal, one-hot encoded; `milestone_class` ordinal target | No arithmetic on nominal codes |
| Eligibility rules applied | Holds | Counts in Section 2 add up exactly | Forecasts describe ordinary, uninterrupted innings |

Figures: `reports/model_benchmark/assumptions/drift_wicket.png`, `drift_batter.png`.

## 5. Evaluation design and metrics

1. **Tuning (2018, 2019, 2020).** For each algorithm, three settings are fitted on all earlier seasons and
   scored on each tuning season. The setting with the lowest mean Brier (tie-break log loss) is frozen.
2. **Ranking (2021–2025).** Each algorithm's frozen setting is fitted on all earlier seasons (expanding
   window from 2008) and scored on each of the five seasons. Algorithms are ranked by mean validation Brier,
   tie-break mean log loss. The same five seasons give paired per-season comparisons.
3. **Learning curves.** Each ranking fold is refitted on its most recent 10%, 25%, 50%, 75% and 100% of
   matches and scored on the same validation season.
4. **2026 retrospective test.** The selected setting is fitted on 2008–2025 and scored once on 2026. 2026 had
   already been examined during Stage 3 development, so this is a retrospective chronological test, not a
   first look at unseen data.
5. **Final refit.** The same setting is refitted on 2008–2026 for the website. It has no later season to be
   tested on yet.

**Metrics** (y = outcome, p = predicted probability, n rows):

| Metric | Definition | Direction |
|---|---|---|
| Brier score | BS = (1/n) Σ (pᵢ − yᵢ)²; batter: the mean of BS(30+) and BS(50+) | lower |
| Log loss | −(1/n) Σ log pᵢ(yᵢ), the probability given to the observed class | lower |
| Accuracy | share of rows whose most probable class is the observed class | higher |
| Balanced accuracy | (1/K) Σₖ recallₖ, the mean recall over classes | higher |
| Macro F1 | (1/K) Σₖ 2·Precisionₖ·Recallₖ / (Precisionₖ + Recallₖ) | higher |
| ROC-AUC | P(a random positive scores above a random negative); batter: mean over 30+ and 50+ | higher |
| Average precision | Σₙ (Rₙ − Rₙ₋₁)·Pₙ over the precision–recall curve; batter: mean over 30+ and 50+ | higher |

**Why Brier is primary.** The website outputs probabilities, so the selection metric must reward honest
probabilities. Brier is a strictly proper scoring rule (it is minimised only by the true probability), it is
bounded (one confident mistake cannot dominate, unlike log loss), it combines calibration and sharpness, and
it reads directly as squared probability error. Log loss, also proper, is the tie-break. Accuracy-type
metrics use only the most probable class: with roughly three quarters of rows in one class they barely move
between models (Section 7), and they ignore whether a 30% forecast means 30%.

## 6. The seven algorithms

All pipelines impute numeric medians and one-hot encode categories inside each training fold; logistic
regression, naive Bayes and the perceptron also standardise numeric inputs. Mean validation results
(2021–2025, ± sample SD across the five seasons):

**Table 6.1. Next-over wicket** (`reports/model_benchmark/wicket_comparison.csv`)

| Rank | Algorithm | Brier | Log loss | Accuracy | Balanced acc. | Macro F1 | ROC-AUC | Avg. precision |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | **Histogram gradient boosting** | **0.19579 ± 0.00280** | 0.57929 ± 0.00625 | 72.24% ± 0.55 | 52.86% ± 0.33 | 0.4881 ± 0.0066 | 0.6032 ± 0.0114 | 0.3947 ± 0.0082 |
| 2 | Random forest | 0.19595 ± 0.00276 | 0.57964 ± 0.00611 | 72.11% ± 0.46 | 52.52% ± 0.31 | 0.4815 ± 0.0068 | 0.6044 ± 0.0111 | 0.3926 ± 0.0123 |
| 3 | Multilayer perceptron | 0.19626 ± 0.00286 | 0.58019 ± 0.00645 | 71.90% ± 0.72 | 52.09% ± 1.21 | 0.4724 ± 0.0242 | 0.6069 ± 0.0145 | 0.3901 ± 0.0148 |
| 4 | Logistic regression | 0.19655 ± 0.00308 | 0.58089 ± 0.00700 | 71.79% ± 0.60 | 51.36% ± 0.47 | 0.4552 ± 0.0124 | 0.6061 ± 0.0150 | 0.3878 ± 0.0152 |
| 5 | Decision tree | 0.19677 ± 0.00295 | 0.58161 ± 0.00648 | 72.25% ± 0.56 | 52.85% ± 0.34 | 0.4878 ± 0.0067 | 0.5931 ± 0.0076 | 0.3641 ± 0.0093 |
| 6 | Class-prior baseline | 0.20318 ± 0.00196 | 0.59637 ± 0.00421 | 71.65% ± 0.44 | 50.00% ± 0.00 | 0.4174 ± 0.0015 | 0.5000 ± 0.0000 | 0.2835 ± 0.0044 |
| 7 | Gaussian naive Bayes | 0.22610 ± 0.00794 | 0.66422 ± 0.02089 | 67.31% ± 1.07 | 56.98% ± 0.73 | 0.5724 ± 0.0079 | 0.5981 ± 0.0159 | 0.3819 ± 0.0147 |

**Table 6.2. Batter milestones** (`reports/model_benchmark/batter_comparison.csv`)

| Rank | Algorithm | Brier | Log loss | Accuracy | Balanced acc. | Macro F1 | ROC-AUC | Avg. precision |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | **Histogram gradient boosting** | **0.13937 ± 0.01157** | 0.71474 ± 0.05020 | 72.89% ± 2.75 | 33.38% ± 0.10 | 0.2819 ± 0.0060 | 0.7039 ± 0.0223 | 0.3279 ± 0.0416 |
| 2 | Random forest | 0.13941 ± 0.01191 | 0.71406 ± 0.05063 | 72.87% ± 2.77 | 33.33% ± 0.00 | 0.2809 ± 0.0062 | 0.7058 ± 0.0260 | 0.3254 ± 0.0382 |
| 3 | Multilayer perceptron | 0.13953 ± 0.01209 | 0.71642 ± 0.05101 | 72.87% ± 2.77 | 33.33% ± 0.00 | 0.2809 ± 0.0062 | 0.7092 ± 0.0237 | 0.3351 ± 0.0387 |
| 4 | Decision tree | 0.14053 ± 0.01201 | 0.72019 ± 0.05080 | 72.87% ± 2.77 | 33.33% ± 0.00 | 0.2809 ± 0.0062 | 0.6920 ± 0.0246 | 0.2949 ± 0.0297 |
| 5 | Logistic regression | 0.14092 ± 0.01086 | 0.72477 ± 0.04624 | 72.67% ± 2.95 | 33.47% ± 0.33 | 0.2859 ± 0.0071 | 0.6941 ± 0.0211 | 0.3195 ± 0.0436 |
| 6 | Class-prior baseline | 0.15203 ± 0.01269 | 0.77243 ± 0.04979 | 72.87% ± 2.77 | 33.33% ± 0.00 | 0.2809 ± 0.0062 | 0.5000 ± 0.0000 | 0.1957 ± 0.0209 |
| 7 | Gaussian naive Bayes | 0.26919 ± 0.01618 | 2.00935 ± 0.19983 | 55.24% ± 3.08 | 43.47% ± 1.98 | 0.3702 ± 0.0129 | 0.6904 ± 0.0223 | 0.3085 ± 0.0360 |

Accuracy SDs are percentage points. Tuning trials: `reports/model_benchmark/{wicket,batter}_tuning.csv`.

### 6.1 Class-prior baseline
- **How it works.** Predicts the training class shares for every row: p̂ₖ = nₖ / n. No inputs, no settings.
- **Assumption.** The base rate is stable from the training seasons to the next season.
- **Evidence.** Wicket rate by season 26.0%–28.9% (χ² homogeneity p = 0.47) → **Holds** for wickets. Batter
  30+ rate 21.4% (2009) to 31.2% (2025), χ² p = 1.3e-07; 50+ rate 7.8%–15.0%, p = 1.1e-08 → **Violated** for
  batters (largest deviation from the pooled rate 5.7 points).
- **Results.** Rank 6 for both tasks (Brier 0.20318 and 0.15203).
- **Why not selected.** It is the reference every model must beat; it has no ranking skill (ROC-AUC 0.5). Every
  other algorithm except naive Bayes beats it in all five seasons for both tasks.

### 6.2 Logistic regression
- **How it works.** P(y=1|x) = σ(β₀ + βᵀx) with σ(t) = 1/(1+e⁻ᵗ) for wickets; a multinomial (softmax) model
  for batters. Fitted by minimising log loss + ‖β‖²/(2C) (L2 penalty).
- **Assumptions.** Log-odds linear in each numeric input; little multicollinearity; independent observations;
  enough events per parameter; a suitable penalty.
- **Evidence.**
  - Linearity (nested likelihood-ratio test of a straight line against line + bin indicators, Bonferroni
    α): 4 of 6 testable wicket features (`completed_overs`, `runs`, `wickets`, `run_rate`) and all 17 batter
    form features depart significantly (`assumptions/linearity.csv`, `logit_linearity_*.png`).
  - Multicollinearity: largest VIF 19.61 (`completed_overs`, wicket) and 50.46 (`recent10_avg_runs`, batter);
    2 wicket and 7 batter features exceed 10 (`assumptions/vif.csv`).
  - Independence: see Section 4 (slight batter clustering).
  - Events per parameter: 146.1 (wicket: 11,542 events, 79 parameters) but 7.41 (batter: 1,913 50+ events,
    258 multinomial parameters), below the usual 10.
  - Penalty: tuning chose C = 0.05 for both tasks, the strongest of the three values, consistent with the
    collinearity.
- **Verdict.** **Violated** (both tasks).
- **Results.** Rank 4 (wicket, Brier 0.19655) and 5 (batter, 0.14092). Boosting is better in all 5 seasons for
  both tasks (mean paired gap 0.000754 and 0.001551).
- **Why not selected.** The non-linear, interacting effects (a wicket late in an innings, form saturating) are
  what a linear log-odds model cannot represent; it ranks well on ROC-AUC but not on probability accuracy.

### 6.3 Decision tree
- **How it works.** Recursive axis-aligned splits that minimise Gini impurity G = 1 − Σₖ pₖ²; each leaf
  predicts its class shares.
- **Assumptions.** None about distributions. It assumes the signal is well approximated by a few axis-aligned
  thresholds (a piecewise-constant surface), and a single tree has high variance.
- **Evidence.** Tuning chose the shallowest setting (depth 3, 100 rows per leaf) for both tasks; deeper trees
  scored worse in tuning. The forest beats the tree in all 5 seasons for both tasks.
- **Verdict.** **Partially holds.**
- **Results.** Rank 5 (wicket, 0.19677) and 4 (batter, 0.14053); best wicket accuracy (72.25%) but weak ranking
  (ROC-AUC 0.5931).
- **Why not selected.** A depth-3 tree is too coarse for calibrated probabilities; ensembles fix this.

### 6.4 Random forest
- **How it works.** Averages 160 trees, each grown on a bootstrap sample with a random subset of features at
  each split: p̂(x) = (1/B) Σ_b T_b(x).
- **Assumption.** Averaging many decorrelated trees reduces variance without adding bias.
- **Evidence.** It beats the single tree in all 5 seasons for both tasks (mean Brier gain 0.00082 wicket,
  0.001127 batter).
- **Verdict.** **Holds.**
- **Results.** Rank 2 for both tasks, very close to boosting: paired Brier gap 0.000161 ± 0.000258 (wicket;
  boosting better in 3 of 5 seasons) and 0.00004 ± 0.000567 (batter; boosting better in 2 of 5 seasons). The
  forest has the lowest batter log loss (0.71406).
- **Why not selected.** Under the pre-specified rule (lowest mean validation Brier) boosting ranks first for
  both tasks. The forest is a statistically indistinguishable alternative on this evidence.

### 6.5 Histogram gradient boosting (selected)
- **How it works.** Starts from the base rate and adds M shallow trees stage by stage, each fitted to the
  gradient of the log loss: F_M(x) = F₀ + Σₘ η·hₘ(x), probabilities σ(F) (softmax for three classes).
  Numeric inputs are binned into at most 255 bins; leaf values carry an L2 penalty.
- **Assumptions.** The signal is an additive sum of small interactions; binning loses little; the learning
  rate, iteration cap, leaf limit and L2 penalty prevent overfitting.
- **Evidence.**
  - Binning: 6 of 7 wicket and 7 of 17 batter numeric features have at most 255 distinct training values and
    are binned losslessly; the rest (e.g. `run_rate`, career averages) are binned at quantiles.
  - Overfitting: train–validation Brier gap 0.006335 (wicket) and 0.013725 (batter); the class-prior baseline
    has gaps of 0.003413 and 0.011795 from season drift alone, so the excess is 0.002922 and 0.001931.
  - Plateau: validation Brier changes by −0.000021 (wicket) and −0.000315 (batter) from 75% to 100% of history.
  - Tuning chose the smallest of three settings (7 leaves, 60 iterations, L2 2.0) for both tasks.
- **Verdict.** **Holds** (both tasks).
- **Results.** Rank 1 for both tasks: Brier 0.19579 ± 0.00280 (wicket) and 0.13937 ± 0.01157 (batter).
- **Why selected.** Lowest mean validation Brier for both tasks, with a small excess train–validation gap and a
  flat learning curve. Its lead over the runner-up is small (0.000161 and 0.00004); see Section 7.

### 6.6 Gaussian naive Bayes
- **How it works.** P(y=k|x) ∝ πₖ Πⱼ N(xⱼ; μⱼₖ, σ²ⱼₖ + ε): class prior times independent normal densities per
  feature, with variance smoothing ε.
- **Assumptions.** Features are conditionally independent given the class and normally distributed within
  each class.
- **Evidence.** 7 wicket and 121 batter within-class feature pairs correlate at |r| ≥ 0.5 (largest 0.926,
  `completed_overs`–`runs`; 0.916, `career_avg_runs`–`career_30_rate`). 25 of 51 batter class–feature pairs are
  strongly non-normal (`days_since_previous_innings`: skewness 7.56). 71 and 68 one-hot columns are binary and
  cannot be Gaussian (`assumptions/correlations.csv`, `shapes.csv`, `nb_qq_*.png`).
- **Link to calibration.** Treating correlated inputs as independent multiplies the same evidence several
  times and pushes probabilities to extremes. On 2025 its expected calibration error was 0.1306 (wicket) and
  0.2952 (batter 30+) against 0.0094 and 0.0447 for boosting; 54% of its batter 30+ probabilities were below
  0.05 or above 0.95.
- **Verdict.** **Violated** (both tasks).
- **Results.** Rank 7 for both tasks, worse than the baseline (Brier 0.22610 and 0.26919), despite the highest
  balanced accuracy and macro F1 (it predicts the minority classes more often).
- **Why not selected.** Its probabilities are badly calibrated, which the website cannot use.

### 6.7 Multilayer perceptron
- **How it works.** One or two hidden ReLU layers, h = max(0, W₁x + b₁), and a sigmoid or softmax output,
  fitted with Adam on log loss + α‖W‖².
- **Assumptions.** Standardised inputs; the non-convex optimisation reaches a good, seed-insensitive solution
  within the epoch budget; enough data for the parameters.
- **Evidence.** Inputs are standardised. Every one of the 34 distinct perceptron fits per task (9 tuning + 25
  learning-curve, which include the 5 validation fits) stopped at its epoch cap (25, 35 or 45 epochs) with a
  convergence warning; no other algorithm raised one. The 5 seed refits below also reached the cap. Refitting the selected setting on the 2025 fold with
  5 seeds moved Brier by 0.000408 (wicket) and 0.001251 (batter); the batter spread exceeds the perceptron's
  gap to boosting (0.000162). Parameters: 1,921 (wicket) and 3,187 (batter) for 39,019 and 16,231 training
  rows.
- **Verdict.** **Partially holds.**
- **Results.** Rank 3 for both tasks (0.19626 and 0.13953); highest ROC-AUC on both.
- **Why not selected.** Slightly worse mean Brier, unconverged optimisation and seed sensitivity of the same
  size as the gap to the leader.

**Table 6.3. Algorithm assumption verdicts** (`assumptions/summary.json`)

| Algorithm | Wicket | Batter |
|---|---|---|
| Class-prior baseline | Holds | Violated |
| Logistic regression | Violated | Violated |
| Decision tree | Partially holds | Partially holds |
| Random forest | Holds | Holds |
| Histogram gradient boosting | Holds | Holds |
| Gaussian naive Bayes | Violated | Violated |
| Multilayer perceptron | Partially holds | Partially holds |

## 7. Convergence and learning curves

"Convergence" here is empirical: as the training history grows, does validation performance stop improving
(a plateau), and how far apart do the leading algorithms end up? It is not a mathematical proof, and the
curves cannot say what more recent seasons would do.

**Selected model, mean validation Brier by training size** (`assumptions/learning.csv`; mean training
matches 94 → 932 for wickets, 94 → 928 for batters):

| Training share | 10% | 25% | 50% | 75% | 100% |
|---|---:|---:|---:|---:|---:|
| Wicket | 0.197114 | 0.196439 | 0.195617 | 0.195813 | 0.195792 |
| Batter | 0.144347 | 0.140821 | 0.139552 | 0.139682 | 0.139367 |

- **Plateau.** From 10% to 50% the Brier improves by 0.001498 (wicket) and 0.004795 (batter). After that it
  is flat: +0.000196 then −0.000021 (wicket) and +0.000130 then −0.000315 (batter) for 50→75% and 75→100%.
  Gains from more history have levelled off over the sizes measured.
- **Leaders.** The spread of mean Brier among the top three (boosting, forest, perceptron) is 0.000657 at 10%
  and 0.000471 at 100% for wickets, and narrows from 0.004805 to 0.000162 for batters. Their order does not
  settle: for batters the forest has the lowest mean Brier at 10% and 25% and the perceptron at 50% and 75%;
  for wickets the forest is lowest at 10% and 75%. Boosting is lowest at 100% for both tasks. What stabilises
  is the size of the gaps, which become very small, not the order.
- **Paired per-season gaps against boosting** (Brier of the algorithm minus boosting's, 2021–2025;
  `{task}_paired_brier_gaps.csv`):

| Algorithm | Wicket mean ± SD | Seasons boosting better | Batter mean ± SD | Seasons boosting better |
|---|---:|---:|---:|---:|
| Random forest | 0.000161 ± 0.000258 | 3 of 5 | 0.000040 ± 0.000567 | 2 of 5 |
| Multilayer perceptron | 0.000471 ± 0.000193 | 5 of 5 | 0.000162 ± 0.000832 | 4 of 5 |
| Logistic regression | 0.000754 ± 0.000506 | 5 of 5 | 0.001551 ± 0.000936 | 5 of 5 |
| Decision tree | 0.000981 ± 0.000320 | 5 of 5 | 0.001167 ± 0.000546 | 5 of 5 |
| Class-prior baseline | 0.007391 ± 0.001477 | 5 of 5 | 0.012666 ± 0.002449 | 5 of 5 |
| Gaussian naive Bayes | 0.030304 ± 0.005229 | 5 of 5 | 0.129823 ± 0.014474 | 5 of 5 |

**What this shows.**
- Accuracy alone cannot pick a model: predicting the majority class already scores 71.65% (wicket) and 72.87%
  (batter), and six of seven algorithms are within one percentage point of that.
- Brier and log loss separate the models: boosting beats the baseline, logistic regression and the tree in
  every season for both tasks.
- The top three are close. Against the random forest the mean gap is smaller than its season-to-season SD,
  and the forest wins 2 of 5 batter seasons: the data do not show boosting is better than the forest, only that
  it is no worse and ranks first under the rule fixed in advance.
- Boosting is still the justified choice because the rule (lowest mean validation Brier, tie-break log loss)
  was set before the comparison, it ranks first for both tasks at full history, its learning curve is flat, its excess
  train–validation gap is small, and its 2026 test (Section 8) beats the class-prior baseline and the archived
  Stage 3 models on Brier.

Figures: `assumptions/learning_curves_wicket.png`, `learning_curves_batter.png` (all four metrics, seven
algorithms), `assumptions/paired_gaps_*.png`, and the benchmark's own train/validation panels
`reports/model_benchmark/{wicket,batter}_{accuracy,balanced_accuracy,brier}_learning.png`.

## 8. Final model and the 2026 retrospective test

Trained on 2008–2025 (41,580 wicket checkpoints from 1,147 matches; 17,316 batter innings from 1,139 matches)
and scored once on 2026 (`reports/model_benchmark/holdout_2026.json`):

| Forecast | Test rows (matches) | Brier | Log loss | Accuracy | Balanced acc. | ROC-AUC | Avg. precision |
|---|---:|---:|---:|---:|---:|---:|---:|
| Next-over wicket | 2,581 (73) | 0.19819 | 0.58457 | 72.03% | 52.71% | 0.59950 | 0.39126 |
| Batter milestones | 1,113 (72) | 0.15140 | 0.74555 | 70.44% | 34.23% | 0.71772 | 0.38462 |

- **Against the class-prior baseline** trained on the same rows (`final_models.json`): Brier 0.19819 vs
  0.20494 (wicket) and 0.15140 vs 0.16936 (batter).
- **Against the archived Stage 3 models** on the same 2026 rows (development history): contextual logistic
  regression Brier 0.200519; random forest average milestone Brier 0.151623 (its log loss, 0.743083, was lower
  than boosting's 0.74555).
- **Calibration.** Wicket: 742 events (28.75%) against a mean forecast of 28.60%. Batter: 29.47% reached 30
  and 15.00% reached 50, against mean forecasts of 28.10% and 13.15%, so the 2026 batter forecasts are slightly
  low, in line with the rising 30+ rate (Section 4). Bin tables: `{wicket,batter}_holdout_calibration.csv`.
- **Confusion matrices** (rows actual, columns most probable class):
  - Wicket: no wicket [1,805, 34], wicket [688, 54].
  - Batter: <30 [778, 0, 7], 30–49 [160, 0, 1], 50+ [161, 0, 6].
  The most probable class is almost always the majority class; the value of these models is in the
  probabilities, not the classifications.

**Caveat.** 2026 was examined during Stage 3 development, so this is a retrospective test. The models refitted
through 2026 have no independent test season yet.

## 9. Deployment

`python -m cricketlens.final_models` fits the selected pipelines through `cricketlens.model_benchmark`'s own
code and saves `models/final/{wicket,batter}_hgb_through_2025.joblib` (holdout) and
`..._through_2026.joblib` (final). The holdout artifacts reproduce the benchmark's 2026 forecasts exactly
(maximum absolute difference 0) and two independent fits give byte-identical probabilities
(`final_models.json`). The website's prediction API loads only the final artifacts and refuses any artifact
whose algorithm, settings or columns differ from `selection.json`. The Methodology page on the website shows
this evidence interactively.

## 10. Limitations

- One season per fold: five validation seasons give a rough spread, not a confidence interval, and the
  seasons share overlapping training histories.
- Drift: scoring rates (wicket `run_rate`) and batter milestone rates have risen; a future season may differ
  again. The class-prior baseline's own train–validation gap measures part of this.
- The leading algorithms are statistically close; another reasonable rule (for example log loss for batters)
  would have chosen the random forest.
- Eligibility excludes D/L matches and censored overs; forecasts do not cover rain-shortened innings. The
  batter forecast assumes the player bats; selection and batting position are not modelled.
- Cold starts and new franchises or venues fall back on defaults and the other inputs.
- The 2026 test is retrospective; the final models have no independent test yet.
- The perceptron results describe finite-budget fits that did not converge.

## 11. Reproduction

From the repository root with the project environment (about 7 minutes for the benchmark on the development
machine; 421 seconds in the latest run):

```text
python -m cricketlens.model_benchmark              # tuning, ranking, learning curves, 2026 test
python -m cricketlens.model_benchmark_audit --verify-raw
python -m cricketlens.final_models                  # final artifacts + exactness and determinism checks
python -m cricketlens.model_assumptions             # assumption evidence and figures
python -m pytest
```

A full re-run of the benchmark reproduced all 23 result files (16 CSV, 6 PNG and `holdout_2026.json`) byte for
byte; `selection.json` differed only in the recorded Python and NumPy patch versions and the key order of one
dictionary, and is kept as committed. `model_benchmark_audit --verify-raw` reproduced `data_audit.json` byte for
byte.
