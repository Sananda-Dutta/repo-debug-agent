"""
Pure scoring/merging logic: combines anchor + structural + semantic
signals into one ranked, deduplicated list of RankedFile.

Pure function — no I/O, no graph/embedding calls — so scoring behavior
(weights, tie-breaking, dedup) is fully unit-testable with plain,
hand-constructed inputs.
"""

from repo_debug_agent.localization.models import RankedFile, RelevanceSource
from repo_debug_agent.retrieval.models import SearchResult

_ANCHOR_SCORE = 1.0
_STRUCTURAL_BASE_SCORE = 0.6
_SEMANTIC_WEIGHT = 0.5


def score_and_rank(
    anchor_file: str | None,
    anchor_symbol: str | None,
    structural_candidates: dict[str, int],
    semantic_candidates: list[SearchResult],
) -> list[RankedFile]:
    """
    Merge all three signal sources into one ranked list.

    Files found by multiple sources have their scores SUMMED (not
    max'd) — a file that is both a structural neighbor AND a semantic
    match is more likely relevant than one found only one way, and the
    combined score should reflect that.
    """
    accumulator: dict[str, RankedFile] = {}

    if anchor_file:
        accumulator[anchor_file] = RankedFile(
            file_path=anchor_file,
            score=_ANCHOR_SCORE,
            sources=[RelevanceSource.ANCHOR],
            relevant_symbols=[anchor_symbol] if anchor_symbol else [],
            hop_distance=0,
        )

    for file_path, hop_distance in structural_candidates.items():
        contribution = _STRUCTURAL_BASE_SCORE / hop_distance
        _accumulate(accumulator, file_path, contribution, RelevanceSource.STRUCTURAL, hop_distance=hop_distance)

    for result in semantic_candidates:
        file_path = result.chunk.file_path
        contribution = _SEMANTIC_WEIGHT * result.score
        _accumulate(accumulator, file_path, contribution, RelevanceSource.SEMANTIC)
        # Semantic hits ARE symbol-level by construction — always record which symbol.
        accumulator[file_path].relevant_symbols = list(
            set(accumulator[file_path].relevant_symbols) | {result.chunk.qualified_name}
        )

    ranked = sorted(accumulator.values(), key=lambda rf: rf.score, reverse=True)
    return ranked


def _accumulate(
    accumulator: dict[str, RankedFile],
    file_path: str,
    contribution: float,
    source: RelevanceSource,
    hop_distance: int | None = None,
) -> None:
    if file_path not in accumulator:
        accumulator[file_path] = RankedFile(file_path=file_path, score=0.0, sources=[], hop_distance=hop_distance)

    entry = accumulator[file_path]
    entry.score += contribution
    if source not in entry.sources:
        entry.sources.append(source)
    if hop_distance is not None and (entry.hop_distance is None or hop_distance < entry.hop_distance):
        entry.hop_distance = hop_distance