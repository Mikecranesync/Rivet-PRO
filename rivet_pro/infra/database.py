"""
Database connection management for Rivet Pro.
Uses asyncpg for async PostgreSQL connections to Neon.

Includes failover logic: Neon -> Supabase -> CockroachDB (emergency)
"""

import os
import asyncio
import asyncpg
from typing import Optional, List, Tuple, Callable, TypeVar, Any
from contextlib import asynccontextmanager
from pathlib import Path
from rivet_pro.config.settings import settings
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

# Type variable for retry helper return type
T = TypeVar('T')

# Transient connection errors that should be retried
RETRYABLE_ERRORS = (
    asyncpg.ConnectionDoesNotExistError,
    asyncpg.InterfaceError,
    asyncpg.TooManyConnectionsError,
    asyncpg.CannotConnectNowError,
    OSError,
)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [0.1, 0.5, 0.5]  # 100ms, 500ms, 500ms (capped)


def get_database_providers() -> List[Tuple[str, str]]:
    """
    Get list of database providers in failover order.

    Returns:
        List of (provider_name, connection_url) tuples

    Failover order:
        1. Neon (primary) - serverless PostgreSQL
        2. Supabase (failover) - true PostgreSQL, 500MB free
        3. CockroachDB (emergency) - PostgreSQL wire compatible, 5GB free
    """
    providers = []

    # Primary: Neon
    if settings.database_url:
        providers.append(("neon", settings.database_url))

    # Failover 1: Supabase (true PostgreSQL)
    supabase_url = os.getenv("SUPABASE_DB_URL")
    if supabase_url:
        providers.append(("supabase", supabase_url))

    # Failover 2: CockroachDB (emergency - PostgreSQL wire compatible)
    cockroach_url = os.getenv("COCKROACH_DB_URL")
    if cockroach_url and "your_user" not in cockroach_url and "your_password" not in cockroach_url:
        providers.append(("cockroachdb", cockroach_url))

    return providers


