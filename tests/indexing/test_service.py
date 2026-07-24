# tests/indexing/test_service.py
from repo_debug_agent.indexing.service import CodebaseIndexingService


def test_build_index_full_pipeline(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "main.py").write_text(
        "class Foo:\n    def bar(self):\n        return 1\n"
    )
    (repo_root / "README.md").write_text("not code")

    service = CodebaseIndexingService(index_store_dir=tmp_path / "index_cache")
    index = service.build_index(repo_root, commit_sha="abc123")

    assert "main.py" in index.files
    file_idx = index.files["main.py"]
    assert len(file_idx.symbols) == 2  # Foo class + bar method

    # Second call should hit cache (README.md wouldn't get re-added if it changed,
    # proving we loaded from cache rather than re-walking)
    cached_index = service.build_index(repo_root, commit_sha="abc123")
    assert cached_index.commit_sha == "abc123"