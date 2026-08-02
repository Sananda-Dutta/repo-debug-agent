# tests/context_retrieval/test_service.py
from repo_debug_agent.context_retrieval.service import ContextRetrievalService
from repo_debug_agent.context_retrieval.compressor import NaiveCompressor, RuleBasedCompressor
from repo_debug_agent.localization.models import LocalizationResult, RankedFile, RelevanceSource
from repo_debug_agent.indexing.models import CodebaseIndex, FileIndex, Language


def _build_result_and_index(tmp_path, n_files: int):
    files = {}
    ranked = []
    for i in range(n_files):
        content = f"def f{i}():\n    return {i}\n" * 20  # padded so token counts are meaningfully large
        (tmp_path / f"file{i}.py").write_text(content)
        files[f"file{i}.py"] = FileIndex(
            relative_path=f"file{i}.py", absolute_path=str(tmp_path / f"file{i}.py"),
            language=Language.PYTHON, content_hash=str(i), line_count=40,
        )
        ranked.append(RankedFile(file_path=f"file{i}.py", score=1.0 - i * 0.1, sources=[RelevanceSource.STRUCTURAL]))

    index = CodebaseIndex(commit_sha="abc", root_path=str(tmp_path), files=files)
    result = LocalizationResult(anchor_file=None, anchor_symbol=None, ranked_files=ranked)
    return result, index


def test_compressed_context_uses_less_or_equal_tokens_than_baseline(tmp_path):
    result, index = _build_result_and_index(tmp_path, n_files=3)
    service = ContextRetrievalService(RuleBasedCompressor())
    context = service.build_context(result, index, tmp_path, token_budget=100000)

    assert context.usage.compressed_token_count <= context.usage.baseline_token_count
    assert context.usage.units_included == context.usage.units_available


def test_token_budget_excludes_lower_ranked_units_when_tight(tmp_path):
    result, index = _build_result_and_index(tmp_path, n_files=5)
    service = ContextRetrievalService(NaiveCompressor())

    # First measure how many tokens ONE unit costs, then set a budget that
    # can only fit a couple of units, to make the exclusion deterministic.
    full_context = service.build_context(result, index, tmp_path, token_budget=1_000_000)
    per_unit_tokens = full_context.usage.baseline_token_count // 5

    tight_budget = per_unit_tokens * 2 + 10
    tight_context = service.build_context(result, index, tmp_path, token_budget=tight_budget)

    assert tight_context.usage.units_included < 5
    assert tight_context.usage.units_included >= 1


def test_higher_ranked_files_are_prioritized(tmp_path):
    result, index = _build_result_and_index(tmp_path, n_files=5)
    service = ContextRetrievalService(NaiveCompressor())

    full_context = service.build_context(result, index, tmp_path, token_budget=1_000_000)
    per_unit_tokens = full_context.usage.baseline_token_count // 5
    tight_budget = per_unit_tokens * 2 + 10

    tight_context = service.build_context(result, index, tmp_path, token_budget=tight_budget)
    included_paths = {u.file_path for u in tight_context.included_units}
    assert "file0.py" in included_paths  # highest-ranked file must be included