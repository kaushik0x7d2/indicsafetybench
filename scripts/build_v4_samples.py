"""Build the v4 Claude-judge expansion samples.

1) TA/BN scale-up: items 21-50 per cell (n=30 more × 6 cells = 180) + 15 retries from first run.
2) 5-lang extension: Sarvam-105B EN/HI/MR/TE/KN × {direct, cultural_framing, code_switched}, n=20/cell = 300.
"""
import json, os, random
from collections import defaultdict

random.seed(2026)

# Load full prepared 300-item sample (n=50/cell × 6 cells TA/BN)
with open('data/validation/claude_sensitivity_sample.json', encoding='utf-8') as f:
    full_300 = json.load(f)

# What was in the first n=20/cell batch? The build script took items[:20] per sorted cell.
by_cell = defaultdict(list)
for it in full_300:
    by_cell[(it['language'], it['attack_vector'])].append(it)
done_first_20 = []
remaining_30 = []
for k in sorted(by_cell):
    done_first_20.extend(by_cell[k][:20])
    remaining_30.extend(by_cell[k][20:50])

# Also retrieve the 15 failed variant_ids to retry
failed_ids = [
    'vw_0013__bn_code_switched', 'vw_0016__bn_code_switched', 'cy_0009__bn_code_switched',
    'pd_0018__bn_cultural_framing', 'cy_0010__bn_cultural_framing',
    'cy_0007__bn_direct', 'cy_0017__bn_direct',
    'cy_0013__ta_code_switched', 'cy_0017__ta_code_switched', 'pd_0010__ta_code_switched',
    'cy_0010__ta_code_switched', 'pd_0013__ta_code_switched',
    'cy_0015__ta_cultural_framing', 'mi_0013__ta_cultural_framing',
    'cy_0030__ta_direct',
]
done_by_id = {it['variant_id']: it for it in done_first_20}
retries = [done_by_id[vid] for vid in failed_ids if vid in done_by_id]
print(f'Scale-up: {len(remaining_30)} new + {len(retries)} retries = {len(remaining_30)+len(retries)}')

ta_bn_scale_up = remaining_30 + retries

slim_scale_up = [{
    'v': it['variant_id'], 'l': it['language'], 'a': it['attack_vector'],
    'p': it['prompt'], 'r': it['response'],
    'g': it['gemini_label'], 'h': it['heur_label'],
} for it in ta_bn_scale_up]

with open('data/validation/claude_v4_ta_bn_scale_up.json', 'w', encoding='utf-8') as f:
    json.dump(slim_scale_up, f, ensure_ascii=False)

# -----------------------------------------------------------------
# 5-lang extension: Sarvam-105B en/hi/mr/te/kn, n=20/cell
# -----------------------------------------------------------------
TARGET_LANGS = ['en', 'hi', 'mr', 'te', 'kn']
TARGET_VECTORS = ['direct', 'cultural_framing', 'code_switched']

responses = {}
with open('data/pilot/responses/sarvam_105b.jsonl', encoding='utf-8') as f:
    for line in f:
        r = json.loads(line)
        if r['language'] in TARGET_LANGS and r['attack_vector'] in TARGET_VECTORS:
            responses.setdefault((r['language'], r['attack_vector']), []).append(r)

# Load Gemini + heuristic labels
gemini = {}
with open('data/pilot/judgments_llm.jsonl', encoding='utf-8') as f:
    for line in f:
        r = json.loads(line)
        if r['model_label'] == 'sarvam_105b' and r['language'] in TARGET_LANGS and r.get('parse_ok'):
            gemini[r['variant_id']] = 'REFUSAL' if r['refusal'] == 1 else 'ENGAGEMENT'

heur = {}
for path in ('data/pilot/judgments_auto.jsonl', 'data/pilot/uncertain_for_review.jsonl'):
    with open(path, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            if r['model_label'] == 'sarvam_105b' and r['language'] in TARGET_LANGS:
                heur[r['variant_id']] = r['auto_label'].upper()

extension_sample = []
for k in sorted(responses):
    items = [r for r in responses[k] if r['variant_id'] in gemini and r['variant_id'] in heur]
    random.shuffle(items)
    extension_sample.extend(items[:20])
print(f'Extension: {len(extension_sample)} items')

slim_ext = []
for r in extension_sample:
    slim_ext.append({
        'v': r['variant_id'], 'l': r['language'], 'a': r['attack_vector'],
        'p': r['prompt'], 'r': r['response'],
        'g': gemini[r['variant_id']], 'h': heur[r['variant_id']],
    })

with open('data/validation/claude_v4_5lang_ext.json', 'w', encoding='utf-8') as f:
    json.dump(slim_ext, f, ensure_ascii=False)

# Print summary
for name, data in [('ta_bn_scale_up', slim_scale_up), ('5lang_ext', slim_ext)]:
    raw = json.dumps(data, ensure_ascii=False)
    print(f'{name}: {len(data)} items, chars {len(raw)}, utf-8 bytes {len(raw.encode("utf-8"))}')
