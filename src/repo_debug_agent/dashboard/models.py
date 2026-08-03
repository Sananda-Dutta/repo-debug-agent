"""
Data models for the Token Usage Dashboard (Phase 12).
"""

from pydantic import BaseModel, Field


class IterationUsageBreakdown(BaseModel):
    """Token accounting for one debug iteration, both Phase 8's local
    compression and Phase 9's real Paritok hosted-GPU compression."""

    iteration: int
    outcome: str = Field(description="IterationOutcome value, e.g. 'fixed', 'regressed'")

    baseline_tokens: int
    compressed_tokens: int
    local_compression_ratio: float

    paritok_requests: int
    paritok_tokens_saved: int
    paritok_compression_ratio: float
    paritok_cost_saved_usd: str


class UsageDashboard(BaseModel):
    """Aggregated token/cost accounting across a full Phase 11 run —
    every iteration, not just the one that happened to succeed (a
    rolled-back attempt still cost real, Paritok-compressed LLM calls)."""

    success: bool
    total_iterations: int
    outcome_counts: dict[str, int] = Field(description="e.g. {'fixed': 1, 'no_change': 2}")

    baseline_failing_tests: int
    final_failing_tests: int

    total_baseline_tokens: int
    total_compressed_tokens: int
    overall_local_compression_ratio: float = Field(description="1 - (total_compressed / total_baseline)")

    total_paritok_requests: int
    total_paritok_tokens_saved: int
    total_paritok_cost_saved_usd: str

    iterations: list[IterationUsageBreakdown]