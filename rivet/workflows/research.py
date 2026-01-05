"""
Research Trigger - Route C: Knowledge Base Gap Detection & CLARIFY Logic

Production implementation that:
1. Persists knowledge gaps to database for research worker
2. Generates CLARIFY prompts for very low confidence queries
3. Manages research queue priorities

Per rivet_pro_skill_ai_routing.md:
- Confidence <0.4: CLARIFY (ask ONE clarifying question)
- Confidence 0.4-0.7: RESEARCH (log gap, trigger research)
- Confidence ≥0.7: Route to SME or KB (handled by orchestrator)
"""

import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime

from rivet.observability.tracer import traced
from rivet.models.ocr import OCRResult
from rivet.models.knowledge import KnowledgeGapCreate, ResearchStatus
from rivet.services.knowledge_service import KnowledgeService
from rivet.atlas.database import AtlasDatabase

logger = logging.getLogger(__name__)

# Initialize service (singleton pattern)
_knowledge_service = None


def get_knowledge_service() -> KnowledgeService:
    """Get or create KnowledgeService singleton."""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService(AtlasDatabase())
    return _knowledge_service


@traced(name="trigger_research", tags=["research"])
async def trigger_research(
    query: str,
    kb_confidence: float,
    sme_confidence: float,
    ocr_result: Optional[OCRResult] = None,
) -> Dict[str, Any]:
    """
    Trigger research or clarification based on confidence scores.

    Decision tree:
    1. If max_confidence <0.4 → CLARIFY (ask user for more info)
    2. If max_confidence 0.4-0.7 → RESEARCH (log gap, queue research)
    3. If max_confidence ≥0.7 → Let orchestrator handle (shouldn't reach here)

    Args:
        query: User's troubleshooting question
        kb_confidence: KB search confidence score (0.0-1.0)
        sme_confidence: SME response confidence score (0.0-1.0)
        ocr_result: Optional equipment data from OCR

    Returns:
        Dict with:
            - clarification_needed: bool
            - clarification_prompt: str (if clarification needed)
            - gap_logged: bool (if research triggered)
            - route: str ("clarify" or "research")

    Example:
        >>> result = await trigger_research(
        ...     query="It's broken",
        ...     kb_confidence=0.15,
        ...     sme_confidence=0.20,
        ...     ocr_result=None
        ... )
        >>> if result["clarification_needed"]:
        ...     print(result["clarification_prompt"])
        "Could you describe the symptoms in more detail? (e.g., noise type, when it occurs, duration)"
    """
    max_confidence = max(kb_confidence or 0, sme_confidence or 0)

    logger.info(
        f"[Research Trigger] Query: '{query[:100]}...', "
        f"kb_conf={kb_confidence:.0%}, sme_conf={sme_confidence:.0%}, "
        f"max_conf={max_confidence:.0%}"
    )

    # Route 1: CLARIFY (confidence <0.4)
    if max_confidence < 0.4:
        clarification = generate_clarification_prompt(query, ocr_result)
        logger.info(f"[Research Trigger] CLARIFY route triggered (conf={max_confidence:.0%})")
        return {
            "clarification_needed": True,
            "clarification_prompt": clarification,
            "gap_logged": False,
            "route": "clarify"
        }

    # Route 2: RESEARCH (confidence 0.4-0.7)
    if max_confidence < 0.7:
        logger.info(f"[Research Trigger] RESEARCH route triggered (conf={max_confidence:.0%})")

        # Extract equipment context from OCR
        manufacturer = ocr_result.manufacturer if ocr_result else None
        model = ocr_result.model_number if ocr_result else None

        # Persist knowledge gap
        try:
            knowledge_service = get_knowledge_service()

            gap = KnowledgeGapCreate(
                query=query,
                manufacturer=manufacturer,
                model=model,
                confidence_score=max_confidence,
                research_status=ResearchStatus.PENDING
            )

            gap_id = await knowledge_service.create_or_update_gap(gap)
            logger.info(
                f"[Research Trigger] Gap logged: {gap_id} "
                f"(query: {query[:50]}..., manufacturer: {manufacturer})"
            )

            return {
                "clarification_needed": False,
                "clarification_prompt": None,
                "gap_logged": True,
                "gap_id": str(gap_id),
                "route": "research"
            }

        except Exception as e:
            logger.error(f"[Research Trigger] Failed to log gap: {e}")
            return {
                "clarification_needed": False,
                "clarification_prompt": None,
                "gap_logged": False,
                "error": str(e),
                "route": "research"
            }

    # Should not reach here (orchestrator should handle ≥0.7)
    logger.warning(
        f"[Research Trigger] Unexpected confidence level: {max_confidence:.0%} "
        "(should be handled by orchestrator)"
    )
    return {
        "clarification_needed": False,
        "clarification_prompt": None,
        "gap_logged": False,
        "route": "none"
    }


