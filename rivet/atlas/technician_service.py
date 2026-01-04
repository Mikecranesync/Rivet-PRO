#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Technician Service - User Registration and Activity Tracking

Manages technician users who interact with Atlas CMMS via Telegram.
Tracks registration, profile updates, and activity statistics.

Usage:
    from rivet.atlas import AtlasDatabase, TechnicianService

    db = AtlasDatabase()
    await db.connect()

    service = TechnicianService(db)

    technician = await service.create_technician(
        telegram_user_id="123456789",
        username="john_doe",
        first_name="John",
        last_name="Doe",
        specialization="Electrical"
    )
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID

logger = logging.getLogger(__name__)


class TechnicianService:
    """Service for managing technician users."""

    def __init__(self, db):
        """
        Initialize technician service.

        Args:
            db: AtlasDatabase instance
        """
        self.db = db

    async def create_technician(
        self,
        telegram_user_id: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        specialization: Optional[str] = None,
        organization: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new technician user.

        Args:
            telegram_user_id: Telegram user ID (required, unique)
            username: Telegram @username (optional)
            first_name: First name
            last_name: Last name
            specialization: Professional specialization (e.g., "Electrical")
            organization: Company or facility name

        Returns:
            Dictionary with technician details including id

        Example:
            >>> technician = await service.create_technician(
            ...     telegram_user_id="123456789",
            ...     username="john_doe",
            ...     first_name="John",
            ...     specialization="Electrical"
            ... )
            >>> print(f"Registered: {technician['first_name']}")
        """
        try:
            # Check if technician already exists
            existing = await self.get_by_telegram_id(telegram_user_id)
            if existing:
                logger.info(f"Technician already registered: {telegram_user_id}")
                # Update last_activity_at
                await self.update_activity(telegram_user_id)
                return existing

            # Create new technician
            result = await self.db.execute("""
                INSERT INTO technicians (
                    telegram_user_id,
                    username,
                    first_name,
                    last_name,
                    specialization,
                    organization,
                    is_active,
                    last_activity_at
                ) VALUES ($1, $2, $3, $4, $5, $6, TRUE, NOW())
                RETURNING
                    id,
                    telegram_user_id,
                    username,
                    first_name,
                    last_name,
                    specialization,
                    organization,
                    is_active,
                    created_at,
                    work_order_count,
                    equipment_count
            """,
                telegram_user_id,
                username,
                first_name,
                last_name,
                specialization,
                organization,
                fetch_mode="one"
            )

            technician = result[0] if result else None
            if not technician:
                raise Exception("Failed to create technician")

            logger.info(
                f"Technician registered: {technician['first_name']} "
                f"({technician['telegram_user_id']})"
            )

            return technician

        except Exception as e:
            logger.error(f"Failed to create technician: {e}", exc_info=True)
            raise

    async def get_by_telegram_id(self, telegram_user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get technician by Telegram user ID.

        Args:
            telegram_user_id: Telegram user ID

        Returns:
            Technician record if found, None otherwise
        """
        try:
            result = await self.db.execute("""
                SELECT
                    id,
                    telegram_user_id,
                    username,
                    first_name,
                    last_name,
                    specialization,
                    organization,
                    is_active,
                    created_at,
                    updated_at,
                    last_activity_at,
                    work_order_count,
                    equipment_count
                FROM technicians
                WHERE telegram_user_id = $1
            """, telegram_user_id, fetch_mode="one")

            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error fetching technician: {e}")
            return None

    async def get_by_id(self, technician_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get technician by internal UUID.

        Args:
            technician_id: Technician UUID

        Returns:
            Technician record if found, None otherwise
        """
        try:
            result = await self.db.execute("""
                SELECT
                    id,
                    telegram_user_id,
                    username,
                    first_name,
                    last_name,
                    specialization,
                    organization,
                    is_active,
                    created_at,
                    updated_at,
                    last_activity_at,
                    work_order_count,
                    equipment_count
                FROM technicians
                WHERE id = $1
            """, str(technician_id), fetch_mode="one")

            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error fetching technician by ID: {e}")
            return None

    async def update_activity(self, telegram_user_id: str) -> None:
        """
        Update technician's last activity timestamp.

        Call this on every bot interaction to track engagement.

        Args:
            telegram_user_id: Telegram user ID
        """
        try:
            await self.db.execute("""
                UPDATE technicians
                SET last_activity_at = NOW()
                WHERE telegram_user_id = $1
            """, telegram_user_id, fetch_mode="none")

        except Exception as e:
            logger.error(f"Failed to update technician activity: {e}")
            # Don't raise - activity tracking is non-critical

    async def increment_work_order_count(self, telegram_user_id: str) -> None:
        """
        Increment work order count for technician.

        Call this when a technician creates a work order.

        Args:
            telegram_user_id: Telegram user ID
        """
        try:
            await self.db.execute("""
                UPDATE technicians
                SET
                    work_order_count = work_order_count + 1,
                    last_activity_at = NOW()
                WHERE telegram_user_id = $1
            """, telegram_user_id, fetch_mode="none")

            logger.debug(f"Incremented work order count for {telegram_user_id}")

        except Exception as e:
            logger.error(f"Failed to increment work order count: {e}")
            # Don't raise - counter is denormalized, non-critical

    async def increment_equipment_count(self, telegram_user_id: str) -> None:
        """
        Increment equipment count for technician.

        Call this when a technician registers equipment.

        Args:
            telegram_user_id: Telegram user ID
        """
        try:
            await self.db.execute("""
                UPDATE technicians
                SET
                    equipment_count = equipment_count + 1,
                    last_activity_at = NOW()
                WHERE telegram_user_id = $1
            """, telegram_user_id, fetch_mode="none")

            logger.debug(f"Incremented equipment count for {telegram_user_id}")

        except Exception as e:
            logger.error(f"Failed to increment equipment count: {e}")
            # Don't raise - counter is denormalized, non-critical

    async def update_profile(
        self,
        telegram_user_id: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        specialization: Optional[str] = None,
        organization: Optional[str] = None
    ) -> None:
        """
        Update technician profile information.

        Only updates fields that are provided (not None).

        Args:
            telegram_user_id: Telegram user ID
            username: New username (optional)
            first_name: New first name (optional)
            last_name: New last name (optional)
            specialization: New specialization (optional)
            organization: New organization (optional)
        """
        try:
            # Build dynamic UPDATE query for provided fields
            updates = []
            params = []
            param_idx = 1

            if username is not None:
                updates.append(f"username = ${param_idx}")
                params.append(username)
                param_idx += 1

            if first_name is not None:
                updates.append(f"first_name = ${param_idx}")
                params.append(first_name)
                param_idx += 1

            if last_name is not None:
                updates.append(f"last_name = ${param_idx}")
                params.append(last_name)
                param_idx += 1

            if specialization is not None:
                updates.append(f"specialization = ${param_idx}")
                params.append(specialization)
                param_idx += 1

            if organization is not None:
                updates.append(f"organization = ${param_idx}")
                params.append(organization)
                param_idx += 1

            if not updates:
                logger.debug("No profile updates provided")
                return

            # Add telegram_user_id as last parameter
            params.append(telegram_user_id)

            query = f"""
                UPDATE technicians
                SET {', '.join(updates)}, last_activity_at = NOW()
                WHERE telegram_user_id = ${param_idx}
            """

            await self.db.execute(query, *params, fetch_mode="none")

            logger.info(f"Updated profile for {telegram_user_id}")

        except Exception as e:
            logger.error(f"Failed to update technician profile: {e}", exc_info=True)
            raise

    async def deactivate(self, telegram_user_id: str) -> None:
        """
        Deactivate a technician (soft delete).

        Args:
            telegram_user_id: Telegram user ID
        """
        try:
            await self.db.execute("""
                UPDATE technicians
                SET is_active = FALSE
                WHERE telegram_user_id = $1
            """, telegram_user_id, fetch_mode="none")

            logger.info(f"Deactivated technician: {telegram_user_id}")

        except Exception as e:
            logger.error(f"Failed to deactivate technician: {e}", exc_info=True)
            raise

    async def reactivate(self, telegram_user_id: str) -> None:
        """
        Reactivate a previously deactivated technician.

        Args:
            telegram_user_id: Telegram user ID
        """
        try:
            await self.db.execute("""
                UPDATE technicians
                SET is_active = TRUE, last_activity_at = NOW()
                WHERE telegram_user_id = $1
            """, telegram_user_id, fetch_mode="none")

            logger.info(f"Reactivated technician: {telegram_user_id}")

        except Exception as e:
            logger.error(f"Failed to reactivate technician: {e}", exc_info=True)
            raise

    async def list_all(
        self,
        active_only: bool = True,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """
        List all technicians.

        Args:
            active_only: Only return active technicians (default True)
            limit: Maximum number of results (default 100)

        Returns:
            List of technician records
        """
        try:
            if active_only:
                query = """
                    SELECT
                        id,
                        telegram_user_id,
                        username,
                        first_name,
                        last_name,
                        specialization,
                        organization,
                        work_order_count,
                        equipment_count,
                        last_activity_at
                    FROM technicians
                    WHERE is_active = TRUE
                    ORDER BY last_activity_at DESC
                    LIMIT $1
                """
            else:
                query = """
                    SELECT
                        id,
                        telegram_user_id,
                        username,
                        first_name,
                        last_name,
                        specialization,
                        organization,
                        is_active,
                        work_order_count,
                        equipment_count,
                        last_activity_at
                    FROM technicians
                    ORDER BY last_activity_at DESC
                    LIMIT $1
                """

            results = await self.db.execute(query, limit)
            return results or []

        except Exception as e:
            logger.error(f"Error listing technicians: {e}")
            return []
