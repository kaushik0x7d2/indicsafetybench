# Statistical Report — IndicSafetyBench v3

Bootstrap CIs (95%) computed with 1000 resamples, seed=2026.


## 1. Refusal rate with 95% bootstrap CI per (model × language)

| Model | en | hi | mr | te | kn | ta | bn |
|---|---|---|---|---|---|---|---|
| sarvam_105b | 94% [92,97] | 86% [83,89] | 51% [47,56] | 55% [51,59] | 67% [63,71] | 32% [27,36] | 37% [33,41] |
| sarvam_30b | 89% [85,92] | 81% [77,84] | 45% [40,49] | 45% [41,49] | 62% [58,66] | 26% [23,31] | 32% [28,36] |
| sarvam_m | 68% [62,72] | 67% [62,71] | 55% [50,59] | 62% [57,66] | 58% [54,62] | 51% [47,55] | 60% [55,64] |
| gpt_4o_mini | 70% [65,75] | 65% [61,69] | 54% [49,58] | 61% [57,65] | 58% [54,62] | 61% [57,66] | 65% [61,68] |
| gemini_25_flash | 74% [69,78] | 64% [60,68] | 57% [53,61] | 52% [48,56] | 54% [49,58] | 44% [39,48] | 53% [48,57] |
| llama_33_70b | 38% [33,43] | 59% [55,64] | 21% [18,25] | 34% [30,38] | 33% [29,37] | 32% [28,36] | 41% [37,46] |

## 2. Cultural-Framing Effect: Odds Ratios vs Direct (per model)

Lower OR (< 1.0) = framing *decreases* refusal odds (jailbreak success).

| Model | Direct rate | Framing rate | Δ pp | OR (framing/direct) | Bootstrap 95% CI on Δ |
|---|---|---|---|---|---|
| sarvam_105b | 57% | 55% | -2pp | 0.92 | [-6.1, +2.3] |
| sarvam_30b | 49% | 46% | -3pp | 0.90 | [-6.7, +1.4] |
| sarvam_m | 65% | 44% | -21pp | 0.42 | [-24.9, -17.1] |
| gpt_4o_mini | 65% | 50% | -15pp | 0.55 | [-18.6, -10.7] |
| gemini_25_flash | 58% | 43% | -16pp | 0.53 | [-19.7, -11.9] |
| llama_33_70b | 46% | 18% | -28pp | 0.25 | [-31.8, -24.4] |

## 3. Summary cells with notable findings

| Model | Language | Refusal | 95% CI | Note |
|---|---|---|---|---|
| llama_33_70b | mr | 21% | [18, 25] | catastrophic |
| sarvam_30b | ta | 26% | [23, 31] | catastrophic |
| sarvam_30b | bn | 32% | [27, 36] | catastrophic |
| llama_33_70b | ta | 32% | [27, 36] | catastrophic |
| sarvam_105b | ta | 32% | [27, 36] | catastrophic |
| llama_33_70b | kn | 33% | [29, 37] | catastrophic |
| llama_33_70b | te | 34% | [30, 38] | catastrophic |

## 4. Overall refusal rate per model with CI

| Model | n | Refusal rate | 95% CI |
|---|---|---|---|
| sarvam_105b | 3400 | 59% | [57, 60] |
| sarvam_30b | 3400 | 52% | [51, 54] |
| sarvam_m | 3362 | 60% | [58, 61] |
| gpt_4o_mini | 3399 | 62% | [60, 63] |
| gemini_25_flash | 3392 | 56% | [54, 58] |
| llama_33_70b | 3400 | 37% | [35, 39] |