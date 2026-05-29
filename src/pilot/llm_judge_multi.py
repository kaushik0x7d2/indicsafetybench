"""
Multi-judge LLM-as-judge runner.

Generalizes src.pilot.llm_judge to accept a configurable judge model and
write its judgments to a per-judge JSONL file. Designed for v3 ensemble
judging: run this script once per judge in the ensemble, then run
src.pilot.compare_judges_multi to compute pairwise kappa and majority-vote
labels.

Cost-gated. DO NOT run blindly — each invocation spends real money on
OpenRouter / direct API. See cost estimates in docs/FUNDING_REQUEST.md.

Recommended v3 panel:
    --judge google/gemini-2.5-pro        # upgrade from -flash
    --judge anthropic/claude-opus-4.7    # second independent judge
    --judge openai/gpt-5                 # third independent judge

Usage (per judge):
    python -m src.pilot.llm_judge_multi --judge google/gemini-2.5-pro
    python -m src.pilot.llm_judge_multi --judge anthropic/claude-opus-4.7 --limit 50  # smoke
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from src.providers.openrouter import OpenRouterClient
from src.pilot.llm_judge import (
    JUDGE_PROMPT, LANG_NAMES, parse_judgment, RESPONSES_DIR,
)


JUDGMENTS_DIR = Path("data/pilot/judgments_multi")


def judge_slug(model_id: str) -> str:
    """openai/gpt-5 -> openai__gpt-5 (filesystem-safe)."""
    return model_id.replace("/", "__").replace(":", "_")


def output_path(model_id: str) -> Path:
    return JUDGMENTS_DIR / f"judgments_{judge_slug(model_id)}.jsonl"


def load_existing(path: Path) -> set:
    if not path.exists():
        return set()
    seen = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                j = json.loads(line)
                seen.add((j["variant_id"], j["model_label"]))
            except (json.JSONDecodeError, KeyError):
                continue
    return seen


def judge_response(client: OpenRouterClient, rec: dict, judge_model: str) -> dict:
    lang_name = LANG_NAMES.get(rec.get("language", "en"), "English")
    prompt = JUDGE_PROMPT.format(
        language=lang_name,
        prompt=rec["prompt"][:2000],
        response=(rec.get("response") or "(empty)")[:3000],
    )
    r = client.chat(prompt=prompt, model=judge_model, temperature=0.0, max_tokens=300)
    content = r.get("content") or ""
    judgment = parse_judgment(content)
    return {
        "variant_id": rec["variant_id"],
        "model_label": rec["model_label"],
        "language": rec.get("language"),
        "attack_vector": rec.get("attack_vector"),
        "category": rec.get("category"),
        "judge": judge_slug(judge_model),
        "judge_model_id": judge_model,
        "refusal": judgment["refusal"] if judgment else None,
        "harm": judgment["harm"] if judgment else None,
        "rationale": judgment["rationale"] if judgment else "",
        "judge_raw": content[:500],
        "parse_ok": judgment is not None,
        "ts": time.time(),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--judge", required=True,
                   help="OpenRouter model id, e.g. google/gemini-2.5-pro")
    p.add_argument("--limit", type=int, default=None,
                   help="Limit number of pairs (use for smoke testing before full spend)")
    args = p.parse_args()

    out_path = output_path(args.judge)
    JUDGMENTS_DIR.mkdir(parents=True, exist_ok=True)

    client = OpenRouterClient()

    all_responses = []
    for f in sorted(RESPONSES_DIR.glob("*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if "variant_id" not in rec or "model_label" not in rec:
                    continue
                if not rec.get("response"):
                    continue
                all_responses.append(rec)

    seen = load_existing(out_path)
    todo = [r for r in all_responses
            if (r["variant_id"], r["model_label"]) not in seen]
    if args.limit:
        todo = todo[:args.limit]

    print(f"Judge: {args.judge}")
    print(f"Output: {out_path}")
    print(f"Total responses: {len(all_responses)}")
    print(f"Already judged by {args.judge}: {len(seen)}")
    print(f"To judge in this run: {len(todo)}")

    if not todo:
        print("Nothing to do.")
        return 0

    success = failed = 0
    t_start = time.time()
    with open(out_path, "a", encoding="utf-8") as f:
        for i, rec in enumerate(todo, 1):
            try:
                j = judge_response(client, rec, judge_model=args.judge)
                f.write(json.dumps(j, ensure_ascii=False) + "\n")
                f.flush()
                if j["parse_ok"]:
                    success += 1
                else:
                    failed += 1
                if i % 50 == 0:
                    elapsed = time.time() - t_start
                    rate = i / elapsed if elapsed > 0 else 0
                    eta = (len(todo) - i) / rate if rate > 0 else 0
                    print(f"  [{i}/{len(todo)}] success={success} parse_fail={failed} | "
                          f"rate={rate:.1f}/s eta={eta:.0f}s | "
                          f"cost=${client.usage.estimated_cost_usd:.4f}",
                          flush=True)
            except Exception as e:
                failed += 1
                print(f"  [{i}/{len(todo)}] ERROR: {e}", flush=True)

    print(f"\nDone. Success: {success}  Parse-fail: {failed}")
    print(f"OpenRouter spend (this run): ${client.usage.estimated_cost_usd:.4f}")


if __name__ == "__main__":
    raise SystemExit(main())
