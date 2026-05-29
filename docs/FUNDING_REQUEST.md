# IndicSafetyBench v3 — Compute Budget

Prices verified 2026-05-19. Token counts empirical from v1 corpus (target
calls ~86 in / 374 out; judge calls ~1,250 in / 50 out).

Scope: compute only. No human-validator compensation.

## Vendor architecture

**Primary: Prime Intellect** (`api.pinference.ai/api/v1`). Single account
serves 123 models including Claude Opus 4.7, Sonnet 4.6, GPT-5.x, Gemini
3.1 Pro, DeepSeek R1/V4, Llama-4 Maverick, gpt-oss-120b. User has working
access verified 2026-05-19 (6/7 candidate models passed smoke test).

**Secondary:**
- OpenRouter — fallback if a PI model returns 4xx (e.g. DeepSeek thinking-param issue)
- HuggingFace or PI GPU rental — for Param2-17B (not on PI serverless)
- Sarvam direct API — free, already used in v1
- Krutrim direct API — partial gpt-oss-120b run (200 of 3,340 already done; finish via PI instead)

Three vendor accounts eliminated vs prior plan: Anthropic console, OpenAI
direct, Google AI Studio. All three routed through PI instead.

## Target-model runs (3,340 prompts each)

| Model | PI route | Cost (PI passthrough est.) |
|---|---|---:|
| Claude Opus 4.7 (+35% tokenizer) | `anthropic/claude-opus-4.7` | $44 |
| GPT-5.4 (Responses API, max_completion_tokens) | `openai/gpt-5.4` | $21 |
| Gemini 3.1 Pro | `google/gemini-3.1-pro-preview` | $16 |
| DeepSeek R1-0528 | `deepseek/deepseek-r1-0528` | $3 |
| Llama-4 Maverick | `meta-llama/llama-4-maverick` | $1 |
| gpt-oss-120b (finish 3,140 remaining) | `openai/gpt-oss-120b` | $34 |
| Param2-17B-Thinking | **NOT on PI serverless** — HF Endpoint or PI GPU rental | ~$8 |
| **Target subtotal** | | **$127** |

## LLM judge ensemble (19,423 paired labels each)

All judges via PI serverless, single API key.

| Judge | PI route | Standard | Batch-API path |
|---|---|---:|---:|
| Claude Opus 4.7 | `anthropic/claude-opus-4.7` | $197 | unclear if PI exposes batch |
| GPT-5.4 (Responses API) | `openai/gpt-5.4` | $75 | unclear |
| Gemini 3.1 Pro | `google/gemini-3.1-pro-preview` | $60 | unclear |
| **Judge subtotal** | | **$332** | TBD |

## Totals

| Scenario | Targets | Judges | Margin (15%) | Total |
|---|---:|---:|---:|---:|
| Standard PI passthrough | $127 | $332 | $69 | **$528** |
| If user's existing PI credits absorb part | $127 | $332 | $69 | **$0–$528** |

**Commit budget: $533** (rounded). If existing PI credits cover any portion,
out-of-pocket drops proportionally.

## Where the money goes (per vendor, consolidated)

| Vendor | Spend | Setup |
|---|---:|---|
| **Prime Intellect** (Opus + Sonnet + GPT-5 + Gemini + gpt-oss + DeepSeek + Llama-4 target + judge) | $450 | Already have access |
| HuggingFace Inference Endpoint OR PI GPU rental (Param2) | ~$8 | If HF: card. If PI GPU: same PI account. |
| Krutrim wallet (already topped up) | ₹179 spent of ₹300 | Already done |
| OpenRouter (fallback / safety margin) | $0–$70 | Already have key |
| Sarvam direct | $0 | Already have key |

## Out of scope

- Krutrim-2 — not currently on Krutrim or PI inference APIs
- Nanda — institutional access only
- 10× corpus scaling (3,340 → 33,400) — would push budget to ~$4,200
- Human-validator compensation — separate track via institutional collaboration

## Status

- Verified working on PI 2026-05-19: Opus 4.7, Sonnet 4.6, GPT-5.4,
  gpt-oss-120b, Gemini 3.1 Pro, Llama-4 Maverick
- Needs tweaking: DeepSeek-R1 (400 error; param adjustment required)
- Self-host needed: Param2-17B-Thinking (HF or PI GPU rental)
