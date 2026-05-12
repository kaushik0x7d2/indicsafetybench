"""
Pilot runner: send all 48 prompt variants to a target model, save responses.

Usage:
    python -m src.pilot.run_pilot --model sarvam-30b
    python -m src.pilot.run_pilot --model sarvam-m
    python -m src.pilot.run_pilot --model google/gemini-2.5-flash
    python -m src.pilot.run_pilot --model openai/gpt-4o-mini --limit 5
    python -m src.pilot.run_pilot --all                 # run all configured models

Output: data/pilot/responses/{model_label}.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from src.providers.sarvam import SarvamClient, SarvamError
from src.providers.openrouter import OpenRouterClient, OpenRouterError, OpenRouterBudgetExceeded


TEST_SET_PATH = Path("data/pilot/test_set.json")
RESPONSES_DIR = Path("data/pilot/responses")
RESPONSES_DIR.mkdir(parents=True, exist_ok=True)


# Model registry: maps user-facing model identifier to (provider, model_name, label)
MODELS = {
    # Sarvam (free)
    "sarvam-30b":         ("sarvam", "sarvam-30b",   "sarvam_30b"),
    "sarvam-105b":        ("sarvam", "sarvam-105b",  "sarvam_105b"),
    "sarvam-m":           ("sarvam", "sarvam-m",     "sarvam_m"),
    # OpenRouter (paid, careful)
    "google/gemini-2.5-flash":            ("openrouter", "google/gemini-2.5-flash",            "gemini_25_flash"),
    "google/gemini-2.5-pro":              ("openrouter", "google/gemini-2.5-pro",              "gemini_25_pro"),
    "openai/gpt-4o":                      ("openrouter", "openai/gpt-4o",                      "gpt_4o"),
    "openai/gpt-4o-mini":                 ("openrouter", "openai/gpt-4o-mini",                 "gpt_4o_mini"),
    "meta-llama/llama-3.3-70b-instruct":  ("openrouter", "meta-llama/llama-3.3-70b-instruct",  "llama_33_70b"),
    "mistralai/mistral-small-3":          ("openrouter", "mistralai/mistral-small-3",          "mistral_small_3"),
}


def load_test_set():
    with open(TEST_SET_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_existing_variant_ids(out_path: Path) -> set:
    """Return variant_ids already evaluated for this model — supports resume."""
    if not out_path.exists():
        return set()
    seen = set()
    with open(out_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                seen.add(json.loads(line)["variant_id"])
            except (KeyError, json.JSONDecodeError):
                continue
    return seen


def run_one_model(
    model_key: str,
    variants: list[dict],
    sarvam_client: SarvamClient,
    openrouter_client: OpenRouterClient,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    limit: int | None = None,
):
    if model_key not in MODELS:
        raise ValueError(f"Unknown model: {model_key}. Options: {list(MODELS)}")

    provider, model_name, label = MODELS[model_key]
    out_path = RESPONSES_DIR / f"{label}.jsonl"
    seen = get_existing_variant_ids(out_path)
    todo = [v for v in variants if v["variant_id"] not in seen]
    if limit:
        todo = todo[:limit]

    print(f"\n{'='*60}")
    print(f"Model: {model_key}  (provider={provider}, label={label})")
    print(f"Variants: {len(variants)} total | {len(seen)} already done | {len(todo)} to run")
    print(f"Output: {out_path}")
    print(f"{'='*60}")

    if not todo:
        print("Nothing to do.")
        return

    successes = 0
    failures = 0
    t_start = time.time()

    with open(out_path, "a", encoding="utf-8") as f:
        for i, v in enumerate(todo, 1):
            t0 = time.time()
            try:
                if provider == "sarvam":
                    r = sarvam_client.chat(
                        v["prompt"],
                        model=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                elif provider == "openrouter":
                    # Prefer fast providers for Llama and Mistral
                    provider_order = None
                    if "llama" in model_name.lower():
                        provider_order = ["Groq", "Cerebras", "Together", "Fireworks"]
                    elif "mistral" in model_name.lower():
                        provider_order = ["Mistral", "Together", "Fireworks"]
                    r = openrouter_client.chat(
                        v["prompt"],
                        model=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        provider_order=provider_order,
                    )
                else:
                    raise ValueError(f"Unknown provider: {provider}")

                elapsed = time.time() - t0
                content = r.get("content")
                reasoning = r.get("reasoning_content")
                # If content is None due to reasoning truncation, mark explicitly
                if content is None and reasoning:
                    content_status = "reasoning_truncated"
                elif content is None:
                    content_status = "empty"
                else:
                    content_status = "ok"

                record = {
                    "variant_id": v["variant_id"],
                    "seed_id": v["seed_id"],
                    "category": v["category"],
                    "language": v["language"],
                    "attack_vector": v["attack_vector"],
                    "model": model_key,
                    "model_label": label,
                    "provider": provider,
                    "prompt": v["prompt"],
                    "response": content or "",
                    "reasoning_content": reasoning or "",
                    "content_status": content_status,
                    "finish_reason": r.get("finish_reason"),
                    "prompt_tokens": r.get("prompt_tokens"),
                    "completion_tokens": r.get("completion_tokens"),
                    "estimated_cost_usd": r.get("estimated_cost_usd", 0.0),
                    "elapsed_seconds": round(elapsed, 2),
                    "timestamp": time.time(),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()
                successes += 1
                tag = "[OK]" if content_status == "ok" else f"[{content_status.upper()}]"
                print(f"  [{i:>2}/{len(todo)}] {tag} {elapsed:>5.1f}s  {v['variant_id']}")
            except (SarvamError, OpenRouterError, OpenRouterBudgetExceeded) as e:
                failures += 1
                err_record = {
                    "variant_id": v["variant_id"],
                    "model": model_key,
                    "error": str(e),
                    "timestamp": time.time(),
                }
                f.write(json.dumps(err_record, ensure_ascii=False) + "\n")
                f.flush()
                print(f"  [{i:>2}/{len(todo)}] [FAIL] {v['variant_id']}: {str(e)[:80]}")
                if isinstance(e, OpenRouterBudgetExceeded):
                    print("\nBudget exceeded — stopping.")
                    break

    total_time = time.time() - t_start
    print(f"\nDone in {total_time:.1f}s.  Successes: {successes}  Failures: {failures}")
    if provider == "openrouter":
        print(f"OpenRouter cumulative spend: ${openrouter_client.usage.estimated_cost_usd:.4f}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", help=f"Model key from registry. Options: {list(MODELS)}")
    p.add_argument("--all", action="store_true", help="Run all models in registry")
    p.add_argument("--limit", type=int, default=None, help="Run only first N variants")
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument("--temperature", type=float, default=0.7)
    args = p.parse_args()

    if not args.model and not args.all:
        p.error("Must specify --model MODEL_KEY or --all")

    test_set = load_test_set()
    variants = test_set["variants"]
    print(f"Loaded {len(variants)} variants from {TEST_SET_PATH}")

    sarvam_client = SarvamClient()
    openrouter_client = OpenRouterClient()

    if args.all:
        # Default lineup for pilot — fast & cheap models first
        lineup = [
            "sarvam-m",                          # free, fast (~2s/req)
            "google/gemini-2.5-flash",           # very cheap
            "openai/gpt-4o-mini",                # very cheap
            "meta-llama/llama-3.3-70b-instruct", # cheap
            "sarvam-30b",                        # free, slow (~50s/req)
        ]
        for m in lineup:
            try:
                run_one_model(m, variants, sarvam_client, openrouter_client,
                              max_tokens=args.max_tokens,
                              temperature=args.temperature,
                              limit=args.limit)
            except KeyboardInterrupt:
                print("\nInterrupted by user.")
                sys.exit(130)
    else:
        run_one_model(args.model, variants, sarvam_client, openrouter_client,
                      max_tokens=args.max_tokens,
                      temperature=args.temperature,
                      limit=args.limit)


if __name__ == "__main__":
    main()
