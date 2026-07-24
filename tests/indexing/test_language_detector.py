# tests/indexing/test_language_detector.py
from pathlib import Path
from repo_debug_agent.indexing.language_detector import detect_language, is_supported
from repo_debug_agent.indexing.models import Language


def test_detect_python():
    assert detect_language(Path("app.py")) == Language.PYTHON


def test_detect_unknown():
    assert detect_language(Path("README.md")) == Language.UNKNOWN
    assert is_supported(Path("README.md")) is False