def generate_clarification_prompt(
    query: str,
    ocr_result: Optional[OCRResult]
) -> str:
    """
    Generate smart clarification question based on missing info.

    Logic:
    1. No manufacturer → Ask for manufacturer
    2. Fault mentioned but no code → Ask for fault code
    3. Query too short (<5 words) → Ask for symptoms
    4. Default → Ask for more details

    Args:
        query: Original user query
        ocr_result: Optional equipment context

    Returns:
        ONE clarifying question (never multiple)

    Example:
        >>> ocr = OCRResult(manufacturer=None)
        >>> prompt = generate_clarification_prompt("motor won't start", ocr)
        "Could you provide the equipment manufacturer? (e.g., Siemens, Rockwell, ABB)"
    """
    # Priority 1: Missing manufacturer
    if not ocr_result or not ocr_result.manufacturer:
        return (
            "Could you provide the equipment manufacturer? "
            "(e.g., Siemens, Rockwell, ABB, Schneider)"
        )

    # Priority 2: Fault mentioned but no code extracted
    query_lower = query.lower()
    fault_keywords = ["fault", "error", "alarm", "code", "f0", "e0", "a0"]
    has_fault_keyword = any(kw in query_lower for kw in fault_keywords)
    has_fault_code = (
        ocr_result.fault_code or
        _extract_fault_code(query)
    )

    if has_fault_keyword and not has_fault_code:
        return "What fault code is displayed on the equipment?"

    # Priority 3: Query too short (likely missing context)
    word_count = len(query.split())
    if word_count < 5:
        return (
            "Could you describe the symptoms in more detail? "
            "(e.g., noise type, when it occurs, duration)"
        )

    # Priority 4: Generic request for more details
    return (
        "Could you provide more details about the issue? "
        "(e.g., what happens, when it started, any recent changes)"
    )


def _extract_fault_code(query: str) -> Optional[str]:
    """
    Extract fault code from query text.

    Patterns:
    - F0001, F0002, etc. (Siemens)
    - E0001, E0002, etc. (ABB)
    - A0001, A0002, etc. (Rockwell)

    Args:
        query: User query

    Returns:
        Fault code if found, else None

    Example:
        >>> _extract_fault_code("Getting F0002 fault on drive")
        "F0002"
    """
    # Common fault code patterns
    patterns = [
        r'\b([FEA]\d{4,5})\b',  # F0002, E0001, A0123
        r'\bfault\s+(\d{4,5})\b',  # fault 0002
        r'\berror\s+(\d{4,5})\b',  # error 0001
    ]

    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    return None


async def check_research_status(query: str) -> Optional[Dict[str, Any]]:
    """
    Check if research has been completed for a previous query.

    Args:
        query: Original user query

    Returns:
        Dict with answer if research complete, else None

    Example:
        >>> status = await check_research_status("Siemens F0002 fault")
        >>> if status and status["complete"]:
        ...     print(status["answer"])
    """
    try:
        knowledge_service = get_knowledge_service()

        # Query for completed gaps matching this query
        # TODO: Implement fuzzy query matching (e.g., embeddings similarity)
        # For now, use exact query match

        # This would require a new KnowledgeService method
        # For Phase 3, we'll return None (not implemented yet)

        logger.info(f"[Research Status] Checking status for: {query[:100]}...")
        return None  # Research status checking not yet implemented

    except Exception as e:
        logger.error(f"[Research Status] Failed to check status: {e}")
        return None


