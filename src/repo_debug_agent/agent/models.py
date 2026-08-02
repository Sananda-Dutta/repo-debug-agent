"""
Data models for the LLM Agent Layer (Phase 9).
"""

from pathlib import Path
from typing import TypedDict

from pydantic import BaseModel, Field

from repo_debug_agent.context_retrieval.models import CompressedContext, TokenUsageReport
from repo_debug_agent.failure_analysis.models import ParsedException
from repo_debug_agent.indexing.models import CodebaseIndex
from repo_debug_agent.localization.models import LocalizationResult


class ParitokCallStats(BaseModel):
    """Real Paritok hosted-GPU savings for exactly ONE LLM call.

    IMPORTANT: this is NOT the SDK-mode `response._paritok_savings`
    attribute documented for `paritok.ParitokClient`. That wrapper only
    intercepts `client.messages.create()` (Anthropic-shaped clients) —
    it cannot wrap this project's `openai.OpenAI()` client, whose Chat
    Completions interface is `client.chat.completions.create()`.

    Instead we run Paritok in PROXY mode (its own "primary, recommended"
    mode) and diff its `/stats` endpoint immediately before and after
    each call. This is accurate per-call as long as calls to the proxy
    aren't made concurrently — see llm_client.py.
    """

    requests_delta: int = Field(description="Should be 1 for a single, non-concurrent call")
    original_tokens: int
    compressed_tokens: int
    tokens_saved: int
    compression_ratio: float = Field(description="compressed / original for the content Paritok touched")
    estimated_cost_saved_usd: str = Field(description="Dollar delta for this call, e.g. '$0.01'")


class FixSuggestion(BaseModel):
    """One LLM-proposed fix for the localized failure.

    Raw text only — parsing this into an applicable, verifiable patch
    is Phase 10's job (Fix Suggestion & Patching).
    """

    raw_response: str
    model: str
    paritok_stats: ParitokCallStats | None = Field(
        default=None, description="None only if the call somehow bypassed the Paritok proxy"
    )


class AgentRunResult(BaseModel):
    """Full output of one Phase 9 agent run.

    Bundles Phase 8's fetched/compressed context, the LLM's fix
    suggestion, and token accounting from BOTH Phase 8's local
    compression AND Phase 9's real, dashboard-verified Paritok
    hosted-GPU compression.
    """

    compressed_context: CompressedContext
    fix_suggestion: FixSuggestion
    usage: TokenUsageReport


class AgentState(TypedDict, total=False):
    """LangGraph state threaded through the Phase 9 graph.

    `total=False`: fields are populated progressively as nodes run,
    so none are required on the initial invoke() payload except what
    the first node needs.
    """

    repo_root: Path
    index: CodebaseIndex
    exception: ParsedException | None
    user_description: str
    localization_result: LocalizationResult | None
    token_budget: int
    compressed_context: CompressedContext | None
    fix_suggestion: FixSuggestion | None
    usage: TokenUsageReport | None