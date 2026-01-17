"""
Work Order Service for CMMS.

Creates and manages work orders with equipment-first architecture.
Ported from rivet/atlas/work_order_service.py with adaptations for rivet_pro.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID

from rivet_pro.core.services.equipment_service import EquipmentService
from rivet_pro.infra.database import Database
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


class WorkOrderService:
    """Service for creating and managing CMMS work orders."""

    def __init__(self, db: Database):
        """
        Initialize work order service.

        Args:
            db: Database instance
        """
        self.db = db
        self.equipment_service = EquipmentService(db)

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
        source: str = "web",
        priority: str = "medium",
        equipment_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Create a work order.

        Equipment-first architecture:
        1. Match or create equipment in CMMS (if not provided)
        2. Create work order linked to that equipment
        3. Update equipment statistics

        Args:
            user_id: User ID (UUID as string)
            title: Work order title
            description: Detailed description
            manufacturer: Equipment manufacturer (optional)
            model_number: Model number (optional)
            serial_number: Serial number (optional)
            equipment_type: Type of equipment (optional)
            location: Physical location (optional)
            fault_codes: List of fault codes (optional)
            symptoms: List of symptoms (optional)
            source: Source type (web, telegram, api)
            priority: Priority level (low, medium, high, critical)
            equipment_id: Existing equipment ID (optional, will create if not provided)

        Returns:
            Dictionary with work order details:
            {
                "id": UUID,
                "work_order_number": "WO-2026-000001",
                "equipment_id": UUID,
                "equipment_number": "EQ-2026-000001",
                "created_at": datetime
            }
        """
        try:
            # 1. MATCH OR CREATE EQUIPMENT (if equipment_id not provided)
            if not equipment_id:
                equipment_id, equipment_number, is_new_equipment = await self.equipment_service.match_or_create_equipment(
                    manufacturer=manufacturer,
                    model_number=model_number,
                    serial_number=serial_number,
                    equipment_type=equipment_type,
                    location=location,
                    user_id=user_id
                )

                logger.info(
                    f"Equipment {'CREATED' if is_new_equipment else 'MATCHED'}: "
                    f"{equipment_number} (ID: {equipment_id})"
                )
            else:
                # Get equipment number for existing equipment
                equipment = await self.equipment_service.get_equipment_by_id(equipment_id)
                if not equipment:
                    raise ValueError(f"Equipment {equipment_id} not found")
                equipment_number = equipment["equipment_number"]

            # 2. Insert work order (WITH EQUIPMENT LINK)
            work_order_result = await self.db.execute_query_async(
                """
                INSERT INTO work_orders (
                    user_id, source,
                    manufacturer, model_number, serial_number, equipment_type,
                    location,
                    equipment_id, equipment_number,
                    title, description, fault_codes, symptoms,
                    status, priority
                ) VALUES (
                    $1, $2,
                    $3, $4, $5, $6,
                    $7,
                    $8, $9,
                    $10, $11, $12, $13,
                    $14, $15
                )
                RETURNING id, work_order_number, created_at
                """,
                (
                    user_id,
                    source,
                    manufacturer,
                    model_number,
                    serial_number,
                    equipment_type,
                    location,
                    str(equipment_id),  # Equipment ID
                    equipment_number,  # Equipment number (denormalized)
                    title,
                    description,
                    fault_codes or [],
                    symptoms or [],
                    'open',
                    priority,
                ),
                fetch_mode="one"
            )

            if not work_order_result:
                raise Exception("Work order creation failed - no result returned")

            work_order = work_order_result[0]

            logger.info(
                f"Work order created: {work_order['work_order_number']} "
                f"for user {user_id} (equipment: {equipment_number})"
            )

            # 3. Update equipment statistics (fault code)
            if fault_codes:
                await self.db.execute_query_async(
                    """
                    UPDATE cmms_equipment
                    SET last_reported_fault = $1
                    WHERE id = $2
                    """,
                    (fault_codes[0], equipment_id),
                    fetch_mode="none"
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
            await self.db.execute_query_async(
                """
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
                (
                    status,
                    notes,
                    '\n\n--- Status Update ---\n',
                    str(work_order_id),
                ),
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
            result = await self.db.execute_query_async(
                """
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
                    symptoms,
                    created_at,
                    updated_at,
                    completed_at
                FROM work_orders
                WHERE id = $1
                """,
                (str(work_order_id),),
                fetch_mode="one"
            )

            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error fetching work order: {e}")
            return None

    async def list_work_orders_by_user(
        self,
        user_id: str,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        List work orders for a user.

        Args:
            user_id: User ID to filter by
            limit: Maximum number of results (default 50)
            status: Optional status filter

        Returns:
            List of work order records
        """
        try:
            if status:
                results = await self.db.execute_query_async(
                    """
                    SELECT
                        id,
                        work_order_number,
                        equipment_number,
                        title,
                        status,
                        priority,
                        created_at
                    FROM work_orders
                    WHERE user_id = $1 AND status = $2
                    ORDER BY created_at DESC
                    LIMIT $3
                    """,
                    (user_id, status, limit)
                )
            else:
                results = await self.db.execute_query_async(
                    """
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
                    """,
                    (user_id, limit)
                )

            return results or []

        except Exception as e:
            logger.error(f"Error listing work orders: {e}")
            return []

    async def list_work_orders_by_equipment(
        self,
        equipment_id: UUID,
        limit: int = 50
    ) -> List[Dict]:
        """
        List work orders for specific equipment.

        Args:
            equipment_id: Equipment ID to filter by
            limit: Maximum number of results (default 50)

        Returns:
            List of work order records
        """
        try:
            results = await self.db.execute_query_async(
                """
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
                """,
                (str(equipment_id), limit)
            )

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
        """
        try:
            results = await self.db.execute_query_async(
                """
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
                """ % days,
                (str(equipment_id),)
            )

            return results or []

        except Exception as e:
            logger.error(f"Error getting equipment maintenance history: {e}")
            return []
