# tests/ingestion/test_source_resolver.py
import pytest
from pathlib import Path

from repo_debug_agent.ingestion.source_resolver import resolve_source
from repo_debug_agent.ingestion.models import SourceKind
from repo_debug_agent.exceptions import InvalidRepoSourceError


def test_resolve_local_path(tmp_path):
    source = resolve_source(str(tmp_path))
    assert source.kind == SourceKind.LOCAL_PATH
    assert source.local_path == tmp_path.resolve()


def test_resolve_https_url():
    source = resolve_source("https://github.com/psf/requests")
    assert source.kind == SourceKind.REMOTE_URL
    assert source.clone_url == "https://github.com/psf/requests.git"


def test_resolve_ssh_url():
    source = resolve_source("git@github.com:psf/requests.git")
    assert source.kind == SourceKind.REMOTE_URL
    assert source.clone_url == "https://github.com/psf/requests.git"


def test_resolve_shorthand():
    source = resolve_source("psf/requests")
    assert source.kind == SourceKind.SHORTHAND
    assert source.clone_url == "https://github.com/psf/requests.git"


def test_resolve_invalid_input():
    with pytest.raises(InvalidRepoSourceError):
        resolve_source("this is not a repo at all!!")