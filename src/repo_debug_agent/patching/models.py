"""
Data models for Fix Suggestion & Patching (Phase 10).

"What exactly are we going to change?"
"""

from enum import Enum

from pydantic import BaseModel, Field


class PatchFormat(str, Enum):
    """How one file's change was expressed by the LLM."""

    FULL_FILE = "full_file"  # LLM gave the file's complete new content
    UNIFIED_DIFF = "unified_diff"  # LLM gave a standard unified-diff hunk


class FileChange(BaseModel):
    """One file's proposed change, in whichever format the LLM used."""

    file_path: str = Field(description="Path relative to the repo root")
    format: PatchFormat
    new_content: str | None = Field(default=None, description="Set when format is FULL_FILE")
    diff_text: str | None = Field(default=None, description="Set when format is UNIFIED_DIFF")


class ParsedPatch(BaseModel):
    """All file changes extracted from one Phase 9 fix suggestion."""

    file_changes: list[FileChange]
    raw_source: str = Field(description="The raw_response this was parsed from, for traceability")


class AppliedFile(BaseModel):
    """Bookkeeping for one applied file change, enough to roll it back."""

    file_path: str
    backup_path: str = Field(description="Where the pre-patch content was backed up")
    existed_before: bool = Field(description="False means this patch CREATED the file — rollback deletes it")


class PatchApplyResult(BaseModel):
    """Outcome of applying a ParsedPatch to a real checkout."""

    success: bool
    applied_files: list[AppliedFile]
    backup_dir: str | None = Field(default=None, description="Directory holding all backups for this apply, for rollback")
    error: str | None = None