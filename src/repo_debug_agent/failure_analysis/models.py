"""
Data models for the failure analysis phase.
"""

from enum import Enum
from pydantic import BaseModel, Field


class StackFrame(BaseModel):
    """One frame of a parsed stack trace, in the order Python prints them
    (outermost/caller first, innermost/where-it-raised last)."""

    file_path: str
    line_number: int
    function_name: str
    code_line: str | None = None


class ParsedException(BaseModel):
    """A single parsed exception with its full call stack."""

    exception_type: str
    message: str
    frames: list[StackFrame] = Field(default_factory=list)
    raw_traceback: str

    @property
    def innermost_frame(self) -> StackFrame | None:
        """The frame where the exception was actually raised — usually
        the highest-value starting point for localization (Phase 7)."""
        return self.frames[-1] if self.frames else None

    @property
    def outermost_frame(self) -> StackFrame | None:
        """The entry point of the call chain that led to the failure."""
        return self.frames[0] if self.frames else None


class TestOutcome(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestFailure(BaseModel):
    """One failing (or errored) test, with its parsed exception if available."""

    node_id: str = Field(description="pytest node id, e.g. 'tests/test_foo.py::test_bar'")
    file_path: str
    outcome: TestOutcome
    exception: ParsedException | None = None
    duration_seconds: float = 0.0


class FailureReport(BaseModel):
    """Full result of a test run."""

    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    failures: list[TestFailure] = Field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return (self.failed + self.errors) > 0