# tests/ingestion/test_validator.py
import pytest
from repo_debug_agent.ingestion.validator import validate_repo
from repo_debug_agent.exceptions import RepoValidationError


def test_validate_empty_dir_fails(tmp_path):
    with pytest.raises(RepoValidationError, match="appears empty"):
        validate_repo(tmp_path)


def test_validate_no_code_files_fails(tmp_path):
    (tmp_path / "README.md").write_text("hello")
    with pytest.raises(RepoValidationError, match="none match known source-code"):
        validate_repo(tmp_path)


def test_validate_passes_with_code(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')")
    validate_repo(tmp_path)  # should not raise