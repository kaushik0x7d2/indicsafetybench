"""
Moonshot AI (Kimi) client wrapper.

Used for cost-efficient seed generation, rewrites, and bulk transformation tasks.
Kimi K2 is OpenAI-compatible at ~$0.50-1.00/M tokens — order-of-magnitude cheaper
than Claude/GPT-4 for synthesis tasks where we don't need frontier reasoning.

Endpoint: https://api.moonshot.ai/v1/chat/completions  (OpenAI-compatible)

Models (as of 2026):
  - kimi-k2-0905-preview     — most capable, ~$1/M
  - kimi-k2-turbo-preview    — fast variant
  - moonshot-v1-128k         — long-context

Smoke test:
    python -m src.providers.moonshot --test
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

load_dotenv()

MOONSHOT_BASE_URL = "https://api.moonshot.ai/v1"
DEFAULT_MODEL = "kimi-k2-0905-preview"
DEFAULT_TIMEOUT = 120.0


@dataclass
class MoonshotUsage:
    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    errors: int = 0
    by_model: dict = field(default_factory=dict)

    def add(self, model: str, prompt_tokens: int, completion_tokens: int):
        self.requests += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        m = self.by_model.setdefault(model, {"requests": 0, "prompt": 0, "completion": 0})
        m["requests"] += 1
        m["prompt"] += prompt_tokens
        m["completion"] += completion_tokens

    def __repr__(self):
        return (
            f"MoonshotUsage(requests={self.requests}, "
            f"prompt_tokens={self.prompt_tokens}, "
            f"completion_tokens={self.completion_tokens}, "
            f"errors={self.errors})"
        )


class MoonshotError(Exception):
    pass


class MoonshotClient:
    """Thin Moonshot API client (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = MOONSHOT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or os.getenv("MOONSHOT_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Moonshot API key required. Set MOONSHOT_API_KEY in .env or pass api_key."
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.usage = MoonshotUsage()

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
                raise MoonshotError(f"HTTP {r.status_code}: {r.text}")
            return r.json()

    def chat(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict:
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

        raw = self._post("/chat/completions", payload)
        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise MoonshotError(f"Unexpected response schema: {raw}") from e

        usage_block = raw.get("usage", {})
        prompt_tokens = usage_block.get("prompt_tokens", 0)
        completion_tokens = usage_block.get("completion_tokens", 0)
        self.usage.add(model, prompt_tokens, completion_tokens)

        return {
            "content": content,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "raw": raw,
        }


def smoke_test() -> int:
    print("=" * 60)
    print("Moonshot (Kimi) API Smoke Test")
    print("=" * 60)

    try:
        client = MoonshotClient()
    except ValueError as e:
        print(f"[FAIL] {e}")
        return 1

    print(f"[OK] API key loaded (prefix: {client.api_key[:8]}...)")

    print("\n[Test 1] English chat with kimi-k2-0905-preview...")
    try:
        t0 = time.time()
        r = client.chat("What is 2+2? Answer with just the number.", max_tokens=50)
        elapsed = time.time() - t0
        print(f"  [OK] Response in {elapsed:.2f}s")
        print(f"  [OK] Content: {r['content'][:120]}")
        print(f"  [OK] Tokens: prompt={r['prompt_tokens']}, completion={r['completion_tokens']}")
    except MoonshotError as e:
        print(f"  [FAIL] {e}")
        return 2

    print("\n" + "=" * 60)
    print(f"Total usage: {client.usage}")
    print("=" * 60)
    print("[OK] Smoke test PASSED")
    return 0


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        sys.exit(smoke_test())
    else:
        print("Usage: python -m src.providers.moonshot --test")
        sys.exit(1)
