# tests/retrieval/test_service.py
from pathlib import Path
from repo_debug_agent.retrieval.service import SemanticSearchService
from repo_debug_agent.retrieval.vector_store import FAISSVectorStore
from repo_debug_agent.indexing.models import CodebaseIndex, FileIndex, CodeSymbol, SymbolKind, Language
from tests.support.fakes import FakeEmbeddingProvider


def test_index_and_search_full_flow(tmp_path):
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a + b\n")
    index = CodebaseIndex(
        commit_sha="abc", root_path=str(tmp_path),
        files={"app.py": FileIndex(
            relative_path="app.py", absolute_path=str(tmp_path / "app.py"),
            language=Language.PYTHON, content_hash="x", line_count=2,
            symbols=[CodeSymbol(name="add", qualified_name="add", kind=SymbolKind.FUNCTION,
                                  start_line=1, end_line=2)],
        )},
    )

    service = SemanticSearchService(
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=FAISSVectorStore(persist_dir=tmp_path / "store", dimension=2),
    )
    count = service.index_codebase(index, repo_root=tmp_path)
    assert count == 1

    results = service.search("addition function", k=1)
    assert len(results) == 1
    assert results[0].chunk.qualified_name == "add"