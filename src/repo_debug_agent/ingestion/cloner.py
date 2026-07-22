"""
Handles the actual git clone operation via GitPython.

This is the ONLY module in the ingestion package that touches the
network or mutates the filesystem by cloning. Isolating it here means
tests for source_resolver.py and validator.py never need network mocks —
only tests targeting THIS module do.
"""

from pathlib import Path

import git
from git.exc import GitCommandError

from repo_debug_agent.core.logger import logger
from repo_debug_agent.exceptions import CloneFailedError
from repo_debug_agent.ingestion.models import RepoSource


def clone_repo(source: RepoSource, destination: Path, github_token: str = "") -> Path:
    """
    Clone `source.clone_url` into `destination`.

    If `destination` already exists and contains a valid git repo,
    we skip cloning and just fetch/checkout the requested ref
    (cheap re-use instead of re-downloading everything).

    Returns the path to the cloned repo (== destination).
    """
    if destination.exists() and (destination / ".git").exists():
        logger.info(f"Reusing existing checkout at {destination}")
        repo = git.Repo(destination)
        _fetch_and_checkout(repo, source.ref)
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)

    clone_url = source.clone_url
    if github_token and clone_url and clone_url.startswith("https://"):
        # Inject token for private-repo auth without ever logging it.
        clone_url = clone_url.replace("https://", f"https://{github_token}@")

    logger.info(f"Cloning {source.raw_input} into {destination}")
    try:
        repo = git.Repo.clone_from(clone_url, destination, depth=1 if not source.ref else None)
    except GitCommandError as exc:
        # Strip any embedded token from the error message before it hits logs.
        safe_msg = str(exc).replace(github_token, "***") if github_token else str(exc)
        raise CloneFailedError(f"Failed to clone '{source.raw_input}': {safe_msg}") from exc

    if source.ref:
        _fetch_and_checkout(repo, source.ref)

    return destination


def _fetch_and_checkout(repo: git.Repo, ref: str | None) -> None:
    """Fetch latest refs and checkout a specific branch/tag/commit if requested."""
    if not ref:
        return
    try:
        repo.remotes.origin.fetch()
        repo.git.checkout(ref)
    except GitCommandError as exc:
        raise CloneFailedError(f"Failed to checkout ref '{ref}': {exc}") from exc