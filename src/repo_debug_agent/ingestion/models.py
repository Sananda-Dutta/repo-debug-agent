"""
Data models for the ingestion phase.

RepoSource: normalized representation of "what the user asked us to debug."
RepoMetadata: normalized representation of "what we actually got on disk."

Keeping these separate (input intent vs. resolved fact) is deliberate:
RepoSource can be wrong/ambiguous; RepoMetadata is only ever produced
after a successful, validated clone.
"""

from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field


class SourceKind(str, Enum):
    """How the repo was originally specified by the user."""

    REMOTE_URL = "remote_url"
    SHORTHAND = "shorthand"       # e.g. "owner/repo"
    LOCAL_PATH = "local_path"     # already exists on disk


class RepoSource(BaseModel):
    """Normalized description of where a repo comes from, before cloning."""

    kind: SourceKind
    raw_input: str = Field(description="Exactly what the user typed")
    clone_url: str | None = Field(default=None, description="HTTPS clone URL, if remote")
    local_path: Path | None = Field(default=None, description="Filesystem path, if local")
    ref: str | None = Field(default=None, description="Branch, tag, or commit the user requested")


class RepoMetadata(BaseModel):
    """Facts about a repo AFTER it has been successfully ingested onto disk."""

    owner: str
    name: str
    local_path: Path
    commit_sha: str
    default_branch: str
    is_private: bool
    size_kb: int = Field(description="Repo size in KB as reported by GitHub API, 0 if unknown/local-only")

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"