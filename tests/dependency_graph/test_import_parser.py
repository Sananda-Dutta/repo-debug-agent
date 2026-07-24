# tests/dependency_graph/test_import_parser.py
from repo_debug_agent.dependency_graph.import_parser import parse_import
from repo_debug_agent.indexing.models import Language


def test_parse_python_absolute_import():
    parsed = parse_import("import os", Language.PYTHON)
    assert parsed.module == "os"
    assert parsed.is_relative is False


def test_parse_python_from_import():
    parsed = parse_import("from typing import List, Dict", Language.PYTHON)
    assert parsed.module == "typing"
    assert parsed.imported_names == ["List", "Dict"]


def test_parse_python_relative_import():
    parsed = parse_import("from ..utils import helper", Language.PYTHON)
    assert parsed.module == "utils"
    assert parsed.is_relative is True
    assert parsed.relative_level == 2


def test_parse_js_relative_import():
    parsed = parse_import("import { foo } from './bar'", Language.JAVASCRIPT)
    assert parsed.module == "./bar"
    assert parsed.is_relative is True


def test_parse_js_external_import():
    parsed = parse_import("import React from 'react'", Language.JAVASCRIPT)
    assert parsed.module == "react"
    assert parsed.is_relative is False