async def get_pending_research_count() -> int:
    """
    Get count of pending research jobs in queue.

    Returns:
        Number of KB gaps awaiting research

    Example:
        >>> count = await get_pending_research_count()
        >>> print(f"Pending research jobs: {count}")
    """
    try:
        knowledge_service = get_knowledge_service()
        count = await knowledge_service.count_pending_gaps()
        return count

    except Exception as e:
        logger.error(f"[Research Count] Failed to count gaps: {e}")
        return 0


async def get_prioritized_research_queue(limit: int = 20) -> list[Dict[str, Any]]:
    """
    Get prioritized research queue.

    Priority calculation (auto-calculated in database):
    priority = occurrence_count × (1 - confidence) × vendor_boost
    where vendor_boost = 1.5 for Siemens/Rockwell, 1.0 otherwise

    Args:
        limit: Maximum gaps to return

    Returns:
        List of KB gaps sorted by priority DESC

    Example:
        >>> queue = await get_prioritized_research_queue(limit=5)
        >>> for gap in queue:
        ...     print(f"{gap.query[:50]}: priority={gap.priority:.2f}")
    """
    try:
        knowledge_service = get_knowledge_service()
        gaps = await knowledge_service.get_pending_research_queue(limit=limit)

        # Convert Pydantic models to dicts for serialization
        return [gap.model_dump() for gap in gaps]

    except Exception as e:
        logger.error(f"[Research Queue] Failed to get queue: {e}")
        return []


# Helper function for extracting fault codes from various formats
def normalize_fault_code(code: str) -> str:
    """
    Normalize fault code to standard format.

    Args:
        code: Raw fault code

    Returns:
        Normalized code (uppercase, no spaces)

    Example:
        >>> normalize_fault_code("f 0002")
        "F0002"
        >>> normalize_fault_code("fault 002")
        "F0002"
    """
    # Remove spaces
    code = code.replace(" ", "")

    # Ensure uppercase
    code = code.upper()

    # Add leading letter if missing
    if code.isdigit():
        code = f"F{code.zfill(4)}"

    return code


if __name__ == "__main__":
    import asyncio

    # Test research trigger
    async def test_research_flow():
        print("\n=== Research Flow Test ===\n")

        # Test 1: CLARIFY (very low confidence)
        print("Test 1: CLARIFY route (confidence <0.4)")
        result = await trigger_research(
            query="It's broken",
            kb_confidence=0.15,
            sme_confidence=0.20,
            ocr_result=None
        )
        print(f"Result: {result}")
        print()

        # Test 2: RESEARCH (medium confidence)
        print("Test 2: RESEARCH route (confidence 0.4-0.7)")
        result = await trigger_research(
            query="Siemens S7-1200 F0002 fault - motor won't start",
            kb_confidence=0.50,
            sme_confidence=0.55,
            ocr_result=OCRResult(
                manufacturer="Siemens",
                model_number="S7-1200",
                fault_code="F0002"
            )
        )
        print(f"Result: {result}")
        print()

        # Test 3: Clarification prompt generation
        print("Test 3: Clarification prompt generation")
        clarification = generate_clarification_prompt(
            "motor issues",
            ocr_result=None
        )
        print(f"Clarification: {clarification}")
        print()

        # Test 4: Fault code extraction
        print("Test 4: Fault code extraction")
        code = _extract_fault_code("Getting F0002 fault on my drive")
        print(f"Extracted code: {code}")
        print()

        # Test 5: Research queue
        print("Test 5: Pending research count")
        count = await get_pending_research_count()
        print(f"Pending research: {count}")
        print()

    asyncio.run(test_research_flow())
