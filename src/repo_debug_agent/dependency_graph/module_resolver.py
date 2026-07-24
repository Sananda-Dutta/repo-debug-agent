"""
Resolves a ParsedImport (syntax-level) into either:
  - a concrete repo-relative file path (if it refers to a file in this repo), or
  - a marker that it's an external/stdlib dependency.

This is the ONLY module in this package that consults the actual
CodebaseIndex.files dict — i.e. the only place "does this path exist
in the repo" is checked.
"""

from pathlib import PurePosixPath

from repo_debug_agent.dependency_graph.models import ParsedImport
from repo_debug_agent.indexing.models import CodebaseIndex, Language


def resolve_import(
    parsed: ParsedImport,
    importing_file: str,
    index: CodebaseIndex,
    language: Language,
) -> str | None:
    """
    Attempt to resolve `parsed` (an import found inside `importing_file`)
    to a relative_path that exists in `index.files`.

    Returns None if it cannot be resolved to a repo file (i.e. it's
    external — a third-party package or stdlib module).
    """
    if language == Language.PYTHON:
        return _resolve_python(parsed, importing_file, index)
    if language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
        return _resolve_js(parsed, importing_file, index)
    # Java/Go: package systems are more complex to resolve purely from
    # import strings (require classpath/go.mod awareness); we record them
    # as external for now rather than guessing incorrectly.
    return None


def _resolve_python(parsed: ParsedImport, importing_file: str, index: CodebaseIndex) -> str | None:
    importing_dir = PurePosixPath(importing_file).parent

    if parsed.is_relative:
        base_dir = importing_dir
        for _ in range(parsed.relative_level - 1):
            base_dir = base_dir.parent
        module_parts = parsed.module.split(".") if parsed.module else []
        candidate_dir = base_dir
        for part in module_parts:
            candidate_dir = candidate_dir / part
        return _match_candidate(candidate_dir, index)

    # Absolute-style import: try treating the FIRST dotted segment as
    # matching a top-level package name found in the repo, only if the
    # resulting path actually exists in the index (otherwise it's external,
    # e.g. `import os` or `import numpy`).
    module_parts = parsed.module.split(".")
    candidate_path = PurePosixPath(*module_parts)
    return _match_candidate(candidate_path, index)


def _resolve_js(parsed: ParsedImport, importing_file: str, index: CodebaseIndex) -> str | None:
    if not parsed.is_relative:
        return None  # bare specifiers ('react', 'lodash') are always external/node_modules

    importing_dir = PurePosixPath(importing_file).parent
    candidate_path = (importing_dir / parsed.module).as_posix()
    # normalize "./" and "../" segments
    candidate = PurePosixPath(candidate_path)
    return _match_candidate(candidate, index, js_style=True)


def _match_candidate(candidate: PurePosixPath, index: CodebaseIndex, js_style: bool = False) -> str | None:
    """
    Try a handful of concrete file-path variants for a resolved candidate
    module path, returning the first one that exists in the index.
    """
    candidates_to_try: list[str]
    if js_style:
        candidates_to_try = [
            f"{candidate}.js", f"{candidate}.jsx", f"{candidate}.ts", f"{candidate}.tsx",
            f"{candidate}/index.js", f"{candidate}/index.ts",
        ]
    else:
        candidates_to_try = [
            f"{candidate}.py",
            f"{candidate}/__init__.py",
        ]

    for candidate_str in candidates_to_try:
        normalized = str(PurePosixPath(candidate_str))
        if normalized in index.files:
            return normalized
    return None