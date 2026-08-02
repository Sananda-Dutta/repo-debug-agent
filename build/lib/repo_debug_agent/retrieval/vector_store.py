"""
VectorStore: abstract interface + FAISS and Chroma implementations.

Both implementations persist to disk, keyed by commit_sha, mirroring
Phase 3's caching pattern — re-running against the same commit loads
the existing index instead of re-embedding everything.
"""
#Now that I have vectors, where do I store them and how do I search them later?

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from repo_debug_agent.core.logger import logger
from repo_debug_agent.retrieval.models import CodeChunk, SearchResult


class VectorStore(ABC):
    @abstractmethod
    def add(self, chunks: list[CodeChunk], vectors: list[list[float]]) -> None:
        ...

    @abstractmethod
    def search(self, query_vector: list[float], k: int) -> list[SearchResult]:
        ...

    @abstractmethod
    def persist(self) -> None:
        ...

    @abstractmethod
    def is_empty(self) -> bool:
        ...


class FAISSVectorStore(VectorStore):
    """
    FAISS-backed store. FAISS itself only stores vectors + integer ids,
    so we maintain a parallel `self._chunks` list mapping id -> CodeChunk,
    persisted alongside the FAISS index file as JSON.
    """

    def __init__(self, persist_dir: Path, dimension: int):
        import faiss

        self._faiss = faiss
        self._persist_dir = persist_dir
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._dimension = dimension
        self._index_path = persist_dir / "faiss.index"
        self._chunks_path = persist_dir / "chunks.json"

        self._chunks: list[CodeChunk] = []
        if self._index_path.exists() and self._chunks_path.exists():
            self._index = faiss.read_index(str(self._index_path))
            self._chunks = [
                CodeChunk.model_validate(c)
                for c in __import__("json").loads(self._chunks_path.read_text())
            ]
            logger.info(f"Loaded existing FAISS index with {len(self._chunks)} chunks")
        else:
            self._index = faiss.IndexFlatIP(dimension)  # inner product == cosine sim on normalized vectors

    def add(self, chunks: list[CodeChunk], vectors: list[list[float]]) -> None:
        matrix = np.array(vectors, dtype="float32")
        faiss_normalize = self._faiss.normalize_L2
        faiss_normalize(matrix)
        self._index.add(matrix)
        self._chunks.extend(chunks)

    def search(self, query_vector: list[float], k: int) -> list[SearchResult]:
        if self.is_empty():
            return []
        query = np.array([query_vector], dtype="float32")
        self._faiss.normalize_L2(query)
        scores, indices = self._index.search(query, min(k, len(self._chunks)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append(SearchResult(chunk=self._chunks[idx], score=float(score)))
        return results

    def persist(self) -> None:
        import json
        self._faiss.write_index(self._index, str(self._index_path))
        self._chunks_path.write_text(json.dumps([c.model_dump() for c in self._chunks]))

    def is_empty(self) -> bool:
        return len(self._chunks) == 0


class ChromaVectorStore(VectorStore):
    """
    ChromaDB-backed store. Chroma natively stores metadata alongside
    vectors, so we don't need a parallel chunk-tracking structure —
    the tradeoff is a slightly heavier per-query API surface.
    """

    def __init__(self, persist_dir: Path, collection_name: str):
        import chromadb

        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(name=collection_name)

    def add(self, chunks: list[CodeChunk], vectors: list[list[float]]) -> None:
        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=vectors,
            metadatas=[c.model_dump(exclude={"embedding_text"}) for c in chunks],
            documents=[c.embedding_text for c in chunks],
        )

    def search(self, query_vector: list[float], k: int) -> list[SearchResult]:
        if self.is_empty():
            return []
        result = self._collection.query(query_embeddings=[query_vector], n_results=k)
        results = []
        for metadata, distance in zip(result["metadatas"][0], result["distances"][0]):
            chunk = CodeChunk(**metadata, embedding_text="")
            # Chroma returns distance (lower=closer); convert to a similarity-style score
            results.append(SearchResult(chunk=chunk, score=1.0 - distance))
        return results

    def persist(self) -> None:
        pass  # PersistentClient writes through automatically; kept for interface symmetry

    def is_empty(self) -> bool:
        return self._collection.count() == 0


def get_vector_store(
    backend: str, persist_dir: Path, dimension: int, collection_name: str = "code_chunks"
) -> VectorStore:
    """Factory: instantiate the configured vector store backend."""
    if backend == "chroma":
        return ChromaVectorStore(persist_dir, collection_name)
    return FAISSVectorStore(persist_dir, dimension)