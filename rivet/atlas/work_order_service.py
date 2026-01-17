#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Work Order Service - CMMS Work Order Creation

Creates and manages CMMS work orders from technician interactions.
Implements equipment-first architecture with automatic equipment matching.

Usage:
    from rivet.atlas import AtlasDatabase, EquipmentMatcher, WorkOrderService

    db = AtlasDatabase()
    await db.connect()

    matcher = EquipmentMatcher(db)
    service = WorkOrderService(db, matcher)

    work_order = await service.create_work_order(
        user_id="telegram_123",
        title="VFD Fault F0001",
        description="Drive showing overcurrent",
        manufacturer="Siemens",
        model_number="G120C",
        equipment_type="VFD",
        fault_codes=["F0001"]
    )
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID

from rivet.atlas.equipment_matcher import EquipmentMatcher

logger = logging.getLogger(__name__)


class WorkOrderService:
    """Service for creating and managing CMMS work orders."""

    def __init__(self, db, equipment_matcher: Optional[EquipmentMatcher] = None):
        """
        Initialize work order service.

        Args:
            db: AtlasDatabase instance
            equipment_matcher: EquipmentMatcher instance (created if not provided)
        """
        self.db = db
        self.equipment_matcher = equipment_matcher or EquipmentMatcher(db)

    async def create_work_order(
        self,
        user_id: str,
        title: str,
        description: str,
        manufacturer: Optional[str] = None,
        model_number: Optional[str] = None,
        serial_number: Optional[str] = None,
        equipment_type: Optional[str] = None,
        location: Optional[str] = None,
        fault_codes: Optional[List[str]] = None,
        symptoms: Optional[List[str]] = None,
        telegram_username: Optional[str] = None,
        source: str = "telegram_text",
        answer_text: Optional[str] = None,
        confidence_score: Optional[float] = None,
        route_taken: Optional[str] = None,
        suggested_actions: Optional[List[str]] = None,
        safety_warnings: Optional[List[str]] = None,
        manual_links: Optional[List[str]] = None,
        machine_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
        trace_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Create a work order.

        Equipment-first architecture:
        1. Match or create equipment in CMMS
        2. Create work order linked to that equipment
        3. Update equipment statistics

        Args:
            user_id: Telegram user ID
            title: Work order title (e.g., "Siemens VFD - Fault F0001")
            description: Detailed description
            manufacturer: Equipment manufacturer (optional)
            model_number: Model number (optional)
            serial_number: Serial number (optional)
            equipment_type: Type of equipment (optional)
            location: Physical location (optional)
            fault_codes: List of fault codes (optional)
            symptoms: List of symptoms (optional)
            telegram_username: Telegram @username (optional)
            source: Source type (default: telegram_text)
            answer_text: AI-generated answer (optional)
            confidence_score: AI confidence 0-1 (optional)
            route_taken: RIVET route (A/B/C/D) (optional)
            suggested_actions: Recommended actions (optional)
            safety_warnings: Safety warnings (optional)
            manual_links: Manual references (optional)
            machine_id: User's machine library ID (optional)
            conversation_id: Multi-turn conversation ID (optional)
            trace_id: RequestTrace ID (optional)

        Returns:
            Dictionary with work order details:
            {
                "id": UUID,
                "work_order_number": "WO-2025-0001",
                "equipment_id": UUID,
                "equipment_number": "EQ-2025-0001",
                "created_at": datetime
            }

        Example:
            >>> work_order = await service.create_work_order(
            ...     user_id="telegram_123",
            ...     title="Siemens VFD - Fault F0001",
            ...     description="Drive showing overcurrent fault",
            ...     manufacturer="Siemens",
            ...     model_number="G120C",
            ...     equipment_type="VFD",
            ...     fault_codes=["F0001"]
            ... )
            >>> print(f"Created: {work_order['work_order_number']}")
        """

        try:
            # 1. MATCH OR CREATE EQUIPMENT IN CMMS (equipment-first architecture)
            equipment_id, equipment_number, is_new_equipment = await self.equipment_matcher.match_or_create_equipment(
                manufacturer=manufacturer,
                model_number=model_number,
                serial_number=serial_number,
                equipment_type=equipment_type,
                location=location,
                user_id=user_id,
                machine_id=machine_id
            )

            logger.info(
                f"Equipment {'CREATED' if is_new_equipment else 'MATCHED'}: "
                f"{equipment_number} (ID: {equipment_id})"
            )

            # 2. Calculate priority from confidence + fault severity + safety warnings
            priority = self._calculate_priority(
                confidence_score=confidence_score,
                route=route_taken,
                fault_codes=fault_codes or [],
                safety_warnings=safety_warnings or []
            )

            # 3. Insert work order (WITH EQUIPMENT LINK)
            work_order_result = await self.db.execute("""
                INSERT INTO work_orders (
                    user_id, telegram_username, source,
                    manufacturer, model_number, serial_number, equipment_type,
                    machine_id, location,
                    equipment_id, equipment_number,
                    title, description, fault_codes, symptoms,
                    answer_text, confidence_score, route_taken,
                    suggested_actions, safety_warnings, manual_links,
                    status, priority,
                    trace_id, conversation_id
                ) VALUES (
                    $1, $2, $3,
                    $4, $5, $6, $7,
                    $8, $9,
                    $10, $11,
                    $12, $13, $14, $15,
                    $16, $17, $18,
                    $19, $20, $21,
                    $22, $23,
                    $24, $25
                )
                RETURNING id, work_order_number, created_at
            """,
                user_id,
                telegram_username,
                source,
                manufacturer,
                model_number,
                serial_number,
                equipment_type,
                str(machine_id) if machine_id else None,
                location,
                str(equipment_id),  # Equipment ID
                equipment_number,  # Equipment number (denormalized)
                title,
                description,
                fault_codes or [],
                symptoms or [],
                answer_text,
                confidence_score,
                route_taken,
                suggested_actions or [],
                safety_warnings or [],
                manual_links or [],
                'open',
                priority,
                str(trace_id) if trace_id else None,
                str(conversation_id) if conversation_id else None
            )

            work_order = work_order_result[0]

            logger.info(
                f"Work order created: {work_order['work_order_number']} "
                f"for user {user_id} (equipment: {equipment_number})"
            )

            # 4. Update equipment statistics (fault code only - counts updated by trigger)
            if fault_codes:
                await self.equipment_matcher.update_equipment_stats(
                    equipment_id=equipment_id,  # Already UUID from matcher
                    fault_code=fault_codes[0]
                )

            return {
                "id": work_order["id"],
                "work_order_number": work_order["work_order_number"],
                "equipment_id": equipment_id,
                "equipment_number": equipment_number,
                "created_at": work_order["created_at"]
            }

        except Exception as e:
            logger.error(f"Failed to create work order: {e}", exc_info=True)
            raise

    async def update_status(
        self,
        work_order_id: UUID,
        status: str,
        notes: Optional[str] = None
    ) -> None:
        """
        Update work order status (open → in_progress → completed).

        Args:
            work_order_id: UUID of work order
            status: New status ('open', 'in_progress', 'completed', 'cancelled')
            notes: Optional notes to append to description
        """
        try:
            await self.db.execute("""
                UPDATE work_orders
                SET
                    status = $1,
                    description = CASE
                        WHEN $2 IS NOT NULL THEN description || $3 || $2
                        ELSE description
                    END,
                    updated_at = NOW(),
                    completed_at = CASE WHEN $1 = 'completed' THEN NOW() ELSE completed_at END
                WHERE id = $4
            """,
                status,
                notes,
                '\n\n--- Status Update ---\n',
                str(work_order_id),
                fetch_mode="none"
            )

            logger.info(f"Updated work order {work_order_id} status to: {status}")

        except Exception as e:
            logger.error(f"Failed to update work order status: {e}", exc_info=True)
            raise

    async def get_work_order_by_id(self, work_order_id: UUID) -> Optional[Dict]:
        """
        Get work order details by ID.

        Args:
            work_order_id: UUID of work order

        Returns:
            Work order record if found, None otherwise
        """
        try:
            result = await self.db.execute("""
                SELECT
                    id,
                    work_order_number,
                    equipment_id,
                    equipment_number,
                    user_id,
                    title,
                    description,
                    status,
                    priority,
                    fault_codes,
                    confidence_score,
                    route_taken,
                    created_at,
                    updated_at,
                    completed_at
                FROM work_orders
                WHERE id = $1
            """, str(work_order_id))

            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error fetching work order: {e}")
            return None

    async def list_work_orders_by_user(
        self,
        user_id: str,
        limit: int = 50
    ) -> list[Dict]:
        """
        List work orders for a user.

        Args:
            user_id: User ID to filter by
            limit: Maximum number of results (default 50)

        Returns:
            List of work order records
        """
        try:
            results = await self.db.execute("""
                SELECT
                    id,
                    work_order_number,
                    equipment_number,
                    title,
                    status,
                    priority,
                    created_at
                FROM work_orders
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, user_id, limit)

            return results or []

        except Exception as e:
            logger.error(f"Error listing work orders: {e}")
            return []

    async def list_work_orders_by_equipment(
        self,
        equipment_id: UUID,
        limit: int = 50
    ) -> list[Dict]:
        """
        List work orders for specific equipment.

        Args:
            equipment_id: Equipment ID to filter by
            limit: Maximum number of results (default 50)

        Returns:
            List of work order records
        """
        try:
            results = await self.db.execute("""
                SELECT
                    id,
                    work_order_number,
                    title,
                    description,
                    status,
                    priority,
                    fault_codes,
                    created_at,
                    user_id
                FROM work_orders
                WHERE equipment_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, str(equipment_id), limit)

            return results or []

        except Exception as e:
            logger.error(f"Error listing work orders for equipment: {e}")
            return []

    async def get_equipment_maintenance_history(
        self,
        equipment_id: UUID,
        days: int = 90
    ) -> List[Dict]:
        """
        Get maintenance history for equipment within specified time period.

        Used by photo pipeline to provide historical context for AI analysis.

        Args:
            equipment_id: UUID of equipment to get history for
            days: Number of days to look back (default 90)

        Returns:
            List of work order history records with:
            - work_order_number: WO identifier
            - created_at: When WO was created
            - completed_at: When WO was completed (if applicable)
            - status: Current status
            - title: WO title
            - fault_codes: List of fault codes
            - priority: Priority level
            - resolution_time_hours: Hours from creation to completion (if completed)

        Example:
            >>> history = await service.get_equipment_maintenance_history(
            ...     equipment_id=uuid.UUID("..."),
            ...     days=90
            ... )
            >>> for wo in history:
            ...     print(f"{wo['work_order_number']}: {wo['title']}")
        """
        try:
            results = await self.db.execute("""
                SELECT
                    work_order_number,
                    created_at,
                    completed_at,
                    status,
                    title,
                    fault_codes,
                    priority,
                    CASE
                        WHEN completed_at IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600.0
                        ELSE NULL
                    END AS resolution_time_hours
                FROM work_orders
                WHERE equipment_id = $1
                  AND created_at >= NOW() - INTERVAL '%s days'
                ORDER BY created_at DESC
            """ % days, str(equipment_id))

            return results or []

        except Exception as e:
            logger.error(f"Error getting equipment maintenance history: {e}")
            return []

    async def get_technician_work_history(
        self,
        user_id: str,
        days: int = 90,
        status_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Get work order history for a specific technician.

        Used for performance tracking, workload analysis, and technician dashboards.

        Args:
            user_id: Telegram user ID or internal user ID
            days: Number of days to look back (default 90)
            status_filter: Optional status filter ('open', 'in_progress', 'completed', 'cancelled')

        Returns:
            List of work order records with:
            - work_order_number: WO identifier
            - equipment_number: Equipment reference
            - manufacturer: Equipment manufacturer
            - model_number: Equipment model
            - status: Current status
            - title: WO title
            - fault_codes: List of fault codes
            - resolution_time_hours: Hours from creation to completion (if completed)

        Example:
            >>> history = await service.get_technician_work_history(
            ...     user_id="telegram_123",
            ...     days=30,
            ...     status_filter="completed"
            ... )
            >>> for wo in history:
            ...     print(f"{wo['work_order_number']}: {wo['resolution_time_hours']}h")
        """
        try:
            # Build query with optional status filter
            base_query = """
                SELECT
                    work_order_number,
                    equipment_number,
                    manufacturer,
                    model_number,
                    status,
                    title,
                    fault_codes,
                    CASE
                        WHEN completed_at IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600.0
                        ELSE NULL
                    END AS resolution_time_hours
                FROM work_orders
                WHERE user_id = $1
                  AND created_at >= NOW() - INTERVAL '%s days'
            """ % days

            if status_filter:
                base_query += " AND status = $2"
                base_query += " ORDER BY created_at DESC"
                results = await self.db.execute(base_query, user_id, status_filter)
            else:
                base_query += " ORDER BY created_at DESC"
                results = await self.db.execute(base_query, user_id)

            return results or []

        except Exception as e:
            logger.error(f"Error getting technician work history: {e}")
            return []

    def _calculate_priority(
        self,
        confidence_score: Optional[float],
        route: Optional[str],
        fault_codes: List[str],
        safety_warnings: List[str]
    ) -> str:
        """
        Calculate work order priority from response metadata.

        Priority Rules:
        1. Safety warnings = CRITICAL
        2. Low confidence (Route C/D or <0.5) = HIGH
        3. Critical fault codes (F7, F8, F9, E prefix) = HIGH
        4. Other fault codes = MEDIUM
        5. Default = MEDIUM

        Args:
            confidence_score: AI confidence score (0.0-1.0)
            route: Routing decision (A/B/C/D)
            fault_codes: List of fault codes
            safety_warnings: List of safety warnings

        Returns:
            Priority level ('low', 'medium', 'high', 'critical')
        """
        # Priority 1: Safety warnings = CRITICAL
        if safety_warnings:
            return "critical"

        # Priority 2: Low confidence (Route C/D) = HIGH
        if route in ["C", "D"] or (confidence_score is not None and confidence_score < 0.5):
            return "high"

        # Priority 3: Fault codes = MEDIUM to HIGH
        if fault_codes:
            # Check if critical fault (e.g., F-prefix high numbers)
            critical_faults = ["F7", "F8", "F9", "E"]  # Common critical prefixes
            if any(fc.startswith(prefix) for fc in fault_codes for prefix in critical_faults):
                return "high"
            return "medium"

        # Default: MEDIUM
        return "medium"
