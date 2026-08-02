"""
Data models for the file localization phase.
"""

from enum import Enum
from pydantic import BaseModel, Field


class RelevanceSource(str, Enum):
    ANCHOR = "anchor"           # the exact file/line the exception was raised at
    STRUCTURAL = "structural"   # found via dependency graph traversal
    SEMANTIC = "semantic"       # found via vector similarity search


class RankedFile(BaseModel):
    """One file, with its aggregated relevance score and contributing sources."""
    """This represents one file that the localization engine thinks is relevant."""

    file_path: str
    score: float
    sources: list[RelevanceSource] = Field(default_factory=list) #where the relevance came from.
    relevant_symbols: list[str] = Field( #This is about which symbols inside the file are relevant.
        default_factory=list,
        description="Qualified names known to be specifically relevant (empty = whole file, unknown symbol-level detail)",
    )
    hop_distance: int | None = Field(default=None, description="Graph distance from anchor, if structural")
    #This is related to the dependency graph.

class LocalizationResult(BaseModel):
    """Full output of the localization engine for one failure."""
    """This represents the complete localization result for one failure."""

    anchor_file: str | None #This is the file where the exception was actually raised.
    anchor_symbol: str | None #This identifies the specific function/class/method associated with the failure.
    ranked_files: list[RankedFile] = Field(default_factory=list) #It contains all the files the localization engine found, ranked by relevance.

    def top_files(self, n: int = 10) -> list[RankedFile]:
        return self.ranked_files[:n]