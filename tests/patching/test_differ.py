# tests/patching/test_differ.py
from repo_debug_agent.patching.differ import unified_diff


def test_unified_diff_shows_added_and_removed_lines():
    original = "def add(a, b):\n    return a - b\n"
    new = "def add(a, b):\n    return a + b\n"

    diff = unified_diff("src/app.py", original, new)

    assert "--- a/src/app.py" in diff
    assert "+++ b/src/app.py" in diff
    assert "-    return a - b" in diff
    assert "+    return a + b" in diff


def test_unified_diff_is_empty_for_identical_content():
    text = "same content\n"
    assert unified_diff("src/app.py", text, text) == ""