class Database:
    """
    PostgreSQL database connection manager.
    Manages connection pool and provides async context manager.
    """

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.active_provider: Optional[str] = None

    async def connect(self) -> None:
        """
        Create database connection pool with automatic failover.

        Tries providers in order: Neon -> Supabase -> CockroachDB
        Alerts via Telegram on failover.
        """
        if self.pool is not None:
            logger.warning("Database pool already exists")
            return

        providers = get_database_providers()
        if not providers:
            raise RuntimeError("No database providers configured")

        errors = []
        for provider_name, dsn in providers:
            try:
                logger.info(f"Attempting database connection | Provider: {provider_name}")

                self.pool = await asyncpg.create_pool(
                    dsn=dsn,
                    min_size=settings.database_pool_min_size,
                    max_size=settings.database_pool_max_size,
                    command_timeout=60,
                )

                # Test connection
                async with self.pool.acquire() as conn:
                    version = await conn.fetchval("SELECT version()")
                    logger.info(
                        f"Database connected successfully | "
                        f"Provider: {provider_name} | "
                        f"PostgreSQL: {version[:50]}..."
                    )

                self.active_provider = provider_name

                # Alert on failover (not primary)
                if provider_name != "neon":
                    await self._send_failover_alert(provider_name, errors)

                return  # Success!

            except Exception as e:
                logger.warning(f"Connection failed | Provider: {provider_name} | Error: {e}")
                errors.append((provider_name, str(e)))
                self.pool = None
                continue

        # All providers failed
        error_summary = "; ".join([f"{p}: {e}" for p, e in errors])
        raise RuntimeError(f"All database providers failed: {error_summary}")

    async def _send_failover_alert(self, active_provider: str, errors: List[Tuple[str, str]]) -> None:
        """Send Telegram alert when failing over to backup database."""
        try:
            import httpx
            bot_token = settings.telegram_bot_token
            chat_id = settings.telegram_admin_chat_id  # From config

            error_details = "\n".join([f"  - {p}: {e[:50]}" for p, e in errors])
            message = (
                f"⚠️ DATABASE FAILOVER\n\n"
                f"Active: {active_provider.upper()}\n"
                f"Failed providers:\n{error_details}\n\n"
                f"Check Neon status: https://console.neon.tech"
            )

            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": message},
                    timeout=5.0
                )
            logger.info(f"Failover alert sent | Active: {active_provider}")
        except Exception as e:
            logger.warning(f"Failed to send failover alert: {e}")

    async def disconnect(self) -> None:
        """
        Close database connection pool.
        Should be called on application shutdown.
        """
        if self.pool is None:
            logger.warning("Database pool does not exist")
            return

        try:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing database pool: {e}")
            raise

    @asynccontextmanager
    async def acquire(self):
        """
        Async context manager for acquiring a database connection.

        Usage:
            async with db.acquire() as conn:
                result = await conn.fetch("SELECT * FROM users")
        """
        if self.pool is None:
            raise RuntimeError("Database pool not initialized. Call connect() first.")

        async with self.pool.acquire() as connection:
            yield connection

    async def _execute_with_retry(
        self,
        operation: Callable[..., Any],
        query: str,
        *args
    ) -> T:
        """
        Execute a database operation with retry logic for transient errors.

        Retries on connection errors with exponential backoff:
        - Attempt 1: immediate
        - Attempt 2: after 100ms
        - Attempt 3: after 500ms
        - Attempt 4: after 500ms (capped)

        Does NOT retry on query errors (syntax errors, unique violations, etc.)

        Args:
            operation: The async method to call (e.g., conn.fetch)
            query: SQL query string
            *args: Query parameters

        Returns:
            Result from the database operation

        Raises:
            The last exception if all retries fail
        """
        last_exception = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                async with self.acquire() as conn:
                    method = getattr(conn, operation)
                    return await method(query, *args)

            except RETRYABLE_ERRORS as e:
                last_exception = e

                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(
                        f"Database connection error (attempt {attempt + 1}/{MAX_RETRIES + 1}), "
                        f"retrying in {delay}s | Error: {type(e).__name__}: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Database connection failed after {MAX_RETRIES + 1} attempts | "
                        f"Error: {type(e).__name__}: {e}"
                    )
                    raise

            except Exception:
                # Non-retryable errors (query errors, etc.) - raise immediately
                raise

        # Should not reach here, but just in case
        raise last_exception

    async def execute(self, query: str, *args) -> str:
        """
        Execute a query without returning results.

        Includes automatic retry with exponential backoff for transient errors.

        Args:
            query: SQL query string
            *args: Query parameters

        Returns:
            Status string from database
        """
        return await self._execute_with_retry("execute", query, *args)

    async def fetch(self, query: str, *args) -> list:
        """
        Execute a query and return all results.

        Includes automatic retry with exponential backoff for transient errors.

        Args:
            query: SQL query string
            *args: Query parameters

        Returns:
            List of records
        """
        return await self._execute_with_retry("fetch", query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Execute a query and return a single row.

        Includes automatic retry with exponential backoff for transient errors.

        Args:
            query: SQL query string
            *args: Query parameters

        Returns:
            Single record or None
        """
        return await self._execute_with_retry("fetchrow", query, *args)

    async def fetchval(self, query: str, *args):
        """
        Execute a query and return a single value.

        Includes automatic retry with exponential backoff for transient errors.

        Args:
            query: SQL query string
            *args: Query parameters

        Returns:
            Single value
        """
        return await self._execute_with_retry("fetchval", query, *args)

    async def execute_query_async(self, query: str, params: tuple = (), fetch_mode: str = "all"):
        """
        Unified query execution matching equipment service expectations.

        Wrapper method that adapts the existing fetch/fetchrow/execute API
        to match the interface expected by EquipmentService.

        Args:
            query: SQL query string
            params: Query parameters as tuple
            fetch_mode: "all" (return list), "one" (return single record), or "none" (no return)

        Returns:
            List of dict records for "all", list with single dict for "one", None for "none"

        Example:
            # Fetch all results
            results = await db.execute_query_async("SELECT * FROM users WHERE status = $1", ("active",))

            # Fetch single result
            result = await db.execute_query_async("SELECT * FROM users WHERE id = $1", (user_id,), fetch_mode="one")

            # Execute without returning
            await db.execute_query_async("DELETE FROM users WHERE id = $1", (user_id,), fetch_mode="none")
        """
        if fetch_mode == "none":
            await self.execute(query, *params)
            return None
        elif fetch_mode == "one":
            result = await self.fetchrow(query, *params)
            return [dict(result)] if result else None
        else:  # "all"
            results = await self.fetch(query, *params)
            return [dict(row) for row in results]

    async def health_check(self) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            True if database is accessible, False otherwise
        """
        try:
            async with self.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def run_migrations(self, migrations_dir: str = None) -> None:
        """
        Run all pending database migrations.

        Args:
            migrations_dir: Path to migrations directory (default: rivet_pro/migrations)
        """
        if migrations_dir is None:
            migrations_dir = Path(__file__).parent.parent / "migrations"
        else:
            migrations_dir = Path(migrations_dir)

        logger.info(f"Running migrations from: {migrations_dir}")

        # Create migrations tracking table if it doesn't exist
        await self._create_migrations_table()

        # Get list of applied migrations
        applied_migrations = await self._get_applied_migrations()

        # Get all migration files
        migration_files = sorted(migrations_dir.glob("*.sql"))

        if not migration_files:
            logger.warning(f"No migration files found in {migrations_dir}")
            return

        # Run pending migrations
        for migration_file in migration_files:
            migration_name = migration_file.name

            if migration_name in applied_migrations:
                logger.info(f"[SKIP] {migration_name} (already applied)")
                continue

            logger.info(f"[RUN] {migration_name}")

            try:
                # Read migration file
                with open(migration_file, "r") as f:
                    migration_sql = f.read()

                # Execute migration
                async with self.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(migration_sql)

                        # Record migration
                        await conn.execute(
                            """
                            INSERT INTO schema_migrations (migration_name)
                            VALUES ($1)
                            """,
                            migration_name
                        )

                logger.info(f"[DONE] {migration_name}")

            except Exception as e:
                logger.error(f"[FAILED] {migration_name}: {e}")
                raise

        logger.info("All migrations complete")

    async def _create_migrations_table(self) -> None:
        """
        Create the schema_migrations table if it doesn't exist.
        """
        async with self.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )

    async def _get_applied_migrations(self) -> set:
        """
        Get the set of applied migration names.

        Returns:
            Set of migration names that have been applied
        """
        async with self.acquire() as conn:
            rows = await conn.fetch(
                "SELECT migration_name FROM schema_migrations ORDER BY id"
            )
            return {row["migration_name"] for row in rows}

    async def rollback_migration(self, migration_name: str) -> None:
        """
        Mark a migration as rolled back (does NOT execute rollback SQL).

        Args:
            migration_name: Name of the migration to rollback
        """
        logger.warning(f"Marking migration as rolled back: {migration_name}")

        async with self.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM schema_migrations WHERE migration_name = $1",
                migration_name
            )

        logger.info(f"Rolled back migration: {migration_name} | Result: {result}")


