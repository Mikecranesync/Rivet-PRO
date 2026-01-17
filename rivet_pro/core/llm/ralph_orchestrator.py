"""
RalphOrchestrator - Base orchestration framework for multi-LLM photo pipeline.

Provides the foundation for photo screening, spec extraction, and KB analysis
using multiple LLM providers. Includes retry logic, cost tracking, and caching.

Part of PHOTO-ORCH-001: Ralph Wiggum Orchestrator Base Class.
"""

import hashlib
import time
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TypeVar, Callable, Awaitable, List
from datetime import datetime

from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

# Type variable for generic retry function
T = TypeVar('T')


@dataclass
class LLMCallResult:
    """Result from an LLM call with cost and timing info."""
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    latency_ms: float = 0.0
    provider: str = ""


@dataclass
class PipelineStageResult:
    """Result from a pipeline stage with timing."""
    stage: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    llm_calls: List[LLMCallResult] = field(default_factory=list)


@dataclass
class OrchestratorSettings:
    """Configuration settings for the orchestrator."""
    # Retry settings
    max_retries: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 5000

    # Cost limits (in USD)
    max_cost_per_photo: float = 0.10
    warn_cost_threshold: float = 0.05

    # Timeouts (in seconds)
    screening_timeout: float = 10.0
    extraction_timeout: float = 15.0
    kb_analysis_timeout: float = 20.0

    # Feature flags
    enable_caching: bool = True
    enable_cost_tracking: bool = True


