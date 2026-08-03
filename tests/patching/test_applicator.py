# tests/patching/test_applicator.py
import git
import pytest

from repo_debug_agent.exceptions import PatchApplicationError
from repo_debug_agent.patching.applicator import PatchApplicator
from repo_debug_agent.patching.models import FileChange, ParsedPatch, PatchFormat


@pytest.fixture
def repo(tmp_path):
    """A real, minimal git checkout — PatchApplicator requires `repo_root`
    to be a real git repo (matches Phase 2's guarantee for cloned repos)."""
    git.Repo.init(tmp_path)
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a - b\n")
    return tmp_path


def test_apply_full_file_change_overwrites_existing_file(repo):
    patch = ParsedPatch(
        file_changes=[FileChange(
            file_path="app.py", format=PatchFormat.FULL_FILE,
            new_content="def add(a, b):\n    return a + b\n",
        )],
        raw_source="...",
    )
    result = PatchApplicator(repo).apply(patch)

    assert result.success is True
    assert (repo / "app.py").read_text() == "def add(a, b):\n    return a + b\n"
    assert result.applied_files[0].existed_before is True


def test_apply_full_file_change_creates_new_file(repo):
    patch = ParsedPatch(
        file_changes=[FileChange(
            file_path="new_module.py", format=PatchFormat.FULL_FILE, new_content="x = 1\n",
        )],
        raw_source="...",
    )
    result = PatchApplicator(repo).apply(patch)

    assert (repo / "new_module.py").read_text() == "x = 1\n"
    assert result.applied_files[0].existed_before is False


def test_apply_unified_diff_change_modifies_file_via_git_apply(repo):
    diff_text = (
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def add(a, b):\n"
        "-    return a - b\n"
        "+    return a + b\n"
    )
    patch = ParsedPatch(
        file_changes=[FileChange(file_path="app.py", format=PatchFormat.UNIFIED_DIFF, diff_text=diff_text)],
        raw_source="...",
    )
    result = PatchApplicator(repo).apply(patch)

    assert result.success is True
    assert (repo / "app.py").read_text() == "def add(a, b):\n    return a + b\n"


def test_apply_with_no_file_changes_returns_unsuccessful_result(repo):
    result = PatchApplicator(repo).apply(ParsedPatch(file_changes=[], raw_source="..."))
    assert result.success is False
    assert result.error is not None


def test_rollback_restores_modified_file_to_original_content(repo):
    original = (repo / "app.py").read_text()
    patch = ParsedPatch(
        file_changes=[FileChange(file_path="app.py", format=PatchFormat.FULL_FILE, new_content="ruined\n")],
        raw_source="...",
    )
    applicator = PatchApplicator(repo)
    result = applicator.apply(patch)

    applicator.rollback(result)

    assert (repo / "app.py").read_text() == original


def test_rollback_deletes_a_newly_created_file(repo):
    patch = ParsedPatch(
        file_changes=[FileChange(file_path="scratch.py", format=PatchFormat.FULL_FILE, new_content="x = 1\n")],
        raw_source="...",
    )
    applicator = PatchApplicator(repo)
    result = applicator.apply(patch)
    assert (repo / "scratch.py").exists()

    applicator.rollback(result)

    assert not (repo / "scratch.py").exists()


def test_invalid_diff_triggers_automatic_rollback_and_raises(repo):
    original = (repo / "app.py").read_text()
    bad_diff = (
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1,2 +1,2 @@\n"
        " this context line does not match the real file at all\n"
        "-neither does this one\n"
        "+so git apply must fail\n"
    )
    patch = ParsedPatch(
        file_changes=[FileChange(file_path="app.py", format=PatchFormat.UNIFIED_DIFF, diff_text=bad_diff)],
        raw_source="...",
    )

    with pytest.raises(PatchApplicationError):
        PatchApplicator(repo).apply(patch)

    # rolled back automatically -> original content untouched
    assert (repo / "app.py").read_text() == original