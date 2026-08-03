"""
PatchService: single public entrypoint for Phase 10.

Turns Phase 9's raw LLM fix suggestion into applied changes on disk,
with automatic backup so a caller (Phase 11's future test-execution
loop) can roll back a fix that doesn't actually fix the failure.

This keeps the rest of your project from needing to understand all the internal patching machinery.
"""

from __future__ import annotations

from pathlib import Path

from repo_debug_agent.agent.models import FixSuggestion
from repo_debug_agent.core.logger import logger
from repo_debug_agent.exceptions import PatchParsingError
from repo_debug_agent.patching.applicator import PatchApplicator
from repo_debug_agent.patching.models import ParsedPatch, PatchApplyResult
from repo_debug_agent.patching.parser import parse_fix_suggestion


class PatchService:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self._applicator = PatchApplicator(repo_root)

    def parse(self, fix_suggestion: FixSuggestion) -> ParsedPatch:
        """Parse only — no filesystem changes. Useful for previewing a fix
        before deciding whether to apply it."""
        parsed = parse_fix_suggestion(fix_suggestion.raw_response)
        if not parsed.file_changes:
            raise PatchParsingError(
                "Could not parse any applicable file change out of the LLM's fix "
                "suggestion. Expected a 'File: <path>' header followed by a fenced "
                "code block, or a fenced ```diff block."
            )
        logger.info(f"Parsed {len(parsed.file_changes)} file change(s) from fix suggestion.")
        return parsed

    def apply(self, fix_suggestion: FixSuggestion) -> PatchApplyResult:
        """Parse AND apply to `repo_root`, with automatic backup."""
        parsed = self.parse(fix_suggestion)
        return self._applicator.apply(parsed)

    def rollback(self, result: PatchApplyResult) -> None:
        self._applicator.rollback(result)