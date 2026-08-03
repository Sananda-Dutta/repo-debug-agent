"""
Data models for the context retrieval & compression phase.
retrieve relevant code → compress it → track how many tokens you saved 
→ send the compressed context to the LLM.
"""

from pydantic import BaseModel, Field


class ContextUnit(BaseModel):
    """One piece of retrievable context — a specific file or symbol's source text."""

    file_path: str
    symbol_name: str | None = Field(default=None, description="None means 'whole file'")
    raw_text: str
    relevance_score: float
    raw_token_count: int = 0
    compressed_text: str = ""
    compressed_token_count: int = 0


class TokenUsageReport(BaseModel):
    """Token accounting for one localize->fetch->compress cycle (one debug iteration).

    The `paritok_*` fields are populated separately by Phase 9, AFTER the
    LLM call — they are real, dashboard-verified numbers from Paritok's
    hosted-GPU compression proxy, distinct from `baseline_token_count`/
    `compressed_token_count` above (which are Phase 8's LOCAL, pre-LLM-call
    compression accounting). They default to zero/None because a report
    can exist before any LLM call has been made.
    """

    baseline_token_count: int = Field(description="Sum of raw_token_count across ALL ranked units, uncompressed")
    compressed_token_count: int = Field(description="Sum of compressed_token_count across units actually INCLUDED in the final context")
    units_available: int
    units_included: int
    compression_ratio: float = Field(description="1 - (compressed / baseline); 0 if baseline is 0")

    paritok_requests: int = Field(default=0, description="Number of LLM calls routed through the Paritok hosted-GPU proxy")
    paritok_tokens_saved: int = Field(default=0, description="Tokens saved by Paritok's hosted-GPU compression, across paritok_requests")
    paritok_compression_ratio: float = Field(default=0.0, description="Paritok's own compressed/original ratio for the content it touched")
    paritok_estimated_cost_saved_usd: str = Field(default="$0.00", description="Paritok's own cost-saved estimate, as reported by its /stats endpoint")

    @property
    def tokens_saved(self) -> int:
        return self.baseline_token_count - self.compressed_token_count

    def with_paritok_stats(
        self, *, requests: int, tokens_saved: int, compression_ratio: float, cost_saved_usd: str
    ) -> "TokenUsageReport":
        """Return a copy of this report with real Paritok hosted-GPU stats attached."""
        return self.model_copy(
            update={
                "paritok_requests": requests,
                "paritok_tokens_saved": tokens_saved,
                "paritok_compression_ratio": compression_ratio,
                "paritok_estimated_cost_saved_usd": cost_saved_usd,
            }
        )


class CompressedContext(BaseModel):
    """Final assembled context ready to hand to the LLM agent (Phase 9)."""

    assembled_text: str
    included_units: list[ContextUnit]
    usage: TokenUsageReport