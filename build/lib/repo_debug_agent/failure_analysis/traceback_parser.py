"""
Parses raw stack trace text (standard Python `Traceback (most recent
call last):` format) into a structured ParsedException.

This is a pure, dependency-free parser — zero I/O, fully unit-testable
with plain strings. It is used by BOTH input paths: a user-pasted
trace, and pytest's own `--tb=native` output (Phase 6 deliberately
forces pytest into this same standard format so we only maintain ONE
parsing grammar — see Phase 6 design notes).

Frame/code-context/caret-decoration lines are always INDENTED; the
final exception type/message line is always UNINDENTED (column 0).
We rely on that structural fact to find the boundary between "call
stack" and "exception header" — not content pattern-matching, which
is unreliable (an ordinary source line like `result: TResult = func()`
looks exactly like an "ExceptionType: message" header by content
alone, but is clearly not one once indentation is considered).

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
_CARET_DECORATION_LINE = re.compile(r"^[\^~\s]+$")  # PEP 657 fine-grained error location markers


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


def _is_decoration_line(line: str) -> bool:
    return bool(line.strip()) and bool(_CARET_DECORATION_LINE.match(line))


def _is_indented(line: str) -> bool:
    return line.startswith(" ") or line.startswith("\t")


def _parse_frames(lines: list[str], start: int) -> tuple[list[StackFrame], int]:
    """
    Walk lines from `start`, collecting StackFrame entries.

    Uses indentation (not content-sniffing) to decide where the frame
    stack ends and the exception header begins.
    """
    frames: list[StackFrame] = []
    i = start

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        frame_match = _FRAME_LINE.match(line)
        if not frame_match:
            if not _is_indented(line):
                break  # unindented, non-frame line = start of exception header
            i += 1      # stray indented line with no owning frame; skip defensively
            continue

        i += 1
        code_line = None

        # Consume this frame's indented source-context / caret lines,
        # stopping at the next frame line OR the first unindented line.
        while i < len(lines):
            nxt = lines[i]
            if not nxt.strip():
                i += 1
                continue
            if not _is_indented(nxt):
                break
            if _FRAME_LINE.match(nxt):
                break
            if _is_decoration_line(nxt):
                i += 1
                continue
            if code_line is None:
                code_line = nxt.strip()
            i += 1

        frames.append(StackFrame(
            file_path=frame_match.group("file"),
            line_number=int(frame_match.group("line")),
            function_name=frame_match.group("func"),
            code_line=code_line,
        ))

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