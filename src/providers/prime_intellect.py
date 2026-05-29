"""
Prime Intellect inference client.

Prime Intellect (https://app.primeintellect.ai) offers OpenAI-compatible
inference endpoints for models you deploy via their dashboard, plus raw GPU
rental for self-hosted vLLM servers. Either path produces a base URL we can
hit OpenAI-style; this client is agnostic to which.

Two configuration paths:

  1. Managed deployment (dashboard 1-click):
     Set PI_ENDPOINT_URL to the deployment URL (e.g.
     https://your-deployment-id.primeintellect.ai/v1) and PI_API_KEY to your
     deployment's bearer token from the dashboard.

  2. Self-hosted vLLM on a rented GPU pod:
     SSH into the pod, run `vllm serve bharatgenai/Param2-17B-A2.4B-Thinking
     --quantization bitsandbytes --load-format bitsandbytes` (or similar),
     expose port 8000, and set PI_ENDPOINT_URL to http://<pod-ip>:8000/v1.
     No PI_API_KEY needed if the vLLM server is auth-less.

Spend is tracked in tokens (no per-token billing on PI — billing is per
GPU-hour at the dashboard level). The cost field here is best-effort and
defaults to 0; the authoritative spend number is your PI wallet activity.

Smoke test:
    python -m src.providers.prime_intellect --test
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

DEFAULT_TIMEOUT = 240.0  # generous: 17B MoE first-token latency can be ~30s
USAGE_LOG_PATH = Path("data/prime_intellect_usage.jsonl")


@dataclass
class PrimeIntellectUsage:
    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    gpu_seconds_est: float = 0.0
    errors: int = 0
    by_model: dict = field(default_factory=dict)

    def add(self, model: str, prompt_tokens: int, completion_tokens: int, latency_ms: float):
        self.requests += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.gpu_seconds_est += latency_ms / 1000.0
        m = self.by_model.setdefault(model, {"requests": 0, "prompt": 0, "completion": 0, "gpu_s": 0.0})
        m["requests"] += 1
        m["prompt"] += prompt_tokens
        m["completion"] += completion_tokens
        m["gpu_s"] += latency_ms / 1000.0

    def __repr__(self):
        return (
            f"PrimeIntellectUsage(req={self.requests}, "
            f"prompt={self.prompt_tokens}, comp={self.completion_tokens}, "
            f"gpu_s~{self.gpu_seconds_est:.0f})"
        )


class PrimeIntellectError(Exception):
    pass


class PrimeIntellectClient:
    """OpenAI-compatible client for Prime Intellect deployments / self-hosted vLLM pods."""

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.endpoint_url = (endpoint_url or os.getenv("PI_ENDPOINT_URL", "")).rstrip("/")
        if not self.endpoint_url:
            raise ValueError(
                "Set PI_ENDPOINT_URL in .env. "
                "Format: https://<deployment-id>.primeintellect.ai/v1 "
                "or http://<pod-ip>:8000/v1 for self-hosted vLLM."
            )
        self.api_key = api_key or os.getenv("PI_API_KEY")  # optional for self-hosted
        self.timeout = timeout
        self.usage = PrimeIntellectUsage()

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.endpoint_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(url, json=payload, headers=self._headers())
            if r.status_code >= 400:
                self.usage.errors += 1
                raise PrimeIntellectError(f"HTTP {r.status_code}: {r.text[:500]}")
            return r.json()

    def chat(
        self,
        prompt: str,
        model: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
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
        self.usage.add(model, prompt_tokens, completion_tokens, latency_ms)

        USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USAGE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": time.time(), "model": model,
                "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                "latency_ms": latency_ms, "finish_reason": finish,
                "preview": content[:200],
            }) + "\n")

        return {
            "content": content,
            "model": model,
            "finish_reason": finish,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
            "raw": raw,
        }


def smoke_test():
    print("Prime Intellect endpoint smoke test")
    c = PrimeIntellectClient()
    print(f"Endpoint: {c.endpoint_url}")
    print(f"API key set: {bool(c.api_key)}")
    print()
    # Model name depends on what's served. Common defaults:
    candidates = [
        "bharatgenai/Param2-17B-A2.4B-Thinking",
        "Param2-17B-A2.4B-Thinking",
        "param2",
    ]
    for model in candidates:
        print(f"--- trying model={model} ---")
        try:
            r = c.chat(prompt="Reply with exactly the word: pong",
                       model=model, temperature=0.0, max_tokens=20)
            print(f"  OK ({r['latency_ms']:.0f} ms)  tokens={r['prompt_tokens']}/{r['completion_tokens']}")
            print(f"  reply: {r['content']!r}")
            return 0
        except Exception as e:
            print(f"  FAIL: {str(e)[:200]}")
    print("\nNo candidate model name worked. Check what model id your deployment is serving.")
    return 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true")
    args = p.parse_args()
    raise SystemExit(smoke_test() if args.test else print("Usage: python -m src.providers.prime_intellect --test"))
