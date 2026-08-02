"""
Builds a networkx-based DependencyGraph from a CodebaseIndex, using
import_parser + module_resolver to turn raw import strings into edges.
"""

import networkx as nx

from repo_debug_agent.core.logger import logger
from repo_debug_agent.dependency_graph.import_parser import parse_import
from repo_debug_agent.dependency_graph.models import DependencyEdge, GraphStats, NodeKind
from repo_debug_agent.dependency_graph.module_resolver import resolve_import
from repo_debug_agent.indexing.models import CodebaseIndex


class DependencyGraph:
    """
    Queryable wrapper around a networkx.DiGraph.

    Node = repo-relative file path (or "external:<module>" for external deps).
    Edge direction: source_file -> target means "source_file imports target."
    """

    def __init__(self, graph: nx.DiGraph, edges: list[DependencyEdge]):
        self._graph = graph
        self._edges = edges

    def imports(self, file_path: str) -> list[str]:
        """Files (and external deps) directly imported BY file_path."""
        if file_path not in self._graph:
            return []
        return list(self._graph.successors(file_path))

    def imported_by(self, file_path: str) -> list[str]:
        """Files that directly import file_path (its 'blast radius' at depth 1)."""
        if file_path not in self._graph:
            return []
        return list(self._graph.predecessors(file_path))

    def blast_radius(self, file_path: str, depth: int = 2) -> set[str]:
        """
        All files that TRANSITIVELY depend on file_path, up to `depth` hops.
        This answers: "if file_path breaks, what else might be affected?"
        """
        if file_path not in self._graph:
            return set()
        visited: set[str] = set()
        frontier = {file_path}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for node in frontier:
                next_frontier.update(self._graph.predecessors(node))
            next_frontier -= visited
            if not next_frontier:
                break
            visited.update(next_frontier)
            frontier = next_frontier
        return visited

    def dependencies_of(self, file_path: str, depth: int = 2) -> set[str]:
        """
        All files file_path TRANSITIVELY depends on, up to `depth` hops.
        This answers: "to understand file_path, what else should I read?"
        """
        if file_path not in self._graph:
            return set()
        visited: set[str] = set()
        frontier = {file_path}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for node in frontier:
                next_frontier.update(self._graph.successors(node))
            next_frontier -= visited
            if not next_frontier:
                break
            visited.update(next_frontier)
            frontier = next_frontier
        return visited

    def find_cycles(self) -> list[list[str]]:
        """Detect circular imports — a common real-world bug source."""
        repo_only = self._graph.subgraph(
            [n for n, d in self._graph.nodes(data=True) if d.get("kind") == NodeKind.REPO_FILE]
        )
        return [cycle for cycle in nx.simple_cycles(repo_only)]

    def stats(self) -> GraphStats:
        external_count = sum(
            1 for _, d in self._graph.nodes(data=True) if d.get("kind") == NodeKind.EXTERNAL
        )
        return GraphStats(
            total_files=sum(1 for _, d in self._graph.nodes(data=True) if d.get("kind") == NodeKind.REPO_FILE),
            total_edges=self._graph.number_of_edges(),
            external_dependencies=external_count,
            circular_import_groups=self.find_cycles(),
        )


def build_dependency_graph(index: CodebaseIndex) -> DependencyGraph:
    """Build a DependencyGraph from a fully-populated CodebaseIndex."""
    graph = nx.DiGraph()
    edges: list[DependencyEdge] = []

    for relative_path, file_idx in index.files.items():
        graph.add_node(relative_path, kind=NodeKind.REPO_FILE)

    for relative_path, file_idx in index.files.items():
        for raw_import in file_idx.imports:
            parsed = parse_import(raw_import, file_idx.language)
            if parsed is None:
                continue

            resolved_path = resolve_import(parsed, relative_path, index, file_idx.language)

            if resolved_path:
                target, kind = resolved_path, NodeKind.REPO_FILE
            else:
                target, kind = f"external:{parsed.module}", NodeKind.EXTERNAL
                graph.add_node(target, kind=NodeKind.EXTERNAL)

            graph.add_edge(relative_path, target)
            edges.append(DependencyEdge(
                source_file=relative_path,
                target=target,
                target_kind=kind,
                imported_names=parsed.imported_names,
            ))

    logger.info(
        f"Dependency graph built: {graph.number_of_nodes()} nodes, "
        f"{graph.number_of_edges()} edges"
    )
    return DependencyGraph(graph, edges)