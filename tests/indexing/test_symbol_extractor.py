# tests/indexing/test_symbol_extractor.py
from repo_debug_agent.indexing.parser import parse_source
from repo_debug_agent.indexing.symbol_extractor import extract_symbols, extract_imports
from repo_debug_agent.indexing.models import Language, SymbolKind

SAMPLE_PY = b'''
import os
from typing import List

class Calculator:
    """A simple calculator."""

    def add(self, a, b):
        """Add two numbers."""
        return a + b

def standalone_function(x):
    return x * 2
'''


def test_extract_symbols_python():
    tree = parse_source(SAMPLE_PY, Language.PYTHON)
    symbols = extract_symbols(tree, SAMPLE_PY, Language.PYTHON)

    names = {s.qualified_name: s for s in symbols}

    assert "Calculator" in names
    assert names["Calculator"].kind == SymbolKind.CLASS
    assert names["Calculator"].docstring == "A simple calculator."

    assert "Calculator.add" in names
    assert names["Calculator.add"].kind == SymbolKind.METHOD
    assert names["Calculator.add"].parent == "Calculator"

    assert "standalone_function" in names
    assert names["standalone_function"].kind == SymbolKind.FUNCTION
    assert names["standalone_function"].parent is None


def test_extract_imports_python():
    tree = parse_source(SAMPLE_PY, Language.PYTHON)
    imports = extract_imports(tree, SAMPLE_PY, Language.PYTHON)
    assert any("import os" in i for i in imports)
    assert any("from typing import List" in i for i in imports)