# Singleton database instance (primary - neondb)
db = Database()


class AtlasCMMSDatabase(Database):
    """
    Dedicated database connection for Atlas CMMS (atlas_cmms database).
    Used for dual-write sync to make equipment visible in Atlas CMMS web UI.
    """

    async def connect(self) -> None:
        """
        Create database connection pool for Atlas CMMS.
        Uses ATLAS_DATABASE_URL environment variable.
        """
        if self.pool is not None:
            logger.warning("Atlas CMMS database pool already exists")
            return

        atlas_url = os.getenv("ATLAS_DATABASE_URL")
        if not atlas_url:
            logger.warning("ATLAS_DATABASE_URL not configured - Atlas sync disabled")
            return

        try:
            logger.info("Attempting Atlas CMMS database connection")

            self.pool = await asyncpg.create_pool(
                dsn=atlas_url,
                min_size=1,
                max_size=3,  # Smaller pool - only for sync writes
                command_timeout=30,
            )

            # Test connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(
                    f"Atlas CMMS database connected | "
                    f"PostgreSQL: {version[:50]}..."
                )

            self.active_provider = "atlas_cmms"

        except Exception as e:
            logger.warning(f"Atlas CMMS connection failed (non-blocking): {e}")
            self.pool = None


# Singleton database instance for Atlas CMMS (dual-write target)
atlas_db = AtlasCMMSDatabase()
