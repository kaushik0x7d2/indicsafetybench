"""
Stratified sampler for the multilingual data-validation pass.

Reads data/pilot/test_set.json. For each (language, attack_vector) cell, draws
N items stratified uniformly across the 8 harm categories. Emits a flat JSONL
of selected variants plus a CSV ready for native-speaker annotation.

Per the protocol in docs/VALIDATION_PROTOCOL.md:
  - Default N = 30 per cell (matches power analysis for d=0.4, alpha=0.05, power=0.8)
  - Default seed = 2026 for reproducibility
  - Code-switching is not split into Variant A vs B by this script; that split
    requires script detection per item (see split_cs_variants() helper below,
    not yet wired in).

Usage:
    python -m src.validation.sample                          # defaults
    python -m src.validation.sample --n-per-cell 50          # bigger sample
    python -m src.validation.sample --languages en hi te     # subset
    python -m src.validation.sample --out data/validation/v2 # alternate dest
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import defaultdict
from pathlib import Path

TEST_SET = Path("data/pilot/test_set.json")
DEFAULT_OUT_DIR = Path("data/validation")

CATEGORIES = [
    "csam_adjacent", "cybercrime", "hate_speech", "misinformation",
    "privacy_doxxing", "self_harm", "sexual_exploitation", "violence_weapons",
]

# Per-language Indic Unicode block ranges, used to detect Variant B (mono-script)
# code-switching (English words transliterated INTO the Indic script).
# Heuristic: if a CS variant has >= 90% of its non-space chars in the target
# script's Unicode range, it's Variant B (mono-script). Otherwise Variant A
# (interleaved-script: target-script base + Latin-script English embeds).
SCRIPT_RANGES = {
    "hi": (0x0900, 0x097F),  # Devanagari
    "mr": (0x0900, 0x097F),  # Devanagari
    "bn": (0x0980, 0x09FF),  # Bengali
    "te": (0x0C00, 0x0C7F),  # Telugu
    "kn": (0x0C80, 0x0CFF),  # Kannada
    "ta": (0x0B80, 0x0BFF),  # Tamil
}


def detect_cs_variant(prompt: str, lang: str) -> str:
    """Return 'A' (interleaved-script) or 'B' (mono-script) for a CS prompt."""
    rng = SCRIPT_RANGES.get(lang)
    if not rng or not prompt:
        return "A"
    chars = [c for c in prompt if not c.isspace() and c.isalpha()]
    if not chars:
        return "A"
    in_script = sum(1 for c in chars if rng[0] <= ord(c) <= rng[1])
    in_latin = sum(1 for c in chars if 0x0041 <= ord(c) <= 0x007A)
    if in_script == 0:
        return "A"
    script_frac = in_script / (in_script + in_latin) if (in_script + in_latin) > 0 else 0
    return "B" if script_frac >= 0.9 else "A"


def cell_key(v: dict) -> tuple[str, str]:
    """(language, attack_vector) cell key, with CS split into A/B per script detection."""
    av = v["attack_vector"]
    if av == "code_switched":
        sub = detect_cs_variant(v["prompt"], v["language"])
        return (v["language"], f"code_switched_{sub}")
    return (v["language"], av)


def load_variants(test_set: Path) -> list[dict]:
    with open(test_set, encoding="utf-8") as f:
        d = json.load(f)
    return d["variants"]


def load_seed_lookup() -> dict[str, str]:
    """seed_id -> English seed text, for the equivalence-rating column."""
    lookup = {}
    seeds_dir = Path("data/seeds")
    for f in sorted(seeds_dir.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
            for p in d.get("prompts", []):
                lookup[p["id"]] = p["text"]
        except (json.JSONDecodeError, KeyError):
            continue
    return lookup


def stratified_sample(
    variants: list[dict],
    n_per_cell: int,
    rng: random.Random,
    languages: set[str] | None = None,
) -> list[dict]:
    """For each cell, draw n_per_cell items stratified uniformly across categories."""
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for v in variants:
        if languages and v["language"] not in languages:
            continue
        cells[cell_key(v)].append(v)

    selected: list[dict] = []
    for cell, items in sorted(cells.items()):
        per_cat = max(1, n_per_cell // len(CATEGORIES))
        bycat = defaultdict(list)
        for v in items:
            bycat[v["category"]].append(v)
        cell_pick: list[dict] = []
        for cat in CATEGORIES:
            pool = bycat.get(cat, [])
            if not pool:
                continue
            k = min(per_cat, len(pool))
            cell_pick.extend(rng.sample(pool, k))
        # Top up to n_per_cell from the leftover pool if categories underfilled
        if len(cell_pick) < n_per_cell:
            picked_ids = {v["variant_id"] for v in cell_pick}
            leftover = [v for v in items if v["variant_id"] not in picked_ids]
            shortfall = n_per_cell - len(cell_pick)
            cell_pick.extend(rng.sample(leftover, min(shortfall, len(leftover))))
        # Trim if overfilled
        cell_pick = cell_pick[:n_per_cell]
        # Annotate with cell so downstream knows the split
        for v in cell_pick:
            v = dict(v)
            v["_cell"] = f"{cell[0]}__{cell[1]}"
            selected.append(v)
    return selected


def write_jsonl(records: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_annotation_csv(records: list[dict], seed_lookup: dict[str, str], path: Path):
    """Spreadsheet for annotators: one row per item, blank score columns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "variant_id", "cell", "language", "attack_vector", "category",
            "english_seed", "prompt",
            "naturalness_1to5", "equivalence_1to5", "attack_validity_1to5",
            "comment",
        ])
        for r in records:
            w.writerow([
                r["variant_id"], r["_cell"], r["language"], r["attack_vector"],
                r["category"],
                seed_lookup.get(r["seed_id"], ""),
                r["prompt"],
                "", "", "",
                "",
            ])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n-per-cell", type=int, default=30)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--languages", nargs="*", default=None,
                   help="Subset of language codes (default: all)")
    args = p.parse_args()

    variants = load_variants(TEST_SET)
    seed_lookup = load_seed_lookup()
    rng = random.Random(args.seed)

    langs = set(args.languages) if args.languages else None
    selected = stratified_sample(variants, args.n_per_cell, rng, languages=langs)

    out_jsonl = args.out / f"sample_n{args.n_per_cell}.jsonl"
    out_csv = args.out / f"sample_n{args.n_per_cell}.csv"
    write_jsonl(selected, out_jsonl)
    write_annotation_csv(selected, seed_lookup, out_csv)

    # Summary
    cells = defaultdict(int)
    for r in selected:
        cells[r["_cell"]] += 1
    print(f"Selected {len(selected)} items across {len(cells)} cells")
    for cell, n in sorted(cells.items()):
        print(f"  {cell}: {n}")
    print(f"\nJSONL: {out_jsonl}")
    print(f"Annotation CSV: {out_csv}")


if __name__ == "__main__":
    raise SystemExit(main())
