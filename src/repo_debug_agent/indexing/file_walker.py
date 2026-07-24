"""
Walks a repository directory, respecting .gitignore, and excludes
binary/vendor/build directories that would waste parsing time and
add noise (node_modules, .git, __pycache__, dist, build, venv, etc.)

Design note: we ALWAYS exclude a hardcoded set of noise directories
even if .gitignore doesn't list them (e.g. .git itself is never
gitignored but must never be walked).
"""

from pathlib import Path
import pathspec

from repo_debug_agent.core.logger import logger

_ALWAYS_EXCLUDED_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".pytest_cache", ".mypy_cache", "vendor",
    ".tox", "egg-info",
}

_MAX_FILE_SIZE_BYTES = 2_000_000  # 2 MB — skip generated/minified/data files


def _load_gitignore_spec(repo_root: Path) -> pathspec.PathSpec:
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])
    lines = gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def walk_repo_files(repo_root: Path) -> list[Path]:
    """
    Return all source-relevant files in the repo, excluding noise
    directories, gitignored files, and oversized files.
    """
    spec = _load_gitignore_spec(repo_root)
    result: list[Path] = []

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _ALWAYS_EXCLUDED_DIRS for part in path.parts):
            continue

        relative = path.relative_to(repo_root)
        if spec.match_file(str(relative)):
            continue

        try:
            if path.stat().st_size > _MAX_FILE_SIZE_BYTES:
                logger.debug(f"Skipping oversized file: {relative}")
                continue
        except OSError:
            continue

        result.append(path)

    logger.info(f"File walk complete: {len(result)} files found under {repo_root}")
    return result