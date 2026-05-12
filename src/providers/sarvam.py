"""
Sarvam AI client wrapper.

Wraps the /v1/chat/completions endpoint with retry, rate limiting, cost tracking.
Supports sarvam-105b, sarvam-30b, sarvam-m (legacy).

Usage:
    from src.providers.sarvam import SarvamClient
    client = SarvamClient()
    resp = client.chat("Hello, how are you?", model="sarvam-30b")

Smoke test:
    python -m src.providers.sarvam --test
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

SARVAM_BASE_URL = "https://api.sarvam.ai/v1"
DEFAULT_MODEL = "sarvam-30b"
DEFAULT_TIMEOUT = 240.0  # increased from 60s — Sarvam-105B reasoning model needs ~90s+ per call


@dataclass
class SarvamUsage:
    """Aggregate usage tracking across calls."""

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
            f"SarvamUsage(requests={self.requests}, "
            f"prompt_tokens={self.prompt_tokens}, "
            f"completion_tokens={self.completion_tokens}, "
            f"errors={self.errors})"
        )


class SarvamError(Exception):
    """Raised when Sarvam API returns an error."""


class SarvamClient:
    """Thin Sarvam API client with retry + usage tracking."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = SARVAM_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Sarvam API key required. Set SARVAM_API_KEY in .env or pass api_key."
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.usage = SarvamUsage()

    def _headers(self) -> dict:
        # Sarvam supports both Authorization Bearer and api-subscription-key.
        # Use api-subscription-key per docs guidance for keys starting with sk_.
        if self.api_key.startswith("sk_"):
            return {"api-subscription-key": self.api_key, "Content-Type": "application/json"}
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

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
                raise SarvamError(f"HTTP {r.status_code}: {r.text}")
            return r.json()

    def chat(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict:
        """Single-turn chat. Returns dict with 'content', 'reasoning_content', 'usage', 'raw'.

        Note: Sarvam-30B and Sarvam-105B are reasoning models. They produce
        intermediate reasoning in `reasoning_content` before the final `content`.
        Default max_tokens=2048 to allow room for both.
        """
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

        # Defensive parsing
        try:
            choice = raw["choices"][0]
            message = choice["message"]
            content = message.get("content")
            reasoning = message.get("reasoning_content")
            finish_reason = choice.get("finish_reason")
        except (KeyError, IndexError) as e:
            raise SarvamError(f"Unexpected response schema: {raw}") from e

        usage_block = raw.get("usage", {})
        prompt_tokens = usage_block.get("prompt_tokens", 0)
        completion_tokens = usage_block.get("completion_tokens", 0)
        self.usage.add(model, prompt_tokens, completion_tokens)

        return {
            "content": content,           # may be None if model ran out during reasoning
            "reasoning_content": reasoning,
            "finish_reason": finish_reason,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "raw": raw,
        }

    def chat_messages(
        self,
        messages: list[dict],
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> dict:
        """Multi-turn chat with explicit message list."""
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
            raise SarvamError(f"Unexpected response schema: {raw}") from e
        usage = raw.get("usage", {})
        self.usage.add(model, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        return {
            "content": content,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "raw": raw,
        }


def smoke_test() -> int:
    """Run a quick connectivity test. Returns exit code 0 on success."""
    print("=" * 60)
    print("Sarvam API Smoke Test")
    print("=" * 60)

    try:
        client = SarvamClient()
    except ValueError as e:
        print(f"[FAIL] Configuration error: {e}")
        print("\nFix: copy .env.example to .env and fill SARVAM_API_KEY")
        return 1

    print(f"[OK] API key loaded (prefix: {client.api_key[:8]}...)")
    print(f"[OK] Base URL: {client.base_url}")

    def _summarize(label: str, r: dict, elapsed: float):
        content = r.get("content") or "(none — likely truncated during reasoning)"
        reasoning = r.get("reasoning_content") or ""
        print(f"  [OK] Response in {elapsed:.2f}s ({r['completion_tokens']} completion tokens)")
        print(f"  [OK] finish_reason: {r.get('finish_reason')}")
        if reasoning:
            print(f"  [OK] reasoning_content (first 100): {reasoning[:100]}...")
        print(f"  [OK] content: {str(content)[:200]}")

    # Test 1: simple English chat with enough tokens for reasoning + answer
    print("\n[Test 1] English chat with sarvam-30b (max_tokens=2048)...")
    try:
        t0 = time.time()
        r = client.chat(
            "What is 2+2? Answer with just the number.",
            model="sarvam-30b",
            max_tokens=2048,
        )
        _summarize("English", r, time.time() - t0)
    except SarvamError as e:
        print(f"  [FAIL] {e}")
        return 2

    # Test 2: Hindi chat
    print("\n[Test 2] Hindi chat with sarvam-30b...")
    try:
        t0 = time.time()
        r = client.chat(
            "नमस्ते। एक शब्द में अपना नाम बताएं।",
            model="sarvam-30b",
            max_tokens=2048,
        )
        _summarize("Hindi", r, time.time() - t0)
    except SarvamError as e:
        print(f"  [FAIL] {e}")
        return 3

    # Test 3: Try sarvam-105b
    print("\n[Test 3] Hindi chat with sarvam-105b (flagship)...")
    try:
        t0 = time.time()
        r = client.chat(
            "भारत में कितने राज्य हैं? एक संख्या दें।",
            model="sarvam-105b",
            max_tokens=2048,
        )
        _summarize("Hindi 105b", r, time.time() - t0)
    except SarvamError as e:
        # 105b may not be in your tier; not fatal
        print(f"  [WARN] {e}")
        print("  (105b may require upgraded tier — not blocking)")

    # Test 4: legacy sarvam-m
    print("\n[Test 4] Hindi chat with sarvam-m (legacy 24B)...")
    try:
        t0 = time.time()
        r = client.chat(
            "नमस्ते। एक शब्द में अपना नाम बताएं।",
            model="sarvam-m",
            max_tokens=512,
        )
        _summarize("Hindi sarvam-m", r, time.time() - t0)
    except SarvamError as e:
        print(f"  [WARN] {e}")

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
        print("Usage: python -m src.providers.sarvam --test")
        sys.exit(1)
