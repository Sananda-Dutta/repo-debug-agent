"""
FailureAnalysisService: single public entrypoint for Phase 6.
"""

from pathlib import Path

from repo_debug_agent.core.logger import logger
from repo_debug_agent.failure_analysis.models import FailureReport, ParsedException
from repo_debug_agent.failure_analysis.pytest_runner import run_tests
from repo_debug_agent.failure_analysis.traceback_parser import parse_traceback


class FailureAnalysisService:
    def analyze_pasted_traceback(self, raw_text: str) -> ParsedException | None:
        """Path A: the user provides a stack trace / bug report directly."""
        parsed = parse_traceback(raw_text)
        if parsed is None:
            logger.warning("No 'Traceback (most recent call last):' block found in provided text")
        else:
            logger.info(
                f"Parsed exception: {parsed.exception_type} "
                f"({len(parsed.frames)} frames, innermost="
                f"{parsed.innermost_frame.file_path if parsed.innermost_frame else 'n/a'})"
            )
        return parsed

    def run_and_analyze_tests(
        self, repo_root: Path, test_target: str = "", python_executable: str | None = None,
    ) -> FailureReport:
        """Path B: run the repo's own test suite and analyze the results."""
        report = run_tests(repo_root, test_target=test_target, python_executable=python_executable)
        if report.has_failures:
            logger.warning(
                f"{report.failed} failed, {report.errors} errored "
                f"out of {report.total_tests} tests"
            )
        else:
            logger.info(f"All {report.total_tests} tests passed")
        return report