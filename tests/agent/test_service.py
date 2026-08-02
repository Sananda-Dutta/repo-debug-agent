# tests/agent/test_service.py
from pathlib import Path

import pytest

import repo_debug_agent.agent.service as service_module
from repo_debug_agent.agent.models import ParitokCallStats
from repo_debug_agent.agent.service import LLMAgentService
from repo_debug_agent.context_retrieval.compressor import NaiveCompressor
from repo_debug_agent.indexing.models import CodebaseIndex
from repo_debug_agent.localization.models import LocalizationResult, RankedFile, RelevanceSource


class _FakeProxyManager:
    instances: list["_FakeProxyManager"] = []

    def __init__(self, port=8080):
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self.started = False
        self.stopped = False
        _FakeProxyManager.instances.append(self)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def stats(self):
        return {
            "total_requests": 1, "input_tokens_original": 1000,
            "input_tokens_compressed": 250, "estimated_cost_saved_usd": "$0.01",
        }


class _FakeLLMClient:
    def __init__(self, proxy, model=None):
        self.proxy = proxy
        self.model = model or "gpt-4o-mini"

    def complete(self, messages):
        stats = ParitokCallStats(
            requests_delta=1, original_tokens=1000, compressed_tokens=250,
            tokens_saved=750, compression_ratio=0.25, estimated_cost_saved_usd="$0.01",
        )
        return "Suggested fix here.", stats


@pytest.fixture(autouse=True)
def _patch_proxy_and_llm(monkeypatch):
    _FakeProxyManager.instances.clear()
    monkeypatch.setattr(service_module, "ParitokProxyManager", _FakeProxyManager)
    monkeypatch.setattr(service_module, "ParitokLLMClient", _FakeLLMClient)


def _localization_result() -> LocalizationResult:
    return LocalizationResult(
        anchor_file="app.py", anchor_symbol="add",
        ranked_files=[RankedFile(file_path="app.py", score=1.0, sources=[RelevanceSource.ANCHOR])],
    )


def test_service_starts_proxy_on_construction():
    LLMAgentService(compressor=NaiveCompressor())
    assert _FakeProxyManager.instances[0].started is True


def test_debug_requires_localization_result_or_service():
    agent = LLMAgentService(compressor=NaiveCompressor())
    with pytest.raises(ValueError):
        agent.debug(repo_root=Path("/repo"), index=CodebaseIndex(commit_sha="a", root_path="/repo", files={}))


def test_debug_runs_end_to_end_with_precomputed_localization():
    agent = LLMAgentService(compressor=NaiveCompressor())
    index = CodebaseIndex(
        commit_sha="a", root_path="/repo",
        files={},  # NaiveCompressor + empty ranked-file symbols means whole-file fetch; see note below
    )

    result = agent.debug(
        repo_root=Path("/repo"),
        index=index,
        localization_result=_localization_result(),
    )

    assert result.fix_suggestion.raw_response == "Suggested fix here."
    assert result.usage.paritok_tokens_saved == 750


def test_close_stops_the_proxy():
    agent = LLMAgentService(compressor=NaiveCompressor())
    agent.close()
    assert _FakeProxyManager.instances[0].stopped is True


def test_context_manager_stops_proxy_on_exit():
    with LLMAgentService(compressor=NaiveCompressor()):
        pass
    assert _FakeProxyManager.instances[0].stopped is True