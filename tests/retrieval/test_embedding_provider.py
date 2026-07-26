# tests/retrieval/test_embedding_provider.py
"""
Fake provider used across retrieval tests so we NEVER hit network/torch
in the test suite for logic that doesn't specifically test embedding backends.
"""
from repo_debug_agent.retrieval.embedding_provider import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic fake: embeds text by its length + character sum, for test reproducibility."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 10), float(sum(ord(c) for c in t) % 100)] for t in texts]

    @property
    def dimension(self) -> int:
        return 2


def test_fake_embedding_provider_deterministic():
    provider = FakeEmbeddingProvider()
    v1 = provider.embed(["hello"])
    v2 = provider.embed(["hello"])
    assert v1 == v2