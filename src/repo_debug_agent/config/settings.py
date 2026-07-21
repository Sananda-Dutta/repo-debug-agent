"""
Centralized application configuration.

All environment-driven values (API keys, paths, limits) MUST be
read through this module. No other module should call os.environ
directly — this keeps configuration auditable in one place.
"""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM Provider ---
    openai_api_key: str = Field(default="", description="OpenAI API key for agent reasoning")

    # --- GitHub ---
    github_token: str = Field(default="", description="GitHub personal access token for repo cloning/API")

    # --- Agent behavior ---
    max_debug_iterations: int = Field(default=5, description="Max fix-test iteration loops before stopping")
    log_level: str = Field(default="INFO", description="Logging verbosity")

    # --- Storage paths ---
    workspace_dir: str = Field(default="./workspace", description="Where cloned repos are stored locally")
    vector_store_dir: str = Field(default="./vector_store", description="Where FAISS/Chroma indices are persisted")


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    lru_cache ensures we parse the environment only once per process,
    instead of re-reading/re-validating .env on every call site.
    """
    return Settings()