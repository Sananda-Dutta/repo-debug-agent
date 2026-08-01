"""
Shared test doubles used across multiple test modules.

Deliberately NOT named test_*.py and NOT inside any test_*.py file —
pytest's test collection / import-mode machinery is only guaranteed
to behave consistently for files it actually collects as tests.
Cross-importing FROM one test module INTO another depends on
incidental sys.path state and breaks under different pytest
import-mode settings (importlib vs. prepend), different invocation
directories, and different rootdir configurations. A plain support
module, imported normally, has none of that fragility.
"""

from repo_debug_agent.retrieval.embedding_provider import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic fake: embeds text by its length + character sum, for test reproducibility."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 10), float(sum(ord(c) for c in t) % 100)] for t in texts]

    @property
    def dimension(self) -> int:
        return 2