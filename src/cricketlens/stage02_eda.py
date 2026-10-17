"""Reproducible Stage 2, Session 01 men's IPL statistical EDA.

Purpose: descriptive research, NOT ML model tuning. Exclude 2026 from all analyses
here to preserve its role as the final unseen ML test season.

Usage: python -m cricketlens.stage02_eda --data data/processed --output reports/stage_02/session_01 --figures reports/figures/stage_02
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error

CURRENT_TEAMS = (
    "Chennai Super Kings", "Delhi Capitals", "Gujarat Titans",
    "Kolkata Knight Riders", "Lucknow Super Giants", "Mumbai Indians",
    "Punjab Kings", "Rajasthan Royals", "Royal Challengers Bengaluru",
    "Sunrisers Hyderabad",
)


def development_only(df: pd.DataFrame, cutoff: int = 2025) -> pd.DataFrame:
    """Protect the chronological ML holdout by filtering to past seasons only."""
    if "season" not in df.columns:
        raise KeyError("Expected season column")
    return df.loc[df.season <= cutoff].copy()


def describe(series: pd.Series) -> dict:
    """Return sample-based descriptive statistics; MAD = median abs deviation."""
    s = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if s.empty:
        raise ValueError("Cannot describe empty numeric series")
    q = s.quantile([0.25, 0.5, 0.75])
    sd = float(s.std(ddof=1)) if len(s) > 1 else float("nan")
    median = float(q.loc[0.5])
    mean = float(s.mean())
    modes = s.mode()
    return {
        "count": len(s), "mean": mean, "median": median,
        "mode_smallest": float(modes.min()), "min": float(s.min()),
        "q1": float(q.loc[0.25]), "q3": float(q.loc[0.75]),
        "max": float(s.max()), "range": float(s.max() - s.min()),
        "variance_sample": float(s.var(ddof=1)) if len(s) > 1 else float("nan"),
        "sd_sample": sd, "iqr": float(q.loc[0.75] - q.loc[0.25]),
        "median_abs_deviation": float(np.median(np.abs(s.to_numpy() - median))),
        "cv_pct": float(100 * sd / mean) if mean != 0 else float("nan"),
    }


def standardized_phase(over_index: pd.Series) -> pd.Series:
    """Cricket 20-over phase; keep invalid/out-of-range events explicit."""
    return pd.cut(over_index, bins=[-1, 5, 15, 19],
                  labels=["Powerplay (1-6)", "Middle (7-16)", "Death (17-20)"])


def variance_inflation_factors(x: pd.DataFrame) -> dict:
    """VIF on numerical columns with intercept, for explanatory (not predictive) EDA."""
    out = {}
    a = x.to_numpy(dtype=float)
    for i, name in enumerate(x.columns):
        y = a[:, i]
        others = np.delete(a, i, axis=1)
        others = np.column_stack((np.ones(len(y)), others))
        coefs, *_ = np.linalg.lstsq(others, y, rcond=None)
        resid = y - others @ coefs
        denom = np.sum((y - y.mean()) ** 2)
        r2 = (1 - np.sum(resid ** 2) / denom) if denom else np.nan
        out[str(name)] = float(1 / (1 - r2)) if r2 < 1 else float("inf")
    return out


def _plot_base():
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.facecolor": "white", 
                         "axes.facecolor": "white", "savefig.facecolor": "white"})


def _save(fig, folder: Path, name: str):
    fig.tight_layout(pad=1.8)
    fig.savefig(folder / name, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _write(df: pd.DataFrame, folder: Path, stem: str):
    df.to_csv(folder / f"{stem}.csv", index=False)


def generate(data: Path, output: Path, figures: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    _plot_base()
    matches = pd.read_csv(data / "matches.csv")
    innings = pd.read_csv(data / "innings.csv")
    deliveries = pd.read_csv(data / "deliveries.csv")
    batters = pd.read_csv(data / "batter_innings.csv")
    checkpoints = pd.read_csv(data / "next_over_samples.csv")
    if matches.match_id.duplicated().any():
        raise ValueError("Duplicate matches: Stage 1 inputs changed")
    if int(matches.season.max()) != 2026:
        raise ValueError("Expected 2008-2026 archive, check input path")
    if not (matches.gender == "male").all():
        raise ValueError("Dataset contains non-men's IPL records")
    if (matches.season < 2008).any():
        raise ValueError("Unexpected old season")

    # Explicitly NEVER use the 2026 model holdout in Stage 2 development EDA.
    m = development_only(matches)
    i = development_only(innings)
    d = development_only(deliveries)
    b = development_only(batters)
    c = development_only(checkpoints)
    first = i.loc[i.innings == 1].copy()
    first_recent = first.query("season >= 2018").copy()
    recent_b = b.query("season >= 2018").copy()
    recent_d = d.query("season >= 2018").copy()

    missing = (m.isna().sum().rename("missing_count").to_frame()
               .assign(total_records=len(m)))
    missing["missing_pct"] = 100 * missing.missing_count / missing.total_records
    missing.index.name = "field"
    _write(missing.reset_index(), output, "match_field_missingness_pre2026")

    dist = pd.DataFrame([{"scope": "all_history_2008_2025", "variable": "first_innings_runs", **describe(first.runs)},
                         {"scope": "recent_2018_2025", "variable": "first_innings_runs", **describe(first_recent.runs)},
                         {"scope": "recent_2018_2025", "variable": "batter_runs_per_appearance", **describe(recent_b.runs)},
                         {"scope": "recent_2018_2025", "variable": "batter_balls_faced", **describe(recent_b.balls_faced)}])
    _write(dist.round(4), output, "numeric_descriptive_summary")

    season = (first.groupby("season").agg(first_innings=("runs", "size"),
                        mean_runs=("runs", "mean"), median_runs=("runs", "median"),
                        sd_runs=("runs", "std")).reset_index())
    _write(season.round(3), output, "season_first_innings_trends")
    regression_season_means = stats.linregress(season.season.to_numpy(), season.mean_runs.to_numpy())

    recent_m = m.query("2022 <= season <= 2025").copy()
    match_sides = pd.concat([recent_m.assign(team=recent_m.team1),
                             recent_m.assign(team=recent_m.team2)], ignore_index=True)
    match_sides = match_sides.loc[match_sides.team.isin(CURRENT_TEAMS)].copy()
    if 'final_winner' not in match_sides:
        raise ValueError('Regenerate Stage 1 match table with final_winner field')
    match_sides["decided"] = match_sides.final_winner.notna()
    match_sides["win"] = match_sides.decided & (match_sides.final_winner == match_sides.team)
    teams = (match_sides.groupby("team", as_index=False)
              .agg(total_matches=("match_id", "nunique"), decided_matches=("decided", "sum"), wins=("win", "sum")))
    teams["win_pct_of_decided"] = 100 * teams.wins / teams.decided_matches.replace(0, np.nan)
    teams["unresolved_or_no_result"] = teams.total_matches - teams.decided_matches
    teams = teams.sort_values("win_pct_of_decided", ascending=False)
    _write(teams.round(2), output, "current_teams_win_rates_2022_2025")

    # Venue means from recorded first innings (including shortened/all-out innings).
    venues = (first_recent.groupby("venue_canonical", as_index=False)
              .agg(n_first_innings=("runs", "size"), mean_first_innings_runs=("runs", "mean"),
                   median_first_innings_runs=("runs", "median")))
    venues = venues.query("n_first_innings >= 20").sort_values("mean_first_innings_runs", ascending=False)
    _write(venues.round(2), output, "venues_min20_first_innings_2018_2025")

    recent_d["phase"] = standardized_phase(recent_d.over_index)
    phase = (recent_d.groupby("phase", observed=True)
             .agg(total_runs=("runs_total", "sum"), legal_balls=("legal_delivery", "sum"),
                  team_wickets=("team_wickets_on_ball", "sum"), deliveries_recorded=("runs_total", "size"))
             .reset_index())
    phase["runs_per_six_legal_balls"] = 6 * phase.total_runs / phase.legal_balls
    phase["wickets_per_six_legal_balls"] = 6 * phase.team_wickets / phase.legal_balls
    _write(phase.round(4), output, "innings_phase_patterns_2018_2025")

    checkpoint_phase = c.query("season >= 2018").copy()
    cp_out = checkpoint_phase.groupby("completed_overs", as_index=False).agg(
        n_samples=("wicket_next_over", "size"), wicket_events=("wicket_next_over", "sum"),
        observed_wicket_rate=("wicket_next_over", "mean"))
    _write(cp_out.round(4), output, "next_over_historical_rates_2018_2025")

    # Batting analyses use batter IDs; match appearances, not playing-XI selections.
    batters_recent = (recent_b.groupby("batter_id", as_index=False)
                      .agg(name=("batter", "first"), innings=("runs", "size"),
                           total_runs=("runs", "sum"), avg_per_appearance=("runs", "mean"),
                           milestone30_rate=("reached_30", "mean"), milestone50_rate=("reached_50", "mean")))
    batters_recent = batters_recent.query("innings >= 40").sort_values("total_runs", ascending=False)
    _write(batters_recent.round(4), output, "batters_min40_appearances_2018_2025")

    # Association is descriptive; does not imply causation or deployable prediction.
    cols = ["runs", "wickets", "legal_balls", "season"]
    pearson = first_recent[cols].corr(method="pearson")
    spearman = first_recent[cols].corr(method="spearman")
    pearson.to_csv(output / "first_innings_pearson_corr_2018_2025.csv")
    spearman.to_csv(output / "first_innings_spearman_corr_2018_2025.csv")
    x = first_recent[["wickets", "legal_balls", "season"]].copy()
    x["season"] = x["season"] - 2018
    lin = LinearRegression().fit(x, first_recent.runs)
    lin_pred = lin.predict(x)
    vif = variance_inflation_factors(x)

    # Charts: standalone figures, not a synthetic UI; all use measured values.
    fig, ax = plt.subplots(figsize=(8.4, 4.25))
    ax.plot(season.season, season.mean_runs, marker="o", linewidth=2)
    ax.set(title="Mean first-innings total by IPL season, 2008-2025", xlabel="IPL season", ylabel="Recorded runs per first innings")
    ax.grid(axis="y", alpha=.2)
    _save(fig, figures, "01_season_scoring_trend.png")

    fig, ax = plt.subplots(figsize=(8.4, 4.25))
    ax.hist(first_recent.runs, bins=np.arange(0, 310, 10), edgecolor="white")
    ax.axvline(first_recent.runs.median(), ls="--", linewidth=1.7, label=f"Median {first_recent.runs.median():.0f}")
    ax.set(title="First-innings totals: 2018-2025", xlabel="Runs (all first innings, including shortened)", ylabel="Number of innings")
    ax.legend(frameon=False)
    _save(fig, figures, "02_first_innings_histogram.png")

    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    s1=first.query("2008 <= season <= 2012").runs
    s2=first.query("2013 <= season <= 2017").runs
    s3=first.query("2018 <= season <= 2021").runs
    s4=first.query("2022 <= season <= 2025").runs
    ax.boxplot([s1,s2,s3,s4], tick_labels=["2008-12","2013-17","2018-21","2022-25"],
               patch_artist=True, boxprops={"facecolor":"#BDD7DE"}, medianprops={"color":"#203647", "linewidth":2})
    ax.set(title="First-innings score variability by era", xlabel="IPL seasons", ylabel="Recorded first-innings runs")
    ax.grid(axis="y", alpha=.2)
    _save(fig, figures, "03_score_boxplots_by_era.png")

    fig, ax = plt.subplots(figsize=(8.4, 4.25))
    ax.bar(phase.phase.astype(str), phase.runs_per_six_legal_balls)
    for k,v in enumerate(phase.runs_per_six_legal_balls): ax.text(k,v+.08,f"{v:.2f}",ha="center",fontsize=9)
    ax.set(title="Run rate by innings phase, 2018-2025", ylabel="Runs per six legal deliveries", ylim=(0,max(phase.runs_per_six_legal_balls)*1.22))
    _save(fig, figures, "04_scoring_rate_by_phase.png")

    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    tt = teams.sort_values("win_pct_of_decided")
    ax.barh(tt.team, tt.win_pct_of_decided)
    ax.set(title="Current franchises: decided-match win rate, 2022-2025", xlabel="Wins / matches with recorded winner (%)", xlim=(0,75))
    _save(fig, figures, "05_current_team_win_rates.png")

    fig, ax = plt.subplots(figsize=(9,5.4))
    vv = venues.head(10).sort_values("mean_first_innings_runs")
    ax.barh(vv.venue_canonical, vv.mean_first_innings_runs)
    ax.set(title="Venue first-innings means, 2018-2025 (min 20 innings)", xlabel="Mean recorded first-innings runs")
    _save(fig, figures, "06_venue_first_innings_means.png")

    fig, ax = plt.subplots(figsize=(8.4, 4.25))
    ax.plot(cp_out.completed_overs, 100*cp_out.observed_wicket_rate, marker="o", linewidth=1.8)
    ax.set(title="Observed next-over wicket frequency, 2018-2025", xlabel="Completed overs at checkpoint", ylabel="Eligible-window wicket frequency (%)")
    ax.grid(axis="y", alpha=.2)
    _save(fig, figures, "07_next_over_event_frequency.png")

    fig, ax = plt.subplots(figsize=(7.5, 5.4))
    im = ax.imshow(pearson, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(4),cols);ax.set_yticks(range(4),cols)
    for j in range(4):
        for k in range(4): ax.text(k,j,f"{pearson.iloc[j,k]:+.2f}",ha="center",va="center",color="black")
    ax.set(title="Pearson correlation: first innings, 2018-2025")
    fig.colorbar(im, ax=ax, shrink=.8)
    _save(fig, figures, "08_first_innings_correlation.png")

    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    top = batters_recent.head(10).sort_values("total_runs")
    labels = [f"{name} [{pid[:4]}]" for name,pid in zip(top.name,top.batter_id)]
    ax.barh(labels, top.total_runs)
    ax.set(title="Total batter runs, 2018-2025 (min 40 innings)", xlabel="Recorded batter runs")
    _save(fig, figures, "09_top_batters_recent.png")

    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    ax.scatter(recent_b.balls_faced, recent_b.runs, s=8, alpha=.19)
    ax.set(title="Batter runs vs balls faced, 2018-2025", xlabel="Recorded balls faced", ylabel="Runs")
    _save(fig, figures, "10_batting_innings_scatter.png")

    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    missing_nonzero=missing.loc[missing.missing_count>0].sort_values("missing_pct", ascending=True)
    ax.barh(missing_nonzero.index, missing_nonzero.missing_pct)
    ax.set(title="Missing fields in match-level data, 2008-2025", xlabel="Missing (%)")
    _save(fig,figures,"11_match_field_missingness.png")

    summary = {
        "status":"Stage 2 Session 01: initial EDA complete; full Stage 2 not yet signed off",
        "training_holdout_protection":"Only seasons 2008-2025 were analyzed; 2026 reserved for ML testing",
        "full_archive_matches_including_2026":int(len(matches)),
        "development_matches_2008_2025":int(len(m)),
        "recent_matches_2018_2025":int(m.query('season >= 2018').shape[0]),
        "recent_first_innings_count":int(len(first_recent)),
        "first_innings_2008_2025":describe(first.runs),
        "first_innings_2018_2025":describe(first_recent.runs),
        "recent_batter_appearances":int(len(recent_b)),
        "batter_30plus_frequency_2018_2025":float(recent_b.reached_30.mean()),
        "batter_50plus_frequency_2018_2025":float(recent_b.reached_50.mean()),
        "recent_batting_top":batters_recent.head(5)[["name","batter_id","innings","total_runs"]].to_dict(orient="records"),
        "team_window_2022_2025_decided_matches":int(recent_m.final_winner.notna().sum()),
        "venue_minimum_n":20,
        "eligible_checkpoint_2018_2025_n":int(len(checkpoint_phase)),
        "eligible_checkpoint_2018_2025_wicket_frequency":float(checkpoint_phase.wicket_next_over.mean()),
        "phase_run_rates":{str(a.phase):float(a.runs_per_six_legal_balls) for _,a in phase.iterrows()},
        "season_mean_trend_2008_2025":{
          "slope_runs_per_year":float(regression_season_means.slope),
          "r_squared":float(regression_season_means.rvalue**2),
          "p_value":float(regression_season_means.pvalue),
          "method":"Unweighted line fitted to 18 annual means; descriptive, not causal"},
        "descriptive_multiple_linear_regression_2018_2025":{
           "meaning":"In-sample explanatory association ONLY, not a future-score predictor",
           "n_first_innings":int(len(first_recent)),
           "target":"final first-innings runs (observed outcome)",
           "predictors":["final wickets lost", "final legal balls recorded", "season - 2018"],
           "intercept":float(lin.intercept_),
           "coefficients":{str(k):float(v) for k,v in zip(x.columns,lin.coef_)},
           "in_sample_r2":float(r2_score(first_recent.runs,lin_pred)),
           "in_sample_mae":float(mean_absolute_error(first_recent.runs,lin_pred)),
           "vif":vif,
           "important_warning":"Uses END-OF-INNINGS quantities; invalid to use as a pre-match score predictor"},
        "limitations":[
            "Score and venue comparisons include all recorded first innings, even shortened or all-out innings; not controlled for era, pitch, or weather.",
            "Team win rates exclude ties/no-results and cover only 2022-2025, for franchise overlap.",
            "Players' 30+/50+ frequencies are conditional on a recorded batting appearance, not playing-XI selection.",
            "Next-over event frequencies are conditional on Stage 1 eligible full-over windows and may have censoring/selection bias.",
            "2026 outcomes must not be used to tune features, models, or thresholds before final held-out evaluation.",
            "Unweighted season trend and linear-regression associations are observational, not causal.",
        ],
    }
    (output / "stage02_session01_summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf-8")
    return summary


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--data",type=Path,default=Path("data/processed"))
    a.add_argument("--output",type=Path,default=Path("reports/stage_02/session_01"))
    a.add_argument("--figures",type=Path,default=Path("reports/figures/stage_02"))
    args=a.parse_args()
    x=generate(args.data,args.output,args.figures)
    print(json.dumps({"matches_dev":x["development_matches_2008_2025"],
                      "recent_first_innings":x["recent_first_innings_count"],
                      "recent_mean":round(x["first_innings_2018_2025"]["mean"],2),
                      "checkpoint_n":x["eligible_checkpoint_2018_2025_n"]},indent=2))

if __name__=="__main__":
    main()
