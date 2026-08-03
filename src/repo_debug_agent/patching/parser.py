"""
Phase 10: parse Phase 9's raw LLM fix-suggestion text into structured,
per-file changes ready to apply.

Deliberately lenient about the exact markdown the LLM used, since we
don't want a brittle parser silently producing nothing for a
reasonable-looking response. Recognizes two shapes:

  1. FULL-FILE replacement: a file-path header (several common forms
     accepted — see _HEADER_PATTERNS) immediately followed by a fenced
     code block containing that file's COMPLETE new content.
  2. UNIFIED DIFF: a fenced ```diff or ```patch block (or an unfenced
     block that already looks like a unified diff), containing
     standard `--- a/<path>` / `+++ b/<path>` / `@@ ... @@` hunks —
     possibly covering multiple files in one block.

Anything else (prose, code blocks with no attached file path) is
ignored — Phase 10 would rather apply nothing than guess wrong; the
caller (PatchService.parse) turns "nothing parsed" into a clear error.
"""

from __future__ import annotations

import re

from repo_debug_agent.patching.models import FileChange, ParsedPatch, PatchFormat

# A generic fenced code block: ```<optional language>\n<content>```
_FENCE = re.compile(r"```(?P<lang>[\w+-]*)\n(?P<content>.*?)```", re.DOTALL)

# File-path headers we recognize immediately before a fenced block,
# e.g. "### File: src/app.py", "**File:** src/app.py", "File: src/app.py"
_HEADER_PATTERNS = [
    re.compile(r"^#{1,6}\s*File:\s*(?P<path>\S+)\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\*\*File:?\*\*:?\s*`?(?P<path>[^\s`]+)`?\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^File:\s*`?(?P<path>[^\s`]+)`?\s*$", re.MULTILINE | re.IGNORECASE),
]

_DIFF_LANGS = {"diff", "patch"}
_DIFF_FILE_HEADER = re.compile(r"^\+\+\+ b/(?P<path>\S+)", re.MULTILINE)
_LOOKS_LIKE_DIFF = re.compile(r"^--- a/\S+", re.MULTILINE)


def parse_fix_suggestion(raw_response: str) -> ParsedPatch:
    """Extract every FileChange this response describes. Order of
    detection matters: a fenced block is claimed by whichever
    detector recognizes it first, so a fence isn't double-counted."""
    claimed_spans: list[tuple[int, int]] = []
    file_changes: list[FileChange] = []

    for match in _FENCE.finditer(raw_response):
        lang = match.group("lang").lower()
        content = match.group("content")

        if lang in _DIFF_LANGS or _LOOKS_LIKE_DIFF.search(content):
            file_changes.extend(_parse_diff_block(content))
            claimed_spans.append(match.span())
            continue

        header_path = _find_preceding_header(raw_response, match.start())
        if header_path is not None:
            file_changes.append(_full_file_change(header_path, content))
            claimed_spans.append(match.span())

    return ParsedPatch(file_changes=file_changes, raw_source=raw_response)


def _full_file_change(path: str, content: str) -> FileChange:
    # Fenced content ends with a trailing newline before the closing
    # fence in well-formed markdown; drop exactly one so we don't
    # silently introduce a phantom blank line at EOF.
    if content.endswith("\n"):
        content = content[:-1]
    return FileChange(file_path=path, format=PatchFormat.FULL_FILE, new_content=content)


def _find_preceding_header(text: str, fence_start: int) -> str | None:
    """Look at the text immediately before a fence for a recognized
    file-path header. Only considers the nearest ~200 chars so an
    unrelated header far earlier in the response isn't mistakenly
    attached to this fence."""
    window = text[max(0, fence_start - 200):fence_start]
    best_path: str | None = None
    best_pos = -1
    for pattern in _HEADER_PATTERNS:
        for match in pattern.finditer(window):
            if match.start() > best_pos:
                best_pos = match.start()
                best_path = match.group("path")
    return best_path


def _parse_diff_block(diff_text: str) -> list[FileChange]:
    changes = []
    for file_diff in _split_multi_file_diff(diff_text):
        path_match = _DIFF_FILE_HEADER.search(file_diff)
        if not path_match:
            continue
        changes.append(FileChange(
            file_path=path_match.group("path").strip(),
            format=PatchFormat.UNIFIED_DIFF,
            diff_text=file_diff,
        ))
    return changes


def _split_multi_file_diff(diff_text: str) -> list[str]:
    """Split one diff block into per-file diffs, on '--- a/' boundaries."""
    parts = re.split(r"(?=^--- a/)", diff_text, flags=re.MULTILINE)
    return [p for p in parts if p.strip()]