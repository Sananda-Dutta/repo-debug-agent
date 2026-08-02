"""
SemanticSearchService: single public entrypoint for Phase 5.
"""

from pathlib import Path

from repo_debug_agent.core.logger import logger
from repo_debug_agent.indexing.models import CodebaseIndex
from repo_debug_agent.retrieval.chunk_builder import build_chunks
from repo_debug_agent.retrieval.embedding_provider import EmbeddingProvider
from repo_debug_agent.retrieval.models import SearchResult
from repo_debug_agent.retrieval.vector_store import VectorStore


class SemanticSearchService:
    def __init__(self, embedding_provider: EmbeddingProvider, vector_store: VectorStore):
        self._embedder = embedding_provider
        self._store = vector_store

    def index_codebase(self, index: CodebaseIndex, repo_root: Path, force: bool = False) -> int:
        """
        Embed all symbols in `index` and add them to the vector store.
        Returns the number of chunks indexed. Skips work if the store
        is already populated (unless force=True) — mirrors Phase 3's
        commit-sha-based caching philosophy.
        """
        if not force and not self._store.is_empty():
            logger.info("Vector store already populated for this commit — skipping re-embedding")
            return 0

        chunks = build_chunks(index, repo_root)
        if not chunks:
            logger.warning("No embeddable symbols found in codebase index")
            return 0

        logger.info(f"Embedding {len(chunks)} code chunks...")
        vectors = self._embedder.embed([c.embedding_text for c in chunks])

        self._store.add(chunks, vectors)
        self._store.persist()

        logger.info(f"Indexed {len(chunks)} chunks into vector store")
        return len(chunks)

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        """Semantic search: return the top-k most relevant code chunks for `query`."""
        query_vector = self._embedder.embed([query])[0]
        results = self._store.search(query_vector, k)
        logger.debug(f"Search '{query[:60]}...' returned {len(results)} results")
        return results