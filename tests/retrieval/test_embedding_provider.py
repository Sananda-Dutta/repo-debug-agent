from tests.support.fakes import FakeEmbeddingProvider


def test_fake_embedding_provider_deterministic():
    provider = FakeEmbeddingProvider()
    v1 = provider.embed(["hello"])
    v2 = provider.embed(["hello"])
    assert v1 == v2