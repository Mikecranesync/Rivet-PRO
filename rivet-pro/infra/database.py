"""
Database Infrastructure

PostgreSQL connection management using asyncpg.
"""

import asyncpg
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def test_connection(database_url: str) -> bool:
    """
    Test PostgreSQL database connection.

    Args:
        database_url: PostgreSQL connection string

    Returns:
        True if connection successful, False otherwise

    Example:
        >>> success = await test_connection("postgresql://user:pass@localhost/db")
        >>> if success:
        ...     print("Database is accessible")
    """
    try:
        logger.info("Testing database connection...")
        conn = await asyncpg.connect(database_url)

        # Run simple query to verify connection
        result = await conn.fetchval("SELECT 1")

        if result == 1:
            logger.info("✓ Database connection successful")
            await conn.close()
            return True
        else:
            logger.error("✗ Database returned unexpected result")
            await conn.close()
            return False

    except asyncpg.PostgresError as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error during database connection: {e}")
        return False


async def create_connection_pool(
    database_url: str,
    min_size: int = 10,
    max_size: int = 20
) -> Optional[asyncpg.Pool]:
    """
    Create asyncpg connection pool.

    Args:
        database_url: PostgreSQL connection string
        min_size: Minimum number of connections in pool
        max_size: Maximum number of connections in pool

    Returns:
        Connection pool or None if failed

    Example:
        >>> pool = await create_connection_pool("postgresql://...")
        >>> async with pool.acquire() as conn:
        ...     result = await conn.fetch("SELECT * FROM users")
    """
    try:
        logger.info(f"Creating connection pool (min={min_size}, max={max_size})...")
        pool = await asyncpg.create_pool(
            database_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60
        )
        logger.info("✓ Connection pool created successfully")
        return pool

    except Exception as e:
        logger.error(f"✗ Failed to create connection pool: {e}")
        return None


async def close_connection_pool(pool: asyncpg.Pool) -> None:
    """
    Close database connection pool gracefully.

    Args:
        pool: Connection pool to close
    """
    try:
        logger.info("Closing database connection pool...")
        await pool.close()
        logger.info("✓ Connection pool closed")
    except Exception as e:
        logger.error(f"✗ Error closing connection pool: {e}")
