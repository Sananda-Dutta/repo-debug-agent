# tests/localization/test_relevance_scorer.py
from repo_debug_agent.localization.relevance_scorer import score_and_rank
from repo_debug_agent.localization.models import RelevanceSource
from repo_debug_agent.retrieval.models import SearchResult, CodeChunk


def _chunk(file_path: str, qname: str) -> CodeChunk:
    return CodeChunk(chunk_id=f"{file_path}::{qname}", file_path=file_path, symbol_name=qname,
                       qualified_name=qname, kind="function", start_line=1, end_line=2, embedding_text="")


def test_anchor_always_outranks_pure_semantic():
    ranked = score_and_rank(
        anchor_file="app/main.py",
        anchor_symbol="run",
        structural_candidates={},
        semantic_candidates=[SearchResult(chunk=_chunk("app/other.py", "unrelated"), score=0.99)],
    )
    by_path = {r.file_path: r for r in ranked}
    assert by_path["app/main.py"].score > by_path["app/other.py"].score


def test_multi_source_file_scores_higher_than_single_source():
    ranked = score_and_rank(
        anchor_file=None,
        anchor_symbol=None,
        structural_candidates={"app/utils.py": 1},
        semantic_candidates=[SearchResult(chunk=_chunk("app/utils.py", "helper"), score=0.8),
                              SearchResult(chunk=_chunk("app/other.py", "thing"), score=0.8)],
    )
    by_path = {r.file_path: r for r in ranked}
    assert by_path["app/utils.py"].score > by_path["app/other.py"].score
    assert set(by_path["app/utils.py"].sources) == {RelevanceSource.STRUCTURAL, RelevanceSource.SEMANTIC}


def test_closer_structural_hop_scores_higher():
    ranked = score_and_rank(
        anchor_file=None, anchor_symbol=None,
        structural_candidates={"app/near.py": 1, "app/far.py": 2},
        semantic_candidates=[],
    )
    by_path = {r.file_path: r for r in ranked}
    assert by_path["app/near.py"].score > by_path["app/far.py"].score