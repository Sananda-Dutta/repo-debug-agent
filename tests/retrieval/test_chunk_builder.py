# tests/retrieval/test_chunk_builder.py

'''test_chunk_builder.py: Verifies that code symbols are converted into correctly formatted CodeChunk objects.
test_embedding_provider.py: Verifies that the fake embedding provider produces deterministic vectors without relying on external models or APIs.
test_vector_store.py: Verifies that the vector store can add, search, save, and reload embeddings correctly.
test_service.py: Verifies that the entire semantic search pipeline—from indexing code to retrieving relevant results—works end to end.
'''


from pathlib import Path
from repo_debug_agent.retrieval.chunk_builder import build_chunks
from repo_debug_agent.indexing.models import CodebaseIndex, FileIndex, CodeSymbol, SymbolKind, Language


def test_build_chunks_from_index(tmp_path):
    (tmp_path / "app.py").write_text(
        "def greet(name):\n    \"\"\"Say hello.\"\"\"\n    return f'hello {name}'\n"
    )
    index = CodebaseIndex(
        commit_sha="abc", root_path=str(tmp_path),
        files={
            "app.py": FileIndex(
                relative_path="app.py", absolute_path=str(tmp_path / "app.py"),
                language=Language.PYTHON, content_hash="x", line_count=3,
                symbols=[CodeSymbol(
                    name="greet", qualified_name="greet", kind=SymbolKind.FUNCTION,
                    start_line=1, end_line=3, docstring="Say hello.",
                )],
            )
        },
    )
    chunks = build_chunks(index, tmp_path)
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "app.py::greet"
    assert "Say hello." in chunks[0].embedding_text
    assert "hello {name}" in chunks[0].embedding_text