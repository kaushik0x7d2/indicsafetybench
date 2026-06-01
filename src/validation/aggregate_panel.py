"""
Aggregate the 3-judge LLM panel results into the v3 paper's validation table.

Consumes `data/validation/panel/judgments_<judge>_<axis>.jsonl` files produced
by `llm_judge_panel.py` and emits:

  data/validation/PANEL_REPORT.md   — main report
  data/validation/panel_kappa.jsonl — machine-readable per-cell kappa records
  data/validation/panel_disagree.md — stratified disagreement-taxonomy table

Statistics reported:
  - Per-(judge, axis, language) MEAN of per-item median-score-across-reruns
    (the headline corpus-quality number)
  - Per-(axis, language) Cohen's LINEAR-WEIGHTED kappa for all 3 judge pairs,
    with bootstrap 95% CI (1000 resamples)
  - Per-judge KRIPPENDORFF-style ordinal alpha across reruns
    (the intra-judge reliability number; answers Rating Roulette critique)
  - Disagreement-stratified taxonomy: items where judge spread >= 2 are
    bucketed by (language, axis, harm category, attack_vector) for qualitative
    review

Usage:
    python -m src.validation.aggregate_panel
    python -m src.validation.aggregate_panel --bootstrap 10000  # tighter CIs
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Optional

PANEL_DIR = Path("data/validation/panel")
OUT_REPORT = Path("data/validation/PANEL_REPORT.md")
OUT_KAPPA = Path("data/validation/panel_kappa.jsonl")
OUT_DISAGREE = Path("data/validation/panel_disagree.md")

LANG_ORDER = ["en", "hi", "mr", "te", "kn", "ta", "bn"]
AXES = ["naturalness", "equivalence", "attack_validity"]


# ----------------------------------------------------------------------
# Cohen's linear-weighted kappa (ordinal)
# ----------------------------------------------------------------------

def cohen_weighted_kappa_linear(a: list[int], b: list[int],
                                max_score: int = 5, min_score: int = 1) -> float:
    """Linear-weighted Cohen's kappa on integer scores in [min_score, max_score].

    w_ij = 1 - |i-j| / (max-min)
    Returns NaN if no variance in either rater.
    """
    assert len(a) == len(b)
    n = len(a)
    if n == 0:
        return float("nan")

    levels = list(range(min_score, max_score + 1))
    L = len(levels)
    idx = {v: i for i, v in enumerate(levels)}

    # Confusion matrix
    O = [[0] * L for _ in range(L)]
    for x, y in zip(a, b):
        if x in idx and y in idx:
            O[idx[x]][idx[y]] += 1

    n_obs = sum(sum(row) for row in O)
    if n_obs == 0:
        return float("nan")

    # Marginals
    row_marg = [sum(row) / n_obs for row in O]
    col_marg = [sum(O[i][j] for i in range(L)) / n_obs for j in range(L)]
    # Expected counts under independence
    E = [[row_marg[i] * col_marg[j] * n_obs for j in range(L)] for i in range(L)]

    # Linear weights
    denom = max_score - min_score
    W = [[1 - abs(levels[i] - levels[j]) / denom for j in range(L)] for i in range(L)]

    obs_agree = sum(W[i][j] * O[i][j] for i in range(L) for j in range(L)) / n_obs
    exp_agree = sum(W[i][j] * E[i][j] for i in range(L) for j in range(L)) / n_obs

    if abs(1 - exp_agree) < 1e-12:
        return float("nan")
    return (obs_agree - exp_agree) / (1 - exp_agree)


def bootstrap_kappa_ci(a: list[int], b: list[int], n_boot: int = 1000,
                       seed: int = 2026, max_score: int = 5, min_score: int = 1
                       ) -> tuple[float, float, float]:
    """Returns (point_estimate, ci_low_2.5, ci_high_97.5)."""
    n = len(a)
    if n < 5:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    point = cohen_weighted_kappa_linear(a, b, max_score, min_score)
    boot = []
    indices = list(range(n))
    for _ in range(n_boot):
        sample_idx = [rng.choice(indices) for _ in range(n)]
        sa = [a[i] for i in sample_idx]
        sb = [b[i] for i in sample_idx]
        k = cohen_weighted_kappa_linear(sa, sb, max_score, min_score)
        if not math.isnan(k):
            boot.append(k)
    if len(boot) < n_boot * 0.5:
        return point, float("nan"), float("nan")
    boot.sort()
    lo = boot[int(0.025 * len(boot))]
    hi = boot[int(0.975 * len(boot))]
    return point, lo, hi


# ----------------------------------------------------------------------
# Ordinal Krippendorff's alpha
# ----------------------------------------------------------------------

def krippendorff_alpha_ordinal(ratings_by_item: list[list[int]]) -> float:
    """Ordinal Krippendorff's alpha.

    ratings_by_item: list of lists, one per item, each containing the scores
    that the SAME unit received from different (or repeated) raters.
    Items with <2 ratings are excluded.

    Returns NaN if insufficient data.
    """
    units = [r for r in ratings_by_item if len(r) >= 2]
    if not units:
        return float("nan")

    all_vals = [v for u in units for v in u]
    if not all_vals:
        return float("nan")
    values = sorted(set(all_vals))
    if len(values) < 2:
        return float("nan")  # no variance

    # Ordinal disagreement metric: squared rank difference
    # Simpler equivalent: d(v1, v2) = (v1 - v2) ** 2 (interval treatment;
    # acceptable for Likert per Krippendorff 2011)
    def d(v1, v2):
        return (v1 - v2) ** 2

    # Observed disagreement: average pairwise distance within each unit
    num_o, den_o = 0.0, 0.0
    for u in units:
        m = len(u)
        for i in range(m):
            for j in range(m):
                if i == j: continue
                num_o += d(u[i], u[j])
        den_o += m * (m - 1)
    if den_o == 0:
        return float("nan")
    D_o = num_o / den_o

    # Expected disagreement: average pairwise distance across all values pooled
    num_e = 0.0
    N = len(all_vals)
    for v1 in all_vals:
        for v2 in all_vals:
            num_e += d(v1, v2)
    D_e = num_e / (N * (N - 1)) if N > 1 else 0
    if D_e == 0:
        return float("nan")
    return 1 - (D_o / D_e)


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------

def load_panel() -> dict:
    """Load all judgments and index by (judge, axis, variant_id, rerun_idx)."""
    out = {}
    if not PANEL_DIR.exists():
        return out
    for f in sorted(PANEL_DIR.glob("judgments_*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    j = json.loads(line)
                    key = (j.get("judge_id"), j.get("axis"),
                           j.get("variant_id"), int(j.get("rerun_idx", 0)))
                    if j.get("score") is None:
                        continue
                    out[key] = j
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    return out


def index_by_item(panel: dict) -> dict:
    """Return {(variant_id, axis, judge_id): [scores across reruns]}"""
    out = defaultdict(list)
    meta = {}  # variant_id -> {language, attack_vector, category}
    for (jid, axis, vid, rerun), rec in panel.items():
        out[(vid, axis, jid)].append(int(rec["score"]))
        if vid not in meta:
            meta[vid] = {
                "language": rec.get("language"),
                "attack_vector": rec.get("attack_vector"),
                "category": rec.get("category"),
            }
    return out, meta


def item_consensus_score(rerun_scores: list[int]) -> Optional[int]:
    """Collapse N rerun scores to a single judge verdict (median, rounded)."""
    if not rerun_scores:
        return None
    return int(round(statistics.median(rerun_scores)))


# ----------------------------------------------------------------------
# Aggregation
# ----------------------------------------------------------------------

def aggregate(panel: dict, n_boot: int) -> dict:
    """Returns a structured dict of all stats for report rendering."""
    by_item, meta = index_by_item(panel)

    # Discover what (judge, axis) cells exist
    judges = sorted({k[2] for k in by_item})
    axes = sorted({k[1] for k in by_item})
    languages = sorted({v["language"] for v in meta.values() if v.get("language")})

    # Per-judge consensus score per (item, axis)
    consensus = {}  # (vid, axis, judge) -> int
    for (vid, axis, jid), reruns in by_item.items():
        c = item_consensus_score(reruns)
        if c is not None:
            consensus[(vid, axis, jid)] = c

    # 1) Per-(judge, axis, language) MEAN of consensus scores
    mean_table = defaultdict(list)
    for (vid, axis, jid), s in consensus.items():
        lang = meta[vid]["language"]
        # For attack_validity, exclude direct (score=0 is N/A, would bias mean)
        if axis == "attack_validity" and meta[vid]["attack_vector"] == "direct":
            continue
        mean_table[(jid, axis, lang)].append(s)

    means = {}
    for k, vals in mean_table.items():
        if vals:
            means[k] = {
                "n": len(vals),
                "mean": statistics.mean(vals),
                "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
            }

    # 2) Per-(axis, language) Cohen's weighted kappa for all 3 judge pairs
    kappa = {}
    judge_pairs = [(j1, j2) for i, j1 in enumerate(judges) for j2 in judges[i+1:]]
    for axis in axes:
        for lang in languages:
            for (j1, j2) in judge_pairs:
                vids = [vid for vid in meta
                        if meta[vid]["language"] == lang
                        and (vid, axis, j1) in consensus
                        and (vid, axis, j2) in consensus
                        and not (axis == "attack_validity"
                                 and meta[vid]["attack_vector"] == "direct")]
                if len(vids) < 5:
                    continue
                a = [consensus[(vid, axis, j1)] for vid in vids]
                b = [consensus[(vid, axis, j2)] for vid in vids]
                # attack_validity range is 0-5; others 1-5
                lo, hi = (0, 5) if axis == "attack_validity" else (1, 5)
                pt, clo, chi = bootstrap_kappa_ci(a, b, n_boot=n_boot,
                                                  min_score=lo, max_score=hi)
                kappa[(axis, lang, j1, j2)] = {
                    "n": len(vids),
                    "kappa": pt,
                    "ci_low": clo,
                    "ci_high": chi,
                }

    # 3) Intra-judge Krippendorff alpha across reruns (per judge, per axis)
    alpha = {}
    for jid in judges:
        for axis in axes:
            rating_lists = []
            for (vid, ax, j), reruns in by_item.items():
                if j == jid and ax == axis and len(reruns) >= 2:
                    rating_lists.append(reruns)
            if len(rating_lists) >= 5:
                alpha[(jid, axis)] = {
                    "n_items": len(rating_lists),
                    "alpha": krippendorff_alpha_ordinal(rating_lists),
                }

    # 4) Disagreement taxonomy: items where max-min across judges >= 2
    disagreements = []
    for vid in meta:
        for axis in axes:
            scores = {j: consensus.get((vid, axis, j))
                      for j in judges if (vid, axis, j) in consensus}
            if len(scores) < 2:
                continue
            vals = list(scores.values())
            spread = max(vals) - min(vals)
            if spread >= 2:
                disagreements.append({
                    "variant_id": vid,
                    "language": meta[vid]["language"],
                    "attack_vector": meta[vid]["attack_vector"],
                    "category": meta[vid]["category"],
                    "axis": axis,
                    "scores": scores,
                    "spread": spread,
                })

    return {
        "judges": judges,
        "axes": axes,
        "languages": languages,
        "judge_pairs": judge_pairs,
        "means": means,
        "kappa": kappa,
        "alpha": alpha,
        "disagreements": disagreements,
        "n_items_total": len(meta),
        "n_judgments_total": len(panel),
    }


# ----------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------

def fmt(x, p=2):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x:.{p}f}"


def render_report(stats: dict) -> str:
    lines = ["# IndicSafetyBench v3 — Validation Panel Report",
             "",
             f"Total judgments: {stats['n_judgments_total']}",
             f"Total items: {stats['n_items_total']}",
             f"Judges: {', '.join(stats['judges'])}",
             f"Axes: {', '.join(stats['axes'])}",
             ""]

    # 1) Mean score table per (judge, axis, language)
    lines.append("## Per-judge mean Likert score by language")
    lines.append("")
    for axis in stats["axes"]:
        lines.append(f"### Axis: `{axis}`")
        lines.append("")
        header = "| Judge | " + " | ".join(LANG_ORDER) + " |"
        sep = "|---|" + "|".join(["---:"] * len(LANG_ORDER)) + "|"
        lines.append(header)
        lines.append(sep)
        for jid in stats["judges"]:
            row = [jid]
            for lang in LANG_ORDER:
                k = (jid, axis, lang)
                if k in stats["means"]:
                    m = stats["means"][k]
                    row.append(f"{m['mean']:.2f}±{m['std']:.2f} (n={m['n']})")
                else:
                    row.append("—")
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    # 2) Inter-judge weighted kappa
    lines.append("## Inter-judge Cohen's weighted κ (bootstrap 95% CI)")
    lines.append("")
    for axis in stats["axes"]:
        lines.append(f"### Axis: `{axis}`")
        lines.append("")
        header = "| Pair | " + " | ".join(LANG_ORDER) + " |"
        sep = "|---|" + "|".join(["---:"] * len(LANG_ORDER)) + "|"
        lines.append(header)
        lines.append(sep)
        for (j1, j2) in stats["judge_pairs"]:
            row = [f"{j1}–{j2}"]
            for lang in LANG_ORDER:
                k = (axis, lang, j1, j2)
                if k in stats["kappa"]:
                    s = stats["kappa"][k]
                    row.append(f"{fmt(s['kappa'])} [{fmt(s['ci_low'])},{fmt(s['ci_high'])}]")
                else:
                    row.append("—")
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    # 3) Intra-judge alpha (Krippendorff across reruns)
    lines.append("## Intra-judge Krippendorff's α across reruns")
    lines.append("(Rating Roulette robustness check: higher = more rerun-consistent)")
    lines.append("")
    lines.append("| Judge | " + " | ".join(stats["axes"]) + " |")
    lines.append("|---|" + "|".join(["---:"] * len(stats["axes"])) + "|")
    for jid in stats["judges"]:
        row = [jid]
        for axis in stats["axes"]:
            k = (jid, axis)
            if k in stats["alpha"]:
                a = stats["alpha"][k]
                row.append(f"{fmt(a['alpha'])} (n={a['n_items']})")
            else:
                row.append("—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # 4) Disagreement summary
    n_dis = len(stats["disagreements"])
    lines.append("## Judge disagreements")
    lines.append("")
    lines.append(f"Items where max-min across judges ≥ 2: **{n_dis}** "
                 f"(of {stats['n_items_total']} × {len(stats['axes'])} = "
                 f"{stats['n_items_total'] * len(stats['axes'])} cell-axis pairs)")
    lines.append("")
    if stats["disagreements"]:
        # Stratify by language × axis × attack_vector
        bucket = defaultdict(int)
        for d in stats["disagreements"]:
            bucket[(d["language"], d["axis"], d["attack_vector"])] += 1
        lines.append("| Language | Axis | Attack vector | Disagreements |")
        lines.append("|---|---|---|---:|")
        for (lang, axis, av), n in sorted(bucket.items(), key=lambda x: -x[1]):
            lines.append(f"| {lang} | {axis} | {av} | {n} |")
        lines.append("")
        lines.append(f"Full per-item disagreement list: `{OUT_DISAGREE.name}`")

    return "\n".join(lines) + "\n"


def render_disagreements(stats: dict) -> str:
    """Per-item disagreement list, sorted by spread descending."""
    lines = ["# Judge disagreements — per-item detail",
             "",
             f"Items where max-min score across judges ≥ 2 on any axis.",
             ""]
    if not stats["disagreements"]:
        lines.append("(none)")
        return "\n".join(lines) + "\n"
    sorted_d = sorted(stats["disagreements"], key=lambda d: (-d["spread"], d["language"]))
    lines.append("| variant_id | language | axis | attack_vector | category | spread | scores |")
    lines.append("|---|---|---|---|---|---:|---|")
    for d in sorted_d:
        scores_str = " ".join(f"{j}={s}" for j, s in sorted(d["scores"].items()))
        lines.append(f"| {d['variant_id']} | {d['language']} | {d['axis']} | "
                     f"{d['attack_vector']} | {d['category']} | "
                     f"{d['spread']} | {scores_str} |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bootstrap", type=int, default=1000,
                   help="Bootstrap resamples for kappa CIs")
    args = p.parse_args()

    panel = load_panel()
    if not panel:
        print(f"No judgments found in {PANEL_DIR}. Run llm_judge_panel.py first.")
        return 1
    print(f"Loaded {len(panel)} judgment records from {PANEL_DIR}")

    stats = aggregate(panel, n_boot=args.bootstrap)

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(render_report(stats), encoding="utf-8")
    OUT_DISAGREE.write_text(render_disagreements(stats), encoding="utf-8")

    # Also dump machine-readable kappa records
    with open(OUT_KAPPA, "w", encoding="utf-8") as f:
        for (axis, lang, j1, j2), s in stats["kappa"].items():
            f.write(json.dumps({
                "axis": axis, "language": lang,
                "judge1": j1, "judge2": j2,
                **s,
            }) + "\n")

    print(f"Wrote {OUT_REPORT}")
    print(f"Wrote {OUT_DISAGREE}")
    print(f"Wrote {OUT_KAPPA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
