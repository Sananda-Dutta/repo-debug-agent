# tests/context_retrieval/test_context_fetcher.py
from repo_debug_agent.context_retrieval.context_fetcher import fetch_context_units
from repo_debug_agent.localization.models import LocalizationResult, RankedFile, RelevanceSource
from repo_debug_agent.indexing.models import CodebaseIndex, FileIndex, CodeSymbol, SymbolKind, Language


def test_fetch_symbol_level_units(tmp_path):
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a + b\n\ndef sub(a, b):\n    return a - b\n")
    index = CodebaseIndex(
        commit_sha="abc", root_path=str(tmp_path),
        files={"app.py": FileIndex(
            relative_path="app.py", absolute_path=str(tmp_path / "app.py"),
            language=Language.PYTHON, content_hash="x", line_count=5,
            symbols=[
                CodeSymbol(name="add", qualified_name="add", kind=SymbolKind.FUNCTION, start_line=1, end_line=2),
                CodeSymbol(name="sub", qualified_name="sub", kind=SymbolKind.FUNCTION, start_line=4, end_line=5),
            ],
        )},
    )
    result = LocalizationResult(
        anchor_file="app.py", anchor_symbol="add",
        ranked_files=[RankedFile(file_path="app.py", score=1.0, sources=[RelevanceSource.ANCHOR],
                                    relevant_symbols=["add"])],
    )
    units = fetch_context_units(result, index, tmp_path)
    assert len(units) == 1
    assert units[0].symbol_name == "add"
    assert "return a + b" in units[0].raw_text
    assert "return a - b" not in units[0].raw_text  # sub() correctly excluded


def test_fetch_whole_file_when_no_symbols_known(tmp_path):
    (tmp_path / "app.py").write_text("x = 1\ny = 2\n")
    index = CodebaseIndex(commit_sha="abc", root_path=str(tmp_path), files={})
    result = LocalizationResult(
        anchor_file=None, anchor_symbol=None,
        ranked_files=[RankedFile(file_path="app.py", score=0.5, sources=[RelevanceSource.STRUCTURAL])],
    )
    units = fetch_context_units(result, index, tmp_path)
    assert len(units) == 1
    assert units[0].symbol_name is None
    assert "x = 1" in units[0].raw_text and "y = 2" in units[0].raw_text