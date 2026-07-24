"""
Parses raw import strings (extracted in Phase 3 via Tree-sitter) into
structured ParsedImport objects, per language.

Pure functions, zero I/O — takes text extracted from source, returns
structured data. Fully unit-testable without any filesystem/repo context.
"""

import re

from repo_debug_agent.dependency_graph.models import ParsedImport
from repo_debug_agent.indexing.models import Language

# --- Python ---
_PY_FROM_IMPORT = re.compile(
    r"^from\s+(?P<dots>\.*)(?P<module>[\w.]*)\s+import\s+(?P<names>.+)$"
)
_PY_PLAIN_IMPORT = re.compile(r"^import\s+(?P<module>[\w.]+)")

# --- JavaScript / TypeScript ---
_JS_IMPORT = re.compile(
    r"""^import\s+(?:.*\sfrom\s+)?['"](?P<module>[^'"]+)['"]"""
)

# --- Java ---
_JAVA_IMPORT = re.compile(r"^import\s+(?:static\s+)?(?P<module>[\w.]+)\s*;?")

# --- Go ---
_GO_IMPORT = re.compile(r'^["]?(?P<module>[\w./-]+)["]?$')


def parse_import(raw_text: str, language: Language) -> ParsedImport | None:
    """
    Parse one raw import statement string into a ParsedImport.
    Returns None if the text doesn't match any known pattern for the language
    (defensive — malformed/unusual syntax should not crash the pipeline).
    """
    raw_text = raw_text.strip()

    if language == Language.PYTHON:
        return _parse_python(raw_text)
    if language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
        return _parse_js(raw_text)
    if language == Language.JAVA:
        return _parse_java(raw_text)
    if language == Language.GO:
        return _parse_go(raw_text)
    return None


def _parse_python(raw_text: str) -> ParsedImport | None:
    match = _PY_FROM_IMPORT.match(raw_text)
    if match:
        dots = match.group("dots")
        names = [n.strip().split(" as ")[0].strip() for n in match.group("names").split(",")]
        return ParsedImport(
            raw_text=raw_text,
            module=match.group("module"),
            imported_names=names,
            is_relative=len(dots) > 0,
            relative_level=len(dots),
        )

    match = _PY_PLAIN_IMPORT.match(raw_text)
    if match:
        return ParsedImport(
            raw_text=raw_text,
            module=match.group("module"),
            imported_names=[],
            is_relative=False,
            relative_level=0,
        )
    return None


def _parse_js(raw_text: str) -> ParsedImport | None:
    match = _JS_IMPORT.match(raw_text)
    if not match:
        return None
    module = match.group("module")
    is_relative = module.startswith(".")
    return ParsedImport(raw_text=raw_text, module=module, is_relative=is_relative)


def _parse_java(raw_text: str) -> ParsedImport | None:
    match = _JAVA_IMPORT.match(raw_text)
    if not match:
        return None
    return ParsedImport(raw_text=raw_text, module=match.group("module"), is_relative=False)


def _parse_go(raw_text: str) -> ParsedImport | None:
    match = _GO_IMPORT.match(raw_text)
    if not match:
        return None
    module = match.group("module")
    is_relative = module.startswith(".")
    return ParsedImport(raw_text=raw_text, module=module, is_relative=is_relative)