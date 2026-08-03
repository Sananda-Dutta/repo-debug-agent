"""
TestExecutionLoopService: single public entrypoint for Phase 11.

Orchestrates the full debug cycle: run the repo's own tests (Phase 6) to
get a baseline -> repeatedly ask Phase 9 for a fix -> apply it (Phase 10)
-> re-run tests -> decide whether to keep or roll back -> stop when the
target failure(s) are resolved, a hard iteration cap is hit, or nothing
is parseable/applicable.

Deliberately does NOT re-run localization (Phase 7) between iterations —
it's given a fixed target (either a precomputed LocalizationResult, or a
localization_service to compute it once). What changes between
iterations is the PROMPT: after a failed attempt, the next one is told
what's still failing, so it isn't just re-asked the same question.
"""

from __future__ import annotations

from pathlib import Path

from repo_debug_agent.agent.models import FixSuggestion
from repo_debug_agent.agent.service import LLMAgentService
from repo_debug_agent.config.settings import get_settings
from repo_debug_agent.context_retrieval.models import TokenUsageReport
from repo_debug_agent.core.logger import logger
from repo_debug_agent.exceptions import PatchParsingError, TestRunError
from repo_debug_agent.failure_analysis.models import FailureReport, ParsedException
from repo_debug_agent.failure_analysis.pytest_runner import run_tests
from repo_debug_agent.indexing.models import CodebaseIndex
from repo_debug_agent.localization.models import LocalizationResult
from repo_debug_agent.localization.service import FileLocalizationService
from repo_debug_agent.patching.models import PatchApplyResult
from repo_debug_agent.patching.service import PatchService
from repo_debug_agent.test_loop.models import IterationOutcome, IterationRecord, TestLoopResult

_DEFAULT_TOKEN_BUDGET = 8000


class TestExecutionLoopService:
    def __init__(
        self,
        agent_service: LLMAgentService,
        max_iterations: int | None = None,
        patch_service_factory=PatchService,
    ):
        self._agent = agent_service
        settings = get_settings()
        self._max_iterations = max_iterations or settings.max_debug_iterations
        # Injectable so tests can substitute a fake PatchService without a real git checkout.
        self._patch_service_factory = patch_service_factory

    def run(
        self,
        repo_root: Path,
        index: CodebaseIndex,
        test_target: str = "",
        localization_service: FileLocalizationService | None = None,
        exception: ParsedException | None = None,
        user_description: str = "",
        localization_result: LocalizationResult | None = None,
        token_budget: int = _DEFAULT_TOKEN_BUDGET,
    ) -> TestLoopResult:
        baseline = run_tests(repo_root, test_target=test_target)
        if not baseline.has_failures:
            logger.info("Baseline test run has no failures — nothing to fix.")
            return TestLoopResult(success=True, iterations=[], baseline_report=baseline, final_report=baseline)

        target_node_ids = {f.node_id for f in baseline.failures}
        patch_service = self._patch_service_factory(repo_root)
        iterations: list[IterationRecord] = []
        current_report = baseline

        for i in range(1, self._max_iterations + 1):
            iteration_description = self._build_iteration_description(user_description, current_report, target_node_ids)

            agent_result = self._agent.debug(
                repo_root=repo_root,
                index=index,
                localization_service=localization_service,
                exception=exception,
                user_description=iteration_description,
                localization_result=localization_result,
                token_budget=token_budget,
            )
            usage = agent_result.usage

            try:
                apply_result = patch_service.apply(agent_result.fix_suggestion)
            except PatchParsingError as exc:
                iterations.append(IterationRecord(
                    iteration=i, fix_suggestion=agent_result.fix_suggestion, apply_result=None,
                    test_report=None, outcome=IterationOutcome.NO_CHANGE, usage=usage, notes=str(exc),
                ))
                continue

            if not apply_result.success:
                iterations.append(IterationRecord(
                    iteration=i, fix_suggestion=agent_result.fix_suggestion, apply_result=apply_result,
                    test_report=None, outcome=IterationOutcome.NO_CHANGE, usage=usage,
                    notes=apply_result.error or "Patch did not apply.",
                ))
                continue

            record, resolved = self._evaluate(i, agent_result.fix_suggestion, apply_result, usage,
                                                patch_service, repo_root, test_target, target_node_ids)
            iterations.append(record)
            if record.test_report is not None:
                current_report = record.test_report

            if resolved:
                return TestLoopResult(success=True, iterations=iterations, baseline_report=baseline,
                                       final_report=record.test_report)

        logger.warning(f"Exhausted {self._max_iterations} iteration(s) without resolving the target failure(s).")
        return TestLoopResult(success=False, iterations=iterations, baseline_report=baseline, final_report=current_report)

    def _evaluate(
        self, iteration: int, fix_suggestion: FixSuggestion, apply_result: PatchApplyResult, usage: TokenUsageReport,
        patch_service: PatchService, repo_root: Path, test_target: str, target_node_ids: set[str],
    ) -> tuple[IterationRecord, bool]:
        """Re-run tests after applying a fix and decide FIXED / REGRESSED / NO_CHANGE.
        Rolls back everything except a genuine FIXED outcome."""
        try:
            new_report = run_tests(repo_root, test_target=test_target)
        except TestRunError as exc:
            patch_service.rollback(apply_result)
            return IterationRecord(
                iteration=iteration, fix_suggestion=fix_suggestion, apply_result=apply_result, test_report=None,
                outcome=IterationOutcome.RUN_FAILED, usage=usage, notes=f"pytest failed to run after applying fix: {exc}",
            ), False

        failing_node_ids = {f.node_id for f in new_report.failures}
        still_failing = target_node_ids & failing_node_ids
        newly_broken = failing_node_ids - target_node_ids

        if not still_failing and not newly_broken:
            return IterationRecord(
                iteration=iteration, fix_suggestion=fix_suggestion, apply_result=apply_result, test_report=new_report,
                outcome=IterationOutcome.FIXED, usage=usage,
            ), True

        if not still_failing and newly_broken:
            patch_service.rollback(apply_result)
            return IterationRecord(
                iteration=iteration, fix_suggestion=fix_suggestion, apply_result=apply_result, test_report=new_report,
                outcome=IterationOutcome.REGRESSED, usage=usage,
                notes=f"Fixed the target failure(s) but introduced {len(newly_broken)} new failure(s); rolled back.",
            ), False

        patch_service.rollback(apply_result)
        return IterationRecord(
            iteration=iteration, fix_suggestion=fix_suggestion, apply_result=apply_result, test_report=new_report,
            outcome=IterationOutcome.NO_CHANGE, usage=usage,
            notes=f"{len(still_failing)} target failure(s) still failing; rolled back.",
        ), False

    @staticmethod
    def _build_iteration_description(user_description: str, report: FailureReport, target_node_ids: set[str]) -> str:
        """Feed the CURRENT state of the target failure(s) into the next
        prompt, so a rejected attempt doesn't just get re-asked verbatim."""
        lines = [f"{f.node_id}: {f.outcome.value}" + (f" — {f.exception.exception_type}: {f.exception.message}" if f.exception else "")
                 for f in report.failures if f.node_id in target_node_ids]
        failure_block = "\n".join(lines)
        parts = [p for p in (user_description, f"Currently failing:\n{failure_block}" if failure_block else "") if p]
        return "\n\n".join(parts)