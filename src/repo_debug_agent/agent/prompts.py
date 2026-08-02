"""
Prompt templates for Phase 9's fix-suggestion node.

Kept deliberately simple: Phase 9's job is to produce a raw LLM fix
suggestion grounded in the localized, compressed context. Parsing that
suggestion into an applicable, verifiable patch is Phase 10's job.
"""

from repo_debug_agent.failure_analysis.models import ParsedException

SYSTEM_PROMPT = (
    "You are an expert software engineer debugging a real codebase. "
    "You are given a description of a failure and a curated, "
    "token-budgeted set of the most relevant source files/symbols. "
    "Propose a specific, minimal fix. Reference exact file paths and "
    "function/class names from the provided context — do not invent "
    "files or symbols that were not shown to you. First explain the "
    "root cause in 1-2 sentences, then give the fix as a unified diff "
    "or a clearly-marked before/after code block."
)


def summarize_failure(exception: ParsedException | None, user_description: str) -> str:
    """Build a short, LLM-readable failure summary from Phase 6's parsed
    exception (if any) and/or free-text user description."""
    parts: list[str] = []
    if exception is not None:
        parts.append(f"{exception.exception_type}: {exception.message}")
        frame = exception.innermost_frame
        if frame is not None:
            parts.append(f"Raised at {frame.file_path}:{frame.line_number} in {frame.function_name}")
    if user_description:
        parts.append(user_description)
    return "\n".join(parts) if parts else "No structured failure info was provided."


def build_user_prompt(failure_summary: str, assembled_context: str) -> str:
    return (
        f"## Failure\n{failure_summary}\n\n"
        f"## Relevant code context\n{assembled_context}\n\n"
        "## Task\nDiagnose the root cause and propose a fix."
    )