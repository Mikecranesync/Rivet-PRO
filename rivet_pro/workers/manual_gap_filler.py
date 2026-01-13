"""
Manual Gap Filler Worker - Background job to find manuals for equipment (MANUAL-004).

Runs daily to identify equipment without manuals and search for them proactively.
Priority based on work_order count, knowledge gap occurrence, recency, and vendor importance.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from uuid import UUID

from rivet_pro.infra.observability import get_logger
from rivet_pro.core.services.manual_matcher_service import ManualMatcherService

logger = get_logger(__name__)


class ManualGapFiller:
    """
    Background worker that proactively finds manuals for equipment.
    Runs daily to fill knowledge gaps with priority-based selection.
    """

    # Priority vendors for boosted searching
    PRIORITY_VENDORS = [
        'siemens', 'rockwell automation', 'allen bradley',
        'abb', 'schneider electric', 'mitsubishi', 'yaskawa'
    ]

    def __init__(self, db):
        self.db = db
        self.manual_matcher = ManualMatcherService(db)

    async def fill_gaps_daily(self, limit: int = 10) -> Dict[str, int]:
        """
        Daily job: Find equipment without manuals, search top N priority.

        Args:
            limit: Max number of equipment to process (default: 10)

        Returns:
            Dict with statistics (total_processed, manuals_found, etc.)
        """
        logger.info(f"Starting manual gap filler (limit: {limit})")
        start_time = datetime.now()

        # Get high-priority equipment without manuals
        equipment_list = await self.get_high_priority_equipment_without_manuals(limit)

        logger.info(f"Found {len(equipment_list)} equipment without manuals")

        results = {
            "total_processed": 0,
            "manuals_found": 0,
            "manuals_validated": 0,
            "gaps_resolved": 0,
            "errors": 0
        }

        for equipment in equipment_list:
            try:
                logger.info(
                    f"Searching manual for: {equipment['manufacturer']} "
                    f"{equipment['model_number']} (priority: {equipment['priority']:.1f})"
                )

                # Run manual search (telegram_chat_id=0 for background job)
                result = await self.manual_matcher.search_and_validate_manual(
                    equipment_id=equipment['id'],
                    manufacturer=equipment['manufacturer'],
                    model=equipment['model_number'],
                    equipment_type=equipment['equipment_type'],
                    telegram_chat_id=0  # No direct notification for background job
                )

                results['total_processed'] += 1

                if result['status'] == 'completed':
                    results['manuals_found'] += 1

                    if result.get('atom_id'):
                        results['manuals_validated'] += 1

                        # Mark knowledge gap as resolved
                        resolved = await self._mark_gap_resolved(
                            manufacturer=equipment['manufacturer'],
                            model=equipment['model_number'],
                            atom_id=result['atom_id']
                        )
                        if resolved:
                            results['gaps_resolved'] += 1

                        # Notify recent user if applicable
                        await self._notify_user_of_indexed_manual(
                            equipment_id=equipment['id'],
                            equipment_number=equipment['equipment_number'],
                            manufacturer=equipment['manufacturer'],
                            model=equipment['model_number'],
                            manuals_found=[{
                                "url": result['manual_url'],
                                "title": "Manual",
                                "confidence": result['confidence'],
                                "manual_type": "user_manual"
                            }]
                        )

                # Rate limit: 5 seconds between searches
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error processing {equipment['id']}: {e}", exc_info=True)
                results['errors'] += 1

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Manual gap filler completed in {duration:.1f}s: "
            f"{results['manuals_validated']}/{results['total_processed']} validated"
        )

        # Also process pending retries
        retry_count = await self.manual_matcher.process_pending_retries()
        logger.info(f"Processed {retry_count} pending retries")

        return results

    async def get_high_priority_equipment_without_manuals(
        self,
        limit: int = 10
    ) -> List[Dict]:
        """
        Query equipment without validated manuals, sorted by priority.

        Priority formula:
        (work_order_count * 2.0) + (gap_count * 1.5) + (recency_score * 1.0) + (vendor_boost * 1.2)
        """
        query = """
        WITH equipment_priority AS (
            SELECT
                e.id,
                e.equipment_number,
                e.manufacturer,
                e.model_number,
                e.equipment_type,
                e.work_order_count,
                COALESCE(kg.occurrence_count, 0) as gap_count,
                e.last_work_order_at,

                -- Recency score: 10 if today, decay to 0 over 90 days
                CASE
                    WHEN e.last_work_order_at IS NULL THEN 0
                    ELSE GREATEST(0, 10.0 * (1.0 - EXTRACT(EPOCH FROM (NOW() - e.last_work_order_at)) / (90 * 86400)))
                END as recency_score,

                -- Vendor boost for priority manufacturers
                CASE
                    WHEN LOWER(e.manufacturer) IN ('siemens', 'rockwell automation', 'allen bradley',
                                                    'abb', 'schneider electric', 'mitsubishi', 'yaskawa')
                    THEN 1.5
                    ELSE 1.0
                END as vendor_boost

            FROM cmms_equipment e
            LEFT JOIN knowledge_gaps kg
                ON LOWER(kg.manufacturer) = LOWER(e.manufacturer)
                AND LOWER(kg.model) = LOWER(e.model_number)

            WHERE NOT EXISTS (
                -- No validated manual in cache
                SELECT 1 FROM manual_cache mc
                WHERE LOWER(mc.manufacturer) = LOWER(e.manufacturer)
                    AND LOWER(mc.model) = LOWER(e.model_number)
                    AND mc.llm_validated = TRUE
                    AND mc.found_at > NOW() - INTERVAL '90 days'
            )
            AND NOT EXISTS (
                -- No recent failed search
                SELECT 1 FROM equipment_manual_searches ems
                WHERE ems.equipment_id = e.id
                    AND ems.search_status = 'no_manual_found'
                    AND ems.created_at > NOW() - INTERVAL '30 days'
            )
        )
        SELECT
            id,
            equipment_number,
            manufacturer,
            model_number,
            equipment_type,
            work_order_count,
            gap_count,
            recency_score,
            vendor_boost,
            -- Calculate priority
            (work_order_count * 2.0) +
            (gap_count * 1.5) +
            (recency_score * 1.0) +
            (vendor_boost * 1.2) as priority
        FROM equipment_priority
        ORDER BY priority DESC
        LIMIT $1
        """

        rows = await self.db.fetch(query, limit)
        return [dict(row) for row in rows]

    async def _mark_gap_resolved(
        self,
        manufacturer: str,
        model: str,
        atom_id: UUID
    ) -> bool:
        """Mark knowledge gap as resolved with atom_id."""
        try:
            result = await self.db.execute("""
                UPDATE knowledge_gaps
                SET research_status = 'completed',
                    resolved_atom_id = $1,
                    updated_at = NOW()
                WHERE LOWER(manufacturer) = LOWER($2)
                    AND LOWER(model) = LOWER($3)
                    AND research_status != 'completed'
            """, atom_id, manufacturer, model)

            return result is not None

        except Exception as e:
            logger.error(f"Failed to mark gap as resolved: {e}", exc_info=True)
            return False

    async def _notify_user_of_indexed_manual(
        self,
        equipment_id: UUID,
        equipment_number: str,
        manufacturer: str,
        model: str,
        manuals_found: List[Dict]
    ) -> None:
        """
        Notify user when background job indexes a manual.
        Finds most recent user who interacted with this equipment.
        """
        try:
            # Find most recent user who interacted with this equipment
            recent_interaction = await self.db.fetchrow("""
                SELECT i.telegram_user_id, u.full_name
                FROM interactions i
                JOIN users u ON u.user_id = i.user_id
                WHERE i.context_data->>'equipment_id' = $1
                ORDER BY i.created_at DESC
                LIMIT 1
            """, str(equipment_id))

            if not recent_interaction:
                logger.info(f"No recent user found for {equipment_id}, skipping notification")
                return

            telegram_chat_id = recent_interaction['telegram_user_id']

            # Format manual list
            manual_list = "\n".join([
                f"• {m['manual_type'].replace('_', ' ').title()}: "
                f"{m.get('title', 'Manual')}\n  {m['url']} ({m['confidence']:.0%} confidence)"
                for m in manuals_found[:3]  # Show top 3
            ])

            message = f"""📚 *Manual Indexed: {equipment_number}*

{manufacturer} {model}

Great news! We found and validated {len(manuals_found)} manual(s) for this equipment:

{manual_list}

You can now:
• Use `/manual {equipment_number}` for instant access
• Chat with the manual content (coming soon)
• Share with your team

This equipment is now in the knowledge base for all future users."""

            # TODO: Send via Telegram bot
            logger.info(
                f"Manual indexed notification queued | chat_id={telegram_chat_id} | "
                f"equipment_number={equipment_number}"
            )

        except Exception as e:
            logger.error(f"Failed to send manual indexed notification: {e}", exc_info=True)
