"""
Research Trigger - Route C: Knowledge Base Gap Detection & Research Queue

Logs KB gaps when confidence is low and triggers async research.
Does NOT block user response - queues research for later.
"""

import logging
from typing import Optional
from datetime import datetime

from rivet.observability.tracer import traced

logger = logging.getLogger(__name__)


@traced(name="trigger_research", tags=["research"])
async def trigger_research(
    query: str,
    manufacturer: Optional[str] = None,
    model_number: Optional[str] = None,
    fault_code: Optional[str] = None,
    kb_confidence: Optional[float] = None,
    sme_confidence: Optional[float] = None,
) -> None:
    """
    Trigger async research for KB gap.

    This function:
    1. Logs the KB gap (query + equipment context)
    2. Queues async research job (Redis/database)
    3. Returns immediately (does NOT wait for research)

    Args:
        query: User's troubleshooting question
        manufacturer: Detected manufacturer (optional)
        model_number: Equipment model (optional)
        fault_code: Fault code if present (optional)
        kb_confidence: KB search confidence score (optional)
        sme_confidence: SME response confidence score (optional)

    Returns:
        None (research queued asynchronously)

    Example:
        >>> await trigger_research(
        ...     query="Siemens S7-1200 F0002 fault",
        ...     manufacturer="siemens",
        ...     model_number="S7-1200",
        ...     fault_code="F0002",
        ...     kb_confidence=0.40,
        ...     sme_confidence=0.65
        ... )
        # Logs KB gap and queues research job
    """
    logger.info(
        f"[Research Trigger] KB gap detected: "
        f"query='{query[:100]}...', "
        f"manufacturer={manufacturer}, "
        f"model={model_number}, "
        f"fault={fault_code}, "
        f"kb_conf={kb_confidence:.0%}, "
        f"sme_conf={sme_confidence:.0%}"
    )

    # TODO Phase 3: Implement async research queue
    # - Add to Redis queue (LPUSH kb_research_queue)
    # - OR insert into database (kb_gaps table)
    # - Research worker processes queue asynchronously
    # - Updates KB with new knowledge atoms

    # MOCK IMPLEMENTATION (Phase 2)
    # Log the gap for manual review
    gap_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "manufacturer": manufacturer,
        "model_number": model_number,
        "fault_code": fault_code,
        "kb_confidence": kb_confidence,
        "sme_confidence": sme_confidence,
    }

    # TODO Phase 3: Queue to Redis or database
    # redis_client.lpush("kb_research_queue", json.dumps(gap_data))
    # OR
    # db.insert("kb_gaps", gap_data)

    logger.info(
        f"[Research Trigger] KB gap logged for async research: "
        f"{manufacturer or 'generic'} / {fault_code or 'N/A'}"
    )

    # Return immediately (don't wait for research to complete)
    return None


async def check_research_status(query: str) -> Optional[dict]:
    """
    Check if research has been completed for a previous query.

    Phase 3 will implement:
    - Query research queue for matching KB gaps
    - Check if research worker has resolved the gap
    - Return updated answer if available

    Args:
        query: Original user query

    Returns:
        Dict with updated answer if research complete, else None

    Example:
        >>> status = await check_research_status("Siemens F0002 fault")
        >>> if status and status["complete"]:
        ...     print(status["answer"])
    """
    # TODO Phase 3: Implement research status checking
    # - Query kb_gaps table for matching query
    # - Check if research_complete=true
    # - Return new KB atoms or answer if available

    # MOCK IMPLEMENTATION (Phase 2)
    logger.info(f"[Research Status] Checking status for: {query[:100]}...")
    return None  # Research not complete


def get_pending_research_count() -> int:
    """
    Get count of pending research jobs in queue.

    Returns:
        Number of KB gaps awaiting research

    Example:
        >>> count = get_pending_research_count()
        >>> print(f"Pending research jobs: {count}")
    """
    # TODO Phase 3: Implement queue counting
    # return redis_client.llen("kb_research_queue")
    # OR
    # return db.count("kb_gaps", where="research_complete=false")

    # MOCK IMPLEMENTATION (Phase 2)
    return 0


def prioritize_research_queue() -> list[dict]:
    """
    Prioritize research queue based on:
    - Query frequency (how many users asked same question)
    - Confidence gap (lower = higher priority)
    - Manufacturer popularity

    Returns:
        List of prioritized KB gaps

    Example:
        >>> queue = prioritize_research_queue()
        >>> for item in queue[:5]:  # Top 5 priority items
        ...     print(item["query"], item["priority_score"])
    """
    # TODO Phase 3: Implement priority scoring
    # - Count duplicate queries (GROUP BY normalized_query)
    # - Calculate confidence gap (1.0 - max(kb_conf, sme_conf))
    # - Boost popular manufacturers (Siemens, Rockwell)
    # - Return sorted list

    # MOCK IMPLEMENTATION (Phase 2)
    logger.info("[Research Queue] Priority queue not yet implemented")
    return []


# Phase 3 Stub: Research worker
async def research_worker_loop():
    """
    Async worker that processes research queue.

    Phase 3 implementation:
    1. Pop from Redis queue (BRPOP kb_research_queue)
    2. Call research agents (web scraping, manual parsing, etc.)
    3. Generate knowledge atoms
    4. Update vector database
    5. Mark gap as resolved

    Example:
        >>> import asyncio
        >>> asyncio.create_task(research_worker_loop())
        # Runs indefinitely, processing queue
    """
    # TODO Phase 3: Implement research worker
    # while True:
    #     gap = redis_client.brpop("kb_research_queue", timeout=5)
    #     if gap:
    #         await process_research_job(gap)
    raise NotImplementedError("Phase 3: Implement research worker")


if __name__ == "__main__":
    import asyncio

    # Test research trigger
    async def test_research_trigger():
        print("\n=== Research Trigger Test ===\n")

        await trigger_research(
            query="Siemens S7-1200 F0002 fault - motor won't start",
            manufacturer="siemens",
            model_number="S7-1200",
            fault_code="F0002",
            kb_confidence=0.40,
            sme_confidence=0.65,
        )

        print("\nResearch job queued successfully (mock implementation)\n")
        print(f"Pending research count: {get_pending_research_count()}")

    asyncio.run(test_research_trigger())
