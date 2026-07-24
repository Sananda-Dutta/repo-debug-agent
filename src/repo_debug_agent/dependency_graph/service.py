"""
DependencyGraphService: single public entrypoint for Phase 4.
"""

from repo_debug_agent.core.logger import logger
from repo_debug_agent.dependency_graph.graph_builder import DependencyGraph, build_dependency_graph
from repo_debug_agent.dependency_graph.models import GraphStats
from repo_debug_agent.indexing.models import CodebaseIndex


class DependencyGraphService:
    def build(self, index: CodebaseIndex) -> DependencyGraph:
        graph = build_dependency_graph(index)
        stats: GraphStats = graph.stats()

        if stats.circular_import_groups:
            logger.warning(
                f"Detected {len(stats.circular_import_groups)} circular import group(s): "
                f"{stats.circular_import_groups[:3]}{'...' if len(stats.circular_import_groups) > 3 else ''}"
            )

        logger.info(
            f"Graph stats: {stats.total_files} files, {stats.total_edges} edges, "
            f"{stats.external_dependencies} external deps"
        )
        return graph