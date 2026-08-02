# tests/context_retrieval/test_compressor.py
from repo_debug_agent.context_retrieval.compressor import NaiveCompressor, RuleBasedCompressor, get_compressor
from repo_debug_agent.context_retrieval.token_counter import count_tokens

SAMPLE = """
# This is a standalone comment
def add(a, b):

    # another standalone comment
    return a + b  # inline comment stays



def subtract(a, b):
    return a - b
"""


def test_naive_compressor_no_op():
    assert NaiveCompressor().compress(SAMPLE) == SAMPLE


def test_rule_based_compressor_reduces_tokens():
    compressed = RuleBasedCompressor().compress(SAMPLE)
    assert count_tokens(compressed) < count_tokens(SAMPLE)


def test_rule_based_compressor_keeps_inline_comments():
    compressed = RuleBasedCompressor().compress(SAMPLE)
    assert "inline comment stays" in compressed


def test_rule_based_compressor_strips_standalone_comments():
    compressed = RuleBasedCompressor().compress(SAMPLE)
    assert "This is a standalone comment" not in compressed


def test_get_compressor_factory():
    assert isinstance(get_compressor("naive"), NaiveCompressor)
    assert isinstance(get_compressor("rule_based"), RuleBasedCompressor)