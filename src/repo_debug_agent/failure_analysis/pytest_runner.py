"""
Runs a repo's own test suite via subprocess and returns a structured
FailureReport, using pytest-json-report for counts/timing and our own
traceback_parser (via forced --tb=native) for call-stack detail.

ASSUMPTION (documented scope boundary): the target repo's test
dependencies must already be importable in whatever environment runs
this command — whether this process's own venv, or one the caller
points `python_executable` at. Automatically creating an isolated venv
and installing the target repo's requirements is a legitimate future
enhancement but is out of scope for Phase 6.

We NEVER import the target repo's code into this process directly —
running it via subprocess is a deliberate isolation boundary, since
the repo being debugged is arbitrary, untrusted code.
"""

import json
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
        "--tb=native",                        # unify with traceback_parser's grammar
        "-p", "pytest_jsonreport.plugin",     # explicit, in case plugin autoload is disabled
        "-q",
        "--json-report",
        f"--json-report-file={report_path}",
    ]

    logger.info(f"Running tests: {' '.join(command)} (cwd={repo_root})")
    try:
        subprocess.run(command, cwd=repo_root, capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        raise TestRunError(f"Test run exceeded {timeout_seconds}s timeout") from exc
    except OSError as exc:
        raise TestRunError(f"Failed to invoke pytest: {exc}") from exc

    if not report_path.exists():
        raise TestRunError(
            "pytest did not produce a JSON report. Ensure 'pytest-json-report' is "
            "installed in the environment used to run the target repo's tests."
        )

    try:
        raw_report = json.loads(report_path.read_text(encoding="utf-8"))
    finally:
        report_path.unlink(missing_ok=True)  # don't leave our tooling's artifacts in the user's repo

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