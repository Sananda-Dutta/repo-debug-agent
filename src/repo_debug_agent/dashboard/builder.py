"""
Phase 12: turns a Phase 11 TestLoopResult into an aggregated UsageDashboard.

The numbers that actually matter for judging: total token savings from
BOTH Phase 8's local compression and Phase 9's real, dashboard-verified
Paritok hosted-GPU compression, across EVERY iteration of a debug run —
including rolled-back ones, which still cost real, Paritok-compressed
LLM calls and are part of the honest total.
"""

from __future__ import annotations

from repo_debug_agent.dashboard.models import IterationUsageBreakdown, UsageDashboard
from repo_debug_agent.test_loop.models import IterationRecord, TestLoopResult


def build_dashboard(result: TestLoopResult) -> UsageDashboard:
    breakdowns = [_iteration_breakdown(record) for record in result.iterations]

    total_baseline = sum(b.baseline_tokens for b in breakdowns)
    total_compressed = sum(b.compressed_tokens for b in breakdowns)
    local_ratio = round(1 - (total_compressed / total_baseline), 3) if total_baseline else 0.0

    outcome_counts: dict[str, int] = {}
    for record in result.iterations:
        outcome_counts[record.outcome.value] = outcome_counts.get(record.outcome.value, 0) + 1

    total_cost_saved = round(sum(_parse_usd(b.paritok_cost_saved_usd) for b in breakdowns), 2)

    final_report = result.final_report or result.baseline_report

    return UsageDashboard(
        success=result.success,
        total_iterations=len(result.iterations),
        outcome_counts=outcome_counts,
        baseline_failing_tests=result.baseline_report.failed + result.baseline_report.errors,
        final_failing_tests=final_report.failed + final_report.errors,
        total_baseline_tokens=total_baseline,
        total_compressed_tokens=total_compressed,
        overall_local_compression_ratio=local_ratio,
        total_paritok_requests=result.total_paritok_requests,
        total_paritok_tokens_saved=result.total_paritok_tokens_saved,
        total_paritok_cost_saved_usd=f"${total_cost_saved:.2f}",
        iterations=breakdowns,
    )


def _iteration_breakdown(record: IterationRecord) -> IterationUsageBreakdown:
    usage = record.usage
    return IterationUsageBreakdown(
        iteration=record.iteration,
        outcome=record.outcome.value,
        baseline_tokens=usage.baseline_token_count,
        compressed_tokens=usage.compressed_token_count,
        local_compression_ratio=usage.compression_ratio,
        paritok_requests=usage.paritok_requests,
        paritok_tokens_saved=usage.paritok_tokens_saved,
        paritok_compression_ratio=usage.paritok_compression_ratio,
        paritok_cost_saved_usd=usage.paritok_estimated_cost_saved_usd,
    )


def _parse_usd(value: str) -> float:
    return float(value.replace("$", "").strip() or 0.0)