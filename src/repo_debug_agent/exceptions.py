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
    

class FailureAnalysisError(AgentError):
    """Base exception for stack trace / test failure analysis errors."""


class TestRunError(FailureAnalysisError):
    """
    Raised when pytest itself could not be invoked or produced no report
    (e.g. missing plugin, timeout, bad command). NOT raised when tests
    run successfully but some of them fail — that's a normal, expected
    FailureReport result, not an error.
    """

class ContextRetrievalError(AgentError):
    """Base exception for context fetching/compression failures."""


class AgentLayerError(AgentError):
    """Base exception for LLM agent layer (Phase 9) failures."""


class ParitokProxyError(AgentLayerError):
    """Raised when the local Paritok compression proxy fails to start or become healthy."""


class PatchingError(AgentError):
    """Base exception for Phase 10 (Fix Suggestion & Patching) failures."""


class PatchParsingError(PatchingError):
    """Raised when a fix suggestion can't be parsed into any applicable file change."""


class PatchApplicationError(PatchingError):
    """Raised when applying a parsed patch to the repo checkout fails."""