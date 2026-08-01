"""
FileLocalizationService: single public entrypoint for Phase 7.
"""

from repo_debug_agent.core.logger import logger
from repo_debug_agent.dependency_graph.graph_builder import DependencyGraph
from repo_debug_agent.failure_analysis.models import ParsedException
from repo_debug_agent.indexing.models import CodebaseIndex
from repo_debug_agent.localization.anchor_resolver import resolve_anchor_file, resolve_anchor_symbol
from repo_debug_agent.localization.models import LocalizationResult
from repo_debug_agent.localization.relevance_scorer import score_and_rank
from repo_debug_agent.localization.semantic_expander import expand_semantically
from repo_debug_agent.localization.structural_expander import expand_structurally
from repo_debug_agent.retrieval.service import SemanticSearchService


class FileLocalizationService:
    def __init__(
        self,
        index: CodebaseIndex,
        graph: DependencyGraph,
        search_service: SemanticSearchService,
        repo_root: str,
    ):
        self._index = index
        self._graph = graph
        self._search_service = search_service
        self._repo_root = repo_root

    def localize(
        self,
        exception: ParsedException | None = None,
        user_description: str = "",
        structural_depth: int = 2,
        semantic_k: int = 10,
    ) -> LocalizationResult:
        """
        Produce a ranked list of relevant files for the given failure.

        Handles the anchor-present and anchor-absent cases explicitly:
        - With an exception's innermost_frame resolvable to a repo file:
          anchor + structural expansion + semantic expansion.
        - Without a usable anchor (no exception provided, or the
          innermost frame is outside the repo, e.g. a third-party
          library frame): semantic expansion only, driven by whatever
          text we have (exception message and/or user_description).
        """
        anchor_file, anchor_symbol = self._resolve_anchor(exception)

        structural_candidates: dict[str, int] = {}
        if anchor_file:
            structural_candidates = expand_structurally(anchor_file, self._graph, depth=structural_depth)
        else:
            logger.info("No resolvable anchor file — skipping structural expansion, relying on semantic search only")

        semantic_query = self._build_semantic_query(exception, user_description)
        semantic_candidates = expand_semantically(semantic_query, self._search_service, k=semantic_k)

        ranked = score_and_rank(anchor_file, anchor_symbol, structural_candidates, semantic_candidates)

        logger.info(
            f"Localization complete: anchor={anchor_file or 'none'}, "
            f"{len(structural_candidates)} structural candidates, "
            f"{len(semantic_candidates)} semantic candidates, "
            f"{len(ranked)} ranked files total"
        )

        return LocalizationResult(anchor_file=anchor_file, anchor_symbol=anchor_symbol, ranked_files=ranked)

    def _resolve_anchor(self, exception: ParsedException | None) -> tuple[str | None, str | None]:
        if exception is None or exception.innermost_frame is None:
            return None, None

        frame = exception.innermost_frame
        anchor_file = resolve_anchor_file(frame, self._index, self._repo_root)
        if anchor_file is None:
            return None, None  # e.g. innermost frame was in a third-party library, not repo code

        symbol = resolve_anchor_symbol(frame, self._index, self._repo_root)
        return anchor_file, (symbol.qualified_name if symbol else None)

    @staticmethod
    def _build_semantic_query(exception: ParsedException | None, user_description: str) -> str:
        parts = []
        if exception:
            parts.append(f"{exception.exception_type}: {exception.message}")
        if user_description:
            parts.append(user_description)
        return " — ".join(parts)