"""
Troubleshooting Orchestrator - 4-Route Decision System

Routes queries through:
- Route A: KB Search (high confidence → return immediately)
- Route B: Vendor SME Dispatch (manufacturer-specific troubleshooting)
- Route C: Research Trigger (log KB gap, queue async research)
- Route D: General Claude Fallback (best-effort answer)

This is the main entry point for all troubleshooting queries.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from rivet.models.ocr import OCRResult
from rivet.workflows.kb_search import search_knowledge_base
from rivet.workflows.sme_router import route_to_sme, detect_manufacturer
from rivet.workflows.research import trigger_research
from rivet.workflows.general import general_troubleshoot
from rivet.observability.tracer import traced, log_kb_gap

logger = logging.getLogger(__name__)


@dataclass
class TroubleshootResult:
    """Result from troubleshooting orchestrator."""

    answer: str                           # Final answer to user
    route: str                            # Which route provided answer (kb/sme/general/clarify)
    confidence: float                     # Confidence score (0.0-1.0)

    # Metadata
    manufacturer: Optional[str] = None    # Detected manufacturer
    model_number: Optional[str] = None    # Equipment model
    fault_code: Optional[str] = None      # Fault code if present

    # Routing info
    kb_attempted: bool = False
    kb_confidence: Optional[float] = None
    sme_attempted: bool = False
    sme_confidence: Optional[float] = None
    sme_vendor: Optional[str] = None
    research_triggered: bool = False
    clarification_prompt: Optional[str] = None  # Clarifying question if needed

    # Performance
    processing_time_ms: int = 0
    llm_calls: int = 0                    # Total LLM API calls made
    cost_usd: float = 0.0                 # Total cost

    # Safety
    safety_warnings: list = None
    sources: list = None

    def __post_init__(self):
        if self.safety_warnings is None:
            self.safety_warnings = []
        if self.sources is None:
            self.sources = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "answer": self.answer,
            "route": self.route,
            "confidence": self.confidence,
            "manufacturer": self.manufacturer,
            "model_number": self.model_number,
            "fault_code": self.fault_code,
            "kb_attempted": self.kb_attempted,
            "kb_confidence": self.kb_confidence,
            "sme_attempted": self.sme_attempted,
            "sme_confidence": self.sme_confidence,
            "sme_vendor": self.sme_vendor,
            "research_triggered": self.research_triggered,
            "clarification_prompt": self.clarification_prompt,
            "processing_time_ms": self.processing_time_ms,
            "llm_calls": self.llm_calls,
            "cost_usd": self.cost_usd,
            "safety_warnings": self.safety_warnings,
            "sources": self.sources,
        }


@traced(name="troubleshoot", tags=["orchestrator"])
async def troubleshoot(
    query: str,
    ocr_result: Optional[OCRResult] = None,
    user_id: Optional[str] = None,
    min_kb_confidence: float = 0.85,
    min_sme_confidence: float = 0.70,
) -> TroubleshootResult:
    """
    Main troubleshooting orchestrator with 4-route decision logic.

    Routes queries through:
    1. KB Search (if confidence >= 0.85, return immediately)
    2. Vendor SME Dispatch (if manufacturer detected, use vendor expert)
    3. Research Trigger (if SME confidence < 0.70, log KB gap)
    4. General Claude Fallback (best-effort answer)

    Args:
        query: User's troubleshooting question
        ocr_result: Optional OCR data from equipment photo
        user_id: User ID for logging
        min_kb_confidence: Minimum confidence to accept KB answer (default 0.85)
        min_sme_confidence: Minimum confidence to accept SME answer (default 0.70)

    Returns:
        TroubleshootResult with answer and routing metadata

    Example:
        >>> result = await troubleshoot("Siemens S7-1200 F0002 fault, motor won't start")
        >>> print(result.answer)
        >>> print(f"Routed via: {result.route}, Confidence: {result.confidence}")
    """
    start_time = datetime.utcnow()
    total_cost = 0.0
    llm_calls = 0

    user_log = f"[{user_id}]" if user_id else "[troubleshoot]"
    logger.info(f"{user_log} Query: {query[:100]}...")

    # Extract equipment context from OCR
    manufacturer = None
    model_number = None
    fault_code = None

    if ocr_result:
        manufacturer = ocr_result.manufacturer
        model_number = ocr_result.model_number
        fault_code = ocr_result.fault_code
        logger.info(
            f"{user_log} OCR context: {manufacturer} {model_number}, "
            f"fault={fault_code}, confidence={ocr_result.confidence:.0%}"
        )

    # ========================================================================
    # ROUTE A: Knowledge Base Search
    # ========================================================================
    kb_attempted = True
    kb_result = await search_knowledge_base(query, ocr_result)
    llm_calls += kb_result.get("llm_calls", 0)
    total_cost += kb_result.get("cost_usd", 0.0)

    logger.info(
        f"{user_log} Route A (KB Search): "
        f"confidence={kb_result['confidence']:.0%}, "
        f"threshold={min_kb_confidence:.0%}"
    )

    if kb_result["confidence"] >= min_kb_confidence:
        # High confidence KB match - return immediately
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        logger.info(
            f"{user_log} ✅ Returning KB answer "
            f"(confidence={kb_result['confidence']:.0%})"
        )

        return TroubleshootResult(
            answer=kb_result["answer"],
            route="kb",
            confidence=kb_result["confidence"],
            manufacturer=manufacturer,
            model_number=model_number,
            fault_code=fault_code,
            kb_attempted=True,
            kb_confidence=kb_result["confidence"],
            sme_attempted=False,
            research_triggered=False,
            processing_time_ms=elapsed_ms,
            llm_calls=llm_calls,
            cost_usd=total_cost,
            safety_warnings=kb_result.get("safety_warnings", []),
            sources=kb_result.get("sources", []),
        )

    # ========================================================================
    # ROUTE B: Vendor SME Dispatch
    # ========================================================================
    sme_attempted = True

    # Detect manufacturer from query or OCR
    detected_vendor = detect_manufacturer(query, ocr_result)
    logger.info(
        f"{user_log} Route B (SME): Detected vendor = {detected_vendor or 'generic'}"
    )

    # Route to appropriate vendor SME
    sme_result = await route_to_sme(
        query=query,
        vendor=detected_vendor,
        ocr_result=ocr_result,
    )
    llm_calls += sme_result.get("llm_calls", 0)
    total_cost += sme_result.get("cost_usd", 0.0)

    logger.info(
        f"{user_log} Route B (SME): "
        f"vendor={sme_result['vendor']}, "
        f"confidence={sme_result['confidence']:.0%}, "
        f"threshold={min_sme_confidence:.0%}"
    )

    if sme_result["confidence"] >= min_sme_confidence:
        # Acceptable SME answer - return it
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        logger.info(
            f"{user_log} ✅ Returning SME answer "
            f"(vendor={sme_result['vendor']}, confidence={sme_result['confidence']:.0%})"
        )

        return TroubleshootResult(
            answer=sme_result["answer"],
            route="sme",
            confidence=sme_result["confidence"],
            manufacturer=manufacturer or detected_vendor,
            model_number=model_number,
            fault_code=fault_code,
            kb_attempted=True,
            kb_confidence=kb_result["confidence"],
            sme_attempted=True,
            sme_confidence=sme_result["confidence"],
            sme_vendor=sme_result["vendor"],
            research_triggered=False,
            processing_time_ms=elapsed_ms,
            llm_calls=llm_calls,
            cost_usd=total_cost,
            safety_warnings=sme_result.get("safety_warnings", []),
            sources=sme_result.get("sources", []),
        )

    # ========================================================================
    # ROUTE C: Research Trigger (KB gap detected) / CLARIFY
    # ========================================================================
    # SME confidence < threshold → check if clarification needed or log KB gap

    research_result = await trigger_research(
        query=query,
        kb_confidence=kb_result["confidence"],
        sme_confidence=sme_result["confidence"],
        ocr_result=ocr_result,
    )

    # Check if clarification needed (confidence <0.4)
    if research_result.get("clarification_needed"):
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        clarification_prompt = research_result["clarification_prompt"]

        logger.info(
            f"{user_log} Route C (CLARIFY): Requesting clarification "
            f"(kb={kb_result['confidence']:.0%}, sme={sme_result['confidence']:.0%})"
        )

        return TroubleshootResult(
            answer=clarification_prompt,
            route="clarify",
            confidence=max(kb_result["confidence"], sme_result["confidence"]),
            manufacturer=manufacturer or detected_vendor,
            model_number=model_number,
            fault_code=fault_code,
            kb_attempted=True,
            kb_confidence=kb_result["confidence"],
            sme_attempted=True,
            sme_confidence=sme_result["confidence"],
            sme_vendor=sme_result["vendor"],
            research_triggered=False,
            clarification_prompt=clarification_prompt,
            processing_time_ms=elapsed_ms,
            llm_calls=llm_calls,
            cost_usd=total_cost,
            safety_warnings=[],
            sources=[],
        )

    # Knowledge gap logged for research
    research_triggered = research_result.get("gap_logged", False)

    if research_triggered:
        # Legacy observability logging (still used for monitoring)
        log_kb_gap(
            query=query,
            manufacturer=manufacturer or detected_vendor,
            model_number=model_number,
            fault_code=fault_code,
        )

        logger.info(
            f"{user_log} Route C (RESEARCH): KB gap logged "
            f"(kb={kb_result['confidence']:.0%}, sme={sme_result['confidence']:.0%})"
        )
    else:
        logger.info(
            f"{user_log} Route C (RESEARCH): Gap logging skipped "
            f"(kb={kb_result['confidence']:.0%}, sme={sme_result['confidence']:.0%})"
        )

    # ========================================================================
    # ROUTE D: General Claude Fallback
    # ========================================================================
    # Continue to fallback (don't wait for research)
    logger.info(f"{user_log} Route D (General Fallback): Using Claude Opus")

    general_result = await general_troubleshoot(
        query=query,
        ocr_result=ocr_result,
    )
    llm_calls += general_result.get("llm_calls", 0)
    total_cost += general_result.get("cost_usd", 0.0)

    elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    logger.info(
        f"{user_log} ✅ Returning general fallback answer "
        f"(confidence={general_result['confidence']:.0%})"
    )

    return TroubleshootResult(
        answer=general_result["answer"],
        route="general",
        confidence=general_result["confidence"],
        manufacturer=manufacturer or detected_vendor,
        model_number=model_number,
        fault_code=fault_code,
        kb_attempted=True,
        kb_confidence=kb_result["confidence"],
        sme_attempted=True,
        sme_confidence=sme_result["confidence"],
        sme_vendor=sme_result["vendor"],
        research_triggered=True,
        processing_time_ms=elapsed_ms,
        llm_calls=llm_calls,
        cost_usd=total_cost,
        safety_warnings=general_result.get("safety_warnings", []),
        sources=general_result.get("sources", []),
    )


# Convenience sync wrapper
def troubleshoot_sync(
    query: str,
    ocr_result: Optional[OCRResult] = None,
    **kwargs
) -> TroubleshootResult:
    """Synchronous wrapper for troubleshoot()."""
    import asyncio
    return asyncio.run(troubleshoot(query, ocr_result, **kwargs))
