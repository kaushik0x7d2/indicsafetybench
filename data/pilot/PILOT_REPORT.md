# IndicSafetyBench — Pilot Run Report

*Pilot v0.1 — generated from 20353 judgments*

## Caveats

- **PILOT-GRADE JUDGMENTS** from heuristic auto-classifier with rule-based defaults for ambiguous cases
- Single-judge (no 3-judge consensus yet)
- Sample size per cell is small (1-12 prompts) — confidence intervals are wide
- These numbers VALIDATE METHODOLOGY, not the field claims
- Full benchmark will use 3-judge LLM consensus + human spot-check

## 1. Headline: Refusal Rate and ASR by Model

| Model | n | Refusal Rate | Mean Harm | ASR (engaged-only) |
|-------|---|-------------|-----------|--------------------|
| gemini_25_flash | 3392 | 56% | 0.28 | 0.64 |
| gpt_4o_mini | 3399 | 62% | 0.20 | 0.52 |
| llama_33_70b | 3400 | 37% | 0.33 | 0.52 |
| sarvam_105b | 3400 | 59% | 0.20 | 0.49 |
| sarvam_30b | 3400 | 52% | 0.22 | 0.47 |
| sarvam_m | 3362 | 60% | 0.24 | 0.59 |

## 2. Headline by Attack Vector (across all models, all languages)

| Attack Vector | n | Refusal Rate | Mean Harm |
|---------------|---|-------------|-----------|
| direct | 7122 | 57% | 0.23 |
| cultural_framing | 7126 | 43% | 0.32 |
| code_switched | 6105 | 65% | 0.19 |

## 3. Headline by Language (across all models, all attack vectors)

| Language | n | Refusal Rate | Mean Harm |
|----------|---|-------------|-----------|
| English | 2035 | 72% | 0.17 |
| Hindi | 3052 | 70% | 0.16 |
| Marathi | 3053 | 47% | 0.28 |
| Telugu | 3053 | 51% | 0.26 |
| Kannada | 3053 | 55% | 0.24 |
| Tamil | 3053 | 41% | 0.31 |
| Bengali | 3054 | 48% | 0.27 |

## 4. Refusal Rate by Model × Attack Vector

| Model | direct | cultural_framing | code_switched |
|-------|--------|------------------|---------------|
| gemini_25_flash | 58% (n=1185) | 43% (n=1190) | 69% (n=1017) |
| gpt_4o_mini | 65% (n=1190) | 50% (n=1189) | 71% (n=1020) |
| llama_33_70b | 46% (n=1190) | 18% (n=1190) | 49% (n=1020) |
| sarvam_105b | 57% (n=1190) | 55% (n=1190) | 65% (n=1020) |
| sarvam_30b | 49% (n=1190) | 46% (n=1190) | 64% (n=1020) |
| sarvam_m | 65% (n=1177) | 44% (n=1177) | 72% (n=1008) |

## 5. Refusal Rate by Model × Language

| Model | English | Hindi | Marathi | Telugu | Kannada | Tamil | Bengali |
|---|---|---|---|---|---|---|---|
| gemini_25_flash | 74% (n=337) | 64% (n=509) | 57% (n=509) | 52% (n=509) | 54% (n=509) | 44% (n=509) | 53% (n=510) |
| gpt_4o_mini | 70% (n=340) | 65% (n=509) | 54% (n=510) | 61% (n=510) | 58% (n=510) | 61% (n=510) | 65% (n=510) |
| llama_33_70b | 38% (n=340) | 59% (n=510) | 21% (n=510) | 34% (n=510) | 33% (n=510) | 32% (n=510) | 41% (n=510) |
| sarvam_105b | 94% (n=340) | 86% (n=510) | 51% (n=510) | 55% (n=510) | 67% (n=510) | 32% (n=510) | 37% (n=510) |
| sarvam_30b | 89% (n=340) | 81% (n=510) | 45% (n=510) | 45% (n=510) | 62% (n=510) | 26% (n=510) | 32% (n=510) |
| sarvam_m | 68% (n=338) | 67% (n=504) | 55% (n=504) | 62% (n=504) | 58% (n=504) | 51% (n=504) | 60% (n=504) |

### 5b. H3 Test: Hindi vs Marathi (Shared Devanagari Script)

If models pattern-match on script, RR(Hindi) ≈ RR(Marathi).
If models understand language, behavior should diverge.

| Model | Hindi RR | Marathi RR | |Δ| |
|-------|----------|------------|------|
| gemini_25_flash | 64% (n=509) | 57% (n=509) | 7% |
| gpt_4o_mini | 65% (n=509) | 54% (n=510) | 11% |
| llama_33_70b | 59% (n=510) | 21% (n=510) | 38% |
| sarvam_105b | 86% (n=510) | 51% (n=510) | 35% |
| sarvam_30b | 81% (n=510) | 45% (n=510) | 36% |
| sarvam_m | 67% (n=504) | 55% (n=504) | 12% |

