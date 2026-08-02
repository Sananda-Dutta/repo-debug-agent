"""
ParitokAdapter: the ISOLATED integration point for the real Paritok
library.

⚠️ STATUS: STUB. This class currently delegates to RuleBasedCompressor
so the rest of the system (service.py, tests, Phase 9+) has a working,
correctly-shaped dependency to build against RIGHT NOW.

TO FINALIZE: once you provide Paritok's actual package name and
usage docs/API signature, replace the body of `compress()` below
with the real call. Everything else in this codebase — the
TokenCompressor interface, the factory in compressor.py, and every
caller — will continue to work unchanged, since ParitokAdapter
already implements the same interface.

Expected shape of the real integration (adjust once confirmed):

    import paritok  # or whatever the actual import is

    class ParitokAdapter(TokenCompressor):
        def __init__(self):
            self._client = paritok.Compressor(...)  # or however it's constructed

        def compress(self, text: str) -> str:
            return self._client.compress(text)      # or whatever the real call is
"""

from repo_debug_agent.core.logger import logger
from repo_debug_agent.context_retrieval.compressor import TokenCompressor, RuleBasedCompressor


class ParitokAdapter(TokenCompressor):
    def __init__(self):
        logger.warning(
            "ParitokAdapter is a STUB — delegating to RuleBasedCompressor. "
            "Provide Paritok's real API to finalize this integration."
        )
        self._fallback = RuleBasedCompressor()

    def compress(self, text: str) -> str:
        return self._fallback.compress(text)