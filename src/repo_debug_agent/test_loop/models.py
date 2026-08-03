"""
Data models for the Test Execution Loop (Phase 11).
"""

from enum import Enum

from pydantic import BaseModel, Field

from repo_debug_agent.agent.models import FixSuggestion
from repo_debug_agent.context_retrieval.models import TokenUsageReport
from repo_debug_agent.failure_analysis.models import FailureReport
from repo_debug_agent.patching.models import PatchApplyResult


class IterationOutcome(str, Enum):
    """What happened after applying and testing one candidate fix."""

    FIXED = "fixed"  # target failure(s) now pass, no new failures introduced -> KEPT
    NO_CHANGE = "no_change"  # couldn't parse/apply the fix, or target still fails -> rolled back
    REGRESSED = "regressed"  # target fixed but new failures appeared elsewhere -> rolled back
    RUN_FAILED = "run_failed"  # applied, but pytest itself couldn't run afterward -> rolled back


class IterationRecord(BaseModel):
    """Full record of one fix-test iteration, kept whether it succeeded or not
    (this is the audit trail — also raw material for Phase 12's dashboard)."""

    iteration: int
    fix_suggestion: FixSuggestion
    apply_result: PatchApplyResult | None = Field(default=None, description="None if parsing failed before any apply was attempted")
    test_report: FailureReport | None = Field(default=None, description="None if the fix wasn't applied or pytest couldn't run")
    outcome: IterationOutcome
    usage: TokenUsageReport
    notes: str = ""


class TestLoopResult(BaseModel):
    """Full result of running the loop to completion (success or exhausted iterations)."""

    success: bool = Field(description="True iff a fix that resolves the ORIGINAL target failure(s) was kept")
    iterations: list[IterationRecord]
    baseline_report: FailureReport = Field(description="Test results before any fix was attempted")
    final_report: FailureReport | None = Field(default=None, description="Test results after the loop finished")

    @property
    def total_paritok_tokens_saved(self) -> int:
        return sum(record.usage.paritok_tokens_saved for record in self.iterations)

    @property
    def total_paritok_requests(self) -> int:
        return sum(record.usage.paritok_requests for record in self.iterations)