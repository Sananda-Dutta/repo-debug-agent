# tests/test_loop/test_service.py
from pathlib import Path
from types import SimpleNamespace

import pytest

import repo_debug_agent.test_loop.service as service_module
from repo_debug_agent.agent.models import FixSuggestion
from repo_debug_agent.context_retrieval.models import TokenUsageReport
from repo_debug_agent.exceptions import PatchParsingError, TestRunError
from repo_debug_agent.failure_analysis.models import FailureReport, ParsedException, TestFailure, TestOutcome
from repo_debug_agent.indexing.models import CodebaseIndex
from repo_debug_agent.patching.models import AppliedFile, PatchApplyResult
from repo_debug_agent.test_loop.models import IterationOutcome
from repo_debug_agent.test_loop.service import TestExecutionLoopService


def _usage(saved=100, requests=1) -> TokenUsageReport:
    return TokenUsageReport(
        baseline_token_count=1000, compressed_token_count=300, units_available=3, units_included=2,
        compression_ratio=0.7,
    ).with_paritok_stats(requests=requests, tokens_saved=saved, compression_ratio=0.3, cost_saved_usd="$0.00")


def _report(*, failing: list[str], passed: int = 5) -> FailureReport:
    failures = [
        TestFailure(node_id=node_id, file_path=node_id.split("::")[0], outcome=TestOutcome.FAILED,
                    exception=ParsedException(exception_type="AssertionError", message="boom", raw_traceback=""))
        for node_id in failing
    ]
    return FailureReport(total_tests=passed + len(failing), passed=passed, failed=len(failing), errors=0, skipped=0, failures=failures)


class _FakeAgent:
    def __init__(self):
        self.calls: list[dict] = []

    def debug(self, **kwargs):
        self.calls.append(kwargs)
        suggestion = FixSuggestion(raw_response="### File: app.py\n```python\nfixed = True\n```\n", model="gpt-4o-mini")
        return SimpleNamespace(fix_suggestion=suggestion, usage=_usage())


class _FakePatchService:
    instances: list["_FakePatchService"] = []

    def __init__(self, repo_root, apply_results=None):
        self.repo_root = repo_root
        self._apply_results = list(apply_results or [])
        self.rollback_calls: list[PatchApplyResult] = []
        _FakePatchService.instances.append(self)

    def apply(self, fix_suggestion):
        outcome = self._apply_results.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def rollback(self, result):
        self.rollback_calls.append(result)


def _ok_apply_result() -> PatchApplyResult:
    return PatchApplyResult(success=True, applied_files=[AppliedFile(file_path="app.py", backup_path="/tmp/x", existed_before=True)], backup_dir="/tmp")


def _index() -> CodebaseIndex:
    return CodebaseIndex(commit_sha="a", root_path="/repo", files={})


@pytest.fixture(autouse=True)
def _reset_fake_patch_service():
    _FakePatchService.instances.clear()


def test_no_baseline_failures_returns_success_without_calling_agent(monkeypatch):
    monkeypatch.setattr(service_module, "run_tests", lambda repo_root, test_target="": _report(failing=[]))
    agent = _FakeAgent()
    loop = TestExecutionLoopService(agent, max_iterations=3, patch_service_factory=_FakePatchService)

    result = loop.run(repo_root=Path("/repo"), index=_index())

    assert result.success is True
    assert result.iterations == []
    assert agent.calls == []


def test_fix_resolves_target_failure_and_stops(monkeypatch):
    reports = iter([_report(failing=["tests/test_x.py::test_foo"]), _report(failing=[])])
    monkeypatch.setattr(service_module, "run_tests", lambda repo_root, test_target="": next(reports))
    agent = _FakeAgent()
    loop = TestExecutionLoopService(
        agent, max_iterations=5,
        patch_service_factory=lambda repo_root: _FakePatchService(repo_root, apply_results=[_ok_apply_result()]),
    )

    result = loop.run(repo_root=Path("/repo"), index=_index())

    assert result.success is True
    assert len(result.iterations) == 1
    assert result.iterations[0].outcome == IterationOutcome.FIXED
    assert _FakePatchService.instances[0].rollback_calls == []  # kept, not rolled back
    assert len(agent.calls) == 1


def test_still_failing_rolls_back_and_exhausts_iterations(monkeypatch):
    still_failing = _report(failing=["tests/test_x.py::test_foo"])
    monkeypatch.setattr(service_module, "run_tests", lambda repo_root, test_target="": still_failing)
    agent = _FakeAgent()
    apply_results = [_ok_apply_result() for _ in range(3)]
    loop = TestExecutionLoopService(
        agent, max_iterations=3,
        patch_service_factory=lambda repo_root: _FakePatchService(repo_root, apply_results=apply_results),
    )

    result = loop.run(repo_root=Path("/repo"), index=_index())

    assert result.success is False
    assert len(result.iterations) == 3
    assert all(r.outcome == IterationOutcome.NO_CHANGE for r in result.iterations)
    assert len(_FakePatchService.instances[0].rollback_calls) == 3


