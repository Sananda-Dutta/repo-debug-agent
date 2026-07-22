"""
Shared exception hierarchy for the entire application.

Every phase adds its own exceptions here, all inheriting from
AgentError. This lets callers (e.g., the future FastAPI layer)
catch AgentError broadly for a clean HTTP error response, while
still allowing fine-grained handling where needed.
"""


class AgentError(Exception):
    """Base exception for all Repo-Aware Debugging Agent errors."""


class IngestionError(AgentError):
    """Base exception for repository ingestion failures."""


class InvalidRepoSourceError(IngestionError):
    """Raised when the given input cannot be resolved to a valid repo source."""


class CloneFailedError(IngestionError):
    """Raised when git clone/fetch operations fail."""


class RepoValidationError(IngestionError):
    """Raised when a cloned/local repo fails post-clone sanity checks."""