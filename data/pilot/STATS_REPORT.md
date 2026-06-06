# Statistical Report — IndicSafetyBench v3

Bootstrap CIs (95%) computed with 1000 resamples, seed=2026.


## 1. Refusal rate with 95% bootstrap CI per (model × language)

| Model | en | hi | mr | te | kn | ta | bn |
|---|---|---|---|---|---|---|---|
| sarvam_105b | 96% [94,98] | 93% [90,95] | 93% [90,95] | 92% [90,94] | 91% [89,94] | 91% [89,94] | 93% [91,95] |
| sarvam_30b | 91% [87,94] | 87% [84,90] | 87% [84,90] | 82% [79,85] | 83% [79,86] | 83% [80,87] | 85% [82,88] |
| sarvam_m | 55% [50,60] | 64% [60,68] | 66% [62,71] | 68% [64,72] | 65% [61,69] | 66% [62,71] | 66% [62,70] |
| gpt_4o_mini | 67% [62,71] | 61% [57,66] | 57% [53,61] | 62% [58,66] | 58% [53,62] | 61% [57,66] | 64% [59,68] |
| gemini_25_flash | 74% [69,79] | 64% [60,69] | 72% [69,76] | 62% [58,66] | 57% [52,61] | 60% [56,64] | 67% [63,71] |
| llama_33_70b | 38% [33,43] | 54% [50,58] | 39% [35,43] | 39% [35,44] | 40% [36,45] | 39% [35,43] | 50% [46,55] |

## 2. Cultural-Framing Effect: Odds Ratios vs Direct (per model)

Lower OR (< 1.0) = framing *decreases* refusal odds (jailbreak success).

CI: paired bootstrap on (seed_id × language) pairs. Each resample draws pairs with both a direct and a cultural_framing label; Δ is computed within the resampled pair set.

| Model | Direct rate | Framing rate | Δ pp | OR (framing/direct) | Paired-bootstrap 95% CI on Δ |
|---|---|---|---|---|---|
| sarvam_105b | 91% | 93% | +2pp | 1.29 | [-0.3, +3.5] (n=1162 pairs) |
| sarvam_30b | 82% | 82% | -0pp | 0.97 | [-3.0, +2.3] (n=1132 pairs) |
| sarvam_m | 73% | 42% | -31pp | 0.27 | [-34.3, -27.9] (n=1182 pairs) |
| gpt_4o_mini | 64% | 48% | -16pp | 0.52 | [-19.0, -12.8] (n=1177 pairs) |
| gemini_25_flash | 68% | 49% | -20pp | 0.44 | [-23.0, -17.0] (n=1183 pairs) |
| llama_33_70b | 52% | 22% | -30pp | 0.26 | [-33.5, -26.6] (n=1186 pairs) |

## 3. Summary cells with notable findings

| Model | Language | Refusal | 95% CI | Note |
|---|---|---|---|---|

## 4. Overall refusal rate per model with CI

| Model | n | Refusal rate | 95% CI |
|---|---|---|---|
| sarvam_105b | 3370 | 93% | [92, 94] |
| sarvam_30b | 3333 | 85% | [84, 86] |
| sarvam_m | 3385 | 65% | [63, 67] |
| gpt_4o_mini | 3378 | 61% | [60, 63] |
| gemini_25_flash | 3390 | 65% | [63, 66] |
| llama_33_70b | 3392 | 43% | [42, 45] |