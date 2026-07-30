"""
Parses raw stack trace text (standard Python `Traceback (most recent
call last):` format) into a structured ParsedException.

This is a pure, dependency-free regex state machine — zero I/O, fully
unit-testable with plain strings. It is used by BOTH input paths:
a user-pasted trace, and pytest's own `--tb=native` output (Phase 6
deliberately forces pytest into this same standard format so we only
maintain ONE parsing grammar — see Phase 6 design notes).

Scope boundary (documented, not a bug): if the text contains chained
exceptions ("During handling of the above exception..." / "The above
exception was the direct cause..."), we parse only the FINAL traceback
block — the exception that actually terminated execution.
"""

import re

from repo_debug_agent.failure_analysis.models import ParsedException, StackFrame

_TRACEBACK_HEADER = re.compile(r"^Traceback \(most recent call last\):\s*$")
_FRAME_LINE = re.compile(r'^\s*File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>.+?)\s*$')
_EXCEPTION_HEADER = re.compile(r"^(?P<exc_type>[A-Za-z_][\w.]*)\s*:\s*(?P<message>.*)$")
_BARE_EXCEPTION = re.compile(r"^(?P<exc_type>[A-Za-z_][\w.]*)\s*$")  # e.g. bare "StopIteration"


def parse_traceback(raw_text: str) -> ParsedException | None:
    """
    Parse `raw_text` into a ParsedException, or None if no recognizable
    traceback block is found at all (e.g. the text is unrelated noise).
    """
    if not raw_text:
        return None

    lines = raw_text.splitlines()
    header_indices = [i for i, line in enumerate(lines) if _TRACEBACK_HEADER.match(line)]
    if not header_indices:
        return None

    start = header_indices[-1] + 1  # only the LAST (most recent) traceback block
    frames, exception_start_idx = _parse_frames(lines, start)
    exc_type, message = _parse_exception_header(lines, exception_start_idx)

    return ParsedException(
        exception_type=exc_type,
        message=message,
        frames=frames,
        raw_traceback=raw_text,
    )


def _parse_frames(lines: list[str], start: int) -> tuple[list[StackFrame], int]:
    """
    Walk lines from `start`, collecting StackFrame entries until we hit
    a line that isn't a "File ..." line and isn't a source-code context
    line (i.e. we've reached the exception type/message).

    Returns (frames, index_where_exception_header_begins).
    """
    frames: list[StackFrame] = []
    i = start

    while i < len(lines):
        frame_match = _FRAME_LINE.match(lines[i])
        if not frame_match:
            if lines[i].strip():
                break  # first non-frame, non-blank line = start of exception header
            i += 1
            continue

        code_line = None
        next_i = i + 1
        if next_i < len(lines):
            candidate = lines[next_i]
            is_another_frame = bool(_FRAME_LINE.match(candidate))
            is_exception_header = bool(_EXCEPTION_HEADER.match(candidate.strip()))
            if candidate.strip() and not is_another_frame and not is_exception_header:
                code_line = candidate.strip()
                i = next_i  # consumed as this frame's source line

        frames.append(StackFrame(
            file_path=frame_match.group("file"),
            line_number=int(frame_match.group("line")),
            function_name=frame_match.group("func"),
            code_line=code_line,
        ))
        i += 1

    return frames, i


def _parse_exception_header(lines: list[str], start: int) -> tuple[str, str]:
    """Extract exception type + message from the lines following the frame stack."""
    exception_lines = []
    i = start
    while i < len(lines) and lines[i].strip():
        exception_lines.append(lines[i].strip())
        i += 1

    if not exception_lines:
        return "UnknownError", ""

    first = exception_lines[0]
    header_match = _EXCEPTION_HEADER.match(first)
    if header_match:
        exc_type = header_match.group("exc_type")
        message_parts = [header_match.group("message")] + exception_lines[1:]
        return exc_type, " ".join(p for p in message_parts if p).strip()

    bare_match = _BARE_EXCEPTION.match(first)
    if bare_match:
        return bare_match.group("exc_type"), " ".join(exception_lines[1:]).strip()

    return "UnknownError", " ".join(exception_lines).strip()