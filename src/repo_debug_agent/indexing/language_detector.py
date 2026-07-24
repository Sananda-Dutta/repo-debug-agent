"""
Maps file extensions to our Language enum.

Kept as a pure, dependency-free lookup so it's trivially testable
and easy to extend when we add support for new languages.
"""

from pathlib import Path
from repo_debug_agent.indexing.models import Language

_EXTENSION_MAP: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".java": Language.JAVA,
    ".go": Language.GO,
}


def detect_language(file_path: Path) -> Language:
    """Return the Language for a given file, or Language.UNKNOWN if unrecognized."""
    return _EXTENSION_MAP.get(file_path.suffix.lower(), Language.UNKNOWN)


def is_supported(file_path: Path) -> bool:
    """True if we have symbol-extraction support for this file's language."""
    return detect_language(file_path) != Language.UNKNOWN