"""
Atlas CMMS Database Adapter

Provides async PostgreSQL access for Atlas CMMS operations.
Uses asyncpg connection pooling for performance and reliability.
Compatible with Agent Factory's DatabaseManager interface.
"""

import asyncpg
import logging
from typing import Optional, List, Dict, Tuple, Any
from contextlib import asynccontextmanager

from rivet.config import get_settings

logger = logging.getLogger(__name__)


class AtlasDatabase:
    """
    Atlas CMMS database adapter for Rivet Pro.

    Features:
    - Connection pooling with asyncpg
    - Automatic connection management
    - Compatible with Agent Factory's interface
    - Dict-based results for easy serialization

    Usage:
        db = AtlasDatabase()
        await db.connect()

        results = await db.execute("SELECT * FROM cmms_equipment WHERE manufacturer = $1", "Siemens")

        await db.close()
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize database adapter.

        Args:
            db_url: PostgreSQL connection URL. If None, uses config.database_url
        """
        settings = get_settings()
        self.db_url = db_url or settings.database_url
        self.pool: Optional[asyncpg.Pool] = None
        self._connected = False

        if not self.db_url:
            raise ValueError("Database URL is required. Set DATABASE_URL in .env")

    async def connect(self):
        """
        Create connection pool.

        Pool settings:
        - min_size=2: Keep 2 connections warm
        - max_size=10: Allow up to 10 concurrent connections
        - command_timeout=60: Prevent hung queries
        """
        if self._connected:
            logger.debug("Database already connected")
            return

        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=2,
                max_size=10,
                command_timeout=60.0,
            )
            self._connected = True
            logger.info("Database connection pool created")

            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            logger.info("Database connection verified")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self._connected = False
            logger.info("Database connection pool closed")

    async def execute(
        self,
        query: str,
        *params,
        fetch_mode: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Execute query and return results as list of dicts.

        Args:
            query: SQL query with $1, $2, ... placeholders
            *params: Query parameters
            fetch_mode: "all" (default), "one", or "none"

        Returns:
            List of dicts with column names as keys

        Example:
            results = await db.execute(
                "SELECT * FROM cmms_equipment WHERE manufacturer = $1",
                "Siemens"
            )
            # [{"id": "...", "manufacturer": "Siemens", ...}]
        """
        if not self._connected:
            await self.connect()

        async with self.pool.acquire() as conn:
            if fetch_mode == "none":
                await conn.execute(query, *params)
                return []

            elif fetch_mode == "one":
                row = await conn.fetchrow(query, *params)
                if row:
                    return [dict(row)]
                return []

            else:  # "all"
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]

    async def execute_query_async(
        self,
        query: str,
        params: Tuple = (),
        fetch_mode: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Execute query (Agent Factory compatible interface).

        This method matches Agent Factory's DatabaseManager.execute_query_async()
        signature, allowing extracted services to work without modification.

        Args:
            query: SQL query with $1, $2, ... placeholders
            params: Tuple of query parameters
            fetch_mode: "all", "one", or "none"

        Returns:
            List of dicts with column names as keys
        """
        return await self.execute(query, *params, fetch_mode=fetch_mode)

    async def fetch_one(self, query: str, *params) -> Optional[Dict[str, Any]]:
        """
        Fetch single row as dict.

        Args:
            query: SQL query
            *params: Query parameters

        Returns:
            Dict with column names as keys, or None if no row found
        """
        results = await self.execute(query, *params, fetch_mode="one")
        return results[0] if results else None

    async def fetch_all(self, query: str, *params) -> List[Dict[str, Any]]:
        """
        Fetch all rows as list of dicts.

        Args:
            query: SQL query
            *params: Query parameters

        Returns:
            List of dicts with column names as keys
        """
        return await self.execute(query, *params, fetch_mode="all")

    async def execute_many(
        self,
        query: str,
        params_list: List[Tuple]
    ) -> None:
        """
        Execute same query with multiple parameter sets.

        Args:
            query: SQL query
            params_list: List of parameter tuples

        Example:
            await db.execute_many(
                "INSERT INTO cmms_equipment (manufacturer, model_number) VALUES ($1, $2)",
                [("Siemens", "G120C"), ("Rockwell", "PowerFlex 525")]
            )
        """
        if not self._connected:
            await self.connect()

        async with self.pool.acquire() as conn:
            await conn.executemany(query, params_list)

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.

        Usage:
            async with db.transaction() as tx:
                await tx.execute("INSERT INTO cmms_equipment (...) VALUES (...)")
                await tx.execute("INSERT INTO work_orders (...) VALUES (...)")
                # Auto-commit on success, auto-rollback on exception

        The transaction object (tx) provides execute() and execute_query_async() methods
        that use the same connection, ensuring transactional consistency.
        """
        if not self._connected:
            await self.connect()

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Yield a transaction-aware wrapper
                tx = TransactionContext(conn)
                yield tx


class TransactionContext:
    """
    Transaction-aware database context.

    Provides execute() and execute_query_async() methods that operate
    on a single connection within a transaction.
    """

    def __init__(self, conn):
        """Initialize with a connection object."""
        self.conn = conn

    async def execute(
        self,
        query: str,
        *params,
        fetch_mode: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Execute query within transaction.

        Args:
            query: SQL query with $1, $2, ... placeholders
            *params: Query parameters
            fetch_mode: "all" (default), "one", or "none"

        Returns:
            List of dicts with column names as keys
        """
        if fetch_mode == "none":
            await self.conn.execute(query, *params)
            return []

        elif fetch_mode == "one":
            row = await self.conn.fetchrow(query, *params)
            if row:
                return [dict(row)]
            return []

        else:  # "all"
            rows = await self.conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def execute_query_async(
        self,
        query: str,
        params: Tuple = (),
        fetch_mode: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Execute query (Agent Factory compatible interface).

        Args:
            query: SQL query with $1, $2, ... placeholders
            params: Tuple of query parameters
            fetch_mode: "all", "one", or "none"

        Returns:
            List of dicts with column names as keys
        """
        return await self.execute(query, *params, fetch_mode=fetch_mode)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Convenience function for one-off queries
async def query(sql: str, *params) -> List[Dict[str, Any]]:
    """
    Execute one-off query without managing connection pool.

    Args:
        sql: SQL query
        *params: Query parameters

    Returns:
        List of dicts

    Example:
        equipment = await query("SELECT * FROM cmms_equipment WHERE id = $1", equipment_id)
    """
    async with AtlasDatabase() as db:
        return await db.execute(sql, *params)
