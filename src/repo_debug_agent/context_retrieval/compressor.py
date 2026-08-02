"""
TokenCompressor: abstract interface + two concrete, fully-functional
implementations.

NaiveCompressor is a deliberate no-op — it exists so we can report a
true "uncompressed" baseline using the EXACT SAME interface/pipeline
as the compressed path, guaranteeing an apples-to-apples comparison
(same fetching, same token counter, only the compression step differs).

RuleBasedCompressor is a real, working token-reduction strategy
(not a placeholder) — see paritok_adapter.py for the pending
integration point for the actual Paritok library.

the rest of your system doesn't care how compression happens. 
It only knows: compress(text) goes in, reduced text comes out
"""

import re
from abc import ABC, abstractmethod


class TokenCompressor(ABC):
    @abstractmethod
    def compress(self, text: str) -> str:
        """Return a token-reduced version of `text`. May return `text` unchanged."""


class NaiveCompressor(TokenCompressor):
    """No-op — returns text unchanged. Used to measure the TRUE baseline."""

    def compress(self, text: str) -> str:
        return text


class RuleBasedCompressor(TokenCompressor):
    """
    Deterministic, lossless-for-LLM-purposes compression:
    - Strips blank lines (collapses 2+ consecutive blank lines to 1)
    - Strips trailing whitespace on every line
    - Strips full-line comments consisting ONLY of a comment (keeps
      inline comments, since those often carry meaning attached to code)
    - Collapses multiple consecutive blank lines inside docstrings too

    This is intentionally conservative — it removes formatting noise
    that costs tokens but carries no debugging signal, without
    altering identifiers, logic, or any code semantics.
    """

    _FULL_LINE_COMMENT = re.compile(r"^\s*#.*$")
    _MULTIPLE_BLANK_LINES = re.compile(r"\n{3,}")

    def compress(self, text: str) -> str:
        lines = text.splitlines()
        kept_lines = []
        for line in lines:
            if self._FULL_LINE_COMMENT.match(line):
                continue
            kept_lines.append(line.rstrip())

        collapsed = "\n".join(kept_lines)
        collapsed = self._MULTIPLE_BLANK_LINES.sub("\n\n", collapsed)
        return collapsed.strip("\n")

def get_compressor(strategy: str) -> TokenCompressor:
    """
    Factory: instantiate the configured LOCAL compression strategy.

    NOTE: "paritok" is intentionally NOT a valid value here. Paritok
    compresses at the LLM-call boundary (see paritok_adapter.py's
    docstring) and is wired up in Phase 9 via paritok.ParitokClient,
    not as a TokenCompressor in this local pipeline.
    """
    if strategy == "rule_based":
        return RuleBasedCompressor()
    return NaiveCompressor()