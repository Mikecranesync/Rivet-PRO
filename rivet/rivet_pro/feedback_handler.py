"""
Feedback Handler - Updates knowledge atom success_rate based on user feedback

Processes user feedback (thumbs up/down) and:
1. Increments atom feedback counters
2. Recalculates success_rate (positive / total)
3. Triggers research for low-quality atoms (<0.3 success_rate)

Usage:
    from rivet.rivet_pro.feedback_handler import FeedbackHandler

    handler = FeedbackHandler(db)
    await handler.process_feedback(
        atom_ids=["allen_bradley:controllogix:motor-control"],
        feedback_type="positive"
    )
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FeedbackHandler:
    """Handles user feedback for knowledge atoms and triggers research for low-quality content."""

    def __init__(self, db):
        """
        Initialize feedback handler.

        Args:
            db: DatabaseManager instance
        """
        self.db = db
        self.LOW_QUALITY_THRESHOLD = 0.3  # Trigger research if success_rate < 30%
        self.MIN_FEEDBACK_SAMPLES = 3  # Need at least 3 feedback samples before triggering research

    async def process_feedback(
        self,
        atom_ids: List[str],
        feedback_type: str  # 'positive' or 'negative'
    ) -> List[str]:
        """
        Process user feedback for knowledge atoms.

        Updates feedback counters, recalculates success_rate, and triggers
        research for low-quality atoms.

        Args:
            atom_ids: List of knowledge atom IDs (e.g., ["allen_bradley:controllogix:motor-control"])
            feedback_type: 'positive' or 'negative'

        Returns:
            List of atom IDs that triggered research (success_rate < 0.3)
        """
        if not atom_ids:
            return []

        # Determine which counter to increment
        counter_field = "feedback_positive_count" if feedback_type == "positive" else "feedback_negative_count"

        triggered_research = []

        for atom_id in atom_ids:
            try:
                # 1. Increment feedback counter
                await self._increment_feedback_counter(atom_id, counter_field)

                # 2. Recalculate success_rate
                success_rate = await self._recalculate_success_rate(atom_id)

                # 3. Check if research should be triggered
                if success_rate is not None and success_rate < self.LOW_QUALITY_THRESHOLD:
                    total_feedback = await self._get_total_feedback_count(atom_id)
                    if total_feedback >= self.MIN_FEEDBACK_SAMPLES:
                        # Trigger research for this low-quality atom
                        await self._trigger_research_for_atom(atom_id, success_rate)
                        triggered_research.append(atom_id)

                logger.info(
                    f"Processed {feedback_type} feedback for {atom_id}: "
                    f"success_rate={success_rate:.2f if success_rate else 'N/A'}"
                )

            except Exception as e:
                logger.error(f"Failed to process feedback for {atom_id}: {e}", exc_info=True)

        return triggered_research

    async def _increment_feedback_counter(self, atom_id: str, counter_field: str):
        """
        Increment feedback counter for an atom.

        Args:
            atom_id: Knowledge atom ID
            counter_field: 'feedback_positive_count' or 'feedback_negative_count'
        """
        await asyncio.to_thread(
            self.db.execute_query,
            f"""
            UPDATE knowledge_atoms
            SET {counter_field} = {counter_field} + 1,
                usage_count = usage_count + 1
            WHERE atom_id = $1
            """,
            (atom_id,),
            fetch_mode="none"
        )

    async def _recalculate_success_rate(self, atom_id: str) -> Optional[float]:
        """
        Recalculate success_rate for an atom.

        Args:
            atom_id: Knowledge atom ID

        Returns:
            New success_rate (0.0-1.0) or None if no feedback yet
        """
        result = await asyncio.to_thread(
            self.db.execute_query,
            """
            UPDATE knowledge_atoms
            SET success_rate = CASE
                WHEN (feedback_positive_count + feedback_negative_count) > 0
                THEN feedback_positive_count::FLOAT / (feedback_positive_count + feedback_negative_count)::FLOAT
                ELSE NULL
            END
            WHERE atom_id = $1
            RETURNING success_rate
            """,
            (atom_id,),
            fetch_mode="one"
        )

        if result:
            return result[0] if isinstance(result, tuple) else result.get('success_rate')
        return None

    async def _get_total_feedback_count(self, atom_id: str) -> int:
        """
        Get total feedback count for an atom.

        Args:
            atom_id: Knowledge atom ID

        Returns:
            Total feedback count (positive + negative)
        """
        result = await asyncio.to_thread(
            self.db.execute_query,
            """
            SELECT feedback_positive_count + feedback_negative_count as total
            FROM knowledge_atoms
            WHERE atom_id = $1
            """,
            (atom_id,),
            fetch_mode="one"
        )

        if result:
            return result[0] if isinstance(result, tuple) else result.get('total', 0)
        return 0

    async def _trigger_research_for_atom(self, atom_id: str, success_rate: float):
        """
        Trigger research for a low-quality atom.

        Creates a gap request that will be picked up by the auto-research trigger.

        Args:
            atom_id: Knowledge atom ID with low success_rate
            success_rate: Current success_rate (for logging)
        """
        try:
            from rivet.core.kb_gap_logger import KBGapLogger

            gap_logger = KBGapLogger(self.db)

            # Parse atom_id to extract vendor and equipment type
            # Format: "vendor:product:topic" (e.g., "allen_bradley:controllogix:motor-control")
            parts = atom_id.split(":")
            vendor = parts[0] if len(parts) > 0 else "unknown"
            equipment_type = parts[1] if len(parts) > 1 else "unknown"
            topic = parts[2] if len(parts) > 2 else "unknown"

            # Create gap request
            gap_id = await gap_logger.log_gap_async({
                "user_query": f"Low success rate ({success_rate:.1%}) for atom: {atom_id}",
                "vendor": vendor,
                "equipment_type": equipment_type,
                "symptom": f"Negative user feedback on topic: {topic}",
                "route": "FEEDBACK_TRIGGERED",
                "confidence": 0.0,
                "kb_coverage": "poor",
                "atom_count": 1,
                "avg_relevance": 0.0,
                "priority_score": 80,  # HIGH priority for feedback-triggered research
                "enrichment_type": "feedback_improvement",
                "weakness_type": "low_user_satisfaction"
            })

            logger.info(
                f"Triggered research for low-quality atom {atom_id}: "
                f"gap_id={gap_id}, success_rate={success_rate:.1%}"
            )

        except Exception as e:
            logger.error(f"Failed to trigger research for {atom_id}: {e}", exc_info=True)

    async def get_low_quality_atoms(self, limit: int = 10) -> List[dict]:
        """
        Get atoms with low success_rate that need improvement.

        Args:
            limit: Maximum number of atoms to return

        Returns:
            List of atom dicts with atom_id, title, success_rate, feedback counts
        """
        result = await asyncio.to_thread(
            self.db.execute_query,
            """
            SELECT
                atom_id,
                title,
                success_rate,
                feedback_positive_count,
                feedback_negative_count,
                usage_count
            FROM knowledge_atoms
            WHERE success_rate < $1
            AND (feedback_positive_count + feedback_negative_count) >= $2
            ORDER BY success_rate ASC, usage_count DESC
            LIMIT $3
            """,
            (self.LOW_QUALITY_THRESHOLD, self.MIN_FEEDBACK_SAMPLES, limit),
            fetch_mode="all"
        )

        if result:
            atoms = []
            for row in result:
                if isinstance(row, tuple):
                    atoms.append({
                        "atom_id": row[0],
                        "title": row[1],
                        "success_rate": row[2],
                        "feedback_positive_count": row[3],
                        "feedback_negative_count": row[4],
                        "usage_count": row[5]
                    })
                else:
                    atoms.append(dict(row))
            return atoms
        return []


# Singleton instance
_feedback_handler: Optional[FeedbackHandler] = None


def get_feedback_handler(db=None) -> FeedbackHandler:
    """
    Get global feedback handler instance.

    Args:
        db: DatabaseManager instance (uses existing if None)

    Returns:
        FeedbackHandler singleton
    """
    global _feedback_handler

    if _feedback_handler is None:
        if db is None:
            from rivet.core.database_manager import DatabaseManager
            db = DatabaseManager()
        _feedback_handler = FeedbackHandler(db)

    return _feedback_handler


async def process_feedback(atom_ids: List[str], feedback_type: str) -> List[str]:
    """
    Global function to process feedback (called by rivet_pro_handlers).

    Args:
        atom_ids: List of knowledge atom IDs
        feedback_type: 'positive' or 'negative'

    Returns:
        List of atom IDs that triggered research
    """
    handler = get_feedback_handler()
    return await handler.process_feedback(atom_ids, feedback_type)
