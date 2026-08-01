# tests/localization/test_service.py
"""End-to-end localization test using fakes for graph/search — no real I/O."""

from repo_debug_agent.localization.service import FileLocalizationService
from repo_debug_agent.failure_analysis.models import ParsedException, StackFrame
from repo_debug_agent.indexing.models import CodebaseIndex, FileIndex, CodeSymbol, SymbolKind, Language
from repo_debug_agent.dependency_graph.graph_builder import build_dependency_graph
from repo_debug_agent.retrieval.service import SemanticSearchService
from repo_debug_agent.retrieval.vector_store import FAISSVectorStore
from tests.retrieval.test_embedding_provider import FakeEmbeddingProvider


def test_localize_with_full_anchor(tmp_path):
    index = CodebaseIndex(
        commit_sha="abc", root_path=str(tmp_path),
        files={
            "app/main.py": FileIndex(
                relative_path="app/main.py", absolute_path=str(tmp_path / "app/main.py"),
                language=Language.PYTHON, content_hash="1", line_count=10,
                imports=["from . import utils"],
                symbols=[CodeSymbol(name="run", qualified_name="run", kind=SymbolKind.FUNCTION,
                                      start_line=1, end_line=5)],
            ),
            "app/utils.py": FileIndex(
                relative_path="app/utils.py", absolute_path=str(tmp_path / "app/utils.py"),
                language=Language.PYTHON, content_hash="2", line_count=5,
            ),
        },
    )
    graph = build_dependency_graph(index)
    search = SemanticSearchService(FakeEmbeddingProvider(), FAISSVectorStore(tmp_path / "store", dimension=2))

    service = FileLocalizationService(index, graph, search, repo_root=str(tmp_path))
    exception = ParsedException(
        exception_type="ValueError", message="bad input", raw_traceback="",
        frames=[StackFrame(file_path=str(tmp_path / "app/main.py"), line_number=3, function_name="run")],
    )

    result = service.localize(exception)

    assert result.anchor_file == "app/main.py"
    assert result.anchor_symbol == "run"
    top = result.top_files(5)
    assert top[0].file_path == "app/main.py"
    assert any(f.file_path == "app/utils.py" for f in top)  # structural neighbor pulled in