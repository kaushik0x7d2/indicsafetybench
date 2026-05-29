"""
Multi-judge ensemble comparator.

Loads judgments from:
  - data/pilot/judgments.jsonl                       (heuristic, baseline)
  - data/pilot/judgments_llm.jsonl                   (Gemini-2.5-Flash, current primary)
  - data/pilot/judgments_multi/judgments_*.jsonl     (any v3 ensemble judges)

For every pair of judges with sufficient overlap, computes pairwise Cohen's
kappa, raw agreement, and per-(model, language) cell kappa. Also computes
majority-vote refusal labels across all LLM judges (excludes heuristic) and
reports the disagreement rate of each judge against the majority.

Output: data/pilot/judge_ensemble_report.md

Usage:
    python -m src.pilot.compare_judges_multi
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import median

HEURISTIC = Path("data/pilot/judgments.jsonl")
LLM_PRIMARY = Path("data/pilot/judgments_llm.jsonl")
MULTI_DIR = Path("data/pilot/judgments_multi")
REPORT = Path("data/pilot/judge_ensemble_report.md")


def load(path: Path, judge_name: str | None = None) -> dict[tuple, dict]:
    if not path.exists():
        return {}
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                j = json.loads(line)
                key = (j["variant_id"], j["model_label"])
                if judge_name:
                    j["judge"] = judge_name
                out[key] = j
            except (json.JSONDecodeError, KeyError):
                continue
    return out


def discover_judges() -> dict[str, dict]:
    """{judge_name: {key: judgment}}."""
    judges = {}
    judges["heuristic"] = load(HEURISTIC, judge_name="heuristic")
    if LLM_PRIMARY.exists():
        judges["gemini_25_flash"] = load(LLM_PRIMARY, judge_name="gemini_25_flash")
    if MULTI_DIR.exists():
        for f in sorted(MULTI_DIR.glob("judgments_*.jsonl")):
            name = f.stem.replace("judgments_", "")
            judges[name] = load(f, judge_name=name)
    return {k: v for k, v in judges.items() if v}


def cohens_kappa(a: list[int], b: list[int]) -> tuple[float, float, int]:
    n = len(a)
    if n == 0:
        return float("nan"), 0.0, 0
    agree = sum(1 for x, y in zip(a, b) if x == y)
    raw = agree / n
    a_pos = sum(a) / n
    b_pos = sum(b) / n
    pe = a_pos * b_pos + (1 - a_pos) * (1 - b_pos)
    if pe == 1.0:
        return (1.0 if raw == 1.0 else float("nan")), raw, n
    return (raw - pe) / (1 - pe), raw, n


def aligned_pair(j1: dict, j2: dict) -> tuple[list[int], list[int], list[tuple]]:
    keys = sorted(set(j1) & set(j2))
    a, b, ks = [], [], []
    for k in keys:
        r1, r2 = j1[k].get("refusal"), j2[k].get("refusal")
        if r1 is None or r2 is None:
            continue
        a.append(int(r1))
        b.append(int(r2))
        ks.append(k)
    return a, b, ks


def majority_vote(judges: dict[str, dict]) -> dict[tuple, int]:
    """Per-item majority refusal label across all NON-heuristic judges."""
    llm_judges = {k: v for k, v in judges.items() if k != "heuristic"}
    if not llm_judges:
        return {}
    all_keys = set()
    for j in llm_judges.values():
        all_keys |= set(j)
    out = {}
    for k in all_keys:
        votes = [j[k]["refusal"] for j in llm_judges.values()
                 if k in j and j[k].get("refusal") is not None]
        if not votes:
            continue
        out[k] = 1 if sum(votes) * 2 > len(votes) else 0  # tie → 0
    return out


def render_report(judges: dict[str, dict]) -> str:
    names = list(judges.keys())
    lines = ["# IndicSafetyBench — Multi-judge Ensemble Report\n"]
    lines.append(f"Judges in this report ({len(names)}):")
    for n in names:
        lines.append(f"- `{n}` — {len(judges[n])} judgments")
    lines.append("")

    # Pairwise kappa table
    lines.append("## Pairwise Cohen's kappa\n")
    lines.append("| | " + " | ".join(names) + " |")
    lines.append("|" + "---|" * (len(names) + 1))
    for n1 in names:
        row = [n1]
        for n2 in names:
            if n1 == n2:
                row.append("—")
                continue
            a, b, _ = aligned_pair(judges[n1], judges[n2])
            kappa, _raw, n = cohens_kappa(a, b)
            row.append(f"{kappa:.3f} (n={n})" if n else "—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Disagreement of each judge against the majority vote
    if len([n for n in names if n != "heuristic"]) >= 3:
        mv = majority_vote(judges)
        lines.append("## Disagreement vs majority vote (LLM judges only)\n")
        lines.append(f"Majority labels: {len(mv)} items.\n")
        lines.append("| Judge | Disagreements with majority | % |")
        lines.append("|---|---:|---:|")
        for n in names:
            if n == "heuristic":
                continue
            judg = judges[n]
            disag = 0
            tot = 0
            for k, mvk in mv.items():
                if k in judg and judg[k].get("refusal") is not None:
                    tot += 1
                    if int(judg[k]["refusal"]) != mvk:
                        disag += 1
            pct = (100 * disag / tot) if tot else 0
            lines.append(f"| {n} | {disag}/{tot} | {pct:.1f}% |")
        lines.append("")

    # Per-cell kappa for each judge pair (collapsed to most interesting pair: heuristic vs majority)
    if len([n for n in names if n != "heuristic"]) >= 2 and "heuristic" in judges:
        mv = majority_vote(judges)
        if mv:
            lines.append("## Per-cell kappa: heuristic vs LLM-majority\n")
            lines.append("| Model | EN | HI | MR | TE | KN | TA | BN |")
            lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
            LANG_ORDER = ["en", "hi", "mr", "te", "kn", "ta", "bn"]
            cells: dict[tuple, list[tuple[int, int]]] = defaultdict(list)
            heur = judges["heuristic"]
            for k, mvk in mv.items():
                if k in heur and heur[k].get("refusal") is not None:
                    lang = heur[k].get("language") or (judges.get("gemini_25_flash", {}).get(k, {}).get("language"))
                    model = k[1]
                    if lang:
                        cells[(model, lang)].append((int(heur[k]["refusal"]), mvk))
            models = sorted({m for m, _ in cells.keys()})
            for m in models:
                row = [m]
                for lang in LANG_ORDER:
                    pairs = cells.get((m, lang), [])
                    if len(pairs) < 5:
                        row.append("—")
                        continue
                    a = [p[0] for p in pairs]
                    b = [p[1] for p in pairs]
                    kappa, _r, _n = cohens_kappa(a, b)
                    row.append(f"{kappa:.2f}")
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")

    return "\n".join(lines)


def main():
    judges = discover_judges()
    if len(judges) < 2:
        print(f"Only {len(judges)} judge(s) found; need at least 2 to compare.")
        print("Run `python -m src.pilot.llm_judge_multi --judge <model>` first.")
        return 1

    report = render_report(judges)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT}")
    print(f"Compared {len(judges)} judges: {', '.join(judges)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
