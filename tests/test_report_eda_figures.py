"""Stage 1 and Stage 2 figures quoted in REPORT_DRAFT.md and the Stage 2 findings equal the processed tables."""
from pathlib import Path

import pandas as pd
from scipy.stats import fisher_exact

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = " ".join((ROOT / "reports" / "REPORT_DRAFT.md").read_text(encoding="utf-8").split())
SESSION_02 = " ".join((ROOT / "docs" / "STAGE_02_SESSION_02_FINDINGS.md").read_text(encoding="utf-8").split())


def test_stage1_counts_equal_the_processed_tables():
    samples = pd.read_csv(DATA / "next_over_samples.csv", usecols=["wicket_next_over"])
    issues = pd.read_csv(DATA / "screening_issues.csv").issue.value_counts()
    assert f"| `next_over_samples.csv` | {len(samples):,} |" in REPORT
    assert f"Of **{len(samples):,}** eligible next-over windows" in REPORT
    assert f"**{100 * samples.wicket_next_over.mean():.2f}%** include at least one team wicket" in REPORT
    assert f"| `screening_issues.csv` | {issues.sum():,} |" in REPORT
    assert (f"{issues['censored_next_over']} censored next-over windows, "
            f"{issues['checkpoint_after_invalid_over']} checkpoints that follow an invalid over") in REPORT
    assert f"{issues.sum()} issue records in all" in REPORT


def test_toss_figures_by_window():
    corrected = pd.read_csv(ROOT / "reports" / "stage_02" / "session_03" / "toss_results_with_super_overs_2018_2025.csv")
    rows = corrected.set_index("toss_decision")
    (bw, bn), (fw, fn) = ((int(rows.loc[d, "toss_winner_wins"]), int(rows.loc[d, "matches"])) for d in ("bat", "field"))
    p_window = fisher_exact([[bw, bn - bw], [fw, fn - fw]]).pvalue
    window = f"{bw}/{bn} choosing bat vs {fw}/{fn} choosing field in 2018–2025 (Fisher p≈{p_window:.3f}"
    assert window in REPORT
    assert f"**{bw}/{bn} ({100 * bw / bn:.2f}%)**" in SESSION_02 and f"p ≈ **{p_window:.3f}**" in SESSION_02

    matches = pd.read_csv(DATA / "matches.csv")
    decided = matches[matches.final_winner.notna()]
    won = decided.toss_winner == decided.final_winner
    counts = {d: (int(won[decided.toss_decision == d].sum()), int((decided.toss_decision == d).sum())) for d in ("bat", "field")}
    p_full = fisher_exact([[counts["bat"][0], counts["bat"][1] - counts["bat"][0]],
                           [counts["field"][0], counts["field"][1] - counts["field"][0]]]).pvalue
    full = f"{counts['bat'][0]}/{counts['bat'][1]} against {counts['field'][0]}/{counts['field'][1]} (Fisher p≈{p_full:.3f})"
    assert full in REPORT
    assert f"Fisher p ≈ {p_full:.3f}" in SESSION_02
