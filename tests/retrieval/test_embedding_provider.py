# tests/retrieval/test_embedding_provider.py
"""
Fake provider used across retrieval tests so we NEVER hit network/torch
in the test suite for logic that doesn't specifically test embedding backends.
"""
from tests.support.fakes import FakeEmbeddingProvider


def test_fake_embedding_provider_deterministic():
    provider = FakeEmbeddingProvider()
    v1 = provider.embed(["hello"])
    v2 = provider.embed(["hello"])
    assert v1 == v2