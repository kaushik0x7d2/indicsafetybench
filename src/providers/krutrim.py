"""
Ola Krutrim Cloud API client.

OpenAI-compatible inference for models hosted on Krutrim AI Studio. As of
May 2026, the catalogue includes Krutrim-2 (Indic sovereign), Krutrim-1,
DeepSeek-R1 + distills, Llama-4-Maverick-17B-128E-Instruct, Llama-3.3-70B,
Phi-4-reasoning-plus, Qwen3-32B/30B-A3B, Mistral-7B-v0.2.

API:
  base_url = https://cloud.olakrutrim.com/v1
  auth     = Authorization: Bearer <KRUTRIM_API_KEY>
  format   = OpenAI chat-completions compatible

Budget tracking is in INR (the wallet currency in the Krutrim console).
Public docs do NOT expose per-model token pricing — actual cost per call is
visible only in the console after the call lands. This client therefore
tracks tokens accurately but treats cost as opportunistic: each call's
estimated INR cost defaults to 0 until KRUTRIM_PRICING is populated.

Smoke test:
    python -m src.providers.krutrim --test
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv()

KRUTRIM_BASE_URL = "https://cloud.olakrutrim.com/v1"
DEFAULT_TIMEOUT = 120.0
USAGE_LOG_PATH = Path("data/krutrim_usage.jsonl")

# Per-million-token pricing (INR). Derived from /v1/models response, which
# returns pricing as decimals-per-token (matching the OpenRouter convention).
# Conversion: USD-per-token × 1M × 83 (USD->INR) = INR per million tokens.
# Values below are derived from the catalogue as of 2026-05-18. Verify against
# the Krutrim console wallet after each run; update here if drifted.
USD_TO_INR = 83.0
KRUTRIM_PRICING: dict[str, tuple[float, float]] = {
    # model_id: (INR per million input tokens, INR per million output tokens)
    "gpt-oss-120b":      (13.0 * USD_TO_INR, 65.0 * USD_TO_INR),  # USD 13/M in, 65/M out
    "gpt-oss-20b":       ( 8.0 * USD_TO_INR, 32.0 * USD_TO_INR),
    "gemma-4-E4B-it":    ( 3.0 * USD_TO_INR,  8.0 * USD_TO_INR),
    "gemma-4-31b-it":    ( 9.0 * USD_TO_INR, 33.0 * USD_TO_INR),
    "gemma-4-26B-A4B-it":( 7.0 * USD_TO_INR, 28.0 * USD_TO_INR),
    "Qwen3.5-9B":        ( 3.0 * USD_TO_INR,  8.0 * USD_TO_INR),
    "Qwen3.5-27B":       (23.0 * USD_TO_INR,188.0 * USD_TO_INR),
    "Qwen3.6-27B":       (23.0 * USD_TO_INR,188.0 * USD_TO_INR),
    "Qwen3.6-35B-A3B":   ( 7.0 * USD_TO_INR, 28.0 * USD_TO_INR),
    "tokenizer":         (0.0, 0.0),
}


@dataclass
class KrutrimUsage:
    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_inr: float = 0.0
    errors: int = 0
    by_model: dict = field(default_factory=dict)

    def add(self, model: str, prompt_tokens: int, completion_tokens: int, cost: float):
        self.requests += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.estimated_cost_inr += cost
        m = self.by_model.setdefault(model, {
            "requests": 0, "prompt": 0, "completion": 0, "cost": 0.0,
        })
        m["requests"] += 1
        m["prompt"] += prompt_tokens
        m["completion"] += completion_tokens
        m["cost"] += cost

    def __repr__(self):
        return (
            f"KrutrimUsage(req={self.requests}, "
            f"prompt={self.prompt_tokens}, comp={self.completion_tokens}, "
            f"cost~INR{self.estimated_cost_inr:.4f})"
        )


class KrutrimError(Exception):
    pass


class KrutrimBudgetExceeded(KrutrimError):
    pass


class KrutrimClient:
    """OpenAI-compatible client for Krutrim AI Studio."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = KRUTRIM_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        budget_inr: Optional[float] = None,
    ):
        self.api_key = api_key or os.getenv("KRUTRIM_API_KEY")
        if not self.api_key:
            raise ValueError("Set KRUTRIM_API_KEY in .env (https://cloud.olakrutrim.com)")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.budget_inr = budget_inr if budget_inr is not None else float(
            os.getenv("KRUTRIM_BUDGET_INR", "300.0")
        )
        self.usage = KrutrimUsage()
        self._load_existing_usage()

    def _load_existing_usage(self):
        if USAGE_LOG_PATH.exists():
            with open(USAGE_LOG_PATH, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                        self.usage.estimated_cost_inr += rec.get("cost_inr", 0.0)
                    except json.JSONDecodeError:
                        continue

    def _log_call(self, record: dict):
        USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USAGE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _check_budget(self):
        if self.usage.estimated_cost_inr >= self.budget_inr:
            raise KrutrimBudgetExceeded(
                f"Budget exhausted: ~INR{self.usage.estimated_cost_inr:.4f} >= INR{self.budget_inr:.2f}. "
                f"Adjust KRUTRIM_BUDGET_INR in .env if intentional. "
                f"Note: estimates rely on KRUTRIM_PRICING; verify against console wallet activity."
            )

    def _estimate_cost_inr(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = KRUTRIM_PRICING.get(model)
        if rates is None:
            return 0.0  # unknown — track tokens, defer cost to console audit
        return (prompt_tokens * rates[0] + completion_tokens * rates[1]) / 1_000_000

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(url, json=payload, headers=self._headers())
            if r.status_code >= 400:
                self.usage.errors += 1
                raise KrutrimError(f"HTTP {r.status_code}: {r.text[:500]}")
            return r.json()

    def chat(
        self,
        prompt: str,
        model: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict:
        self._check_budget()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        t0 = time.time()
        raw = self._post("/chat/completions", payload)
        latency_ms = (time.time() - t0) * 1000

        choices = raw.get("choices", [])
        content = ""
        finish = None
        if choices:
            ch0 = choices[0]
            content = ch0.get("message", {}).get("content", "") or ""
            finish = ch0.get("finish_reason")

        usage = raw.get("usage", {}) or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        cost = self._estimate_cost_inr(model, prompt_tokens, completion_tokens)
        self.usage.add(model, prompt_tokens, completion_tokens, cost)

        self._log_call({
            "ts": time.time(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_inr": cost,
            "latency_ms": latency_ms,
            "finish_reason": finish,
            "preview": content[:200],
        })

        return {
            "content": content,
            "model": model,
            "finish_reason": finish,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_inr": cost,
            "latency_ms": latency_ms,
            "raw": raw,
        }


def smoke_test():
    print("Krutrim AI Studio smoke test")
    client = KrutrimClient()
    print(f"Base URL: {client.base_url}")
    print(f"Budget: INR{client.budget_inr}")
    print()

    candidates = ["Krutrim-2", "DeepSeek-R1", "Phi-4-reasoning-plus"]
    prompt = "Reply with exactly the word: pong"

    for model in candidates:
        print(f"--- {model} ---")
        try:
            r = client.chat(prompt=prompt, model=model, temperature=0.0, max_tokens=20)
            print(f"  status: OK ({r['latency_ms']:.0f} ms)")
            print(f"  tokens: in={r['prompt_tokens']} out={r['completion_tokens']}")
            print(f"  reply:  {r['content']!r}")
            print(f"  cost est (INR, will be 0 until KRUTRIM_PRICING is set): {r['cost_inr']:.4f}")
        except Exception as e:
            print(f"  FAIL: {e}")
        print()
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="Run smoke test against Krutrim-2 + DeepSeek-R1 + Phi-4")
    args = p.parse_args()
    if args.test:
        raise SystemExit(smoke_test())
    else:
        print("Usage: python -m src.providers.krutrim --test")
