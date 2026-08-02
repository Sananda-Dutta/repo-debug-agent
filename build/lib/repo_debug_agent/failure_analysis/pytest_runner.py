"""
Runs a repo's own test suite via subprocess and returns a structured
FailureReport, using pytest-json-report for counts/timing and our own
traceback_parser (via forced --tb=native) for call-stack detail.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from repo_debug_agent.core.logger import logger
from repo_debug_agent.exceptions import TestRunError
from repo_debug_agent.failure_analysis.models import FailureReport, TestFailure, TestOutcome
from repo_debug_agent.failure_analysis.traceback_parser import parse_traceback


def run_tests(
    repo_root: Path,
    test_target: str = "",
    python_executable: str | None = None,
    timeout_seconds: int = 300,
) -> FailureReport:
    """
    Run pytest against `repo_root`, optionally scoped to `test_target`
    (a specific file or node id, e.g. "tests/test_utils.py::test_add").
    """
    python_executable = python_executable or sys.executable
    report_path = repo_root / ".repo_debug_agent_report.json"

    command = [
        python_executable, "-m", "pytest",
        test_target if test_target else ".",
        "--tb=native",
        "-q",
        "--json-report",
        f"--json-report-file={report_path}",
    ]

    # pytest-json-report autoloads via its entry point in a normal
    # environment. Only force-load it explicitly when autoload is
    # disabled — forcing it unconditionally risks a duplicate-plugin
    # registration error that silently prevents the report from ever
    # being written.
    if os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD"):
        command[3:3] = ["-p", "pytest_jsonreport.plugin"]

    logger.info(f"Running tests: {' '.join(command)} (cwd={repo_root})")
    try:
        result = subprocess.run(
            command, cwd=repo_root, capture_output=True, text=True, timeout=timeout_seconds
        )
    except subprocess.TimeoutExpired as exc:
        raise TestRunError(f"Test run exceeded {timeout_seconds}s timeout") from exc
    except OSError as exc:
        raise TestRunError(f"Failed to invoke pytest: {exc}") from exc

    if not report_path.exists():
        # Surface pytest's actual stdout/stderr — critical for diagnosing
        # WHY the report wasn't produced (bad args, import errors, plugin
        # conflicts, etc.) instead of a generic, undiagnosable message.
        raise TestRunError(
            "pytest did not produce a JSON report.\n"
            f"Exit code: {result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )

    try:
        raw_report = json.loads(report_path.read_text(encoding="utf-8"))
    finally:
        report_path.unlink(missing_ok=True)

    return _parse_json_report(raw_report)


def _parse_json_report(raw_report: dict) -> FailureReport:
    summary = raw_report.get("summary", {})
    failures: list[TestFailure] = []

    for test_entry in raw_report.get("tests", []):
        outcome_str = test_entry.get("outcome", "passed")
        if outcome_str not in ("failed", "error"):
            continue

        node_id = test_entry.get("nodeid", "")
        file_path = node_id.split("::")[0] if "::" in node_id else node_id

        call_phase = test_entry.get("call") or test_entry.get("setup") or {}
        longrepr = call_phase.get("longrepr", "")
        parsed_exception = parse_traceback(longrepr) if isinstance(longrepr, str) else None

        failures.append(TestFailure(
            node_id=node_id,
            file_path=file_path,
            outcome=TestOutcome.FAILED if outcome_str == "failed" else TestOutcome.ERROR,
            exception=parsed_exception,
            duration_seconds=call_phase.get("duration", 0.0),
        ))

    return FailureReport(
        total_tests=summary.get("total", 0),
        passed=summary.get("passed", 0),
        failed=summary.get("failed", 0),
        errors=summary.get("error", 0),
        skipped=summary.get("skipped", 0),
        failures=failures,
    )