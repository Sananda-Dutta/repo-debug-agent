# tests/failure_analysis/test_service.py
from repo_debug_agent.failure_analysis.service import FailureAnalysisService

SAMPLE_TB = """Traceback (most recent call last):
  File "/app/utils.py", line 20, in helper
    raise RuntimeError("boom")
RuntimeError: boom
"""


def test_analyze_pasted_traceback():
    service = FailureAnalysisService()
    parsed = service.analyze_pasted_traceback(SAMPLE_TB)
    assert parsed.exception_type == "RuntimeError"
    assert parsed.message == "boom"


def test_run_and_analyze_tests(tmp_path):
    (tmp_path / "test_x.py").write_text("def test_bad():\n    assert False\n")
    service = FailureAnalysisService()
    report = service.run_and_analyze_tests(tmp_path)
    assert report.has_failures is True