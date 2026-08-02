"""
LLMAgentService: single public entrypoint for Phase 9.

Owns the Paritok proxy's lifecycle (start once, reuse across debug
iterations — important for Phase 11's future test-execution loop, which
will call `debug()` repeatedly) and wires Phase 7/8's services together
with the new LLM call for one localize -> fetch/compress -> generate-fix
cycle.
"""

from __future__ import annotations

from pathlib import Path

from repo_debug_agent.agent.graph import build_agent_graph
from repo_debug_agent.agent.llm_client import ParitokLLMClient
from repo_debug_agent.agent.models import AgentRunResult
from repo_debug_agent.agent.paritok_proxy import ParitokProxyManager
from repo_debug_agent.config.settings import get_settings
from repo_debug_agent.context_retrieval.compressor import TokenCompressor
from repo_debug_agent.context_retrieval.service import ContextRetrievalService
from repo_debug_agent.core.logger import logger
from repo_debug_agent.failure_analysis.models import ParsedException
from repo_debug_agent.indexing.models import CodebaseIndex
from repo_debug_agent.localization.models import LocalizationResult
from repo_debug_agent.localization.service import FileLocalizationService

_DEFAULT_TOKEN_BUDGET = 8000


class LLMAgentService:
    """Orchestrates Phase 7 (localization, optional) -> Phase 8 (context) ->
    Phase 9's LLM call, with every LLM call routed through a real,
    hosted-GPU Paritok proxy so token savings are dashboard-verified."""

    def __init__(self, compressor: TokenCompressor, model: str | None = None, proxy_port: int | None = None):
        settings = get_settings()
        self._proxy = ParitokProxyManager(port=proxy_port or settings.paritok_proxy_port)
        self._proxy.start()
        self._llm_client = ParitokLLMClient(self._proxy, model=model)
        self._context_service = ContextRetrievalService(compressor)
        logger.info(f"LLMAgentService ready (model={self._llm_client.model}, proxy={self._proxy.base_url})")

    def debug(
        self,
        repo_root: Path,
        index: CodebaseIndex,
        localization_service: FileLocalizationService | None = None,
        exception: ParsedException | None = None,
        user_description: str = "",
        localization_result: LocalizationResult | None = None,
        token_budget: int = _DEFAULT_TOKEN_BUDGET,
    ) -> AgentRunResult:
        """Run one localize -> fetch/compress -> generate-fix cycle.

        Either pass `localization_result` (if Phase 7 already ran
        earlier in the pipeline) or `localization_service` (to have
        this graph run Phase 7 itself). Exactly one must be usable.
        """
        if localization_result is None and localization_service is None:
            raise ValueError(
                "Provide either localization_result (already computed) or "
                "localization_service (to compute it) — got neither."
            )

        graph = build_agent_graph(self._context_service, self._llm_client, localization_service)
        initial_state = {
            "repo_root": repo_root,
            "index": index,
            "exception": exception,
            "user_description": user_description,
            "localization_result": localization_result,
            "token_budget": token_budget,
        }
        final_state = graph.invoke(initial_state)

        return AgentRunResult(
            compressed_context=final_state["compressed_context"],
            fix_suggestion=final_state["fix_suggestion"],
            usage=final_state["usage"],
        )

    def close(self) -> None:
        self._proxy.stop()

    def __enter__(self) -> "LLMAgentService":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()