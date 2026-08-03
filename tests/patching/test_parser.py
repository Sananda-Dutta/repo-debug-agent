# tests/patching/test_parser.py
from repo_debug_agent.patching.models import PatchFormat
from repo_debug_agent.patching.parser import parse_fix_suggestion


def test_parses_full_file_block_with_hash_header():
    response = (
        "Root cause: off-by-one in the loop bound.\n\n"
        "### File: src/app.py\n"
        "```python\n"
        "def add(a, b):\n"
        "    return a + b\n"
        "```\n"
    )
    parsed = parse_fix_suggestion(response)

    assert len(parsed.file_changes) == 1
    change = parsed.file_changes[0]
    assert change.file_path == "src/app.py"
    assert change.format == PatchFormat.FULL_FILE
    assert change.new_content == "def add(a, b):\n    return a + b"


def test_parses_full_file_block_with_bold_header():
    response = (
        "**File:** src/util.py\n"
        "```python\n"
        "x = 1\n"
        "```\n"
    )
    parsed = parse_fix_suggestion(response)
    assert parsed.file_changes[0].file_path == "src/util.py"
    assert parsed.file_changes[0].format == PatchFormat.FULL_FILE


def test_parses_full_file_block_with_plain_header():
    response = (
        "File: src/util.py\n"
        "```python\n"
        "x = 2\n"
        "```\n"
    )
    parsed = parse_fix_suggestion(response)
    assert parsed.file_changes[0].file_path == "src/util.py"
    assert parsed.file_changes[0].new_content == "x = 2"


def test_parses_unified_diff_block_with_diff_language_tag():
    response = (
        "Root cause: wrong comparison operator.\n\n"
        "```diff\n"
        "--- a/src/app.py\n"
        "+++ b/src/app.py\n"
        "@@ -1,3 +1,3 @@\n"
        " def add(a, b):\n"
        "-    return a - b\n"
        "+    return a + b\n"
        "```\n"
    )
    parsed = parse_fix_suggestion(response)

    assert len(parsed.file_changes) == 1
    change = parsed.file_changes[0]
    assert change.file_path == "src/app.py"
    assert change.format == PatchFormat.UNIFIED_DIFF
    assert "+    return a + b" in change.diff_text


def test_parses_unified_diff_without_explicit_diff_tag():
    response = (
        "```\n"
        "--- a/src/app.py\n"
        "+++ b/src/app.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
        "```\n"
    )
    parsed = parse_fix_suggestion(response)
    assert parsed.file_changes[0].format == PatchFormat.UNIFIED_DIFF
    assert parsed.file_changes[0].file_path == "src/app.py"


def test_multi_file_diff_block_splits_into_separate_changes():
    response = (
        "```diff\n"
        "--- a/src/a.py\n"
        "+++ b/src/a.py\n"
        "@@ -1 +1 @@\n"
        "-1\n"
        "+2\n"
        "--- a/src/b.py\n"
        "+++ b/src/b.py\n"
        "@@ -1 +1 @@\n"
        "-3\n"
        "+4\n"
        "```\n"
    )
    parsed = parse_fix_suggestion(response)
    paths = {c.file_path for c in parsed.file_changes}
    assert paths == {"src/a.py", "src/b.py"}


def test_multiple_full_file_blocks_in_one_response():
    response = (
        "### File: src/a.py\n```python\na = 1\n```\n\n"
        "### File: src/b.py\n```python\nb = 2\n```\n"
    )
    parsed = parse_fix_suggestion(response)
    paths = {c.file_path for c in parsed.file_changes}
    assert paths == {"src/a.py", "src/b.py"}


def test_code_block_with_no_attached_header_is_ignored():
    response = "Here's an example:\n```python\nprint('hi')\n```\n"
    parsed = parse_fix_suggestion(response)
    assert parsed.file_changes == []


def test_pure_prose_response_yields_no_changes():
    response = "I think the bug is in the retry logic, but I need more context."
    parsed = parse_fix_suggestion(response)
    assert parsed.file_changes == []


def test_raw_source_is_preserved():
    response = "### File: a.py\n```python\nx = 1\n```\n"
    parsed = parse_fix_suggestion(response)
    assert parsed.raw_source == response