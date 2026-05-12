"""
OpenRouter unified API client.

OpenRouter routes to many providers (Anthropic, OpenAI, Google, Meta, Mistral)
through a single OpenAI-compatible API. Useful for accessing GPT-4o, Gemini,
Llama, Mistral without managing N separate accounts.

Per project policy: we DO NOT route Anthropic models through OpenRouter
(Claude is accessed via Claude Code subagents instead). This client refuses
to call any model whose name contains "anthropic" or "claude".

Budget guardrail: tracks cumulative cost against OPENROUTER_BUDGET_USD;
refuses to make calls once budget exhausted.

Pricing (approximate, 2026):
  - openai/gpt-4o:                $2.50/M input, $10.00/M output
  - openai/gpt-4o-mini:           $0.15/M input, $0.60/M output
  - google/gemini-2.5-flash:      $0.075/M input, $0.30/M output  (cheap!)
  - google/gemini-2.5-pro:        $1.25/M input, $5.00/M output
  - meta-llama/llama-3.3-70b:     $0.59/M (combined)
  - mistralai/mistral-small-3:    $0.20/M input, $0.60/M output

Smoke test:
    python -m src.providers.openrouter --test
"""

from __future__ import annotations

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

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT = 120.0
USAGE_LOG_PATH = Path("data/openrouter_usage.jsonl")

