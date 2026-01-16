"""
Equipment Service - CMMS Equipment Matching & Creation (ADAPTED FOR UNIFIED SCHEMA)

Matches user input to existing CMMS equipment or creates new equipment records.
Implements equipment-first architecture with fuzzy matching to prevent duplicates.

CRITICAL CHANGES FROM RIVET:
- Links to equipment_models table (canonical equipment knowledge)
- Auto-linking handled by database trigger
- Supports unified schema from Phase 2 migrations

Adapted from rivet/atlas/equipment_matcher.py for Phase 2 unified schema
"""

import logging
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class EquipmentService:
    """Match user input to existing CMMS equipment or create new (unified schema)."""

    def __init__(self, db):
        """
        Initialize equipment service.

        Args:
            db: Database connection (from rivet_pro.infra.database)
        """
        self.db = db

    async def find_or_create_equipment_model(
        self,
        manufacturer: str,
        model_number: str,
    ) -> Optional[UUID]:
        """
        Find or create equipment_model record.

        This links CMMS equipment to canonical knowledge base.

        Args:
            manufacturer: Manufacturer name (e.g., "Siemens")
            model_number: Model number (e.g., "G120C")

        Returns:
            equipment_model_id (UUID) or None if creation fails

        Example:
            >>> model_id = await service.find_or_create_equipment_model("Siemens", "G120C")
        """
        try:
            # First, get or create manufacturer
            manufacturer_result = await self.db.execute_query_async("""
                WITH inserted AS (
                    INSERT INTO manufacturers (name)
                    VALUES ($1)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id
                )
                SELECT id FROM inserted
                UNION ALL
                SELECT id FROM manufacturers WHERE name = $1
                LIMIT 1
            """, (manufacturer,))

            if not manufacturer_result:
                logger.error(f"Failed to get/create manufacturer: {manufacturer}")
                return None

            manufacturer_id = manufacturer_result[0]["id"]

            # Now, get or create equipment_model
            model_result = await self.db.execute_query_async("""
                WITH inserted AS (
                    INSERT INTO equipment_models (manufacturer_id, model_number)
                    VALUES ($1, $2)
                    ON CONFLICT (manufacturer_id, model_number) DO NOTHING
                    RETURNING id
                )
                SELECT id FROM inserted
                UNION ALL
                SELECT id FROM equipment_models
                WHERE manufacturer_id = $1 AND model_number = $2
                LIMIT 1
            """, (manufacturer_id, model_number))

            if not model_result:
                logger.error(f"Failed to get/create equipment_model: {manufacturer} {model_number}")
                return None

            equipment_model_id = model_result[0]["id"]
            logger.info(f"Equipment model: {manufacturer} {model_number} → {equipment_model_id}")
            return equipment_model_id

        except Exception as e:
            logger.error(f"Error in find_or_create_equipment_model: {e}", exc_info=True)
            return None

    async def match_or_create_equipment(
        self,
        manufacturer: Optional[str],
        model_number: Optional[str],
        serial_number: Optional[str],
        equipment_type: Optional[str],
        location: Optional[str],
        user_id: str,
        machine_id: Optional[UUID] = None
    ) -> Tuple[UUID, str, bool]:
        """
        Match to existing equipment or create new.

        3-Step Matching Algorithm:
        1. Exact match on serial number (if provided)
        2. Fuzzy match on manufacturer + model (85%+ similarity)
        3. Match via user's machine library (machine_id)
        4. Create new equipment if no match found

        ADAPTED FOR UNIFIED SCHEMA:
        - Creates equipment_model record first (if manufacturer + model provided)
        - Links cmms_equipment to equipment_model via equipment_model_id
        - Auto-linking trigger handles fuzzy matching in database

        Args:
            manufacturer: Equipment manufacturer (e.g., "Siemens")
            model_number: Model number (e.g., "G120C")
            serial_number: Serial number (e.g., "SR123456")
            equipment_type: Type of equipment (e.g., "VFD", "PLC")
            location: Physical location (e.g., "Building A, Floor 2")
            user_id: User who reported this equipment
            machine_id: Optional link to user's machine library

        Returns:
            Tuple of (equipment_id, equipment_number, is_new_equipment)
            - equipment_id: UUID of matched or created equipment
            - equipment_number: Equipment number (e.g., "EQ-2025-0001")
            - is_new_equipment: True if equipment was created, False if matched

        Example:
            >>> service = EquipmentService(db)
            >>> equipment_id, equipment_number, is_new = await service.match_or_create_equipment(
            ...     manufacturer="Siemens",
            ...     model_number="G120C",
            ...     serial_number="SR123456",
            ...     equipment_type="VFD",
            ...     location="Building A, Floor 2",
            ...     user_id="telegram_12345678"  # Example user ID
            ... )
            >>> print(f"Equipment: {equipment_number}, New: {is_new}")
        """

        # Step 1: Try exact match on serial number (if provided)
        if serial_number:
            equipment = await self._match_by_serial(serial_number)
            if equipment:
                logger.info(
                    f"Matched equipment by serial: {equipment['equipment_number']} "
                    f"(serial: {serial_number})"
                )
                return (equipment["id"], equipment["equipment_number"], False)

        # Step 2: Try fuzzy match on manufacturer + model
        if manufacturer and model_number:
            equipment = await self._fuzzy_match(manufacturer, model_number)
            if equipment:
                logger.info(
                    f"Matched equipment by fuzzy: {equipment['equipment_number']} "
                    f"({manufacturer} {model_number})"
                )
                return (equipment["id"], equipment["equipment_number"], False)

        # Step 3: Try match via user's machine library
        if machine_id:
            equipment = await self._match_by_machine_id(machine_id)
            if equipment:
                logger.info(
                    f"Matched equipment by machine_id: {equipment['equipment_number']} "
                    f"(machine_id: {machine_id})"
                )
                return (equipment["id"], equipment["equipment_number"], False)

        # Step 4: No match found → Create new equipment
        equipment_id, equipment_number = await self._create_equipment(
            manufacturer=manufacturer or "Unknown",
            model_number=model_number,
            serial_number=serial_number,
            equipment_type=equipment_type,
            location=location,
            owned_by_user_id=user_id,
            machine_id=machine_id
        )

        logger.info(
            f"Created new equipment: {equipment_number} "
            f"({manufacturer} {model_number})"
        )

        return (equipment_id, equipment_number, True)

    async def _match_by_serial(self, serial_number: str) -> Optional[Dict]:
        """Exact match on serial number."""
        try:
            result = await self.db.execute_query_async("""
                SELECT id, manufacturer, model_number, equipment_number
                FROM cmms_equipment
                WHERE serial_number = $1
                LIMIT 1
            """, (serial_number,))

            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error matching by serial: {e}")
            return None

    async def _fuzzy_match(
        self,
        manufacturer: str,
        model_number: str,
        threshold: float = 0.85
    ) -> Optional[Dict]:
        """Fuzzy match on manufacturer + model."""
        try:
            # Get all equipment from same manufacturer
            candidates = await self.db.execute_query_async("""
                SELECT id, manufacturer, model_number, equipment_number
                FROM cmms_equipment
                WHERE LOWER(manufacturer) = LOWER($1)
            """, (manufacturer,))

            if not candidates:
                return None

            best_match = None
            best_score = 0.0

            for candidate in candidates:
                score = SequenceMatcher(
                    None,
                    model_number.lower(),
                    candidate["model_number"].lower() if candidate["model_number"] else ""
                ).ratio()

                if score > best_score:
                    best_score = score
                    best_match = candidate

            if best_score >= threshold:
                logger.debug(f"Fuzzy match found with {best_score:.2%} similarity")
                return best_match

            logger.debug(f"No fuzzy match above threshold ({threshold:.0%}). Best: {best_score:.2%}")
            return None

        except Exception as e:
            logger.error(f"Error in fuzzy matching: {e}")
            return None

    async def _match_by_machine_id(self, machine_id: UUID) -> Optional[Dict]:
        """Match via user's machine library."""
        try:
            result = await self.db.execute_query_async("""
                SELECT e.id, e.manufacturer, e.model_number, e.equipment_number
                FROM cmms_equipment e
                JOIN user_machines um ON um.equipment_id = e.id
                WHERE um.id = $1
                LIMIT 1
            """, (machine_id,))

            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error matching by machine_id: {e}")
            return None

    async def _create_equipment(
        self,
        manufacturer: str,
        model_number: Optional[str],
        serial_number: Optional[str],
        equipment_type: Optional[str],
        location: Optional[str],
        owned_by_user_id: str,
        machine_id: Optional[UUID]
    ) -> Tuple[UUID, str]:
        """
        Create new equipment in CMMS (ADAPTED FOR UNIFIED SCHEMA).

        CRITICAL: This method now:
        1. Creates equipment_model record (if manufacturer + model provided)
        2. Creates cmms_equipment with equipment_model_id link
        3. Auto-linking trigger handles matching in database

        Args:
            manufacturer: Equipment manufacturer
            model_number: Model number (optional)
            serial_number: Serial number (optional)
            equipment_type: Type of equipment (optional)
            location: Physical location (optional)
            owned_by_user_id: User who first reported this equipment
            machine_id: Optional link to user's machine library

        Returns:
            Tuple of (equipment_id, equipment_number)

        Raises:
            Exception if creation fails
        """
        try:
            # Step 1: Get or create equipment_model (if we have manufacturer + model)
            equipment_model_id = None
            if manufacturer and model_number:
                equipment_model_id = await self.find_or_create_equipment_model(
                    manufacturer, model_number
                )

            # Step 2: Create cmms_equipment
            # NOTE: Auto-linking trigger will set equipment_model_id if we didn't provide it
            result = await self.db.execute_query_async("""
                INSERT INTO cmms_equipment (
                    manufacturer,
                    model_number,
                    serial_number,
                    equipment_type,
                    location,
                    owned_by_user_id,
                    first_reported_by,
                    equipment_model_id,
                    work_order_count
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 0)
                RETURNING id, equipment_number
            """,
                (manufacturer,
                model_number,
                serial_number,
                equipment_type,
                location,
                owned_by_user_id,
                owned_by_user_id,
                equipment_model_id),
                fetch_mode="one"
            )

            equipment_id = result[0]["id"]
            equipment_number = result[0]["equipment_number"]

            logger.info(
                f"Created equipment {equipment_number}: "
                f"{manufacturer} {model_number or 'Unknown Model'} "
                f"(model_id: {equipment_model_id})"
            )

            return (equipment_id, equipment_number)

        except Exception as e:
            logger.error(f"Failed to create equipment: {e}", exc_info=True)
            raise

    async def update_equipment_stats(
        self,
        equipment_id: UUID,
        fault_code: Optional[str] = None
    ) -> None:
        """
        Update equipment statistics after work order creation.

        Note: work_order_count and last_work_order_at are auto-updated
        by the database trigger. This method handles optional fault_code update.

        Args:
            equipment_id: UUID of equipment to update
            fault_code: Optional fault code to record
        """
        try:
            if fault_code:
                await self.db.execute_query_async("""
                    UPDATE cmms_equipment
                    SET
                        last_reported_fault = $2,
                        updated_at = NOW()
                    WHERE id = $1
                """, (equipment_id, fault_code), fetch_mode="none")

                logger.debug(f"Updated equipment {equipment_id} with fault code: {fault_code}")

        except Exception as e:
            logger.error(f"Failed to update equipment stats: {e}")

    async def get_equipment_by_id(self, equipment_id: UUID) -> Optional[Dict]:
        """Get equipment details by ID (with equipment_model info)."""
        try:
            result = await self.db.execute_query_async("""
                SELECT
                    e.id,
                    e.equipment_number,
                    e.manufacturer,
                    e.model_number,
                    e.serial_number,
                    e.equipment_type,
                    e.location,
                    e.work_order_count,
                    e.last_reported_fault,
                    e.last_work_order_at,
                    e.created_at,
                    e.equipment_model_id,
                    em.id AS model_id,
                    m.name AS model_manufacturer
                FROM cmms_equipment e
                LEFT JOIN equipment_models em ON e.equipment_model_id = em.id
                LEFT JOIN manufacturers m ON em.manufacturer_id = m.id
                WHERE e.id = $1
            """, (equipment_id,), fetch_mode="one")

            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error fetching equipment: {e}")
            return None

    async def list_equipment_by_user(
        self,
        user_id: str,
        limit: int = 50
    ) -> list[Dict]:
        """List equipment owned by user."""
        try:
            results = await self.db.execute_query_async("""
                SELECT
                    id,
                    equipment_number,
                    manufacturer,
                    model_number,
                    serial_number,
                    equipment_type,
                    location,
                    work_order_count,
                    last_reported_fault,
                    created_at
                FROM cmms_equipment
                WHERE owned_by_user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, (user_id, limit))

            return results or []

        except Exception as e:
            logger.error(f"Error listing equipment: {e}")
            return []
