# tests/patching/test_service.py
import git
import pytest

from repo_debug_agent.agent.models import FixSuggestion
from repo_debug_agent.exceptions import PatchParsingError
from repo_debug_agent.patching.service import PatchService


@pytest.fixture
def repo(tmp_path):
    git.Repo.init(tmp_path)
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a - b\n")
    return tmp_path


def _suggestion(raw_response: str) -> FixSuggestion:
    return FixSuggestion(raw_response=raw_response, model="gpt-4o-mini")


def test_parse_raises_when_nothing_parseable(repo):
    service = PatchService(repo)
    with pytest.raises(PatchParsingError):
        service.parse(_suggestion("I'm not sure what's wrong here."))


def test_parse_returns_parsed_patch_without_touching_disk(repo):
    service = PatchService(repo)
    original = (repo / "app.py").read_text()

    parsed = service.parse(_suggestion("### File: app.py\n```python\nnew content\n```\n"))

    assert parsed.file_changes[0].file_path == "app.py"
    assert (repo / "app.py").read_text() == original  # untouched


def test_apply_writes_the_change_to_disk(repo):
    service = PatchService(repo)
    result = service.apply(_suggestion(
        "### File: app.py\n```python\ndef add(a, b):\n    return a + b\n```\n"
    ))

    assert result.success is True
    assert (repo / "app.py").read_text() == "def add(a, b):\n    return a + b"
def test_rollback_via_service_restores_original(repo):
    service = PatchService(repo)
    original = (repo / "app.py").read_text()

    result = service.apply(_suggestion("### File: app.py\n```python\nbroken\n```\n"))
    service.rollback(result)

    assert (repo / "app.py").read_text() == original