def test_regression_rolls_back_and_loop_continues(monkeypatch):
    reports = iter([
        _report(failing=["tests/test_x.py::test_foo"]),  # baseline
        _report(failing=["tests/test_y.py::test_new"]),  # iteration 1: target fixed, but new failure
        _report(failing=[]),  # iteration 2: clean fix
    ])
    monkeypatch.setattr(service_module, "run_tests", lambda repo_root, test_target="": next(reports))
    agent = _FakeAgent()
    apply_results = [_ok_apply_result(), _ok_apply_result()]
    loop = TestExecutionLoopService(
        agent, max_iterations=5,
        patch_service_factory=lambda repo_root: _FakePatchService(repo_root, apply_results=apply_results),
    )

    result = loop.run(repo_root=Path("/repo"), index=_index())

    assert result.success is True
    assert len(result.iterations) == 2
    assert result.iterations[0].outcome == IterationOutcome.REGRESSED
    assert result.iterations[1].outcome == IterationOutcome.FIXED
    assert len(_FakePatchService.instances[0].rollback_calls) == 1  # only the regressed one


def test_unparseable_fix_records_no_change_and_continues(monkeypatch):
    reports = iter([_report(failing=["tests/test_x.py::test_foo"]), _report(failing=[])])
    monkeypatch.setattr(service_module, "run_tests", lambda repo_root, test_target="": next(reports))
    agent = _FakeAgent()
    apply_results = [PatchParsingError("could not parse"), _ok_apply_result()]
    loop = TestExecutionLoopService(
        agent, max_iterations=5,
        patch_service_factory=lambda repo_root: _FakePatchService(repo_root, apply_results=apply_results),
    )

    result = loop.run(repo_root=Path("/repo"), index=_index())

    assert result.success is True
    assert result.iterations[0].outcome == IterationOutcome.NO_CHANGE
    assert result.iterations[0].apply_result is None
    assert "could not parse" in result.iterations[0].notes
    assert result.iterations[1].outcome == IterationOutcome.FIXED


def test_unsuccessful_apply_result_records_no_change(monkeypatch):
    monkeypatch.setattr(service_module, "run_tests", lambda repo_root, test_target="": _report(failing=["t::test_foo"]))
    agent = _FakeAgent()
    failed_apply = PatchApplyResult(success=False, applied_files=[], backup_dir=None, error="no changes found")
    loop = TestExecutionLoopService(
        agent, max_iterations=1,
        patch_service_factory=lambda repo_root: _FakePatchService(repo_root, apply_results=[failed_apply]),
    )

    result = loop.run(repo_root=Path("/repo"), index=_index())

    assert result.iterations[0].outcome == IterationOutcome.NO_CHANGE
    assert result.iterations[0].notes == "no changes found"


def test_pytest_failing_to_run_after_apply_triggers_rollback(monkeypatch):
    call_count = {"n": 0}

    def fake_run_tests(repo_root, test_target=""):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _report(failing=["t::test_foo"])
        raise TestRunError("pytest crashed")

    monkeypatch.setattr(service_module, "run_tests", fake_run_tests)
    agent = _FakeAgent()
    loop = TestExecutionLoopService(
        agent, max_iterations=1,
        patch_service_factory=lambda repo_root: _FakePatchService(repo_root, apply_results=[_ok_apply_result()]),
    )

    result = loop.run(repo_root=Path("/repo"), index=_index())

    assert result.iterations[0].outcome == IterationOutcome.RUN_FAILED
    assert len(_FakePatchService.instances[0].rollback_calls) == 1


def test_iteration_description_reflects_current_failure_state(monkeypatch):
    reports = iter([
        _report(failing=["tests/test_x.py::test_foo"]),
        _report(failing=["tests/test_x.py::test_foo"]),
        _report(failing=[]),
    ])
    monkeypatch.setattr(service_module, "run_tests", lambda repo_root, test_target="": next(reports))
    agent = _FakeAgent()
    apply_results = [_ok_apply_result(), _ok_apply_result()]
    loop = TestExecutionLoopService(
        agent, max_iterations=5,
        patch_service_factory=lambda repo_root: _FakePatchService(repo_root, apply_results=apply_results),
    )

    loop.run(repo_root=Path("/repo"), index=_index(), user_description="Fix the failing test")

    first_desc = agent.calls[0]["user_description"]
    second_desc = agent.calls[1]["user_description"]
    assert "Fix the failing test" in first_desc
    assert "tests/test_x.py::test_foo" in first_desc
    assert "AssertionError" in second_desc


def test_total_paritok_stats_sum_across_iterations(monkeypatch):
    reports = iter([_report(failing=["t::test_foo"]), _report(failing=[])])
    monkeypatch.setattr(service_module, "run_tests", lambda repo_root, test_target="": next(reports))
    agent = _FakeAgent()
    loop = TestExecutionLoopService(
        agent, max_iterations=5,
        patch_service_factory=lambda repo_root: _FakePatchService(repo_root, apply_results=[_ok_apply_result()]),
    )

    result = loop.run(repo_root=Path("/repo"), index=_index())

    assert result.total_paritok_tokens_saved == 100
    assert result.total_paritok_requests == 1