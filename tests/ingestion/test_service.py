# tests/ingestion/test_service.py
"""
Service-level tests using pytest-mock to avoid real network/git calls.
We test orchestration logic, not GitPython/PyGithub internals themselves.
"""

from pathlib import Path
from repo_debug_agent.ingestion.service import RepoIngestionService


def test_ingest_local_path(tmp_path):
    (tmp_path / "app.py").write_text("x = 1")

    import git
    repo = git.Repo.init(tmp_path)
    repo.index.add(["app.py"])
    repo.index.commit("initial commit")

    service = RepoIngestionService(workspace_dir=tmp_path / "workspace")
    metadata = service.ingest(str(tmp_path))

    assert metadata.owner == "local"
    assert metadata.local_path == tmp_path.resolve()
    assert len(metadata.commit_sha) == 40  # full SHA length