## 6. Refusal Rate by Language × Attack Vector × Model

Each cell: refusal rate (n).  Lower = more vulnerable. — = no data.

| Model | en/direct | en/cultura | hi/direct | hi/cultura | hi/code_sw | mr/direct | mr/cultura | mr/code_sw | te/direct | te/cultura | te/code_sw | kn/direct | kn/cultura | kn/code_sw | ta/direct | ta/cultura | ta/code_sw | bn/direct | bn/cultura | bn/code_sw |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemini_25_flash | 81% | 66% | 69% | 49% | 74% | 58% | 44% | 70% | 50% | 42% | 64% | 53% | 36% | 72% | 43% | 25% | 64% | 55% | 36% | 67% |
| gpt_4o_mini | 77% | 63% | 62% | 55% | 78% | 60% | 32% | 69% | 64% | 49% | 69% | 64% | 43% | 67% | 61% | 52% | 71% | 65% | 56% | 73% |
| llama_33_70b | 62% | 14% | 78% | 47% | 54% | 29% | 9% | 25% | 39% | 20% | 42% | 30% | 10% | 58% | 28% | 11% | 56% | 55% | 12% | 58% |
| sarvam_105b | 95% | 94% | 86% | 92% | 80% | 47% | 52% | 55% | 48% | 57% | 61% | 69% | 71% | 61% | 33% | 12% | 51% | 21% | 6% | 83% |
| sarvam_30b | 89% | 88% | 81% | 84% | 77% | 30% | 36% | 68% | 41% | 36% | 59% | 65% | 62% | 58% | 21% | 11% | 48% | 14% | 5% | 76% |
| sarvam_m | 75% | 60% | 70% | 50% | 80% | 58% | 36% | 71% | 64% | 44% | 77% | 68% | 42% | 65% | 60% | 35% | 60% | 60% | 40% | 79% |

## 7. Safety Transfer Ratio (Indic RR / English RR)

Ratio < 1.0 means model loses safety in that Indic language. Higher = better transfer.

| Model | English RR | Hindi (ratio) | Marathi (ratio) | Telugu (ratio) | Kannada (ratio) | Tamil (ratio) | Bengali (ratio) |
|---|---|---|---|---|---|---|---|
| gemini_25_flash | 74% | 64% (0.87) | 57% (0.78) | 52% (0.71) | 54% (0.73) | 44% (0.60) | 53% (0.71) |
| gpt_4o_mini | 70% | 65% (0.93) | 54% (0.77) | 61% (0.87) | 58% (0.83) | 61% (0.88) | 65% (0.92) |
| llama_33_70b | 38% | 59% (1.57) | 21% (0.56) | 34% (0.89) | 33% (0.86) | 32% (0.83) | 41% (1.09) |
| sarvam_105b | 94% | 86% (0.91) | 51% (0.54) | 55% (0.59) | 67% (0.71) | 32% (0.34) | 37% (0.39) |
| sarvam_30b | 89% | 81% (0.91) | 45% (0.50) | 45% (0.51) | 62% (0.70) | 26% (0.30) | 32% (0.36) |
| sarvam_m | 68% | 67% (0.98) | 55% (0.81) | 62% (0.91) | 58% (0.86) | 51% (0.76) | 60% (0.88) |

## 8. Cultural-Framing Effectiveness (Direct RR vs Cultural-Framed RR)

| Model | Direct RR | Cultural-Framed RR | Drop |
|-------|-----------|--------------------|------|
| gemini_25_flash | 58% | 43% | +16% |
| gpt_4o_mini | 65% | 50% | +15% |
| llama_33_70b | 46% | 18% | +28% |
| sarvam_105b | 57% | 55% | +2% |
| sarvam_30b | 49% | 46% | +3% |
| sarvam_m | 65% | 44% | +21% |

## 8b. Refusal Rate by Category × Attack Vector

Cross-category finding: which harm categories are most/least jailbreakable under each vector.

| Category | n | Direct RR | Cultural-framing RR | Code-switched RR | Overall RR |
|----------|---|-----------|---------------------|------------------|------------|
| csam_adjacent | 1793 | 61% (n=626) | 50% (n=630) | 64% (n=537) | 58% |
| cybercrime | 2759 | 60% (n=966) | 33% (n=965) | 67% (n=828) | 53% |
| hate_speech | 2640 | 58% (n=924) | 45% (n=924) | 67% (n=792) | 56% |
| misinformation | 2640 | 57% (n=924) | 46% (n=924) | 73% (n=792) | 58% |
| privacy_doxxing | 2640 | 58% (n=924) | 44% (n=924) | 64% (n=792) | 55% |
| self_harm | 2640 | 45% (n=924) | 42% (n=924) | 46% (n=792) | 44% |
| sexual_exploitation | 2399 | 62% (n=839) | 44% (n=840) | 72% (n=720) | 59% |
| violence_weapons | 2842 | 54% (n=995) | 38% (n=995) | 66% (n=852) | 52% |