class RalphOrchestrator(ABC):
    """
    Base orchestration framework for multi-LLM photo pipeline.

    Provides:
    - Abstract methods for pipeline stages (screen_photo, extract_specs, analyze_with_kb)
    - Retry helper with exponential backoff
    - Cost tracking aggregation
    - Photo hash computation for caching
    - Timing/logging for each stage

    Usage:
        class MyOrchestrator(RalphOrchestrator):
            async def screen_photo(self, image_bytes: bytes) -> PipelineStageResult:
                # Implement screening logic
                pass

            async def extract_specs(self, image_bytes: bytes, context: dict) -> PipelineStageResult:
                # Implement extraction logic
                pass

            async def analyze_with_kb(self, specs: dict, kb_context: dict) -> PipelineStageResult:
                # Implement KB analysis
                pass
    """

    def __init__(
        self,
        db_pool: Any,
        settings: Optional[OrchestratorSettings] = None
    ):
        """
        Initialize the orchestrator.

        Args:
            db_pool: Database connection pool (asyncpg pool or compatible)
            settings: Configuration settings (uses defaults if not provided)
        """
        self.db_pool = db_pool
        self.settings = settings or OrchestratorSettings()

        # Cost tracking
        self._llm_calls: List[LLMCallResult] = []
        self._session_start = datetime.utcnow()

        logger.info(
            f"RalphOrchestrator initialized | "
            f"max_retries={self.settings.max_retries} | "
            f"max_cost=${self.settings.max_cost_per_photo:.2f}"
        )

    # =========================================================================
    # Abstract methods - must be implemented by subclasses
    # =========================================================================

    @abstractmethod
    async def screen_photo(
        self,
        image_bytes: bytes,
        photo_hash: str
    ) -> PipelineStageResult:
        """
        Screen photo for quality and content type.

        First stage of the pipeline - quick rejection of non-equipment photos.
        Should use a fast, cheap model (e.g., Gemini Flash).

        Args:
            image_bytes: Raw image data
            photo_hash: SHA256 hash for caching

        Returns:
            PipelineStageResult with:
            - success: True if photo passes screening
            - data: {"is_equipment": bool, "confidence": float, "rejection_reason": str|None}
        """
        pass

    @abstractmethod
    async def extract_specs(
        self,
        image_bytes: bytes,
        photo_hash: str,
        screening_context: Dict[str, Any]
    ) -> PipelineStageResult:
        """
        Extract equipment specifications from photo.

        Second stage - detailed OCR and spec extraction.
        Should use a capable vision model (e.g., Gemini Pro Vision).

        Args:
            image_bytes: Raw image data
            photo_hash: SHA256 hash for caching
            screening_context: Context from screening stage

        Returns:
            PipelineStageResult with:
            - success: True if specs extracted
            - data: {"manufacturer": str, "model": str, "serial": str, ...}
        """
        pass

    @abstractmethod
    async def analyze_with_kb(
        self,
        specs: Dict[str, Any],
        photo_hash: str
    ) -> PipelineStageResult:
        """
        Analyze specs against knowledge base.

        Third stage - enrich with KB data, find manuals, etc.
        Can use Claude or other reasoning model.

        Args:
            specs: Extracted specifications from previous stage
            photo_hash: SHA256 hash for caching

        Returns:
            PipelineStageResult with:
            - success: True if analysis completed
            - data: {"kb_match": dict|None, "manuals": list, "recommendations": list}
        """
        pass

    # =========================================================================
    # Retry helper with exponential backoff
    # =========================================================================

    async def with_retry(
        self,
        func: Callable[[], Awaitable[T]],
        operation_name: str = "operation",
        max_retries: Optional[int] = None,
        base_delay_ms: Optional[int] = None
    ) -> T:
        """
        Execute an async function with exponential backoff retry.

        Args:
            func: Async function to execute
            operation_name: Name for logging
            max_retries: Override default max retries (default: 3)
            base_delay_ms: Override default base delay (default: 100ms)

        Returns:
            Result from the function

        Raises:
            Last exception if all retries exhausted
        """
        retries = max_retries if max_retries is not None else self.settings.max_retries
        delay_ms = base_delay_ms if base_delay_ms is not None else self.settings.base_delay_ms

        last_error: Optional[Exception] = None

        for attempt in range(retries):
            try:
                return await func()
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    # Calculate exponential backoff with jitter
                    wait_ms = min(
                        delay_ms * (2 ** attempt),
                        self.settings.max_delay_ms
                    )
                    # Add 10% jitter
                    wait_ms = int(wait_ms * (0.9 + 0.2 * (time.time() % 1)))

                    logger.warning(
                        f"Retry {attempt + 1}/{retries} for {operation_name} | "
                        f"error={str(e)[:100]} | wait={wait_ms}ms"
                    )
                    await asyncio.sleep(wait_ms / 1000)
                else:
                    logger.error(
                        f"All {retries} retries exhausted for {operation_name} | "
                        f"error={str(e)[:200]}"
                    )

        # Should not reach here, but satisfy type checker
        if last_error:
            raise last_error
        raise RuntimeError(f"Retry loop completed without result for {operation_name}")

    # =========================================================================
    # Cost tracking
    # =========================================================================

    def record_llm_call(self, result: LLMCallResult) -> None:
        """
        Record an LLM call for cost tracking.

        Args:
            result: LLM call result with cost info
        """
        self._llm_calls.append(result)

        if self.settings.enable_cost_tracking:
            logger.info(
                f"LLM call recorded | model={result.model} | "
                f"cost=${result.cost_usd:.4f} | latency={result.latency_ms:.0f}ms"
            )

            # Warn if approaching cost limit
            total = self.total_cost_usd
            if total > self.settings.warn_cost_threshold:
                logger.warning(
                    f"Cost warning | total=${total:.4f} | "
                    f"threshold=${self.settings.warn_cost_threshold:.2f}"
                )

    @property
    def total_cost_usd(self) -> float:
        """Get total cost of all LLM calls in this session."""
        return sum(call.cost_usd for call in self._llm_calls)

    @property
    def total_input_tokens(self) -> int:
        """Get total input tokens used in this session."""
        return sum(call.input_tokens for call in self._llm_calls)

    @property
    def total_output_tokens(self) -> int:
        """Get total output tokens used in this session."""
        return sum(call.output_tokens for call in self._llm_calls)

    def get_cost_breakdown(self) -> Dict[str, Any]:
        """Get detailed cost breakdown by model/provider."""
        breakdown: Dict[str, Dict[str, Any]] = {}

        for call in self._llm_calls:
            key = f"{call.provider}:{call.model}"
            if key not in breakdown:
                breakdown[key] = {
                    "calls": 0,
                    "cost_usd": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_latency_ms": 0.0
                }
            breakdown[key]["calls"] += 1
            breakdown[key]["cost_usd"] += call.cost_usd
            breakdown[key]["input_tokens"] += call.input_tokens
            breakdown[key]["output_tokens"] += call.output_tokens
            breakdown[key]["total_latency_ms"] += call.latency_ms

        return {
            "total_cost_usd": self.total_cost_usd,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "call_count": len(self._llm_calls),
            "by_model": breakdown
        }

    def reset_cost_tracking(self) -> None:
        """Reset cost tracking for a new session."""
        self._llm_calls = []
        self._session_start = datetime.utcnow()

    # =========================================================================
    # Photo hash computation
    # =========================================================================

    @staticmethod
    def compute_photo_hash(image_bytes: bytes) -> str:
        """
        Compute SHA256 hash of image bytes for caching.

        Args:
            image_bytes: Raw image data

        Returns:
            Hex string of SHA256 hash
        """
        return hashlib.sha256(image_bytes).hexdigest()

    # =========================================================================
    # Timing helpers
    # =========================================================================

    def timed_stage(
        self,
        stage_name: str
    ) -> "StageTimer":
        """
        Create a context manager for timing a pipeline stage.

        Usage:
            with self.timed_stage("screening") as timer:
                result = await self._do_screening()
            print(f"Took {timer.elapsed_ms}ms")

        Args:
            stage_name: Name of the stage for logging

        Returns:
            StageTimer context manager
        """
        return StageTimer(stage_name, logger)


class StageTimer:
    """Context manager for timing pipeline stages."""

    def __init__(self, stage_name: str, logger_instance):
        self.stage_name = stage_name
        self.logger = logger_instance
        self.start_time: float = 0
        self.end_time: float = 0

    def __enter__(self) -> "StageTimer":
        self.start_time = time.perf_counter()
        self.logger.debug(f"Stage '{self.stage_name}' started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.logger.info(
            f"Stage '{self.stage_name}' completed | "
            f"elapsed={self.elapsed_ms:.0f}ms | "
            f"success={exc_type is None}"
        )
        return False  # Don't suppress exceptions

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.end_time == 0:
            return (time.perf_counter() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000
