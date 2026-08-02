"""
ContextRetrievalService: single public entrypoint for Phase 8.
"""

from pathlib import Path

from repo_debug_agent.core.logger import logger
from repo_debug_agent.context_retrieval.compressor import TokenCompressor
from repo_debug_agent.context_retrieval.context_fetcher import fetch_context_units
from repo_debug_agent.context_retrieval.models import CompressedContext, ContextUnit, TokenUsageReport
from repo_debug_agent.context_retrieval.token_counter import count_tokens
from repo_debug_agent.indexing.models import CodebaseIndex
from repo_debug_agent.localization.models import LocalizationResult

_DEFAULT_TOKEN_BUDGET = 8000


class ContextRetrievalService:
    def __init__(self, compressor: TokenCompressor):
        self._compressor = compressor

    def build_context(
        self,
        result: LocalizationResult,
        index: CodebaseIndex,
        repo_root: Path,
        token_budget: int = _DEFAULT_TOKEN_BUDGET,
    ) -> CompressedContext:
        """
        Fetch -> count -> compress -> greedily pack within `token_budget`,
        in ranked-score order (highest relevance first).
        """
        units = fetch_context_units(result, index, repo_root)

        for unit in units:
            unit.raw_token_count = count_tokens(unit.raw_text)
            unit.compressed_text = self._compressor.compress(unit.raw_text)
            unit.compressed_token_count = count_tokens(unit.compressed_text)

        baseline_total = sum(u.raw_token_count for u in units)

        included: list[ContextUnit] = []
        running_total = 0
        for unit in units:  # already in ranked (score-descending) order from Phase 7
            if running_total + unit.compressed_token_count > token_budget:
                continue  # skip this one, but keep checking lower-ranked units that might still fit
            included.append(unit)
            running_total += unit.compressed_token_count

        assembled_text = self._assemble(included)

        usage = TokenUsageReport(
            baseline_token_count=baseline_total,
            compressed_token_count=running_total,
            units_available=len(units),
            units_included=len(included),
            compression_ratio=(1 - running_total / baseline_total) if baseline_total else 0.0,
        )

        logger.info(
            f"Context built: {usage.units_included}/{usage.units_available} units included, "
            f"{usage.baseline_token_count} -> {usage.compressed_token_count} tokens "
            f"({usage.compression_ratio:.1%} reduction, {usage.tokens_saved} tokens saved)"
        )

        return CompressedContext(assembled_text=assembled_text, included_units=included, usage=usage)

    @staticmethod
    def _assemble(units: list[ContextUnit]) -> str:
        parts = []
        for unit in units:
            header = f"# File: {unit.file_path}"
            if unit.symbol_name:
                header += f" — Symbol: {unit.symbol_name}"
            parts.append(f"{header}\n{unit.compressed_text}")
        return "\n\n".join(parts)