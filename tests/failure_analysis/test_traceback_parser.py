# tests/failure_analysis/test_traceback_parser.py
from repo_debug_agent.failure_analysis.traceback_parser import parse_traceback

SIMPLE_TB = """Traceback (most recent call last):
  File "/app/main.py", line 10, in run
    result = compute(5)
  File "/app/compute.py", line 3, in compute
    return 10 / x
ZeroDivisionError: division by zero
"""

CHAINED_TB = """Traceback (most recent call last):
  File "/app/a.py", line 1, in first
    raise ValueError("first error")
ValueError: first error

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/app/b.py", line 5, in second
    raise KeyError("second error")
KeyError: 'second error'
"""


def test_parse_simple_traceback():
    parsed = parse_traceback(SIMPLE_TB)
    assert parsed.exception_type == "ZeroDivisionError"
    assert parsed.message == "division by zero"
    assert len(parsed.frames) == 2
    assert parsed.frames[0].file_path == "/app/main.py"
    assert parsed.frames[0].function_name == "run"
    assert parsed.frames[0].code_line == "result = compute(5)"
    assert parsed.innermost_frame.function_name == "compute"


def test_parse_chained_traceback_uses_final_block():
    parsed = parse_traceback(CHAINED_TB)
    assert parsed.exception_type == "KeyError"
    assert len(parsed.frames) == 1
    assert parsed.frames[0].function_name == "second"


def test_parse_no_traceback_returns_none():
    assert parse_traceback("just some random log output, nothing relevant here") is None


def test_parse_empty_string_returns_none():
    assert parse_traceback("") is None