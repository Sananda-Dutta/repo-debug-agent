"""
Tests for the configuration layer.

We test that:
1. Settings load with sane defaults when no env vars are present.
2. Settings correctly pick up overrides from environment variables.
"""

import os
from repo_debug_agent.config.settings import Settings


def test_settings_defaults():
    """Settings should load with defaults even with no .env / env vars set."""
    settings = Settings(_env_file=None)  # bypass .env for a clean-slate test
    assert settings.max_debug_iterations == 5
    assert settings.log_level == "INFO"


def test_settings_env_override(monkeypatch):
    """Environment variables should override defaults."""
    monkeypatch.setenv("MAX_DEBUG_ITERATIONS", "10")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)
    assert settings.max_debug_iterations == 10
    assert settings.log_level == "DEBUG"