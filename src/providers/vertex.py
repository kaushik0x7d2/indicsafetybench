"""
Google Cloud Vertex AI client for Gemini + Claude models.

Two auth paths (auto-detected, no code change needed):
  (1) gcloud Application Default Credentials (run `gcloud auth application-default login` once)
  (2) Service account JSON file path in GOOGLE_APPLICATION_CREDENTIALS env var

Required .env:
  GCP_PROJECT=<your-project-id>
  GCP_REGION=us-east5            # us-east5 hosts both Gemini + Claude; us-central1 hosts Gemini only

Optional:
  GOOGLE_APPLICATION_CREDENTIALS=<path-to-service-account.json>   # only if not using gcloud ADC

Supported model families on Vertex:
  - Gemini: publishers/google/models/{model_id}  (e.g., gemini-2.5-pro, gemini-3.1-pro-preview)
  - Claude: publishers/anthropic/models/{model_id} (e.g., claude-opus-4@20250514, claude-sonnet-4-6@latest)

Smoke test (requires .env populated):
    python -m src.providers.vertex --test
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

DEFAULT_REGION = "us-east5"  # hosts both Gemini + Claude
DEFAULT_TIMEOUT = 180.0


@dataclass
class VertexUsage:
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
        return (f"VertexUsage(req={self.requests}, "
                f"prompt={self.prompt_tokens}, comp={self.completion_tokens})")


class VertexError(Exception):
    pass


class VertexClient:
    """Vertex AI client supporting Gemini (Google) and Claude (Anthropic) on a single GCP project.

    Auto-routes by model id prefix:
      - 'gemini-*'              -> google-genai SDK with Vertex backend
      - 'claude-*'              -> anthropic.AnthropicVertex
    """

    def __init__(self,
                 project: Optional[str] = None,
                 region: Optional[str] = None,
                 timeout: float = DEFAULT_TIMEOUT):
        self.project = project or os.getenv("GCP_PROJECT")
        if not self.project:
            raise ValueError("Set GCP_PROJECT in .env (your Google Cloud project ID)")
        self.region = region or os.getenv("GCP_REGION", DEFAULT_REGION)
        self.timeout = timeout
        self.usage = VertexUsage()

        # Lazy-init SDK handles (avoid import-time failures if a SDK is missing)
        self._genai = None
        self._anthropic_vertex = None

    def _genai_client(self):
        if self._genai is None:
            from google import genai
            self._genai = genai.Client(
                vertexai=True,
                project=self.project,
                location=self.region,
            )
        return self._genai

    def _anthropic_client(self):
        if self._anthropic_vertex is None:
            from anthropic import AnthropicVertex
            self._anthropic_vertex = AnthropicVertex(
                region=self.region,
                project_id=self.project,
            )
        return self._anthropic_vertex

    def chat(self, prompt: str, model: str,
             system: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: int = 1024) -> dict:
        """OpenAI-style chat completion. Returns standard provider dict."""
        t0 = time.time()
        try:
            if model.startswith("gemini"):
                result = self._call_gemini(prompt, model, system, temperature, max_tokens)
            elif model.startswith("claude"):
                result = self._call_claude(prompt, model, system, temperature, max_tokens)
            else:
                raise VertexError(
                    f"Unknown model family for '{model}'. Vertex client routes "
                    "gemini-* and claude-* model IDs.")
        except Exception:
            self.usage.errors += 1
            raise
        result["latency_ms"] = (time.time() - t0) * 1000
        self.usage.add(model, result.get("prompt_tokens") or 0,
                       result.get("completion_tokens") or 0)
        return result

    def _call_gemini(self, prompt: str, model: str,
                     system: Optional[str], temperature: float, max_tokens: int) -> dict:
        from google.genai import types as gtypes
        client = self._genai_client()
        config = gtypes.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system if system else None,
        )
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        content = ""
        try:
            content = resp.text or ""
        except Exception:
            # Fall back to manual extraction
            for c in (resp.candidates or []):
                for part in (getattr(c, "content", None) and c.content.parts) or []:
                    if hasattr(part, "text") and part.text:
                        content += part.text
        usage = getattr(resp, "usage_metadata", None)
        return {
            "content": content,
            "model": model,
            "finish_reason": (resp.candidates[0].finish_reason
                              if resp.candidates else None),
            "prompt_tokens": getattr(usage, "prompt_token_count", 0) if usage else 0,
            "completion_tokens": getattr(usage, "candidates_token_count", 0) if usage else 0,
        }

    def _call_claude(self, prompt: str, model: str,
                     system: Optional[str], temperature: float, max_tokens: int) -> dict:
        client = self._anthropic_client()
        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        content = ""
        for block in (resp.content or []):
            if hasattr(block, "text") and block.text:
                content += block.text
        usage = getattr(resp, "usage", None)
        return {
            "content": content,
            "model": model,
            "finish_reason": getattr(resp, "stop_reason", None),
            "prompt_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
            "completion_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
        }


def smoke_test():
    print("Vertex AI smoke test")
    c = VertexClient()
    print(f"Project: {c.project}  Region: {c.region}")
    print()
    # Try Gemini 3.1 Pro and Claude Opus 4 (latest IDs as of 2026 — adjust if your
    # Model Garden entitlements differ).
    candidates = [
        "gemini-3.1-pro-preview",
        "gemini-2.5-pro",
        "claude-opus-4@20250514",
        "claude-sonnet-4-6@latest",
    ]
    ok = 0
    for model in candidates:
        try:
            r = c.chat(prompt="Reply with exactly the word: pong",
                       model=model, temperature=0.0, max_tokens=50)
            tag = "OK" if r["content"] else "EMPTY"
            print(f"  [{tag}] {model:45s} {r['latency_ms']:>5.0f} ms  "
                  f"tokens={r['prompt_tokens']}/{r['completion_tokens']}  "
                  f"reply={r['content'][:40]!r}")
            if r["content"]:
                ok += 1
        except Exception as e:
            err_short = str(e).splitlines()[0][:150]
            print(f"  [FAIL] {model:45s} {err_short}")
    print(f"\n{ok}/{len(candidates)} models returned text.")
    return 0 if ok else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true")
    args = p.parse_args()
    raise SystemExit(smoke_test() if args.test else print("Usage: python -m src.providers.vertex --test"))
