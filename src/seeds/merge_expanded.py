"""Merge expanded test sets from data/expanded/*.json into master pilot test_set."""

import json
from pathlib import Path
from collections import Counter

EXPANDED_DIR = Path("data/expanded")
MASTER = Path("data/pilot/test_set.json")


def main():
    if not MASTER.exists():
        print(f"[FAIL] {MASTER} not found")
        return 1

    master = json.load(open(MASTER, encoding="utf-8"))
    existing_ids = {v["variant_id"] for v in master["variants"]}

    expanded_files = sorted(EXPANDED_DIR.glob("*_test_set.json"))
    if not expanded_files:
        print(f"[INFO] No expanded files in {EXPANDED_DIR}")
        return 0

    print(f"Found {len(expanded_files)} expanded files. Master starts at {len(master['variants'])} variants.")

    added = 0
    for f in expanded_files:
        ex = json.load(open(f, encoding="utf-8"))
        new_count = 0
        for v in ex["variants"]:
            if v["variant_id"] in existing_ids:
                continue
            master["variants"].append(v)
            existing_ids.add(v["variant_id"])
            new_count += 1
        added += new_count
        print(f"  + {f.name}: added {new_count} new variants ({len(ex['variants'])} total in file)")

    master["n_total_variants"] = len(master["variants"])
    master["languages"] = sorted({v["language"] for v in master["variants"]})
    master["attack_vectors"] = sorted({v["attack_vector"] for v in master["variants"]})

    with open(MASTER, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Master test set now has {len(master['variants'])} variants ({added} new)")
    print(f"By category:")
    for cat, n in Counter(v["category"] for v in master["variants"]).most_common():
        print(f"  {cat}: {n}")
    print(f"By language:")
    for lang, n in Counter(v["language"] for v in master["variants"]).most_common():
        print(f"  {lang}: {n}")


if __name__ == "__main__":
    main()
