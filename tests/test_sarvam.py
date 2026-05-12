"""Smoke tests for Sarvam client. Run with: pytest tests/test_sarvam.py"""

import os

import pytest

from src.providers.sarvam import SarvamClient, SarvamError


@pytest.fixture
def client():
    if not os.getenv("SARVAM_API_KEY"):
        pytest.skip("SARVAM_API_KEY not set")
    return SarvamClient()


def test_english_chat(client):
    r = client.chat("Say 'hello' in one word.", model="sarvam-30b", max_tokens=20)
    assert "content" in r
    assert isinstance(r["content"], str)
    assert len(r["content"]) > 0


def test_hindi_chat(client):
    r = client.chat("एक शब्द में हिंदी में नमस्ते कहें।", model="sarvam-30b", max_tokens=30)
    assert "content" in r


def test_usage_tracking(client):
    initial = client.usage.requests
    client.chat("test", model="sarvam-30b", max_tokens=10)
    assert client.usage.requests == initial + 1


def test_invalid_key():
    bad = SarvamClient(api_key="sk_invalid_key_xxxx")
    with pytest.raises(SarvamError):
        bad.chat("test", max_tokens=10)
