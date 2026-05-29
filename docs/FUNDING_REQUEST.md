# IndicSafetyBench v3 — Compute Budget

Prices verified 2026-05-19. Token counts empirical from v1 corpus (target
calls ~86 in / 374 out; judge calls ~1,250 in / 50 out).

Scope: compute only. No human-validator compensation.

## Vendor architecture

PI access is **scoped to BharatGen Param2 self-hosting only**. Other v3 models route through their existing providers (OpenRouter, Anthropic console, OpenAI direct, Sarvam direct).

| Vendor | What it serves in v3 | Status |
|---|---|---|
| **Prime Intellect** (GPU rental, single H100/H200 + vLLM) | Param2-17B-A2.4B-Thinking only | Have access; limited credits |
| OpenRouter | Gemini-3.1-Pro, DeepSeek-R1, Llama-4 (targets + judge) | Have key; needs top-up |
| Anthropic console | Claude Opus 4.7 (target + judge) | Need signup |
| OpenAI direct | GPT-5.x (target + judge) | Need signup |
| Krutrim direct | gpt-oss-120b (200 done; finish 3,140 more) | Have key; ₹121 remaining of ₹300 |
| Sarvam direct | Sarvam-105B/30B/m | Free, already used |

PI's serverless inference catalogue (`api.pinference.ai/api/v1`) does include
Claude/GPT/Gemini/DeepSeek/Llama-4 as confirmed by smoke test 2026-05-19, but
the user's PI credit balance is reserved for Param2. PI is NOT used as a
multi-vendor consolidator in this budget.

## Target-model runs (3,340 prompts each)

| Model | Route | Cost |
|---|---|---:|
| Claude Opus 4.7 (+35% tokenizer) | Anthropic console (or OR) | $44 |
| GPT-5.5 | OpenAI direct (or OR) | $39 |
| Gemini 3.1 Pro | OpenRouter | $16 |
| DeepSeek R1-0528 | OpenRouter | $3 |
| Llama-4 Maverick | OpenRouter | $1 |
| gpt-oss-120b (finish 3,140 remaining) | Krutrim direct API | ~$30 (₹2,490) |
| **Param2-17B-Thinking** | **Prime Intellect H100/H200 spot + vLLM** | **~$0.40 partial pilot / $5–9 full coverage; absorbed by PI credits** |
| **Target subtotal** | | **~$133** |

## LLM judge ensemble (19,423 paired labels each)

| Judge | Route | Standard | Batch API |
|---|---|---:|---:|
| Claude Opus 4.7 | Anthropic console | $197 | $99 |
| GPT-5.5 | OpenAI direct | $151 | $76 |
| Gemini 3.1 Pro | OpenRouter | $60 | n/a |
| **Judge subtotal** | | **$408** | **$235** |

## Totals

| Scenario | Targets | Judges | Margin (15%) | Total |
|---|---:|---:|---:|---:|
| Standard API throughout | $133 | $408 | $81 | **$622** |
| Batch API for Anthropic + OpenAI judges | $133 | $235 | $55 | **$423** |

**Commit budget: $533** (standard for targets + batch for judges + safety margin).
Param2 cost is absorbed by existing PI credits.

## Where the money goes (per vendor)

| Vendor | Anticipated spend | Setup |
|---|---:|---|
| Anthropic console (Opus target + judge) | $143–$241 | Credit card; $5 starter credit |
| OpenAI direct (GPT-5.5 target + judge) | $115–$190 | Credit card |
| OpenRouter top-up | $80 | Already signed up |
| Krutrim wallet | already spent ₹179; need ~₹2,490 more for finish | Already signed up |
| Prime Intellect (Param2 GPU rental) | absorbed by existing credits | Already signed up |
| Sarvam direct | $0 | Already have key |

## Out of scope

- Krutrim-2 — not currently on Krutrim or PI inference APIs
- Nanda — institutional access only
- 10× corpus scaling — would push budget to ~$4,200
- Routing non-Param2 models through PI — user's PI credits reserved for Param2

## Param2 deployment plan

1. PI dashboard → **Compute → On-Demand GPUs** → deploy single H100 spot ($0.94/hr) or H200 low-tier ($0.47/hr)
2. SSH into the pod, run vLLM serving `bharatgenai/Param2-17B-A2.4B-Thinking` on port 8000
3. Set `PI_ENDPOINT_URL=http://<pod-ip>:8000/v1` in `.env` (no API key needed for self-hosted vLLM)
4. `python -m src.pilot.run_pi_partial --n 200` → ~25 min, ~$0.40 of credits
5. Heuristic + LLM-judge the 200 responses
6. Param2 row added to paper §4.1; §4.3 extended if measurement-crisis pattern holds
