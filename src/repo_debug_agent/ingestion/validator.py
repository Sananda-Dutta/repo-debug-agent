"""
Post-clone sanity checks.

Zero network I/O. Only filesystem reads. This guards against the
"clone succeeded but repo is empty/corrupted/not actually code"
class of silent failures that would otherwise surface confusingly
in Phase 3 (indexing) as "found 0 files to parse."
"""

from pathlib import Path

from repo_debug_agent.exceptions import RepoValidationError

_MIN_EXPECTED_FILES = 1


def validate_repo(local_path: Path) -> None:
    """
    Raise RepoValidationError if the local repo checkout looks invalid.

    Checks:
    1. Directory exists.
    2. Directory is not empty.
    3. Contains at least one file with a recognizable source-code extension
       (a very cheap heuristic to catch "this is just a README, not code").
    """
    if not local_path.exists() or not local_path.is_dir():
        raise RepoValidationError(f"Path does not exist or is not a directory: {local_path}")

    all_files = [p for p in local_path.rglob("*") if p.is_file() and ".git" not in p.parts]
    if len(all_files) < _MIN_EXPECTED_FILES:
        raise RepoValidationError(f"Repo at {local_path} appears empty (0 files found).")

    code_extensions = {".py", ".js", ".ts", ".java", ".go", ".rb", ".cpp", ".c", ".rs", ".jsx", ".tsx"}
    has_code = any(p.suffix in code_extensions for p in all_files)
    if not has_code:
        raise RepoValidationError(
            f"Repo at {local_path} contains files but none match known source-code extensions. "
            "This may not be a code repository."
        )