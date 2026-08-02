# tests/context_retrieval/test_token_counter.py
from repo_debug_agent.context_retrieval.token_counter import count_tokens


def test_count_tokens_nonempty():
    assert count_tokens("def add(a, b):\n    return a + b") > 0


def test_count_tokens_empty_string():
    assert count_tokens("") == 0


def test_count_tokens_consistent():
    text = "hello world, this is a test"
    assert count_tokens(text) == count_tokens(text)