# tests/dependency_graph/test_graph_builder.py
from repo_debug_agent.dependency_graph.graph_builder import build_dependency_graph
from repo_debug_agent.indexing.models import CodebaseIndex, FileIndex, Language


def _index_with_imports() -> CodebaseIndex:
    files = {
        "app/main.py": FileIndex(
            relative_path="app/main.py", absolute_path="x", language=Language.PYTHON,
            content_hash="1", line_count=10, imports=["from . import utils", "import os"],
        ),
        "app/utils.py": FileIndex(
            relative_path="app/utils.py", absolute_path="x", language=Language.PYTHON,
            content_hash="2", line_count=5, imports=["from . import main"],  # circular!
        ),
    }
    return CodebaseIndex(commit_sha="abc", root_path="/repo", files=files)


def test_graph_builds_correct_edges():
    graph = build_dependency_graph(_index_with_imports())
    assert "app/utils.py" in graph.imports("app/main.py")
    assert "external:os" in graph.imports("app/main.py")


def test_graph_detects_circular_import():
    graph = build_dependency_graph(_index_with_imports())
    cycles = graph.find_cycles()
    assert len(cycles) >= 1


def test_blast_radius():
    graph = build_dependency_graph(_index_with_imports())
    # main.py imports utils.py -> utils.py's blast radius includes main.py
    radius = graph.blast_radius("app/utils.py", depth=1)
    assert "app/main.py" in radius