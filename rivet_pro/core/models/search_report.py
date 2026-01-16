"""
Search Transparency Report Model

Captures metadata about manual search attempts for user-facing transparency.
Shows proof of thorough searching when manual is not found.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SearchStage(Enum):
    """Search stages in order of execution."""
    LOCAL_FILES = "local_files"
    DATABASE_CACHE = "database_cache"
    EXTERNAL_SEARCH = "external_search"
    LLM_VALIDATION = "llm_validation"


class SearchStatus(Enum):
    """Status of each search attempt."""
    SUCCESS = "success"       # Found and passed validation
    NOT_FOUND = "not_found"   # Source searched, nothing found
    REJECTED = "rejected"     # Found but failed validation
    SKIPPED = "skipped"       # Stage skipped (e.g., no API key)
    ERROR = "error"           # Stage failed with error


@dataclass
class RejectedURL:
    """A URL that was found but rejected by LLM validation."""
    url: str
    title: Optional[str]
    confidence: float
    rejection_reason: str
    validator: str = "llm"  # Which LLM rejected it: claude, openai, groq, deepseek

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "confidence": self.confidence,
            "rejection_reason": self.rejection_reason,
            "validator": self.validator
        }


@dataclass
class SearchStageResult:
    """Result of a single search stage."""
    stage: SearchStage
    status: SearchStatus
    duration_ms: int
    details: Optional[str] = None
    urls_found: int = 0
    urls_rejected: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "details": self.details,
            "urls_found": self.urls_found,
            "urls_rejected": self.urls_rejected
        }


@dataclass
class SearchReport:
    """
    Complete transparency report for a manual search.

    Captures all search attempts and their results for user display.
    """
    manufacturer: str
    model: str
    search_started_at: datetime = field(default_factory=datetime.utcnow)
    stages: List[SearchStageResult] = field(default_factory=list)
    rejected_urls: List[RejectedURL] = field(default_factory=list)
    total_duration_ms: int = 0
    sources_searched: int = 0
    urls_evaluated: int = 0
    urls_rejected: int = 0
    manual_found: bool = False
    manual_url: Optional[str] = None

    def add_stage(
        self,
        stage: SearchStage,
        status: SearchStatus,
        duration_ms: int,
        details: Optional[str] = None,
        urls_found: int = 0,
        urls_rejected: int = 0
    ) -> None:
        """Add a search stage result."""
        self.stages.append(SearchStageResult(
            stage=stage,
            status=status,
            duration_ms=duration_ms,
            details=details,
            urls_found=urls_found,
            urls_rejected=urls_rejected
        ))
        self.total_duration_ms += duration_ms
        self.sources_searched += 1
        self.urls_evaluated += urls_found
        self.urls_rejected += urls_rejected

    def add_rejected_url(
        self,
        url: str,
        title: Optional[str],
        confidence: float,
        rejection_reason: str,
        validator: str = "llm"
    ) -> None:
        """Record a URL that was rejected."""
        self.rejected_urls.append(RejectedURL(
            url=url,
            title=title,
            confidence=confidence,
            rejection_reason=rejection_reason,
            validator=validator
        ))

    def complete(self, manual_found: bool, manual_url: Optional[str] = None) -> None:
        """Mark search as complete."""
        self.manual_found = manual_found
        self.manual_url = manual_url
        self.total_duration_ms = int(
            (datetime.utcnow() - self.search_started_at).total_seconds() * 1000
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "search_started_at": self.search_started_at.isoformat(),
            "stages": [s.to_dict() for s in self.stages],
            "rejected_urls": [r.to_dict() for r in self.rejected_urls],
            "total_duration_ms": self.total_duration_ms,
            "sources_searched": self.sources_searched,
            "urls_evaluated": self.urls_evaluated,
            "urls_rejected": self.urls_rejected,
            "manual_found": self.manual_found,
            "manual_url": self.manual_url
        }

    @property
    def best_candidate(self) -> Optional[RejectedURL]:
        """
        Get the best rejected URL candidate for human-in-the-loop validation.

        Returns the rejected URL with highest confidence score.
        Used when no direct PDF found but we have close matches to show the user.
        """
        if not self.rejected_urls:
            return None
        return max(self.rejected_urls, key=lambda r: r.confidence)

    def __str__(self) -> str:
        status = "FOUND" if self.manual_found else "NOT_FOUND"
        return (
            f"SearchReport({self.manufacturer} {self.model}, "
            f"{status}, {self.sources_searched} sources, "
            f"{self.urls_evaluated} URLs evaluated, {self.total_duration_ms}ms)"
        )
