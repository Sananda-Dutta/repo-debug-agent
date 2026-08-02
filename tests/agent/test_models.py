# tests/agent/test_models.py
from repo_debug_agent.agent.models import AgentRunResult, FixSuggestion, ParitokCallStats
from repo_debug_agent.context_retrieval.models import CompressedContext, TokenUsageReport


def _usage(**overrides) -> TokenUsageReport:
    base = dict(
        baseline_token_count=1000,
        compressed_token_count=300,
        units_available=5,
        units_included=3,
        compression_ratio=0.7,
    )
    base.update(overrides)
    return TokenUsageReport(**base)


def test_token_usage_report_defaults_have_no_paritok_stats():
    usage = _usage()
    assert usage.paritok_requests == 0
    assert usage.paritok_tokens_saved == 0
    assert usage.paritok_compression_ratio == 0.0
    assert usage.paritok_estimated_cost_saved_usd == "$0.00"


def test_with_paritok_stats_returns_new_instance_with_stats_attached():
    usage = _usage()
    updated = usage.with_paritok_stats(
        requests=1, tokens_saved=420, compression_ratio=0.257, cost_saved_usd="$0.03"
    )

    # Original untouched (pydantic models are copied, not mutated)
    assert usage.paritok_requests == 0
    # New instance carries the real Paritok numbers
    assert updated.paritok_requests == 1
    assert updated.paritok_tokens_saved == 420
    assert updated.paritok_compression_ratio == 0.257
    assert updated.paritok_estimated_cost_saved_usd == "$0.03"
    # Phase 8's own local-compression accounting is preserved unchanged
    assert updated.baseline_token_count == usage.baseline_token_count
    assert updated.tokens_saved == usage.tokens_saved


def test_paritok_call_stats_roundtrip():
    stats = ParitokCallStats(
        requests_delta=1,
        original_tokens=500,
        compressed_tokens=125,
        tokens_saved=375,
        compression_ratio=0.25,
        estimated_cost_saved_usd="$0.01",
    )
    assert stats.tokens_saved == stats.original_tokens - stats.compressed_tokens


def test_fix_suggestion_allows_missing_paritok_stats():
    suggestion = FixSuggestion(raw_response="do X", model="gpt-4o-mini")
    assert suggestion.paritok_stats is None


def test_agent_run_result_bundles_everything():
    compressed = CompressedContext(assembled_text="", included_units=[], usage=_usage())
    suggestion = FixSuggestion(raw_response="fix", model="gpt-4o-mini")
    result = AgentRunResult(compressed_context=compressed, fix_suggestion=suggestion, usage=_usage())
    assert result.fix_suggestion.raw_response == "fix"