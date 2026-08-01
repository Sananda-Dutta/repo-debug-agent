# tests/localization/test_anchor_resolver.py
from repo_debug_agent.localization.anchor_resolver import resolve_anchor_symbol, resolve_anchor_file
from repo_debug_agent.failure_analysis.models import StackFrame
from repo_debug_agent.indexing.models import CodebaseIndex, FileIndex, CodeSymbol, SymbolKind, Language


def _index_with_nested_symbols() -> CodebaseIndex:
    return CodebaseIndex(
        commit_sha="abc", root_path="/repo",
        files={"app/models.py": FileIndex(
            relative_path="app/models.py", absolute_path="/repo/app/models.py",
            language=Language.PYTHON, content_hash="x", line_count=20,
            symbols=[
                CodeSymbol(name="User", qualified_name="User", kind=SymbolKind.CLASS, start_line=1, end_line=20),
                CodeSymbol(name="save", qualified_name="User.save", kind=SymbolKind.METHOD,
                            parent="User", start_line=5, end_line=10),
            ],
        )},
    )


def test_resolve_anchor_symbol_picks_most_specific():
    index = _index_with_nested_symbols()
    frame = StackFrame(file_path="/repo/app/models.py", line_number=7, function_name="save")
    symbol = resolve_anchor_symbol(frame, index, repo_root="/repo")
    assert symbol.qualified_name == "User.save"  # method, not the enclosing class


def test_resolve_anchor_file_outside_repo_returns_none():
    index = _index_with_nested_symbols()
    frame = StackFrame(file_path="/usr/lib/python3.12/site-packages/lib.py", line_number=1, function_name="f")
    assert resolve_anchor_file(frame, index, repo_root="/repo") is None