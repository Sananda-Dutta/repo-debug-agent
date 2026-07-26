"""
EmbeddingProvider: abstract interface + two implementations.

Abstracting this lets the rest of the system (vector_store.py, service.py)
be entirely agnostic to WHICH embedding backend is in use — swappable via
config alone, and trivially fakeable in tests (no network calls needed
to test chunking/storage/search logic).
"""

'''This file abstracts the embedding process, allowing the rest of your application to generate semantic vectors 
from code chunks without caring whether they come from a local SentenceTransformer model or OpenAI's embedding API.'''

#How do we convert code into numbers (vectors) that can be searched semantically?

from abc import ABC, abstractmethod

from repo_debug_agent.core.logger import logger


class EmbeddingProvider(ABC):
    """Turns a batch of text strings into a batch of embedding vectors."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector (list[float]) per input text, same order."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality this provider produces."""


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Free, offline embedding using sentence-transformers.
    Default provider — requires no API key, no network at query time.
    """

    _MODEL_NAME = "all-MiniLM-L6-v2"
    _DIMENSION = 384

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading local embedding model: {self._MODEL_NAME}")
        self._model = SentenceTransformer(self._MODEL_NAME)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return vectors.tolist()

    @property
    def dimension(self) -> int:
        return self._DIMENSION


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Higher-quality embeddings via OpenAI's API. Requires OPENAI_API_KEY
    and incurs API cost — opt-in, not the default.
    """

    _MODEL_NAME = "text-embedding-3-small"
    _DIMENSION = 1536
    _BATCH_SIZE = 100

    def __init__(self, api_key: str):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), self._BATCH_SIZE):
            batch = texts[i: i + self._BATCH_SIZE]
            response = self._client.embeddings.create(model=self._MODEL_NAME, input=batch)
            all_vectors.extend([item.embedding for item in response.data])
        return all_vectors

    @property
    def dimension(self) -> int:
        return self._DIMENSION


def get_embedding_provider(provider_name: str, openai_api_key: str = "") -> EmbeddingProvider:
    """Factory: instantiate the configured embedding provider."""
    if provider_name == "openai":
        if not openai_api_key:
            raise ValueError("OpenAI embedding provider requested but OPENAI_API_KEY is not set")
        return OpenAIEmbeddingProvider(api_key=openai_api_key)
    return LocalEmbeddingProvider()