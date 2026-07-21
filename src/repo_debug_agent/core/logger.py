"""
Centralized logging configuration using loguru.

Every module should import `logger` from here rather than
instantiating its own logger — this guarantees consistent
formatting and a single place to change log behavior (e.g.,
adding file sinks, JSON output for production).
"""

import sys
from loguru import logger

from repo_debug_agent.config.settings import get_settings


def configure_logging() -> None:
    """Configure loguru sinks based on application settings."""
    settings = get_settings()

    logger.remove()  # remove loguru's default handler to avoid duplicate logs

    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    logger.add(
        "logs/agent.log",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )


__all__ = ["logger", "configure_logging"]