"""
Expands outward from an anchor file using the dependency graph (Phase 4),
producing candidate files annotated with their hop distance.

We expand in BOTH directions:
- dependencies_of(anchor): "what does the anchor file need, to be understood"
- blast_radius(anchor): "what else might break/be involved, given the anchor"

Both directions are debugging-relevant for different reasons, so both
are included, each still tagged with its own hop_distance for scoring.
"""

from repo_debug_agent.dependency_graph.graph_builder import DependencyGraph


def expand_structurally(anchor_file: str, graph: DependencyGraph, depth: int = 2) -> dict[str, int]:
    """
    Returns {file_path: hop_distance} for all files reachable from
    anchor_file within `depth` hops, in either direction.
    If a file is reachable via multiple paths/directions, keep the
    SHORTEST hop_distance found.
    """
    distances: dict[str, int] = {}

    for current_depth in range(1, depth + 1):
        deps = graph.dependencies_of(anchor_file, depth=current_depth)
        radius = graph.blast_radius(anchor_file, depth=current_depth)
        for file_path in deps | radius:
            if file_path not in distances:
                distances[file_path] = current_depth

    distances.pop(anchor_file, None)  # anchor itself is scored separately, not as a "structural" hit
    return distances