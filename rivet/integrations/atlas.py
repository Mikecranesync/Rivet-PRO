"""
Atlas CMMS Integration Layer

Bridges Telegram bot to Atlas CMMS services.
Provides high-level API for equipment and work order management.
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from rivet.atlas import (
    AtlasDatabase,
    EquipmentMatcher,
    WorkOrderService,
    MachineLibrary,
    TechnicianService,
)

logger = logging.getLogger(__name__)


# ===== Custom Exceptions =====

class AtlasError(Exception):
    """Base exception for Atlas CMMS errors."""
    pass


class AtlasNotFoundError(AtlasError):
    """Resource not found in Atlas CMMS."""
    pass


class AtlasValidationError(AtlasError):
    """Invalid data provided to Atlas CMMS."""
    pass


# ===== Atlas Client =====

class AtlasClient:
    """
    High-level client for Atlas CMMS operations.

    Manages database connection and provides simplified API for bots.
    """

    def __init__(self):
        """Initialize Atlas client."""
        self.db = AtlasDatabase()
        self.equipment_matcher = EquipmentMatcher(self.db)
        self.work_order_service = WorkOrderService(self.db, self.equipment_matcher)
        self.machine_library = MachineLibrary(self.db)
        self.technician_service = TechnicianService(self.db)
        self._connected = False

    async def connect(self):
        """Connect to database."""
        if not self._connected:
            await self.db.connect()
            self._connected = True
            logger.info("Atlas CMMS client connected")

    async def close(self):
        """Close database connection."""
        if self._connected:
            await self.db.close()
            self._connected = False
            logger.info("Atlas CMMS client disconnected")

    # ===== Equipment Methods =====

    async def create_equipment(
        self,
        user_id: str,
        manufacturer: str,
        model_number: Optional[str] = None,
        serial_number: Optional[str] = None,
        equipment_type: Optional[str] = None,
        location: Optional[str] = None,
        photo_file_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create equipment (with automatic matching to prevent duplicates).
        Updates technician's equipment count if new equipment created.

        Returns:
            Dict with equipment details including id and equipment_number
        """
        try:
            equipment_id, equipment_number, is_new = await self.equipment_matcher.match_or_create_equipment(
                manufacturer=manufacturer,
                model_number=model_number,
                serial_number=serial_number,
                equipment_type=equipment_type,
                location=location,
                user_id=user_id
            )

            # Get full equipment details
            equipment = await self.equipment_matcher.get_equipment_by_id(equipment_id)
            if not equipment:
                raise AtlasError("Failed to retrieve created equipment")

            # Update technician statistics (only if new equipment was created)
            if is_new:
                await self.technician_service.increment_equipment_count(user_id)

            return equipment

        except Exception as e:
            logger.error(f"Failed to create equipment: {e}", exc_info=True)
            raise AtlasError(f"Failed to create equipment: {str(e)}")

    async def search_equipment(
        self,
        user_id: str,
        query: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search user's equipment.

        Args:
            user_id: Telegram user ID
            query: Search query (currently just lists all user equipment)
            limit: Maximum results

        Returns:
            List of equipment records
        """
        try:
            # Simple implementation: list all user equipment
            # Could be enhanced with fuzzy search later
            return await self.equipment_matcher.list_equipment_by_user(
                user_id=user_id,
                limit=limit
            )

        except Exception as e:
            logger.error(f"Failed to search equipment: {e}", exc_info=True)
            raise AtlasError(f"Failed to search equipment: {str(e)}")

    async def get_equipment(self, equipment_id: UUID) -> Dict[str, Any]:
        """
        Get equipment by ID.

        Raises:
            AtlasNotFoundError if equipment not found
        """
        try:
            equipment = await self.equipment_matcher.get_equipment_by_id(equipment_id)
            if not equipment:
                raise AtlasNotFoundError(f"Equipment {equipment_id} not found")
            return equipment

        except AtlasNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get equipment: {e}", exc_info=True)
            raise AtlasError(f"Failed to get equipment: {str(e)}")

    # ===== Work Order Methods =====

    async def create_work_order(
        self,
        user_id: str,
        title: str,
        description: str,
        manufacturer: Optional[str] = None,
        model_number: Optional[str] = None,
        equipment_type: Optional[str] = None,
        fault_codes: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a work order.

        Automatically matches or creates equipment in CMMS.
        Updates technician's work order count.

        Returns:
            Dict with work order details
        """
        try:
            work_order = await self.work_order_service.create_work_order(
                user_id=user_id,
                title=title,
                description=description,
                manufacturer=manufacturer,
                model_number=model_number,
                equipment_type=equipment_type,
                fault_codes=fault_codes,
                **kwargs
            )

            # Update technician statistics
            await self.technician_service.increment_work_order_count(user_id)

            return work_order

        except Exception as e:
            logger.error(f"Failed to create work order: {e}", exc_info=True)
            raise AtlasError(f"Failed to create work order: {str(e)}")

    async def get_work_order(self, work_order_id: UUID) -> Dict[str, Any]:
        """
        Get work order by ID.

        Raises:
            AtlasNotFoundError if work order not found
        """
        try:
            wo = await self.work_order_service.get_work_order_by_id(work_order_id)
            if not wo:
                raise AtlasNotFoundError(f"Work order {work_order_id} not found")
            return wo

        except AtlasNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get work order: {e}", exc_info=True)
            raise AtlasError(f"Failed to get work order: {str(e)}")

    async def list_work_orders(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List user's work orders.

        Returns:
            List of work order records
        """
        try:
            return await self.work_order_service.list_work_orders_by_user(
                user_id=user_id,
                limit=limit
            )

        except Exception as e:
            logger.error(f"Failed to list work orders: {e}", exc_info=True)
            raise AtlasError(f"Failed to list work orders: {str(e)}")

    async def complete_work_order(
        self,
        work_order_id: UUID,
        notes: Optional[str] = None
    ) -> None:
        """
        Mark work order as completed.

        Args:
            work_order_id: Work order UUID
            notes: Optional completion notes
        """
        try:
            await self.work_order_service.update_status(
                work_order_id=work_order_id,
                status="completed",
                notes=notes
            )

        except Exception as e:
            logger.error(f"Failed to complete work order: {e}", exc_info=True)
            raise AtlasError(f"Failed to complete work order: {str(e)}")

    # ===== Technician/User Methods =====

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create/register a technician user.

        Args:
            user_data: Dict with keys:
                - telegram_user_id (required)
                - username (optional)
                - firstName/first_name (optional)
                - lastName/last_name (optional)
                - specialization (optional)
                - organization (optional)

        Returns:
            Technician data with id, telegram_user_id, etc.
        """
        try:
            # Extract and normalize field names (handle both camelCase and snake_case)
            telegram_user_id = user_data.get("telegram_user_id") or user_data.get("telegramUserId")
            if not telegram_user_id:
                raise AtlasValidationError("telegram_user_id is required")

            username = user_data.get("username")
            first_name = user_data.get("firstName") or user_data.get("first_name")
            last_name = user_data.get("lastName") or user_data.get("last_name")
            specialization = user_data.get("specialization")
            organization = user_data.get("organization")

            technician = await self.technician_service.create_technician(
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                specialization=specialization,
                organization=organization
            )

            # Return in format expected by bot (camelCase for backward compatibility)
            return {
                "id": str(technician["id"]),
                "telegram_user_id": technician["telegram_user_id"],
                "username": technician.get("username"),
                "firstName": technician.get("first_name"),
                "lastName": technician.get("last_name"),
                "specialization": technician.get("specialization"),
                "organization": technician.get("organization"),
                "created": True
            }

        except AtlasValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {e}", exc_info=True)
            raise AtlasError(f"Failed to create user: {str(e)}")

    async def get_technician(self, telegram_user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get technician by Telegram user ID.

        Args:
            telegram_user_id: Telegram user ID

        Returns:
            Technician data if found, None otherwise
        """
        try:
            return await self.technician_service.get_by_telegram_id(telegram_user_id)
        except Exception as e:
            logger.error(f"Failed to get technician: {e}")
            return None

    async def update_technician_activity(self, telegram_user_id: str) -> None:
        """
        Update technician's last activity timestamp.

        Args:
            telegram_user_id: Telegram user ID
        """
        try:
            await self.technician_service.update_activity(telegram_user_id)
        except Exception as e:
            logger.error(f"Failed to update technician activity: {e}")
            # Non-critical, don't raise

    # ===== Machine Library Methods =====

    async def add_machine(
        self,
        user_id: str,
        nickname: str,
        manufacturer: Optional[str] = None,
        model_number: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Add machine to user's library.

        Returns:
            Dict with machine details
        """
        try:
            return await self.machine_library.add_machine(
                user_id=user_id,
                nickname=nickname,
                manufacturer=manufacturer,
                model_number=model_number,
                **kwargs
            )

        except Exception as e:
            logger.error(f"Failed to add machine: {e}", exc_info=True)
            raise AtlasError(f"Failed to add machine: {str(e)}")

    async def list_machines(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List user's machines.

        Returns:
            List of machine records
        """
        try:
            return await self.machine_library.list_machines(
                user_id=user_id,
                limit=limit
            )

        except Exception as e:
            logger.error(f"Failed to list machines: {e}", exc_info=True)
            raise AtlasError(f"Failed to list machines: {str(e)}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
