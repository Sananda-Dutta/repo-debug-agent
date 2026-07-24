"""
Thin, language-agnostic wrapper around tree-sitter-languages.

This module knows HOW to get a parsed tree for a given language.
It does NOT know what a "function" looks like in that language's
grammar — that's symbol_extractor.py's job. This separation is what
lets us add a new language here in one line, and separately teach
symbol_extractor.py that language's node-type names.
"""

from tree_sitter import Tree
from tree_sitter_languages import get_parser

from repo_debug_agent.core.logger import logger
from repo_debug_agent.indexing.models import Language

# Maps our Language enum to tree-sitter-languages' string identifiers
_TS_LANGUAGE_NAMES: dict[Language, str] = {
    Language.PYTHON: "python",
    Language.JAVASCRIPT: "javascript",
    Language.TYPESCRIPT: "typescript",
    Language.JAVA: "java",
    Language.GO: "go",
}

_parser_cache: dict[Language, object] = {}


def _get_cached_parser(language: Language):
    """Reuse one parser instance per language across the whole indexing run."""
    if language not in _parser_cache:
        ts_name = _TS_LANGUAGE_NAMES[language]
        _parser_cache[language] = get_parser(ts_name)
    return _parser_cache[language]


def parse_source(source_code: bytes, language: Language) -> Tree | None:
    """
    Parse source bytes into a Tree-sitter AST for the given language.

    Returns None if the language isn't supported (caller should
    fall back to raw-text-only indexing for that file).
    """
    if language not in _TS_LANGUAGE_NAMES:
        return None

    try:
        parser = _get_cached_parser(language)
        return parser.parse(source_code)
    except Exception as exc:  # noqa: BLE001 - Tree-sitter can raise various low-level errors
        logger.warning(f"Tree-sitter failed to parse source for language={language}: {exc}")
        return None