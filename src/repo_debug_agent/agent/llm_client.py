"""
LLM client for Phase 9. Wraps `openai.OpenAI()` so every call is routed
through the local Paritok proxy (see paritok_proxy.py's module docstring
for why proxy mode, not `paritok.ParitokClient` SDK mode). Reports real,
dashboard-verified Paritok hosted-GPU savings per call via `/stats` diffing.
"""

from __future__ import annotations

from openai import OpenAI

from repo_debug_agent.agent.models import ParitokCallStats
from repo_debug_agent.agent.paritok_proxy import ParitokProxyManager
from repo_debug_agent.config.settings import get_settings
from repo_debug_agent.core.logger import logger

_STATS_KEYS = (
    "total_requests",
    "input_tokens_original",
    "input_tokens_compressed",
    "estimated_cost_saved_usd",
)


class ParitokLLMClient:
    """Chat-completion client that always goes through the Paritok compression proxy."""

    def __init__(self, proxy: ParitokProxyManager, model: str | None = None):
        self._proxy = proxy
        settings = get_settings()
        self._model = model or settings.llm_model
        self._client = OpenAI(api_key=settings.openai_api_key, base_url=proxy.base_url)

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: list[dict], **kwargs) -> tuple[str, ParitokCallStats]:
        """Send one chat-completion request through the Paritok proxy.

        Returns (response_text, ParitokCallStats). Diffs the proxy's
        cumulative `/stats` immediately before and after this call, so
        the returned stats are scoped to THIS request — accurate as
        long as calls aren't made concurrently against the same proxy.
        """
        before = self._proxy.stats()
        response = self._client.chat.completions.create(model=self._model, messages=messages, **kwargs)
        after = self._proxy.stats()

        stats = self._diff_stats(before, after)
        logger.info(
            f"LLM call via Paritok proxy: {stats.original_tokens} -> {stats.compressed_tokens} tokens "
            f"({stats.tokens_saved} saved, {stats.estimated_cost_saved_usd} est. cost saved this call)"
        )

        content = response.choices[0].message.content or ""
        return content, stats

    @staticmethod
    def _parse_usd(value: str) -> float:
        return float(value.replace("$", "").strip() or 0.0)

    @classmethod
    def _diff_stats(cls, before: dict, after: dict) -> ParitokCallStats:
        for key in _STATS_KEYS:
            if key not in before or key not in after:
                raise ValueError(f"Paritok /stats response missing expected key '{key}'")

        orig_delta = after["input_tokens_original"] - before["input_tokens_original"]
        comp_delta = after["input_tokens_compressed"] - before["input_tokens_compressed"]
        cost_delta = cls._parse_usd(after["estimated_cost_saved_usd"]) - cls._parse_usd(
            before["estimated_cost_saved_usd"]
        )

        return ParitokCallStats(
            requests_delta=after["total_requests"] - before["total_requests"],
            original_tokens=orig_delta,
            compressed_tokens=comp_delta,
            tokens_saved=orig_delta - comp_delta,
            compression_ratio=round(comp_delta / orig_delta, 3) if orig_delta else 0.0,
            estimated_cost_saved_usd=f"${max(cost_delta, 0.0):.2f}",
        )