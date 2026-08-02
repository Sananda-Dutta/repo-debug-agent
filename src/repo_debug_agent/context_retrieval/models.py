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
    """Token accounting for one localize->fetch->compress cycle (one debug iteration)."""

    baseline_token_count: int = Field(description="Sum of raw_token_count across ALL ranked units, uncompressed")
    compressed_token_count: int = Field(description="Sum of compressed_token_count across units actually INCLUDED in the final context")
    units_available: int
    units_included: int
    compression_ratio: float = Field(description="1 - (compressed / baseline); 0 if baseline is 0")

    @property
    def tokens_saved(self) -> int:
        return self.baseline_token_count - self.compressed_token_count


class CompressedContext(BaseModel):
    """Final assembled context ready to hand to the LLM agent (Phase 9)."""

    assembled_text: str
    included_units: list[ContextUnit]
    usage: TokenUsageReport