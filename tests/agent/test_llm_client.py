# tests/agent/test_llm_client.py
from types import SimpleNamespace

import pytest

from repo_debug_agent.agent.llm_client import ParitokLLMClient


@pytest.fixture(autouse=True)
def _fake_settings(monkeypatch):
    """ParitokLLMClient reads openai_api_key/llm_model from settings to build
    the underlying OpenAI() client, which refuses to construct with no
    credentials at all. Tests don't hit the network, so a dummy key is fine."""
    fake = SimpleNamespace(openai_api_key="sk-test-dummy", llm_model="gpt-4o-mini")
    monkeypatch.setattr("repo_debug_agent.agent.llm_client.get_settings", lambda: fake)


class _FakeProxy:
    """Fake ParitokProxyManager: returns pre-scripted /stats snapshots in order."""

    def __init__(self, snapshots: list[dict]):
        self._snapshots = list(snapshots)
        self.base_url = "http://127.0.0.1:8080"

    def stats(self) -> dict:
        return self._snapshots.pop(0)


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


class _FakeChat:
    def __init__(self, completions: _FakeCompletions):
        self.completions = completions


def _build_client(before: dict, after: dict, response_text: str = "here is a fix"):
    proxy = _FakeProxy([before, after])
    client = ParitokLLMClient(proxy, model="gpt-4o-mini")
    fake_completions = _FakeCompletions(_FakeResponse(response_text))
    client._client.chat = _FakeChat(fake_completions)
    return client, fake_completions


def test_complete_returns_response_text_and_diffed_stats():
    before = {
        "total_requests": 3, "input_tokens_original": 10_000, "input_tokens_compressed": 3_000,
        "estimated_cost_saved_usd": "$0.50",
    }
    after = {
        "total_requests": 4, "input_tokens_original": 12_000, "input_tokens_compressed": 3_400,
        "estimated_cost_saved_usd": "$0.62",
    }
    client, fake_completions = _build_client(before, after)

    text, stats = client.complete([{"role": "user", "content": "hi"}])

    assert text == "here is a fix"
    assert stats.requests_delta == 1
    assert stats.original_tokens == 2_000
    assert stats.compressed_tokens == 400
    assert stats.tokens_saved == 1_600
    assert stats.compression_ratio == 0.2
    assert stats.estimated_cost_saved_usd == "$0.12"
    # the model + messages were actually forwarded to the (fake) OpenAI client
    assert fake_completions.last_kwargs["model"] == "gpt-4o-mini"
    assert fake_completions.last_kwargs["messages"] == [{"role": "user", "content": "hi"}]


def test_complete_handles_zero_original_tokens_without_dividing_by_zero():
    snapshot = {
        "total_requests": 0, "input_tokens_original": 0, "input_tokens_compressed": 0,
        "estimated_cost_saved_usd": "$0.00",
    }
    client, _ = _build_client(snapshot, snapshot)

    _, stats = client.complete([{"role": "user", "content": "hi"}])

    assert stats.original_tokens == 0
    assert stats.compression_ratio == 0.0


def test_diff_stats_missing_key_raises_value_error():
    with pytest.raises(ValueError):
        ParitokLLMClient._diff_stats({}, {})