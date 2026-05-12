"""
Compare LLM judge (Gemini 2.5 Flash) vs heuristic auto-judge.

Computes:
  - Agreement on REFUSAL labels
  - Cohen's κ (chance-corrected agreement)
  - Per-language agreement
  - Per-model agreement
  - Disagreement examples for review

Output: data/pilot/judge_agreement_report.md
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

LLM_JUDGMENTS = Path("data/pilot/judgments_llm.jsonl")
HEURISTIC_JUDGMENTS = Path("data/pilot/judgments.jsonl")
REPORT = Path("data/pilot/judge_agreement_report.md")


def load_judgments(path: Path) -> dict:
    """Load judgments keyed by (variant_id, model_label)."""
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
                out[key] = j
            except (json.JSONDecodeError, KeyError):
                continue
    return out


def cohens_kappa(a_labels: list, b_labels: list) -> tuple[float, float, int]:
    """Compute Cohen's kappa for binary labels.
    Returns (kappa, raw_agreement, n)."""
    n = len(a_labels)
    if n == 0:
        return 0.0, 0.0, 0
    agree = sum(1 for x, y in zip(a_labels, b_labels) if x == y)
    raw = agree / n
    # P(chance)
    a_pos = sum(a_labels) / n
    b_pos = sum(b_labels) / n
    p_e = a_pos * b_pos + (1 - a_pos) * (1 - b_pos)
    if p_e == 1.0:
        return 1.0 if raw == 1.0 else 0.0, raw, n
    kappa = (raw - p_e) / (1 - p_e)
    return kappa, raw, n


def main():
    llm = load_judgments(LLM_JUDGMENTS)
    heuristic = load_judgments(HEURISTIC_JUDGMENTS)

    common_keys = set(llm.keys()) & set(heuristic.keys())
    print(f"LLM judgments: {len(llm)}")
    print(f"Heuristic judgments: {len(heuristic)}")
    print(f"Common (both judges): {len(common_keys)}")

    if not common_keys:
        print("No overlap to compare.")
        return 1

    # Filter to LLM judgments where parse succeeded
    valid_keys = [k for k in common_keys
                  if llm[k].get("refusal") is not None
                  and heuristic[k].get("refusal") is not None]
    print(f"Valid (both refusal labels present): {len(valid_keys)}")

    # Pairwise refusal labels
    llm_refusals = [llm[k]["refusal"] for k in valid_keys]
    heur_refusals = [heuristic[k]["refusal"] for k in valid_keys]

    kappa, raw, n = cohens_kappa(llm_refusals, heur_refusals)

    out = []
    out.append("# Judge Agreement Report\n")
    out.append(f"*Generated from {n} pairs of (LLM judge, heuristic judge) on identical (prompt, response) pairs.*\n")
    out.append(f"\n## Overall Agreement\n")
    out.append(f"- Raw agreement: **{raw:.1%}**")
    out.append(f"- Cohen's κ: **{kappa:.3f}**")

    # κ interpretation
    if kappa >= 0.81:
        interp = "almost perfect (≥0.81)"
    elif kappa >= 0.61:
        interp = "substantial (0.61-0.80)"
    elif kappa >= 0.41:
        interp = "moderate (0.41-0.60)"
    elif kappa >= 0.21:
        interp = "fair (0.21-0.40)"
    else:
        interp = "slight to poor (<0.21)"
    out.append(f"- Interpretation: **{interp}**\n")
    out.append(f"- Sample size: {n}\n")

    # Per-language
    out.append("\n## Agreement by Language\n")
    out.append("| Language | n | Raw agree | κ |")
    out.append("|----------|---|-----------|---|")
    by_lang = defaultdict(list)
    for k in valid_keys:
        lang = llm[k].get("language", "?")
        by_lang[lang].append(k)
    LANG_ORDER = ["en", "hi", "mr", "te", "kn", "ta", "bn"]
    for lang in LANG_ORDER:
        keys = by_lang.get(lang, [])
        if not keys:
            continue
        lr = [llm[k]["refusal"] for k in keys]
        hr = [heuristic[k]["refusal"] for k in keys]
        kk, rr, nn = cohens_kappa(lr, hr)
        out.append(f"| {lang} | {nn} | {rr:.1%} | {kk:.3f} |")

    # Per-model
    out.append("\n## Agreement by Model\n")
    out.append("| Model | n | Raw agree | κ |")
    out.append("|-------|---|-----------|---|")
    by_model = defaultdict(list)
    for k in valid_keys:
        by_model[k[1]].append(k)
    for m in sorted(by_model):
        keys = by_model[m]
        lr = [llm[k]["refusal"] for k in keys]
        hr = [heuristic[k]["refusal"] for k in keys]
        kk, rr, nn = cohens_kappa(lr, hr)
        out.append(f"| {m} | {nn} | {rr:.1%} | {kk:.3f} |")

    # Disagreement breakdown
    out.append("\n## Disagreement Confusion Matrix\n")
    out.append("| | Heuristic: refused (1) | Heuristic: engaged (0) |")
    out.append("|---|---|---|")
    counts = Counter()
    for k in valid_keys:
        counts[(llm[k]["refusal"], heuristic[k]["refusal"])] += 1
    out.append(f"| LLM: refused (1) | {counts[(1, 1)]} | {counts[(1, 0)]} |")
    out.append(f"| LLM: engaged (0) | {counts[(0, 1)]} | {counts[(0, 0)]} |")

    n_llm_strict = counts[(1, 0)]
    n_heur_strict = counts[(0, 1)]
    out.append(f"\n- {n_llm_strict} cases where LLM judge says refused, heuristic says engaged")
    out.append(f"- {n_heur_strict} cases where heuristic says refused, LLM says engaged")

    # Sample disagreements
    disagree_keys = [k for k in valid_keys
                     if llm[k]["refusal"] != heuristic[k]["refusal"]][:10]
    out.append("\n## Sample Disagreements (first 10)\n")
    for k in disagree_keys:
        out.append(f"\n### {k[0]} / {k[1]}")
        out.append(f"- LLM: refusal={llm[k]['refusal']} harm={llm[k].get('harm')}")
        out.append(f"- Heuristic: refusal={heuristic[k]['refusal']} harm={heuristic[k].get('harm')}")
        out.append(f"- LLM rationale: {llm[k].get('rationale', '')}")
        out.append(f"- Heuristic rationale: {heuristic[k].get('rationale', '')}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"\nWrote {REPORT}")
    print(f"κ = {kappa:.3f}, raw agree = {raw:.1%}, n = {n}")


if __name__ == "__main__":
    raise SystemExit(main())
