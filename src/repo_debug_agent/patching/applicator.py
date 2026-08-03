"""
Phase 10: applies a ParsedPatch to a real git checkout.

FULL_FILE changes are applied by writing the new content directly —
reliable, no hunk-matching to fail on. UNIFIED_DIFF changes are applied
via `git apply`, since Phase 2 guarantees `repo_root` is always a real
git checkout (see ingestion/service.py) — this is far more robust than
hand-rolled hunk application (handles fuzzy context, whitespace, etc.
the way real patch tooling does).

Every applied file is backed up first, so a caller (Phase 11's future
test-execution loop) can roll back a fix that doesn't actually fix the
failure.

The applicator finds the actual file and makes that replacement.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import git

from repo_debug_agent.core.logger import logger
from repo_debug_agent.exceptions import PatchApplicationError
from repo_debug_agent.patching.models import AppliedFile, FileChange, ParsedPatch, PatchApplyResult, PatchFormat


class PatchApplicator:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self._git_repo = git.Repo(repo_root)

    def apply(self, patch: ParsedPatch) -> PatchApplyResult:
        if not patch.file_changes:
            return PatchApplyResult(
                success=False, applied_files=[], backup_dir=None,
                error="No parseable file changes found in the fix suggestion.",
            )

        backup_dir = Path(tempfile.mkdtemp(prefix="repo_debug_agent_patch_backup_"))
        applied: list[AppliedFile] = []

        try:
            for change in patch.file_changes:
                target = self.repo_root / change.file_path
                backup_path, existed_before = self._backup(target, backup_dir, change.file_path)
                applied.append(AppliedFile(
                    file_path=change.file_path, backup_path=str(backup_path), existed_before=existed_before,
                ))

                if change.format == PatchFormat.FULL_FILE:
                    self._apply_full_file(target, change)
                else:
                    self._apply_unified_diff(change)

            result = PatchApplyResult(success=True, applied_files=applied, backup_dir=str(backup_dir))
            logger.info(f"Applied {len(applied)} file change(s) from the fix suggestion.")
            return result

        except Exception as exc:  # noqa: BLE001 - defensive boundary; we roll back and re-raise as a domain error
            logger.error(f"Patch application failed, rolling back: {exc}")
            self.rollback(PatchApplyResult(success=False, applied_files=applied, backup_dir=str(backup_dir)))
            raise PatchApplicationError(f"Failed to apply fix suggestion: {exc}") from exc

    def rollback(self, result: PatchApplyResult) -> None:
        """Restore every file this result touched to its pre-patch state.
        Safe to call even on a partially-applied (failed) result."""
        for applied_file in result.applied_files:
            target = self.repo_root / applied_file.file_path
            if applied_file.existed_before:
                backup_path = Path(applied_file.backup_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, target)
            elif target.exists():
                target.unlink()
        logger.info(f"Rolled back {len(result.applied_files)} file(s).")

    @staticmethod
    def _backup(target: Path, backup_dir: Path, relative_path: str) -> tuple[str, bool]:
        backup_path = backup_dir / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        if existed:
            shutil.copy2(target, backup_path)
        return str(backup_path), existed

    @staticmethod
    def _apply_full_file(target: Path, change: FileChange) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change.new_content or "", encoding="utf-8")

    def _apply_unified_diff(self, change: FileChange) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False, encoding="utf-8") as f:
            f.write(change.diff_text or "")
            patch_path = f.name
        try:
            self._git_repo.git.apply("--whitespace=nowarn", patch_path)
        finally:
            Path(patch_path).unlink(missing_ok=True)