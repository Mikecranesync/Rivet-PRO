#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Personal Machine Library Service

Manages users' saved equipment for quick context in troubleshooting.
Provides CRUD operations for the user_machines table.

Usage:
    from rivet.atlas import AtlasDatabase, MachineLibrary

    db = AtlasDatabase()
    await db.connect()

    library = MachineLibrary(db)
    machine = await library.add_machine(
        user_id="telegram_123",
        nickname="Motor A",
        manufacturer="Siemens",
        model_number="1LE1001"
    )
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

logger = logging.getLogger(__name__)


class MachineLibrary:
    """Service for managing user's personal equipment library."""

    def __init__(self, db):
        """
        Initialize machine library service.

        Args:
            db: AtlasDatabase instance
        """
        self.db = db

    async def add_machine(
        self,
        user_id: str,
        nickname: str,
        manufacturer: Optional[str] = None,
        model_number: Optional[str] = None,
        serial_number: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None,
        photo_file_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a machine to user's library.

        Args:
            user_id: Telegram user ID
            nickname: User's name for the machine (e.g., "Motor A", "VFD 3")
            manufacturer: Equipment manufacturer (optional)
            model_number: Model number (optional)
            serial_number: Serial number (optional)
            location: Physical location (optional)
            notes: User notes (optional)
            photo_file_id: Telegram photo file ID (optional)

        Returns:
            Dictionary with machine details including ID

        Raises:
            Exception if nickname already exists for this user

        Example:
            >>> machine = await library.add_machine(
            ...     user_id="telegram_123",
            ...     nickname="Motor A",
            ...     manufacturer="Siemens",
            ...     model_number="1LE1001",
            ...     location="Building A - Line 3"
            ... )
            >>> print(f"Saved: {machine['nickname']} (ID: {machine['id']})")
        """
        try:
            result = await self.db.execute("""
                INSERT INTO user_machines (
                    user_id,
                    nickname,
                    manufacturer,
                    model_number,
                    serial_number,
                    location,
                    notes,
                    photo_file_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, created_at
            """,
                user_id,
                nickname,
                manufacturer,
                model_number,
                serial_number,
                location,
                notes,
                photo_file_id
            )

            machine = result[0]
            logger.info(
                f"Added machine to library: {nickname} for user {user_id} (ID: {machine['id']})"
            )

            return {
                "id": machine["id"],
                "user_id": user_id,
                "nickname": nickname,
                "manufacturer": manufacturer,
                "model_number": model_number,
                "serial_number": serial_number,
                "location": location,
                "notes": notes,
                "photo_file_id": photo_file_id,
                "created_at": machine["created_at"]
            }

        except Exception as e:
            logger.error(f"Failed to add machine: {e}", exc_info=True)
            raise

    async def get_machine(
        self,
        user_id: str,
        machine_id: Optional[UUID] = None,
        nickname: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a machine from user's library.

        Args:
            user_id: Telegram user ID
            machine_id: Machine UUID (optional)
            nickname: Machine nickname (optional)

        Returns:
            Machine details if found, None otherwise

        Note:
            Must provide either machine_id or nickname

        Example:
            >>> machine = await library.get_machine(
            ...     user_id="telegram_123",
            ...     nickname="Motor A"
            ... )
            >>> if machine:
            ...     print(f"Found: {machine['manufacturer']} {machine['model_number']}")
        """
        try:
            if machine_id:
                result = await self.db.execute("""
                    SELECT
                        id,
                        user_id,
                        nickname,
                        manufacturer,
                        model_number,
                        serial_number,
                        location,
                        notes,
                        photo_file_id,
                        created_at,
                        updated_at,
                        last_query_at
                    FROM user_machines
                    WHERE user_id = $1 AND id = $2
                """, user_id, str(machine_id) if isinstance(machine_id, UUID) else machine_id)

            elif nickname:
                result = await self.db.execute("""
                    SELECT
                        id,
                        user_id,
                        nickname,
                        manufacturer,
                        model_number,
                        serial_number,
                        location,
                        notes,
                        photo_file_id,
                        created_at,
                        updated_at,
                        last_query_at
                    FROM user_machines
                    WHERE user_id = $1 AND nickname = $2
                """, user_id, nickname)

            else:
                raise ValueError("Must provide either machine_id or nickname")

            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error fetching machine: {e}")
            return None

    async def list_machines(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List all machines in user's library.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of results (default 50)

        Returns:
            List of machine records, sorted by last query time (most recent first)

        Example:
            >>> machines = await library.list_machines(user_id="telegram_123")
            >>> for machine in machines:
            ...     print(f"- {machine['nickname']}: {machine['manufacturer']}")
        """
        try:
            results = await self.db.execute("""
                SELECT
                    id,
                    nickname,
                    manufacturer,
                    model_number,
                    serial_number,
                    location,
                    notes,
                    photo_file_id,
                    created_at,
                    last_query_at
                FROM user_machines
                WHERE user_id = $1
                ORDER BY last_query_at DESC NULLS LAST, created_at DESC
                LIMIT $2
            """, user_id, limit)

            return results or []

        except Exception as e:
            logger.error(f"Error listing machines: {e}")
            return []

    async def update_machine(
        self,
        user_id: str,
        machine_id: UUID,
        nickname: Optional[str] = None,
        manufacturer: Optional[str] = None,
        model_number: Optional[str] = None,
        serial_number: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None,
        photo_file_id: Optional[str] = None
    ) -> bool:
        """
        Update a machine in user's library.

        Args:
            user_id: Telegram user ID
            machine_id: Machine UUID
            nickname: New nickname (optional)
            manufacturer: New manufacturer (optional)
            model_number: New model number (optional)
            serial_number: New serial number (optional)
            location: New location (optional)
            notes: New notes (optional)
            photo_file_id: New photo file ID (optional)

        Returns:
            True if updated, False if machine not found

        Example:
            >>> success = await library.update_machine(
            ...     user_id="telegram_123",
            ...     machine_id=machine_id,
            ...     location="Building B - Line 2"
            ... )
        """
        try:
            # Build dynamic update query
            updates = []
            params = []
            param_count = 1

            if nickname is not None:
                updates.append(f"nickname = ${param_count}")
                params.append(nickname)
                param_count += 1

            if manufacturer is not None:
                updates.append(f"manufacturer = ${param_count}")
                params.append(manufacturer)
                param_count += 1

            if model_number is not None:
                updates.append(f"model_number = ${param_count}")
                params.append(model_number)
                param_count += 1

            if serial_number is not None:
                updates.append(f"serial_number = ${param_count}")
                params.append(serial_number)
                param_count += 1

            if location is not None:
                updates.append(f"location = ${param_count}")
                params.append(location)
                param_count += 1

            if notes is not None:
                updates.append(f"notes = ${param_count}")
                params.append(notes)
                param_count += 1

            if photo_file_id is not None:
                updates.append(f"photo_file_id = ${param_count}")
                params.append(photo_file_id)
                param_count += 1

            if not updates:
                return False

            # Add user_id and machine_id
            params.append(user_id)
            params.append(str(machine_id) if isinstance(machine_id, UUID) else machine_id)

            query = f"""
                UPDATE user_machines
                SET {', '.join(updates)}
                WHERE user_id = ${param_count} AND id = ${param_count + 1}
            """

            await self.db.execute(query, *params, fetch_mode="none")

            logger.info(f"Updated machine {machine_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update machine: {e}", exc_info=True)
            return False

    async def delete_machine(
        self,
        user_id: str,
        machine_id: UUID
    ) -> bool:
        """
        Delete a machine from user's library.

        Args:
            user_id: Telegram user ID
            machine_id: Machine UUID

        Returns:
            True if deleted, False if machine not found

        Example:
            >>> success = await library.delete_machine(
            ...     user_id="telegram_123",
            ...     machine_id=machine_id
            ... )
        """
        try:
            await self.db.execute("""
                DELETE FROM user_machines
                WHERE user_id = $1 AND id = $2
            """, user_id, str(machine_id) if isinstance(machine_id, UUID) else machine_id, fetch_mode="none")

            logger.info(f"Deleted machine {machine_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete machine: {e}", exc_info=True)
            return False

    async def record_query(
        self,
        machine_id: UUID
    ) -> None:
        """
        Record that this machine was used in a troubleshooting query.

        Updates last_query_at timestamp for sorting by recency.

        Args:
            machine_id: Machine UUID

        Example:
            >>> await library.record_query(machine_id=machine_id)
        """
        try:
            await self.db.execute("""
                UPDATE user_machines
                SET last_query_at = NOW()
                WHERE id = $1
            """, str(machine_id) if isinstance(machine_id, UUID) else machine_id, fetch_mode="none")

            logger.debug(f"Recorded query for machine {machine_id}")

        except Exception as e:
            logger.error(f"Failed to record query: {e}")
            # Don't raise - this is non-critical
