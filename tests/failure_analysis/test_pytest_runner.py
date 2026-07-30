# tests/failure_analysis/test_pytest_runner.py
"""
Runs a REAL pytest subprocess against a tiny generated test file.
Requires pytest-json-report installed in this dev environment (it is,
per pyproject.toml runtime deps).
"""

from repo_debug_agent.failure_analysis.pytest_runner import run_tests


def test_run_tests_reports_pass_and_fail(tmp_path):
    (tmp_path / "test_sample.py").write_text(
        "def test_passes():\n"
        "    assert 1 == 1\n"
        "\n"
        "def test_fails():\n"
        "    assert 1 == 2\n"
    )

    report = run_tests(tmp_path)

    assert report.total_tests == 2
    assert report.passed == 1
    assert report.failed == 1
    assert report.has_failures is True

    failure = report.failures[0]
    assert "test_fails" in failure.node_id
    assert failure.exception is not None
    assert failure.exception.exception_type == "AssertionError"


def test_run_tests_all_pass(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    report = run_tests(tmp_path)
    assert report.has_failures is False
    assert report.failed == 0