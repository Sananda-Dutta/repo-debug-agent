"""
Resolves arbitrary user input (URL, "owner/repo" shorthand, or local
filesystem path) into a normalized RepoSource.

This module performs ZERO network I/O and ZERO filesystem mutation.
It only reads (os.path.exists / Path.is_dir) to distinguish "this is
a local path" from "this is a remote reference" — making it trivially
unit-testable without mocks.
"""

import re
from pathlib import Path

from repo_debug_agent.exceptions import InvalidRepoSourceError
from repo_debug_agent.ingestion.models import RepoSource, SourceKind

# Matches https://github.com/owner/repo(.git)?  and git@github.com:owner/repo(.git)?
_GITHUB_URL_PATTERN = re.compile(
    r"^(https://github\.com/|git@github\.com:)"
    r"(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(\.git)?/?$"
)

# Matches "owner/repo" shorthand, e.g. "psf/requests"
_SHORTHAND_PATTERN = re.compile(r"^(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)$")


def resolve_source(raw_input: str, ref: str | None = None) -> RepoSource:
    """
    Turn user input into a normalized RepoSource.

    Resolution order (first match wins):
    1. Existing local filesystem path
    2. Full GitHub URL (https:// or git@)
    3. "owner/repo" shorthand

    Raises InvalidRepoSourceError if none match.
    """
    raw_input = raw_input.strip()

    local_candidate = Path(raw_input).expanduser()
    if local_candidate.exists() and local_candidate.is_dir():
        return RepoSource(
            kind=SourceKind.LOCAL_PATH,
            raw_input=raw_input,
            local_path=local_candidate.resolve(),
            ref=ref,
        )

    url_match = _GITHUB_URL_PATTERN.match(raw_input)
    if url_match:
        owner, repo = url_match.group("owner"), url_match.group("repo")
        return RepoSource(
            kind=SourceKind.REMOTE_URL,
            raw_input=raw_input,
            clone_url=f"https://github.com/{owner}/{repo}.git",
            ref=ref,
        )

    shorthand_match = _SHORTHAND_PATTERN.match(raw_input)
    if shorthand_match:
        owner, repo = shorthand_match.group("owner"), shorthand_match.group("repo")
        return RepoSource(
            kind=SourceKind.SHORTHAND,
            raw_input=raw_input,
            clone_url=f"https://github.com/{owner}/{repo}.git",
            ref=ref,
        )

    raise InvalidRepoSourceError(
        f"Could not resolve '{raw_input}' as a local path, GitHub URL, or 'owner/repo' shorthand."
    )