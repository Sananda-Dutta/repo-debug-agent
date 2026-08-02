"""
Converts Phase 7's LocalizationResult (file paths + optional symbol
names) into ContextUnits containing REAL source text, using Phase 3's
CodebaseIndex for exact symbol line ranges.

Design: if relevant_symbols is populated for a RankedFile, we fetch
ONLY those symbols' text (precise, small). If relevant_symbols is
empty (a pure-structural hit with unknown symbol-level detail — see
Phase 7 design notes), we fetch the WHOLE file. This directly reflects
what we actually know about relevance at each granularity — we never
guess a symbol we don't have evidence for.

This module takes localization's ranked files/symbols and turns them into actual 
ContextUnits containing the precise source code that will later be compressed and given to the LLM.
"""

from pathlib import Path

from repo_debug_agent.core.logger import logger
from repo_debug_agent.indexing.models import CodebaseIndex
from repo_debug_agent.localization.models import LocalizationResult, RankedFile
from repo_debug_agent.context_retrieval.models import ContextUnit


def fetch_context_units(
    result: LocalizationResult, index: CodebaseIndex, repo_root: Path
) -> list[ContextUnit]:
    """Fetch real source text for every ranked file in `result`, in ranked order."""
    units: list[ContextUnit] = []

    for ranked_file in result.ranked_files:
        try:
            file_text = (repo_root / ranked_file.file_path).read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            logger.warning(f"Could not read {ranked_file.file_path} for context retrieval: {exc}")
            continue

        if ranked_file.relevant_symbols:
            units.extend(_fetch_symbol_units(ranked_file, file_text, index))
        else:
            units.append(ContextUnit(
                file_path=ranked_file.file_path,
                symbol_name=None,
                raw_text=file_text,
                relevance_score=ranked_file.score,
            ))

    return units


def _fetch_symbol_units(ranked_file: RankedFile, file_text: str, index: CodebaseIndex) -> list[ContextUnit]:
    file_idx = index.get_file(ranked_file.file_path)
    if file_idx is None:
        # Index doesn't know this file (shouldn't normally happen since
        # localization derived from the same index) — fall back to whole file.
        return [ContextUnit(
            file_path=ranked_file.file_path, symbol_name=None,
            raw_text=file_text, relevance_score=ranked_file.score,
        )]

    lines = file_text.splitlines()
    symbols_by_name = {sym.qualified_name: sym for sym in file_idx.symbols}
    units: list[ContextUnit] = []

    for symbol_name in ranked_file.relevant_symbols:
        symbol = symbols_by_name.get(symbol_name)
        if symbol is None:
            continue
        symbol_text = "\n".join(lines[symbol.start_line - 1: symbol.end_line])
        units.append(ContextUnit(
            file_path=ranked_file.file_path,
            symbol_name=symbol_name,
            raw_text=symbol_text,
            relevance_score=ranked_file.score,
        ))

    return units