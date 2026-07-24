"""
Data models for the dependency graph phase.
"""

from enum import Enum
from pydantic import BaseModel, Field


class ParsedImport(BaseModel):
    """A single import statement, broken into structured parts."""

    raw_text: str
    module: str = Field(description="Dotted module path, e.g. 'os.path' or '.utils'")
    imported_names: list[str] = Field(default_factory=list, description="Specific names imported, if any")
    is_relative: bool = False
    relative_level: int = Field(default=0, description="Number of leading dots, e.g. 2 for 'from ..x import y'")


class NodeKind(str, Enum):
    REPO_FILE = "repo_file"
    EXTERNAL = "external"


class DependencyEdge(BaseModel):
    """A directed edge: `source_file` imports from `target`."""

    source_file: str
    target: str
    target_kind: NodeKind
    imported_names: list[str] = Field(default_factory=list)


class GraphStats(BaseModel):
    total_files: int
    total_edges: int
    external_dependencies: int
    circular_import_groups: list[list[str]] = Field(default_factory=list)