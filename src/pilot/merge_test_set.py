"""Merge test_set_additions_v2 into test_set.json. Adds languages and conditions."""

import json
from pathlib import Path

import sys

TEST_SET = Path("data/pilot/test_set.json")
ADDITIONS_DEFAULT = Path("data/pilot/test_set_additions_v2.json")
ADDITIONS = Path(sys.argv[1]) if len(sys.argv) > 1 else ADDITIONS_DEFAULT


def main():
    with open(TEST_SET, encoding="utf-8") as f:
        test_set = json.load(f)
    with open(ADDITIONS, encoding="utf-8") as f:
        additions = json.load(f)

    existing_ids = {v["variant_id"] for v in test_set["variants"]}
    new_variants = [v for v in additions["variants"] if v["variant_id"] not in existing_ids]

    print(f"Existing variants: {len(test_set['variants'])}")
    print(f"Additions in file: {len(additions['variants'])}")
    print(f"New (deduplicated): {len(new_variants)}")

    test_set["variants"].extend(new_variants)
    test_set["n_total_variants"] = len(test_set["variants"])

    # Update metadata
    test_set.setdefault("conditions", [])
    new_conditions = [
        {"id": "hi_cultural_framing", "language": "hi", "attack_vector": "cultural_framing"},
        {"id": "mr_direct", "language": "mr", "attack_vector": "direct"},
        {"id": "mr_cultural_framing", "language": "mr", "attack_vector": "cultural_framing"},
        {"id": "mr_code_switched", "language": "mr", "attack_vector": "code_switched"},
        {"id": "te_direct", "language": "te", "attack_vector": "direct"},
        {"id": "te_cultural_framing", "language": "te", "attack_vector": "cultural_framing"},
        {"id": "te_code_switched", "language": "te", "attack_vector": "code_switched"},
    ]
    existing_cond_ids = {c["id"] for c in test_set["conditions"]}
    for c in new_conditions:
        if c["id"] not in existing_cond_ids:
            test_set["conditions"].append(c)

    test_set["pilot_version"] = "v0.2"
    test_set["languages"] = sorted({v["language"] for v in test_set["variants"]})
    test_set["attack_vectors"] = sorted({v["attack_vector"] for v in test_set["variants"]})

    with open(TEST_SET, "w", encoding="utf-8") as f:
        json.dump(test_set, f, ensure_ascii=False, indent=2)

    from collections import Counter
    print(f"\nMerged. Total variants: {len(test_set['variants'])}")
    print(f"Languages: {test_set['languages']}")
    print(f"Attack vectors: {test_set['attack_vectors']}")
    print("\nBy language:")
    for k, v in sorted(Counter(v["language"] for v in test_set["variants"]).items()):
        print(f"  {k}: {v}")
    print("\nBy attack_vector:")
    for k, v in sorted(Counter(v["attack_vector"] for v in test_set["variants"]).items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
