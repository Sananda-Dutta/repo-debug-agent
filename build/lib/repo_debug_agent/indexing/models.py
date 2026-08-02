"""
Data models for the codebase indexing phase.

CodeSymbol: a single function/class/method extracted from a file's AST.
FileIndex: everything we know about one source file.
CodebaseIndex: the full repo index, keyed by relative file path.
"""

from enum import Enum
from pydantic import BaseModel, Field


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    UNKNOWN = "unknown"


class SymbolKind(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"


class CodeSymbol(BaseModel):
    """A single named code unit (function, class, or method)."""

    name: str
    qualified_name: str = Field(description="e.g. 'MyClass.my_method' for methods")
    kind: SymbolKind
    parent: str | None = Field(default=None, description="Enclosing class name, if this is a method")
    start_line: int
    end_line: int
    docstring: str | None = None


class FileIndex(BaseModel):
    """Everything indexed about a single source file."""

    relative_path: str
    absolute_path: str
    language: Language
    content_hash: str
    line_count: int
    symbols: list[CodeSymbol] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    parse_error: str | None = Field(
        default=None, description="Set if Tree-sitter parsing failed; file still indexed with raw metadata only"
    )


class CodebaseIndex(BaseModel):
    """Full index of a repository at a specific commit."""

    commit_sha: str
    root_path: str
    files: dict[str, FileIndex] = Field(default_factory=dict, description="keyed by relative_path")

    def get_file(self, relative_path: str) -> FileIndex | None:
        return self.files.get(relative_path)

    def all_symbols(self) -> list[CodeSymbol]:
        return [sym for f in self.files.values() for sym in f.symbols]