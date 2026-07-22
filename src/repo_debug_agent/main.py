"""
Application entrypoint.

Phase 1 responsibility: prove the scaffold works end-to-end —
config loads, logging initializes, and the app boots cleanly.
Later phases will replace this with actual CLI commands
(ingest, index, debug, etc.) using something like `typer`.
"""

from repo_debug_agent.config.settings import get_settings
from repo_debug_agent.core.logger import configure_logging, logger


def main() -> None:
    configure_logging()
    settings = get_settings()

    logger.info("Repo-Aware Autonomous Debugging Agent starting up")
    logger.debug(f"Max debug iterations configured: {settings.max_debug_iterations}")
    logger.debug(f"Workspace directory: {settings.workspace_dir}")

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is not set — LLM phases will fail later")
    if not settings.github_token:
        logger.warning("GITHUB_TOKEN is not set — private repo access will fail later")

    logger.info("Foundation phase healthy. Ready for Phase 2 (Repository Ingestion).")


if __name__ == "__main__":
    main()