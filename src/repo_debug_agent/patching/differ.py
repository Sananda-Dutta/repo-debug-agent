"""
Phase 10: unified-diff generation helper.

Used to produce a human-readable diff for FULL_FILE changes (which
arrive as raw new content, not an already-formed diff) — purely for
reporting/logging (e.g. a future Phase 12 dashboard showing what
changed), not for applying anything.

This one is for visualizing/reporting the change.
"""

import difflib


def unified_diff(file_path: str, original_text: str, new_text: str) -> str:
    original_lines = original_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff_lines = difflib.unified_diff(
        original_lines, new_lines,
        fromfile=f"a/{file_path}", tofile=f"b/{file_path}",
    )
    return "".join(diff_lines)