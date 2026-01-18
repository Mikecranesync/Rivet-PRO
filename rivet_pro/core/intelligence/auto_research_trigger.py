#!/usr/bin/env python3
"""
Auto-Research Trigger - Priority-based research triggering

Listens for KB gap detection events and triggers research pipeline
based on priority scores. Queues sources to Redis for the 24/7 worker.

Priority Routing:
- CRITICAL/HIGH (>=70): Trigger immediately
- MEDIUM (40-69): Batch and trigger hourly
- LOW (<40): Batch and trigger daily

Based on Agent Factory's auto_research_trigger.py, adapted for:
- RIVET Pro project structure
- Upstash Redis queue integration
- Async database operations
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import httpx

logger = logging.getLogger(__name__)


class AutoResearchTrigger:
    """
    Automatically triggers research pipeline for KB gaps.

    Priority-based triggering:
    - CRITICAL (90-100): Immediate
    - HIGH (70-89): Immediate
    - MEDIUM (40-69): Batched hourly
    - LOW (<40): Batched daily

    In AGGRESSIVE mode (default for new KB), all priorities are immediate.
    """

    # Priority thresholds
    CRITICAL_THRESHOLD = 90
    HIGH_THRESHOLD = 70
    MEDIUM_THRESHOLD = 40

    def __init__(
        self,
        db_pool=None,
        redis_client=None,
        aggressive_mode: bool = True,
    ):
        """
        Initialize auto-research trigger.

        Args:
            db_pool: asyncpg connection pool
            redis_client: Redis client for queue operations
            aggressive_mode: If True, trigger all priorities immediately
        """
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.aggressive_mode = aggressive_mode

        # Batches for non-aggressive mode
        self.medium_priority_batch: List[Tuple[int, Dict]] = []
        self.low_priority_batch: List[Tuple[int, Dict]] = []

        logger.info(
            f"AutoResearchTrigger initialized | aggressive_mode={aggressive_mode}"
        )

    async def trigger_research(self, event_data: Dict):
        """
        Trigger research based on gap priority.

        Args:
            event_data: kb_gap_detected event payload with:
                - gap_id: int
                - priority: int (0-100)
                - equipment: str (e.g., "siemens:s7_1200")
                - query: str
                - weakness_type: str
        """
        gap_id = event_data.get("gap_id")
        priority = event_data.get("priority", 50)
        equipment = event_data.get("equipment", "unknown:unknown")
        query = event_data.get("query", "")

        logger.info(
            f"Auto-research trigger: gap_id={gap_id}, "
            f"priority={priority}, equipment={equipment}"
        )

        # Parse equipment identifier
        vendor, equipment_type = self._parse_equipment(equipment)

        # Build intent for research pipeline
        intent_data = {
            "vendor": vendor,
            "equipment_type": equipment_type,
            "symptom": query[:200],
            "raw_question": query,
            "gap_id": gap_id,
        }

        if self.aggressive_mode:
            # AGGRESSIVE MODE: Process all immediately
            logger.info("AGGRESSIVE MODE: Triggering immediate research")
            await self._trigger_immediate(gap_id, intent_data)
        else:
            # Standard priority-based routing
            if priority >= self.HIGH_THRESHOLD:
                await self._trigger_immediate(gap_id, intent_data)
            elif priority >= self.MEDIUM_THRESHOLD:
                self.medium_priority_batch.append((gap_id, intent_data))
                logger.info(
                    f"Batched medium-priority gap {gap_id} "
                    f"(batch size: {len(self.medium_priority_batch)})"
                )
            else:
                self.low_priority_batch.append((gap_id, intent_data))
                logger.info(
                    f"Batched low-priority gap {gap_id} "
                    f"(batch size: {len(self.low_priority_batch)})"
                )

    async def _trigger_immediate(self, gap_id: int, intent_data: Dict):
        """
        Trigger research immediately for high-priority gaps.

        Queues manufacturer documentation URLs to Redis for processing
        by the 24/7 KB ingestion worker.

        Args:
            gap_id: Gap ID in database
            intent_data: Intent dictionary with vendor, equipment, symptom
        """
        try:
            # Mark ingestion as started in database
            if self.db_pool:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE gap_requests
                        SET updated_at = NOW()
                        WHERE id = $1
                        """,
                        gap_id
                    )

            logger.info(f"Processing gap {gap_id} for research")

            # Get URLs for this equipment type
            urls = self._get_research_urls(
                intent_data["vendor"],
                intent_data["equipment_type"]
            )

            if not urls:
                logger.warning(
                    f"No research URLs for {intent_data['vendor']}:{intent_data['equipment_type']}"
                )
                return

            # Queue URLs to Redis
            queued = 0
            if self.redis_client:
                for url in urls:
                    try:
                        self.redis_client.rpush("kb_ingest_jobs", url)
                        queued += 1
                    except Exception as e:
                        logger.error(f"Failed to queue URL: {e}")

            logger.info(
                f"Research triggered for gap {gap_id}: "
                f"{queued}/{len(urls)} URLs queued"
            )

            # Record source URLs in database
            if self.db_pool and urls:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE gap_requests
                        SET source_urls = $2, updated_at = NOW()
                        WHERE id = $1
                        """,
                        gap_id, urls
                    )

        except Exception as e:
            logger.error(
                f"Failed to trigger research for gap_id={gap_id}: {e}",
                exc_info=True
            )

    def _parse_equipment(self, equipment_str: str) -> Tuple[str, str]:
        """
        Parse equipment identifier into vendor and type.

        Args:
            equipment_str: Format "vendor:equipment_type" (e.g., "siemens:s7_1200")

        Returns:
            (vendor, equipment_type) tuple
        """
        try:
            parts = equipment_str.split(":")
            if len(parts) == 2:
                return parts[0].lower(), parts[1].lower()
        except Exception:
            pass

        return "generic", "unknown"

    def _get_research_urls(self, vendor: str, equipment_type: str) -> List[str]:
        """
        Get research URLs for a vendor/equipment combination.

        Args:
            vendor: Manufacturer name
            equipment_type: Equipment type

        Returns:
            List of documentation URLs to research
        """
        # Manufacturer documentation sources
        RESEARCH_SOURCES = {
            "rockwell": [
                "https://literature.rockwellautomation.com/idc/groups/literature/documents/um/",
                "https://www.rockwellautomation.com/en-us/support.html",
            ],
            "allen-bradley": [
                "https://literature.rockwellautomation.com/idc/groups/literature/documents/um/",
            ],
            "siemens": [
                "https://support.industry.siemens.com/cs/",
            ],
            "abb": [
                "https://search.abb.com/library/",
            ],
            "danfoss": [
                "https://www.danfoss.com/en/service-and-support/downloads/",
            ],
            "trane": [
                "https://www.trane.com/commercial/north-america/us/en/products-systems/",
            ],
            "carrier": [
                "https://www.carrier.com/commercial/en/us/products/hvac/",
            ],
            "grundfos": [
                "https://www.grundfos.com/products",
            ],
        }

        # Get vendor-specific URLs
        urls = []
        vendor_lower = vendor.lower()

        for key, source_urls in RESEARCH_SOURCES.items():
            if key in vendor_lower or vendor_lower in key:
                urls.extend(source_urls)
                break

        # If no specific vendor match, use generic sources
        if not urls:
            urls = [
                f"https://www.google.com/search?q={vendor}+{equipment_type}+manual+pdf",
            ]

        return urls

    async def process_medium_batch(self):
        """
        Process medium-priority batch (called hourly).
        """
        if not self.medium_priority_batch:
            logger.info("No medium-priority gaps to process")
            return

        logger.info(
            f"Processing {len(self.medium_priority_batch)} medium-priority gaps"
        )

        for gap_id, intent_data in self.medium_priority_batch:
            await self._trigger_immediate(gap_id, intent_data)

        self.medium_priority_batch.clear()
        logger.info("Medium-priority batch processed")

    async def process_low_batch(self):
        """
        Process low-priority batch (called daily).
        """
        if not self.low_priority_batch:
            logger.info("No low-priority gaps to process")
            return

        logger.info(
            f"Processing {len(self.low_priority_batch)} low-priority gaps"
        )

        for gap_id, intent_data in self.low_priority_batch:
            await self._trigger_immediate(gap_id, intent_data)

        self.low_priority_batch.clear()
        logger.info("Low-priority batch processed")


# Module-level singleton
_auto_research_trigger: Optional[AutoResearchTrigger] = None


def get_auto_research_trigger(
    db_pool=None,
    redis_client=None,
    aggressive_mode: bool = True,
) -> AutoResearchTrigger:
    """
    Get or create the AutoResearchTrigger singleton.

    Args:
        db_pool: asyncpg connection pool
        redis_client: Redis client
        aggressive_mode: If True, process all priorities immediately

    Returns:
        AutoResearchTrigger instance
    """
    global _auto_research_trigger

    if _auto_research_trigger is None:
        _auto_research_trigger = AutoResearchTrigger(
            db_pool=db_pool,
            redis_client=redis_client,
            aggressive_mode=aggressive_mode,
        )

    return _auto_research_trigger


async def trigger_research(event_data: Dict):
    """
    Global function to trigger research.

    Called when a KB gap is detected.

    Args:
        event_data: kb_gap_detected event payload
    """
    trigger = get_auto_research_trigger()
    await trigger.trigger_research(event_data)


async def process_medium_batch():
    """
    Process medium-priority batch (called hourly by scheduler).
    """
    trigger = get_auto_research_trigger()
    await trigger.process_medium_batch()


async def process_low_batch():
    """
    Process low-priority batch (called daily by scheduler).
    """
    trigger = get_auto_research_trigger()
    await trigger.process_low_batch()


__all__ = [
    "AutoResearchTrigger",
    "get_auto_research_trigger",
    "trigger_research",
    "process_medium_batch",
    "process_low_batch",
]
