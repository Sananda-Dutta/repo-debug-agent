"""
Data models for the retrieval (embedding + vector search) phase.
"""

from pydantic import BaseModel, Field


class CodeChunk(BaseModel):
    """One embeddable unit of code, derived from a CodeSymbol."""

    chunk_id: str = Field(description="Stable unique id, e.g. 'app/utils.py::Calculator.add'")
    file_path: str
    symbol_name: str
    qualified_name: str
    kind: str  # SymbolKind value, kept as str to avoid circular import with indexing.models
    start_line: int
    end_line: int
    embedding_text: str = Field(description="The (possibly truncated) text actually sent to the embedder")


class SearchResult(BaseModel):
    """One result from a semantic search query."""

    chunk: CodeChunk
    score: float = Field(description="Similarity score, higher = more relevant")