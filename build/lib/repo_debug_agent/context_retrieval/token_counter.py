"""
Exact token counting via tiktoken — the single source of truth for
every token count this system reports (baseline AND compressed).
Using one consistent, exact counter across both sides of the
comparison is what makes the "tokens saved" number meaningful.
"""

import tiktoken

_DEFAULT_ENCODING = "cl100k_base"  # GPT-4 / GPT-3.5-turbo family
_encoder_cache: dict[str, "tiktoken.Encoding"] = {}


def _get_encoder(encoding_name: str) -> "tiktoken.Encoding":
    if encoding_name not in _encoder_cache:
        _encoder_cache[encoding_name] = tiktoken.get_encoding(encoding_name)
    return _encoder_cache[encoding_name]


def count_tokens(text: str, encoding_name: str = _DEFAULT_ENCODING) -> int:
    """Return the exact token count of `text` for the given encoding."""
    if not text:
        return 0
    return len(_get_encoder(encoding_name).encode(text))