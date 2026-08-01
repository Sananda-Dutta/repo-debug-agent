"""
Uses the semantic search service (Phase 5) to find candidate files/symbols
based on the exception message and/or a user-provided bug description.
"""

from repo_debug_agent.retrieval.models import SearchResult
from repo_debug_agent.retrieval.service import SemanticSearchService


def expand_semantically(
    query_text: str, search_service: SemanticSearchService, k: int = 10
) -> list[SearchResult]:
    """
    Returns semantic search hits for `query_text` (typically an
    exception type + message, optionally combined with a user's bug
    description).
    """
    if not query_text.strip():
        return []
    return search_service.search(query_text, k=k)