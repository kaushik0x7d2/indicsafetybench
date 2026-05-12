"""Native-speaker validation CLI for translations + judgments.

Usage:
    python -m src.paper.validate_cli --lang hi --task translation --n 50
    python -m src.paper.validate_cli --lang te --task judgment --n 30
    python -m src.paper.validate_cli --lang ta --task cultural_framing --n 20

Saves output to data/validation/{lang}_{task}.jsonl

For each item, prompts user with side-by-side comparison and accepts:
  y / 1 = correct / agree
  n / 0 = incorrect / disagree
  s     = skip
  q     = quit and save progress
"""
from __future__ import annotations
import argparse
import json
import random
import sys
from pathlib import Path

TEST_SET = Path("data/pilot/test_set.json")
JUDGMENTS = Path("data/pilot/judgments_llm.jsonl")
RESPONSES_DIR = Path("data/pilot/responses")
VAL_DIR = Path("data/validation")
VAL_DIR.mkdir(parents=True, exist_ok=True)


def load_variants(lang: str):
    d = json.load(open(TEST_SET, encoding="utf-8"))
    return [v for v in d["variants"] if v.get("language") == lang]


def load_judgments():
    j = {}
    if not JUDGMENTS.exists():
        return j
    with open(JUDGMENTS, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                j[(rec["variant_id"], rec["model_label"])] = rec
            except Exception:
                continue
    return j


def load_responses():
    r = {}
    for f in RESPONSES_DIR.glob("*.jsonl"):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                    if rec.get("response"):
                        r[(rec["variant_id"], rec["model_label"])] = rec["response"]
                except Exception:
                    continue
    return r


def find_english_seed(variant, all_variants):
    """Find the corresponding en_direct variant for an Indic variant."""
    seed_id = variant.get("seed_id")
    en = [v for v in all_variants if v["seed_id"] == seed_id and
          v["language"] == "en" and v["attack_vector"] == "direct"]
    return en[0] if en else None


def run_translation_validation(lang: str, n: int, out_path: Path):
    all_v = json.load(open(TEST_SET, encoding="utf-8"))["variants"]
    indic = [v for v in all_v if v["language"] == lang and v["attack_vector"] == "direct"]
    random.shuffle(indic)
    indic = indic[:n]
    print(f"\n=== Translation validation: {lang} — {len(indic)} items ===\n")
    print("For each item, judge whether the translation preserves the *adversarial intent*.")
    print("y = preserved   n = drifted/lost   s = skip   q = quit\n")
    results = []
    for i, v in enumerate(indic, 1):
        en = find_english_seed(v, all_v)
        if not en:
            continue
        print(f"\n[{i}/{len(indic)}] variant={v['variant_id']}")
        print(f"  EN: {en['prompt']}")
        print(f"  {lang.upper()}: {v['prompt']}")
        while True:
            ans = input("  preserved? [y/n/s/q] > ").strip().lower()
            if ans in ("y", "n", "s", "q", "1", "0"):
                break
        if ans == "q":
            break
        if ans == "s":
            continue
        ok = ans in ("y", "1")
        results.append({"variant_id": v["variant_id"], "lang": lang, "task": "translation",
                        "preserved": ok, "en_prompt": en["prompt"], "indic_prompt": v["prompt"]})
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    accuracy = sum(1 for r in results if r["preserved"]) / max(len(results), 1)
    print(f"\n=== Done. {len(results)} judgments saved to {out_path}")
    print(f"=== Preservation rate: {accuracy:.1%}")


def run_judgment_validation(lang: str, n: int, out_path: Path):
    all_v = json.load(open(TEST_SET, encoding="utf-8"))["variants"]
    indic_ids = {v["variant_id"] for v in all_v if v["language"] == lang}
    judgments = load_judgments()
    responses = load_responses()
    candidates = [(k, j) for k, j in judgments.items()
                  if k[0] in indic_ids and j.get("refusal") is not None and (k in responses)]
    random.shuffle(candidates)
    candidates = candidates[:n]
    print(f"\n=== Judgment validation: {lang} — {len(candidates)} items ===\n")
    print("For each (prompt, response, judge label), agree or disagree with the judge.")
    print("y = agree   n = disagree   s = skip   q = quit\n")
    results = []
    for i, ((vid, model), j) in enumerate(candidates, 1):
        v = next((v for v in all_v if v["variant_id"] == vid), None)
        if not v:
            continue
        resp = responses.get((vid, model), "")
        print(f"\n[{i}/{len(candidates)}] {vid} / {model}")
        print(f"  PROMPT: {v['prompt'][:300]}")
        print(f"  RESPONSE: {resp[:500]}")
        print(f"  JUDGE: refusal={j['refusal']} harm={j.get('harm', 0):.2f} ({j.get('rationale', '')[:100]})")
        while True:
            ans = input("  agree with judge? [y/n/s/q] > ").strip().lower()
            if ans in ("y", "n", "s", "q", "1", "0"):
                break
        if ans == "q":
            break
        if ans == "s":
            continue
        ok = ans in ("y", "1")
        results.append({"variant_id": vid, "model": model, "lang": lang, "task": "judgment",
                        "judge_refusal": j["refusal"], "human_agree": ok,
                        "prompt": v["prompt"][:300], "response": resp[:500]})
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    agree = sum(1 for r in results if r["human_agree"]) / max(len(results), 1)
    print(f"\n=== Done. {len(results)} judgments saved to {out_path}")
    print(f"=== Agreement with LLM judge: {agree:.1%}")


def run_cultural_framing_validation(lang: str, n: int, out_path: Path):
    all_v = json.load(open(TEST_SET, encoding="utf-8"))["variants"]
    cf = [v for v in all_v if v["language"] == lang and v["attack_vector"] == "cultural_framing"]
    random.shuffle(cf)
    cf = cf[:n]
    print(f"\n=== Cultural-framing plausibility: {lang} — {len(cf)} items ===\n")
    print("Rate 1-3: does this sound like an authentic Indian persona?")
    print("1 = obviously fake / fails to impersonate")
    print("2 = passable but artificial")
    print("3 = plausibly authentic")
    print("s = skip   q = quit\n")
    results = []
    for i, v in enumerate(cf, 1):
        en = find_english_seed(v, all_v)
        print(f"\n[{i}/{len(cf)}] {v['variant_id']}")
        if en:
            print(f"  EN BASE: {en['prompt'][:200]}")
        print(f"  {lang.upper()} CULTURAL: {v['prompt']}")
        while True:
            ans = input("  plausibility [1/2/3/s/q] > ").strip().lower()
            if ans in ("1", "2", "3", "s", "q"):
                break
        if ans == "q":
            break
        if ans == "s":
            continue
        results.append({"variant_id": v["variant_id"], "lang": lang, "task": "cultural_framing",
                        "plausibility": int(ans), "framed_prompt": v["prompt"]})
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    avg = sum(r["plausibility"] for r in results) / max(len(results), 1)
    high = sum(1 for r in results if r["plausibility"] >= 2) / max(len(results), 1)
    print(f"\n=== Done. {len(results)} ratings saved to {out_path}")
    print(f"=== Mean plausibility: {avg:.2f}/3.00,  ≥2 rate: {high:.1%}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lang", required=True, choices=["hi", "mr", "te", "kn", "ta", "bn"],
                   help="Indic language to validate")
    p.add_argument("--task", required=True,
                   choices=["translation", "judgment", "cultural_framing"],
                   help="Which validation task to run")
    p.add_argument("--n", type=int, default=50, help="Number of items to validate")
    p.add_argument("--seed", type=int, default=2026, help="Random seed for sampling")
    args = p.parse_args()
    random.seed(args.seed)
    out_path = VAL_DIR / f"{args.lang}_{args.task}.jsonl"
    if args.task == "translation":
        run_translation_validation(args.lang, args.n, out_path)
    elif args.task == "judgment":
        run_judgment_validation(args.lang, args.n, out_path)
    elif args.task == "cultural_framing":
        run_cultural_framing_validation(args.lang, args.n, out_path)


if __name__ == "__main__":
    sys.exit(main() or 0)
