# tests/dependency_graph/test_module_resolver.py
from repo_debug_agent.dependency_graph.import_parser import parse_import
from repo_debug_agent.dependency_graph.module_resolver import resolve_import
from repo_debug_agent.indexing.models import CodebaseIndex, FileIndex, Language


def _make_index(paths: list[str]) -> CodebaseIndex:
    files = {
        p: FileIndex(relative_path=p, absolute_path=p, language=Language.PYTHON,
                      content_hash="x", line_count=1)
        for p in paths
    }
    return CodebaseIndex(commit_sha="abc", root_path="/repo", files=files)


def test_resolve_python_relative_level_1():
    index = _make_index(["pkg/models.py", "pkg/service.py"])
    parsed = parse_import("from . import models", Language.PYTHON)
    resolved = resolve_import(parsed, importing_file="pkg/service.py", index=index, language=Language.PYTHON)
    assert resolved == "pkg/models.py"


def test_resolve_python_relative_level_2():
    index = _make_index(["pkg/utils.py", "pkg/sub/service.py"])
    parsed = parse_import("from .. import utils", Language.PYTHON)
    resolved = resolve_import(parsed, importing_file="pkg/sub/service.py", index=index, language=Language.PYTHON)
    assert resolved == "pkg/utils.py"


def test_resolve_python_external_import():
    index = _make_index(["pkg/service.py"])
    parsed = parse_import("import numpy", Language.PYTHON)
    resolved = resolve_import(parsed, importing_file="pkg/service.py", index=index, language=Language.PYTHON)
    assert resolved is None


def test_resolve_js_relative_import():
    index = _make_index(["src/app.js", "src/utils.js"])
    parsed = parse_import("import { helper } from './utils'", Language.JAVASCRIPT)
    resolved = resolve_import(parsed, importing_file="src/app.js", index=index, language=Language.JAVASCRIPT)
    assert resolved == "src/utils.js"