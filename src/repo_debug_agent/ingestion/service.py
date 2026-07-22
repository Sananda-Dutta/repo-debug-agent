"""
RepoIngestionService: the single public entrypoint for Phase 2.

Every other phase should import and call THIS, not the individual
resolver/cloner/validator modules directly. This keeps the internal
wiring (resolve -> clone -> validate -> fetch metadata) replaceable
without breaking callers.
"""

from pathlib import Path

from github import Github, GithubException

from repo_debug_agent.config.settings import get_settings
from repo_debug_agent.core.logger import logger
from repo_debug_agent.exceptions import IngestionError
from repo_debug_agent.ingestion.cloner import clone_repo
from repo_debug_agent.ingestion.models import RepoMetadata, SourceKind
from repo_debug_agent.ingestion.source_resolver import resolve_source
from repo_debug_agent.ingestion.validator import validate_repo

import git


class RepoIngestionService:
    """Orchestrates resolving, cloning, validating, and describing a repo."""

    def __init__(self, workspace_dir: Path | None = None, github_token: str | None = None):
        settings = get_settings()
        self.workspace_dir = workspace_dir or Path(settings.workspace_dir)
        self.github_token = github_token if github_token is not None else settings.github_token

    def ingest(self, raw_input: str, ref: str | None = None, force: bool = False) -> RepoMetadata:
        """
        Full ingestion pipeline: resolve -> clone/reuse -> validate -> metadata.

        `force=True` deletes any existing checkout at the target path and
        re-clones from scratch (escape hatch for corrupted checkouts).
        """
        source = resolve_source(raw_input, ref=ref)
        logger.info(f"Resolved source: kind={source.kind}, raw='{source.raw_input}'")

        if source.kind == SourceKind.LOCAL_PATH:
            local_path = source.local_path
            validate_repo(local_path)
            return self._build_metadata_from_local(local_path)

        owner, repo_name = self._extract_owner_repo(source.clone_url)
        destination = self.workspace_dir / f"{owner}__{repo_name}"

        if force and destination.exists():
            import shutil
            logger.warning(f"force=True: removing existing checkout at {destination}")
            shutil.rmtree(destination)

        try:
            local_path = clone_repo(source, destination, github_token=self.github_token)
        except IngestionError:
            raise
        except Exception as exc:  # noqa: BLE001 - defensive boundary, we re-raise as domain error
            raise IngestionError(f"Unexpected ingestion failure for '{raw_input}': {exc}") from exc

        validate_repo(local_path)
        return self._build_metadata(local_path, owner, repo_name)

    def _build_metadata(self, local_path: Path, owner: str, repo_name: str) -> RepoMetadata:
        git_repo = git.Repo(local_path)
        commit_sha = git_repo.head.commit.hexsha

        is_private, default_branch, size_kb = False, git_repo.active_branch.name, 0
        try:
            gh = Github(self.github_token) if self.github_token else Github()
            gh_repo = gh.get_repo(f"{owner}/{repo_name}")
            is_private = gh_repo.private
            default_branch = gh_repo.default_branch
            size_kb = gh_repo.size
        except GithubException as exc:
            logger.warning(f"Could not fetch GitHub API metadata for {owner}/{repo_name}: {exc}. "
                            "Continuing with local-only metadata.")

        return RepoMetadata(
            owner=owner,
            name=repo_name,
            local_path=local_path,
            commit_sha=commit_sha,
            default_branch=default_branch,
            is_private=is_private,
            size_kb=size_kb,
        )

    def _build_metadata_from_local(self, local_path: Path) -> RepoMetadata:
        git_repo = git.Repo(local_path)
        commit_sha = git_repo.head.commit.hexsha
        default_branch = git_repo.active_branch.name
        return RepoMetadata(
            owner="local",
            name=local_path.name,
            local_path=local_path,
            commit_sha=commit_sha,
            default_branch=default_branch,
            is_private=False,
            size_kb=0,
        )

    @staticmethod
    def _extract_owner_repo(clone_url: str) -> tuple[str, str]:
        # clone_url is always "https://github.com/<owner>/<repo>.git" by construction
        parts = clone_url.removesuffix(".git").split("/")
        return parts[-2], parts[-1]