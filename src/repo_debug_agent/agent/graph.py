"""
Phase 9: the LangGraph agent that ties Phase 7 (localization, optional)
-> Phase 8 (context retrieval/compression) -> the LLM (routed through
Paritok's hosted GPU proxy) into one graph.

Scope note: this graph's output is the raw LLM fix suggestion plus full
token accounting. PARSING that suggestion into an applicable, verified
patch is Phase 10 (Fix Suggestion & Patching) — not this phase.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from repo_debug_agent.agent.llm_client import ParitokLLMClient
from repo_debug_agent.agent.models import AgentState, FixSuggestion
from repo_debug_agent.agent.prompts import SYSTEM_PROMPT, build_user_prompt, summarize_failure
from repo_debug_agent.context_retrieval.service import ContextRetrievalService
from repo_debug_agent.localization.service import FileLocalizationService

_DEFAULT_TOKEN_BUDGET = 8000


def build_agent_graph(
    context_service: ContextRetrievalService,
    llm_client: ParitokLLMClient,
    localization_service: FileLocalizationService | None = None,
):
    """
    Build and compile the Phase 9 graph.

    `localization_service` is optional: pass it if you want this graph
    to (re)run Phase 7 itself from `exception`/`user_description`.
    Otherwise the caller must populate `localization_result` in the
    initial state (e.g. if Phase 7 already ran earlier in the pipeline).
    """

    def localize_node(state: AgentState) -> dict:
        if state.get("localization_result") is not None:
            return {}
        if localization_service is None:
            # Nothing to do — the caller was responsible for providing
            # localization_result up front. Downstream nodes will fail
            # loudly if it's genuinely missing, which is the correct
            # behavior for a misconfigured pipeline.
            return {}
        result = localization_service.localize(
            exception=state.get("exception"),
            user_description=state.get("user_description", ""),
        )
        return {"localization_result": result}

    def retrieve_context_node(state: AgentState) -> dict:
        result = state.get("localization_result")
        if result is None:
            raise ValueError(
                "No localization_result available. Provide one in the initial "
                "state or pass a localization_service to build_agent_graph()."
            )
        compressed = context_service.build_context(
            result=result,
            index=state["index"],
            repo_root=state["repo_root"],
            token_budget=state.get("token_budget", _DEFAULT_TOKEN_BUDGET),
        )
        return {"compressed_context": compressed}

    def generate_fix_node(state: AgentState) -> dict:
        compressed = state["compressed_context"]
        failure_summary = summarize_failure(state.get("exception"), state.get("user_description", ""))
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(failure_summary, compressed.assembled_text)},
        ]

        raw_response, paritok_stats = llm_client.complete(messages)

        suggestion = FixSuggestion(
            raw_response=raw_response,
            model=llm_client.model,
            paritok_stats=paritok_stats,
        )
        usage = compressed.usage.with_paritok_stats(
            requests=paritok_stats.requests_delta,
            tokens_saved=paritok_stats.tokens_saved,
            compression_ratio=paritok_stats.compression_ratio,
            cost_saved_usd=paritok_stats.estimated_cost_saved_usd,
        )
        return {"fix_suggestion": suggestion, "usage": usage}

    graph = StateGraph(AgentState)
    graph.add_node("localize", localize_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("generate_fix", generate_fix_node)

    graph.set_entry_point("localize")
    graph.add_edge("localize", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_fix")
    graph.add_edge("generate_fix", END)

    return graph.compile()