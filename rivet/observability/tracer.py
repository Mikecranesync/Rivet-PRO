"""
Observability - Phoenix + LangSmith Tracing

Provides tracing for debugging and KB gap detection.
"""

import os
import logging
from functools import wraps
from typing import Optional, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import Phoenix
try:
    import phoenix as px
    from phoenix.otel import register as phoenix_register
    PHOENIX_AVAILABLE = True
except ImportError:
    PHOENIX_AVAILABLE = False
    logger.info("Phoenix not available. Install with: pip install arize-phoenix")

# Try to import LangSmith
try:
    from langsmith import traceable
    from langsmith.run_helpers import get_current_run_tree
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    # Fallback no-op decorator
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def get_current_run_tree():
        return None


def init_tracing(
    project_name: str = "rivet-pro",
    phoenix_endpoint: Optional[str] = None,
) -> bool:
    """
    Initialize tracing backends.

    Returns:
        True if at least one backend initialized
    """
    initialized = False

    # Phoenix
    if PHOENIX_AVAILABLE:
        endpoint = phoenix_endpoint or os.getenv("PHOENIX_ENDPOINT")
        if endpoint:
            try:
                phoenix_register(
                    project_name=project_name,
                    endpoint=endpoint,
                )
                logger.info(f"Phoenix tracing initialized: {endpoint}")
                initialized = True
            except Exception as e:
                logger.warning(f"Phoenix initialization failed: {e}")

    # LangSmith (auto-initializes from env vars)
    if LANGSMITH_AVAILABLE:
        if os.getenv("LANGSMITH_API_KEY"):
            logger.info("LangSmith tracing available")
            initialized = True

    return initialized


def traced(
    name: Optional[str] = None,
    tags: Optional[list] = None,
    metadata: Optional[dict] = None,
):
    """
    Decorator for tracing function calls.

    Works with both Phoenix and LangSmith.

    Usage:
        @traced(name="ocr_analyze", tags=["ocr"])
        async def analyze_image(image_bytes):
            ...
    """
    def decorator(func: Callable) -> Callable:
        trace_name = name or func.__name__
        trace_tags = tags or []
        trace_metadata = metadata or {}

        # Apply LangSmith traceable if available
        if LANGSMITH_AVAILABLE:
            func = traceable(
                name=trace_name,
                tags=trace_tags,
                metadata=trace_metadata,
            )(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.debug(f"[TRACE] {trace_name} completed in {elapsed_ms:.0f}ms")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.debug(f"[TRACE] {trace_name} completed in {elapsed_ms:.0f}ms")

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_ocr_result(
    result: Any,
    user_id: Optional[str] = None,
    image_size_bytes: int = 0,
):
    """Log OCR result for observability."""
    if LANGSMITH_AVAILABLE:
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.metadata.update({
                "user_id": user_id,
                "image_size_bytes": image_size_bytes,
                "provider": getattr(result, "provider", "unknown"),
                "model_used": getattr(result, "model_used", None),
                "confidence": getattr(result, "confidence", 0.0),
                "manufacturer": getattr(result, "manufacturer", None),
                "model_number": getattr(result, "model_number", None),
                "equipment_type": getattr(result, "equipment_type", None),
                "has_error": getattr(result, "error", None) is not None,
                "cost_usd": getattr(result, "cost_usd", 0.0),
                "processing_ms": getattr(result, "processing_time_ms", 0),
            })


def log_kb_gap(
    query: str,
    manufacturer: Optional[str] = None,
    model_number: Optional[str] = None,
    fault_code: Optional[str] = None,
):
    """
    Log a knowledge base gap for later amplification.

    This triggers async research to fill the gap.
    """
    gap_data = {
        "query": query,
        "manufacturer": manufacturer,
        "model_number": model_number,
        "fault_code": fault_code,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Log to file for now (Phase 5 will add DB storage)
    logger.info(f"[KB_GAP] {gap_data}")

    # TODO: Phase 5 - Write to database for research queue
