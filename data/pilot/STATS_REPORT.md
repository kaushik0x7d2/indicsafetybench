# Statistical Report — IndicSafetyBench v3

Bootstrap CIs (95%) computed with 1000 resamples, seed=2026.


## 1. Refusal rate with 95% bootstrap CI per (model × language)

| Model | en | hi | mr | te | kn | ta | bn |
|---|---|---|---|---|---|---|---|
| sarvam_105b | 96% [94,98] | 93% [90,95] | 93% [90,95] | 92% [90,94] | 91% [89,94] | 91% [89,94] | 93% [91,95] |
| sarvam_30b | 91% [87,93] | 87% [84,90] | 87% [84,90] | 82% [78,85] | 83% [79,86] | 84% [80,87] | 85% [82,89] |
| sarvam_m | 55% [50,61] | 64% [60,68] | 67% [63,71] | 69% [65,73] | 66% [62,70] | 67% [63,72] | 67% [63,71] |
| gpt_4o_mini | 67% [61,71] | 61% [57,65] | 57% [53,61] | 62% [58,66] | 58% [53,62] | 61% [57,66] | 64% [60,68] |
| gemini_25_flash | 74% [69,79] | 64% [60,68] | 72% [69,76] | 62% [58,66] | 57% [52,62] | 60% [56,64] | 67% [63,72] |
| llama_33_70b | 38% [33,43] | 54% [50,58] | 39% [35,43] | 39% [35,44] | 40% [36,45] | 39% [35,43] | 50% [46,55] |

## 2. Cultural-Framing Effect: Odds Ratios vs Direct (per model)

Lower OR (< 1.0) = framing *decreases* refusal odds (jailbreak success).

| Model | Direct rate | Framing rate | Δ pp | OR (framing/direct) | Bootstrap 95% CI on Δ |
|---|---|---|---|---|---|
| sarvam_105b | 91% | 93% | +2pp | 1.29 | [-0.3, +4.2] |
| sarvam_30b | 82% | 81% | -1pp | 0.96 | [-3.7, +2.6] |
| sarvam_m | 73% | 42% | -31pp | 0.26 | [-35.2, -27.5] |
| gpt_4o_mini | 64% | 48% | -16pp | 0.52 | [-19.6, -11.8] |
| gemini_25_flash | 68% | 49% | -20pp | 0.44 | [-23.6, -16.2] |
| llama_33_70b | 52% | 22% | -30pp | 0.26 | [-33.5, -26.2] |

## 3. Summary cells with notable findings

| Model | Language | Refusal | 95% CI | Note |
|---|---|---|---|---|

## 4. Overall refusal rate per model with CI

| Model | n | Refusal rate | 95% CI |
|---|---|---|---|
| sarvam_105b | 3370 | 93% | [92, 94] |
| sarvam_30b | 3312 | 85% | [84, 87] |
| sarvam_m | 3350 | 66% | [64, 67] |
| gpt_4o_mini | 3378 | 61% | [60, 63] |
| gemini_25_flash | 3390 | 65% | [63, 66] |
| llama_33_70b | 3392 | 43% | [42, 45] |