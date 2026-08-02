# tests/agent/test_graph.py
from pathlib import Path

import pytest

from repo_debug_agent.agent.graph import build_agent_graph
from repo_debug_agent.agent.models import ParitokCallStats
from repo_debug_agent.context_retrieval.models import CompressedContext, TokenUsageReport
from repo_debug_agent.indexing.models import CodebaseIndex
from repo_debug_agent.localization.models import LocalizationResult, RankedFile, RelevanceSource


def _localization_result() -> LocalizationResult:
    return LocalizationResult(
        anchor_file="app.py",
        anchor_symbol="add",
        ranked_files=[RankedFile(file_path="app.py", score=1.0, sources=[RelevanceSource.ANCHOR])],
    )


def _compressed_context() -> CompressedContext:
    usage = TokenUsageReport(
        baseline_token_count=100, compressed_token_count=40,
        units_available=1, units_included=1, compression_ratio=0.6,
    )
    return CompressedContext(assembled_text="# File: app.py\ndef add(a, b): return a + b", included_units=[], usage=usage)


class _FakeContextService:
    def __init__(self):
        self.calls: list[dict] = []

    def build_context(self, result, index, repo_root, token_budget):
        self.calls.append(dict(result=result, index=index, repo_root=repo_root, token_budget=token_budget))
        return _compressed_context()


class _FakeLLMClient:
    model = "gpt-4o-mini"

    def __init__(self):
        self.received_messages: list[dict] | None = None

    def complete(self, messages: list[dict]):
        self.received_messages = messages
        stats = ParitokCallStats(
            requests_delta=1, original_tokens=1000, compressed_tokens=250,
            tokens_saved=750, compression_ratio=0.25, estimated_cost_saved_usd="$0.02",
        )
        return "Root cause: off-by-one. Fix: use range(n).", stats


class _FakeLocalizationService:
    def __init__(self):
        self.called_with: dict | None = None

    def localize(self, exception, user_description=""):
        self.called_with = dict(exception=exception, user_description=user_description)
        return _localization_result()


def _index() -> CodebaseIndex:
    return CodebaseIndex(commit_sha="abc123", root_path="/repo", files={})


def test_graph_uses_precomputed_localization_result_without_calling_service():
    context_service = _FakeContextService()
    llm_client = _FakeLLMClient()
    graph = build_agent_graph(context_service, llm_client, localization_service=None)

    initial_state = {
        "repo_root": Path("/repo"),
        "index": _index(),
        "localization_result": _localization_result(),
        "token_budget": 8000,
    }
    final_state = graph.invoke(initial_state)

    assert final_state["compressed_context"].assembled_text.startswith("# File: app.py")
    assert "Root cause" in final_state["fix_suggestion"].raw_response
    assert final_state["fix_suggestion"].model == "gpt-4o-mini"
    # real Paritok stats flowed into the merged TokenUsageReport
    assert final_state["usage"].paritok_tokens_saved == 750
    assert final_state["usage"].paritok_requests == 1
    # Phase 8's own local-compression numbers are preserved alongside them
    assert final_state["usage"].baseline_token_count == 100


def test_graph_runs_localization_service_when_result_not_provided():
    context_service = _FakeContextService()
    llm_client = _FakeLLMClient()
    localization_service = _FakeLocalizationService()
    graph = build_agent_graph(context_service, llm_client, localization_service=localization_service)

    initial_state = {
        "repo_root": Path("/repo"),
        "index": _index(),
        "exception": None,
        "user_description": "AssertionError in test_foo",
        "localization_result": None,
        "token_budget": 4000,
    }
    final_state = graph.invoke(initial_state)

    assert localization_service.called_with["user_description"] == "AssertionError in test_foo"
    assert final_state["fix_suggestion"] is not None
    assert context_service.calls[0]["token_budget"] == 4000


def test_generate_fix_prompt_includes_failure_and_context():
    context_service = _FakeContextService()
    llm_client = _FakeLLMClient()
    graph = build_agent_graph(context_service, llm_client, localization_service=None)

    graph.invoke({
        "repo_root": Path("/repo"),
        "index": _index(),
        "user_description": "IndexError on empty list",
        "localization_result": _localization_result(),
    })

    user_message = llm_client.received_messages[1]["content"]
    assert "IndexError on empty list" in user_message
    assert "def add(a, b)" in user_message


def test_missing_localization_result_and_service_raises():
    context_service = _FakeContextService()
    llm_client = _FakeLLMClient()
    graph = build_agent_graph(context_service, llm_client, localization_service=None)

    with pytest.raises(ValueError):
        graph.invoke({"repo_root": Path("/repo"), "index": _index(), "localization_result": None})