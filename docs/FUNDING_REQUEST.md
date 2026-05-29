# IndicSafetyBench v3 — Compute Budget

Prices verified 2026-05-19 against Anthropic / OpenAI / DeepSeek / OpenRouter
public catalogs. Token counts are empirical from the v1 corpus (target calls
~86 in / 374 out; judge calls ~1,250 in / 50 out).

Scope: compute only. No human-validator compensation.

## Target-model runs (3,340 prompts each)

| Model | Route | $/M in | $/M out | Cost |
|---|---|---:|---:|---:|
| Claude Opus 4.7 (+35% tokenizer overhead) | `anthropic/claude-opus-4.7` | 5.00 | 25.00 | $44 |
| GPT-5.5 | `openai/gpt-5.5` | 5.00 | 30.00 | $39 |
| Gemini 3.1 Pro | `google/gemini-3.1-pro-preview` | 2.00 | 12.00 | $16 |
| DeepSeek R1 (0528) | `deepseek/deepseek-r1-0528` | 0.50 | 2.15 | $3 |
| Llama-4 Maverick | `meta-llama/llama-4-maverick` | 0.15 | 0.60 | $1 |
| gpt-oss-120b (finish 3,140 remaining) | Krutrim direct API | empirical ₹0.89/prompt | — | $34 |
| Param2-17B-Thinking | HF Inference Endpoint A10G | $1.10/hr × ~9 hrs | — | $10 |
| **Target subtotal** | | | | **$147** |

## LLM judge ensemble (19,423 paired labels each)

| Judge | Route | Cost (standard) | Cost (50% batch API) |
|---|---|---:|---:|
| Claude Opus 4.7 | `anthropic/claude-opus-4.7` | $197 | $99 |
| GPT-5.5 | `openai/gpt-5.5` | $151 | $76 |
| Gemini 3.1 Pro | `google/gemini-3.1-pro-preview` | $60 | $60 (no batch yet) |
| **Judge subtotal** | | **$408** | **$235** |

## Totals

| Scenario | Targets | Judges | Margin (15%) | Total |
|---|---:|---:|---:|---:|
| Standard API throughout | $147 | $408 | $83 | **$638** |
| Batch API for judging ⭐ | $147 | $235 | $58 | **$440** |

**Commit budget: $533** (sits between, with safety headroom on batch turnaround).

## Where the money goes (per vendor)

| Vendor | Anticipated spend | Setup |
|---|---:|---|
| Anthropic console (Opus 4.7 target + judge) | $143–$241 (batch dependent) | Credit card; $5 starter credit |
| OpenAI (GPT-5.5 target + judge) | $115–$190 (batch dependent) | Credit card |
| OpenRouter top-up (Gemini-3.1-Pro target + judge, DeepSeek, Llama-4) | $80 | Already signed up |
| Hugging Face Inference Endpoints (Param2-17B) | $10 | Credit card |
| Krutrim wallet top-up (gpt-oss-120b finish) | ~$35 (~₹2,900) | Already signed up |
| **Sum** | **$383–$556** | |

## Out of scope

- Krutrim-2 — not currently on Krutrim inference API
- Nanda — institutional access only, pending request
- 10× corpus scaling (3,340 → 33,400) — would push budget to ~$4,200
- Human-validator compensation — separate track via institutional collaboration
