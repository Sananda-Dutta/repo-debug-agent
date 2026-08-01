# tests/retrieval/test_vector_store.py
from pathlib import Path
from repo_debug_agent.retrieval.vector_store import FAISSVectorStore
from repo_debug_agent.retrieval.models import CodeChunk
from tests.support.fakes import FakeEmbeddingProvider


def _sample_chunk(chunk_id: str) -> CodeChunk:
    return CodeChunk(
        chunk_id=chunk_id, file_path="app.py", symbol_name="f",
        qualified_name="f", kind="function", start_line=1, end_line=2,
        embedding_text="sample text",
    )


def test_faiss_add_and_search(tmp_path):
    store = FAISSVectorStore(persist_dir=tmp_path, dimension=2)
    provider = FakeEmbeddingProvider()

    chunks = [_sample_chunk("a"), _sample_chunk("b")]
    vectors = provider.embed(["hello world", "goodbye world"])
    store.add(chunks, vectors)

    results = store.search(provider.embed(["hello world"])[0], k=2)
    assert len(results) == 2
    assert results[0].chunk.chunk_id in {"a", "b"}


def test_faiss_persistence_roundtrip(tmp_path):
    provider = FakeEmbeddingProvider()
    store1 = FAISSVectorStore(persist_dir=tmp_path, dimension=2)
    store1.add([_sample_chunk("a")], provider.embed(["hello"]))
    store1.persist()

    store2 = FAISSVectorStore(persist_dir=tmp_path, dimension=2)
    assert not store2.is_empty()