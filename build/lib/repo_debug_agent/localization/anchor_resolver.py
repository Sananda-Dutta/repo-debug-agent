"""
Resolves a stack frame (file path + line number, from Phase 6) into an
EXACT CodeSymbol from the CodebaseIndex (Phase 3) — i.e., not just
the failure was in this file" but "the failure was in THIS function.

This is what lets downstream phases retrieve exactly the failing
function's body instead of an entire (possibly huge) file.
"""

from repo_debug_agent.failure_analysis.models import StackFrame
from repo_debug_agent.indexing.models import CodebaseIndex, CodeSymbol


def resolve_anchor_symbol(frame: StackFrame, index: CodebaseIndex, repo_root: str) -> CodeSymbol | None:
    """
    Given a stack frame, find the CodeSymbol in the index whose file
    matches and whose [start_line, end_line] range contains the frame's
    line number.

    Returns None if the file isn't in our index (e.g. it's a
    third-party library frame, not repo code — common for the outer
    frames of a traceback, see Phase 6's pytest-internals example).
    """
    relative_path = _to_relative_path(frame.file_path, repo_root)
    if relative_path is None:
        return None

    file_idx = index.get_file(relative_path)
    if file_idx is None:
        return None

    # Prefer the MOST SPECIFIC enclosing symbol — a method's range is
    # nested inside its class's range, so if both match, the method
    # (smaller range) is the more precise answer.
    candidates = [
        sym for sym in file_idx.symbols
        if sym.start_line <= frame.line_number <= sym.end_line
    ]
    if not candidates:
        return None

    return min(candidates, key=lambda s: s.end_line - s.start_line)


def resolve_anchor_file(frame: StackFrame, index: CodebaseIndex, repo_root: str) -> str | None:
    """Convenience: just the relative file path, without requiring symbol resolution to succeed."""
    return _to_relative_path(frame.file_path, repo_root)


def _to_relative_path(absolute_or_frame_path: str, repo_root: str) -> str | None:
    """
    Convert a stack frame's file path (always absolute, as printed by
    Python) into a repo-relative path matching CodebaseIndex keys.
    Returns None if the path isn't actually inside repo_root (i.e. it's
    a stdlib/site-packages/third-party frame).
    """
    normalized_root = repo_root.rstrip("/") + "/"
    if not absolute_or_frame_path.startswith(normalized_root):
        return None
    return absolute_or_frame_path[len(normalized_root):]