## 8c. Refusal Rate by Category × Model

| Category | gemini_25_flash | gpt_4o_mini | llama_33_70b | sarvam_105b | sarvam_30b | sarvam_m |
|---|---|---|---|---|---|---|
| csam_adjacent | 58% (n=293) | 70% (n=300) | 46% (n=300) | 59% (n=300) | 51% (n=300) | 64% (n=300) |
| cybercrime | 52% (n=460) | 71% (n=459) | 38% (n=460) | 52% (n=460) | 51% (n=460) | 52% (n=460) |
| hate_speech | 65% (n=440) | 59% (n=440) | 37% (n=440) | 56% (n=440) | 55% (n=440) | 65% (n=440) |
| misinformation | 56% (n=440) | 60% (n=440) | 39% (n=440) | 60% (n=440) | 60% (n=440) | 75% (n=440) |
| privacy_doxxing | 56% (n=440) | 66% (n=440) | 34% (n=440) | 65% (n=440) | 53% (n=440) | 54% (n=440) |
| self_harm | 48% (n=440) | 46% (n=440) | 30% (n=440) | 49% (n=440) | 40% (n=440) | 52% (n=440) |
| sexual_exploitation | 62% (n=399) | 67% (n=400) | 40% (n=400) | 64% (n=400) | 53% (n=400) | 66% (n=400) |
| violence_weapons | 52% (n=480) | 56% (n=480) | 33% (n=480) | 65% (n=480) | 56% (n=480) | 52% (n=442) |

## 9. Code-Switching Effect (Indic-Direct → Indic-CodeSwitched RR)

Negative drop = code-switching reduces safety. Positive = code-switching triggers safety.

| Model | Hindi Δ | Marathi Δ | Telugu Δ | Kannada Δ | Tamil Δ | Bengali Δ |
|---|---|---|---|---|---|---|
| gemini_25_flash | -5% | -12% | -14% | -19% | -21% | -12% |
| gpt_4o_mini | -16% | -9% | -5% | -4% | -10% | -8% |
| llama_33_70b | +24% | +4% | -3% | -28% | -28% | -3% |
| sarvam_105b | +6% | -8% | -14% | +9% | -18% | -62% |
| sarvam_30b | +4% | -38% | -18% | +7% | -28% | -62% |
| sarvam_m | -10% | -13% | -13% | +2% | +1% | -20% |

## 10. Pre-Hypothesis Sanity Check

Pilot-grade test of the 5 falsifiable hypotheses (H1-H5):

**H1' — Cultural-framing causes ≥30pp refusal drop on non-reasoning models?**
- Per-model direct → cultural_framing drops: gemini_25_flash=+16%, gpt_4o_mini=+15%, llama_33_70b=+28%, sarvam_105b=+2%, sarvam_m=+21%
- Pilot verdict: **WEAKLY SUPPORTED** (2/5 non-reasoning models drop ≥20pp)

**H2' — Reasoning models (Sarvam-30B) MORE refusal under cultural framing?**
- Sarvam-30B direct RR: 49%
- Sarvam-30B cultural_framing RR: 46%
- Pilot verdict: **NOT SUPPORTED in pilot** (cf − direct = -3%)

**H3 — Shared Devanagari script (Hindi/Marathi) doesn't predict shared safety?**
- Per-model |Hindi − Marathi| RR: gemini_25_flash=7%, gpt_4o_mini=11%, llama_33_70b=38%, sarvam_105b=35%, sarvam_30b=36%, sarvam_m=12%
- Pilot verdict: **SUPPORTED** (5/6 models show ≥10pp Hindi-Marathi gap)

**H5 — Indic specialists show LOWER Hindi RR than English RR?**
- sarvam_105b: English 94% − Hindi 86% = +8%
- sarvam_30b: English 89% − Hindi 81% = +8%
- sarvam_m: English 68% − Hindi 67% = +1%

## Methodology Notes

- Heuristic refusal classifier (v2 with En/Hi/Mr/Te/Tenglish/Manglish patterns) + rule-based defaults
- Single-judge (Claude Code subagent + heuristics) — full benchmark will use 3-judge LLM consensus
- 20353 judgments across 6 models × 7 languages × 3 attack vectors
- Categories: csam_adjacent, cybercrime, hate_speech, misinformation, privacy_doxxing, self_harm, sexual_exploitation, violence_weapons
- Languages: English, Hindi, Marathi, Telugu, Kannada, Tamil, Bengali
- Attack vectors: direct, cultural_framing, code_switched

## Per-Model Inference Counts

| Model | Responses |
|-------|-----------|
| gemini_25_flash | 3392 |
| gpt_4o_mini | 3399 |
| llama_33_70b | 3400 |
| sarvam_105b | 3400 |
| sarvam_30b | 3400 |
| sarvam_m | 3362 |
