"""
Partial-coverage Krutrim pilot runner.

Designed for the ~INR 300 budget: stratified-samples a small subset of the
3,340-variant test set across (language x attack_vector x category) and runs
one Krutrim model on that subset. Saves to the standard pilot responses
directory with a clear "_partial" suffix so downstream metrics can flag the
limited n.

Usage:
    python -m src.pilot.run_krutrim_partial --model gpt-oss-120b --n 100
    python -m src.pilot.run_krutrim_partial --model gemma-4-E4B-it --n 200 --budget-inr 150
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import defaultdict
from pathlib import Path

from src.providers.krutrim import KrutrimClient, KrutrimBudgetExceeded, KrutrimError

TEST_SET_PATH = Path("data/pilot/test_set.json")
RESPONSES_DIR = Path("data/pilot/responses")


def stratified_sample(variants: list[dict], n_target: int, seed: int) -> list[dict]:
    """Stratified sample across (language, attack_vector) cells.

    Each cell gets ceil(n_target / n_cells) items, then total is trimmed to
    n_target by uniform random draw from leftover. Within a cell, items are
    chosen uniformly across the 8 harm categories.
    """
    rng = random.Random(seed)
    cells = defaultdict(list)
    for v in variants:
        cells[(v["language"], v["attack_vector"])].append(v)

    per_cell = max(1, n_target // len(cells))
    selected: list[dict] = []
    for cell_key, items in sorted(cells.items()):
        by_cat = defaultdict(list)
        for v in items:
            by_cat[v["category"]].append(v)
        k_per_cat = max(1, per_cell // 8)
        picked = []
        for cat in sorted(by_cat):
            pool = by_cat[cat]
            picked.extend(rng.sample(pool, min(k_per_cat, len(pool))))
        # Top up the cell to per_cell from leftover
        picked_ids = {v["variant_id"] for v in picked}
        leftover = [v for v in items if v["variant_id"] not in picked_ids]
        rng.shuffle(leftover)
        while len(picked) < per_cell and leftover:
            picked.append(leftover.pop())
        selected.extend(picked[:per_cell])

    # Trim to n_target by uniform random
    if len(selected) > n_target:
        rng.shuffle(selected)
        selected = selected[:n_target]
    return selected


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, help="Krutrim model id (e.g. gpt-oss-120b)")
    p.add_argument("--label", default=None,
                   help="Filesystem-safe label for output JSONL (default: krutrim_<model>)")
    p.add_argument("--n", type=int, default=100, help="Approx number of prompts to run")
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--max-tokens", type=int, default=1024)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--budget-inr", type=float, default=None,
                   help="Override KRUTRIM_BUDGET_INR for this run")
    args = p.parse_args()

    label = args.label or f"krutrim_{args.model.replace('/', '_').replace('.', '_')}_partial"
    out_path = RESPONSES_DIR / f"{label}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(TEST_SET_PATH, encoding="utf-8") as f:
        variants = json.load(f)["variants"]
    print(f"Loaded {len(variants)} variants total")

    sample = stratified_sample(variants, args.n, args.seed)
    print(f"Stratified sample: {len(sample)} prompts across "
          f"{len({(v['language'], v['attack_vector']) for v in sample})} cells")

    # Resume support
    seen = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    seen.add(json.loads(line)["variant_id"])
                except (KeyError, json.JSONDecodeError):
                    continue
    todo = [v for v in sample if v["variant_id"] not in seen]
    print(f"Already done: {len(seen)}. To run: {len(todo)}\n")

    if not todo:
        print("Nothing to do.")
        return 0

    client = KrutrimClient(budget_inr=args.budget_inr)
    print(f"Output: {out_path}")
    print(f"Budget remaining: INR {client.budget_inr - client.usage.estimated_cost_inr:.2f}\n")

    successes = failures = 0
    t_start = time.time()
    with open(out_path, "a", encoding="utf-8") as f:
        for i, v in enumerate(todo, 1):
            t0 = time.time()
            try:
                r = client.chat(
                    v["prompt"],
                    model=args.model,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                )
                elapsed = time.time() - t0
                record = {
                    "variant_id": v["variant_id"],
                    "seed_id": v["seed_id"],
                    "category": v["category"],
                    "language": v["language"],
                    "attack_vector": v["attack_vector"],
                    "model": f"krutrim/{args.model}",
                    "model_label": label,
                    "provider": "krutrim",
                    "prompt": v["prompt"],
                    "response": r.get("content") or "",
                    "reasoning_content": "",
                    "content_status": "ok" if r.get("content") else "empty",
                    "finish_reason": r.get("finish_reason"),
                    "prompt_tokens": r.get("prompt_tokens"),
                    "completion_tokens": r.get("completion_tokens"),
                    "estimated_cost_inr": r.get("cost_inr", 0.0),
                    "elapsed_seconds": round(elapsed, 2),
                    "timestamp": time.time(),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()
                successes += 1
                if i % 10 == 0 or i == 1:
                    spent = client.usage.estimated_cost_inr
                    print(f"  [{i:>3}/{len(todo)}] OK  {elapsed:>4.1f}s  "
                          f"tokens={r.get('prompt_tokens')}/{r.get('completion_tokens')}  "
                          f"INR spent~{spent:.2f}", flush=True)
            except (KrutrimError, KrutrimBudgetExceeded) as e:
                failures += 1
                err_record = {
                    "variant_id": v["variant_id"],
                    "model": f"krutrim/{args.model}",
                    "error": str(e)[:300],
                    "timestamp": time.time(),
                }
                f.write(json.dumps(err_record, ensure_ascii=False) + "\n")
                f.flush()
                print(f"  [{i:>3}/{len(todo)}] FAIL {v['variant_id']}: {str(e)[:80]}", flush=True)
                if isinstance(e, KrutrimBudgetExceeded):
                    print("\nBudget exhausted -- stopping.")
                    break

    total_time = time.time() - t_start
    print(f"\nDone in {total_time:.1f}s. Successes: {successes}  Failures: {failures}")
    print(f"Estimated INR spent this run: {client.usage.estimated_cost_inr:.2f}")
    print(f"Verify against console wallet activity at https://cloud.olakrutrim.com")


if __name__ == "__main__":
    raise SystemExit(main())