# Per-million-token pricing (USD). Approximate; OpenRouter publishes exact rates.
# Used for budget tracking. Update if pricing changes.
PRICING = {
    "openai/gpt-4o": (2.50, 10.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4-turbo": (10.00, 30.00),
    "google/gemini-2.5-flash": (0.075, 0.30),
    "google/gemini-2.5-pro": (1.25, 5.00),
    "google/gemini-2.0-flash-exp:free": (0.0, 0.0),
    "meta-llama/llama-3.3-70b-instruct": (0.59, 0.59),
    "meta-llama/llama-3-70b-instruct": (0.59, 0.59),
    "mistralai/mistral-small-3": (0.20, 0.60),
    "mistralai/mistral-large": (2.00, 6.00),
    "qwen/qwen-2.5-72b-instruct": (0.40, 0.40),
}

# Block list — do NOT route these through OpenRouter per project policy
BLOCKED_PATTERNS = ["anthropic/", "claude-"]


@dataclass
class OpenRouterUsage:
    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    errors: int = 0
    by_model: dict = field(default_factory=dict)

    def add(self, model: str, prompt_tokens: int, completion_tokens: int, cost: float):
        self.requests += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.estimated_cost_usd += cost
        m = self.by_model.setdefault(model, {
            "requests": 0, "prompt": 0, "completion": 0, "cost": 0.0,
        })
        m["requests"] += 1
        m["prompt"] += prompt_tokens
        m["completion"] += completion_tokens
        m["cost"] += cost

    def __repr__(self):
        return (
            f"OpenRouterUsage(req={self.requests}, "
            f"prompt={self.prompt_tokens}, comp={self.completion_tokens}, "
            f"cost=${self.estimated_cost_usd:.4f})"
        )


class OpenRouterError(Exception):
    pass


class OpenRouterBudgetExceeded(OpenRouterError):
    pass


class OpenRouterClient:
    """OpenAI-compatible client routed through OpenRouter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = OPENROUTER_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        budget_usd: Optional[float] = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("Set OPENROUTER_API_KEY in .env")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.budget_usd = budget_usd if budget_usd is not None else float(
            os.getenv("OPENROUTER_BUDGET_USD", "25.0")
        )
        self.usage = OpenRouterUsage()
        # Resume cost tracking from log
        self._load_existing_usage()

    def _load_existing_usage(self):
        """Resume cumulative cost tracking from disk to enforce hard budget."""
        if USAGE_LOG_PATH.exists():
            with open(USAGE_LOG_PATH, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    self.usage.estimated_cost_usd += rec.get("cost", 0.0)

    def _log_call(self, record: dict):
        USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USAGE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _check_blocked(self, model: str):
        for pattern in BLOCKED_PATTERNS:
            if pattern in model.lower():
                raise OpenRouterError(
                    f"Model '{model}' is blocked by project policy "
                    f"(Anthropic models routed via Claude Code subagents instead)."
                )

    def _check_budget(self):
        if self.usage.estimated_cost_usd >= self.budget_usd:
            raise OpenRouterBudgetExceeded(
                f"Budget exhausted: ${self.usage.estimated_cost_usd:.4f} >= ${self.budget_usd:.2f}. "
                f"Refuse to make further calls. Adjust OPENROUTER_BUDGET_USD if intentional."
            )

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = PRICING.get(model, (1.0, 3.0))  # conservative default
        return (prompt_tokens * rates[0] + completion_tokens * rates[1]) / 1_000_000

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/kaushik/indicsafetybench",
            "X-Title": "IndicSafetyBench",
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
                raise OpenRouterError(f"HTTP {r.status_code}: {r.text}")
            return r.json()

    def chat(
        self,
        prompt: str,
        model: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        provider_order: Optional[list[str]] = None,
    ) -> dict:
        self._check_blocked(model)
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
        if provider_order:
            payload["provider"] = {"order": provider_order, "allow_fallbacks": True}

        raw = self._post("/chat/completions", payload)

        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise OpenRouterError(f"Unexpected response: {raw}") from e

        usage_block = raw.get("usage", {})
        prompt_tokens = usage_block.get("prompt_tokens", 0)
        completion_tokens = usage_block.get("completion_tokens", 0)
        cost = self._estimate_cost(model, prompt_tokens, completion_tokens)
        self.usage.add(model, prompt_tokens, completion_tokens, cost)

        # Persist to disk for cumulative budget tracking
        self._log_call({
            "ts": time.time(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost,
            "cumulative_cost": self.usage.estimated_cost_usd,
        })

        return {
            "content": content,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost_usd": cost,
            "raw": raw,
        }


def smoke_test() -> int:
    print("=" * 60)
    print("OpenRouter API Smoke Test")
    print("=" * 60)

    try:
        client = OpenRouterClient()
    except ValueError as e:
        print(f"[FAIL] {e}")
        return 1

    print(f"[OK] API key loaded (prefix: {client.api_key[:14]}...)")
    print(f"[OK] Budget: ${client.budget_usd:.2f}")
    print(f"[OK] Spent so far (from log): ${client.usage.estimated_cost_usd:.4f}")

    # Test 1: Gemini Flash (cheapest)
    print("\n[Test 1] google/gemini-2.5-flash (cheapest)...")
    try:
        t0 = time.time()
        r = client.chat("What is 2+2? One number only.",
                        model="google/gemini-2.5-flash",
                        max_tokens=20)
        elapsed = time.time() - t0
        print(f"  [OK] {elapsed:.2f}s | content: {r['content'][:80]}")
        print(f"  [OK] tokens: p={r['prompt_tokens']} c={r['completion_tokens']} cost=${r['estimated_cost_usd']:.6f}")
    except OpenRouterError as e:
        print(f"  [FAIL] {e}")
        return 2

    # Test 2: Block check
    print("\n[Test 2] Anthropic block check (should refuse)...")
    try:
        r = client.chat("test", model="anthropic/claude-3.5-sonnet")
        print(f"  [FAIL] Should have refused but didn't")
        return 3
    except OpenRouterError as e:
        if "blocked" in str(e).lower():
            print(f"  [OK] Refused as expected: {e}")
        else:
            print(f"  [FAIL] Unexpected error: {e}")
            return 4

    print("\n" + "=" * 60)
    print(f"Total: {client.usage}")
    print("=" * 60)
    print("[OK] Smoke test PASSED")
    return 0


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        sys.exit(smoke_test())
    else:
        print("Usage: python -m src.providers.openrouter --test")
        sys.exit(1)
