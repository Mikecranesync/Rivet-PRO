"""
Query Pattern Analyzer - AUTO-KB-011

Analyze user query patterns to prioritize enrichment intelligently.
Tracks manufacturer/model popularity and adjusts enrichment priorities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import asyncpg

logger = logging.getLogger(__name__)


class QueryPatternAnalyzer:
    """
    Service for analyzing user query patterns and adjusting enrichment priorities.

    Features:
    - Track manufacturer popularity
    - Track model family popularity
    - Identify peak query times
    - Generate priority scores based on patterns
    - Auto-adjust enrichment queue priorities daily
    """

    # Priority boost factors
    BOOST_HIGH_QUERY_COUNT = 2.0  # Multiply base priority
    BOOST_RECENT_QUERIES = 1.5   # Queries in last 24h
    BOOST_INCOMPLETE_FAMILY = 1.3  # Family has gaps

    # Priority reduction factors
    REDUCE_COMPLETED_FAMILY = 0.3  # Lower priority if complete
    REDUCE_OLD_NO_QUERIES = 0.5   # No queries in 30 days

    # Thresholds
    HIGH_QUERY_THRESHOLD = 10  # Queries to be considered "high"
    RECENT_WINDOW_HOURS = 24
    STALE_DAYS = 30

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize query pattern analyzer.

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool

    async def track_query(
        self,
        manufacturer: str,
        model: Optional[str] = None,
        product_family: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """
        Track a user query for pattern analysis.

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model (optional)
            product_family: Product family (optional)
            user_id: User identifier (optional, for unique user tracking)
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO query_patterns (
                        manufacturer,
                        model,
                        product_family,
                        user_id,
                        queried_at
                    ) VALUES ($1, $2, $3, $4, NOW())
                    """,
                    manufacturer,
                    model,
                    product_family,
                    user_id
                )
                logger.debug(
                    f"Tracked query | manufacturer={manufacturer} | "
                    f"model={model} | family={product_family}"
                )
        except Exception as e:
            logger.error(f"Failed to track query: {e}")

    async def get_manufacturer_popularity(
        self,
        days: int = 30,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get manufacturer popularity rankings.

        Args:
            days: Look back period in days
            limit: Max manufacturers to return

        Returns:
            List of dicts with manufacturer, query_count, unique_users
        """
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        manufacturer,
                        COUNT(*) as query_count,
                        COUNT(DISTINCT user_id) as unique_users,
                        MAX(queried_at) as last_query,
                        COUNT(*) FILTER (
                            WHERE queried_at > NOW() - INTERVAL '24 hours'
                        ) as recent_queries
                    FROM query_patterns
                    WHERE queried_at > NOW() - ($1 || ' days')::INTERVAL
                    GROUP BY manufacturer
                    ORDER BY query_count DESC
                    LIMIT $2
                    """,
                    str(days),
                    limit
                )

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get manufacturer popularity: {e}")
            return []

    async def get_model_family_popularity(
        self,
        manufacturer: Optional[str] = None,
        days: int = 30,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get model/family popularity rankings.

        Args:
            manufacturer: Filter by manufacturer (optional)
            days: Look back period in days
            limit: Max families to return

        Returns:
            List of dicts with manufacturer, product_family, query_count
        """
        try:
            async with self.db_pool.acquire() as conn:
                if manufacturer:
                    rows = await conn.fetch(
                        """
                        SELECT
                            manufacturer,
                            COALESCE(product_family, model) as family,
                            COUNT(*) as query_count,
                            COUNT(DISTINCT user_id) as unique_users
                        FROM query_patterns
                        WHERE queried_at > NOW() - ($1 || ' days')::INTERVAL
                          AND LOWER(manufacturer) = LOWER($2)
                        GROUP BY manufacturer, COALESCE(product_family, model)
                        ORDER BY query_count DESC
                        LIMIT $3
                        """,
                        str(days),
                        manufacturer,
                        limit
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT
                            manufacturer,
                            COALESCE(product_family, model) as family,
                            COUNT(*) as query_count,
                            COUNT(DISTINCT user_id) as unique_users
                        FROM query_patterns
                        WHERE queried_at > NOW() - ($1 || ' days')::INTERVAL
                        GROUP BY manufacturer, COALESCE(product_family, model)
                        ORDER BY query_count DESC
                        LIMIT $2
                        """,
                        str(days),
                        limit
                    )

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get model family popularity: {e}")
            return []

    async def get_peak_query_times(self, days: int = 7) -> Dict[str, Any]:
        """
        Identify peak query times.

        Args:
            days: Look back period

        Returns:
            Dict with hourly and daily patterns
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Hourly pattern
                hourly = await conn.fetch(
                    """
                    SELECT
                        EXTRACT(HOUR FROM queried_at) as hour,
                        COUNT(*) as query_count
                    FROM query_patterns
                    WHERE queried_at > NOW() - ($1 || ' days')::INTERVAL
                    GROUP BY EXTRACT(HOUR FROM queried_at)
                    ORDER BY query_count DESC
                    """,
                    str(days)
                )

                # Daily pattern
                daily = await conn.fetch(
                    """
                    SELECT
                        EXTRACT(DOW FROM queried_at) as day_of_week,
                        COUNT(*) as query_count
                    FROM query_patterns
                    WHERE queried_at > NOW() - ($1 || ' days')::INTERVAL
                    GROUP BY EXTRACT(DOW FROM queried_at)
                    ORDER BY query_count DESC
                    """,
                    str(days)
                )

                return {
                    'peak_hours': [dict(row) for row in hourly[:5]],
                    'peak_days': [dict(row) for row in daily],
                    'analysis_period_days': days
                }

        except Exception as e:
            logger.error(f"Failed to get peak query times: {e}")
            return {}

    async def calculate_priority_score(
        self,
        manufacturer: str,
        model_pattern: Optional[str] = None
    ) -> int:
        """
        Calculate enrichment priority score based on query patterns.

        Args:
            manufacturer: Equipment manufacturer
            model_pattern: Model or family pattern (optional)

        Returns:
            Priority score (1-10, higher = more urgent)
        """
        base_priority = 5

        try:
            async with self.db_pool.acquire() as conn:
                # Get query stats for this manufacturer/model
                row = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_queries,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(*) FILTER (
                            WHERE queried_at > NOW() - INTERVAL '24 hours'
                        ) as recent_queries,
                        MAX(queried_at) as last_query
                    FROM query_patterns
                    WHERE LOWER(manufacturer) = LOWER($1)
                      AND (
                        $2 IS NULL
                        OR LOWER(model) = LOWER($2)
                        OR LOWER(product_family) = LOWER($2)
                      )
                    """,
                    manufacturer,
                    model_pattern
                )

                if not row:
                    return base_priority

                total_queries = row['total_queries'] or 0
                recent_queries = row['recent_queries'] or 0
                last_query = row['last_query']

                priority = base_priority

                # Boost for high query count
                if total_queries >= self.HIGH_QUERY_THRESHOLD:
                    priority = priority * self.BOOST_HIGH_QUERY_COUNT

                # Boost for recent queries
                if recent_queries > 0:
                    priority = priority * self.BOOST_RECENT_QUERIES

                # Check if family is incomplete (has gaps)
                incomplete_check = await conn.fetchval(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM enrichment_queue
                        WHERE LOWER(manufacturer) = LOWER($1)
                          AND status IN ('pending', 'failed')
                    )
                    """,
                    manufacturer
                )
                if incomplete_check:
                    priority = priority * self.BOOST_INCOMPLETE_FAMILY

                # Reduce for stale entries (no recent queries)
                if last_query:
                    days_since_query = (datetime.now() - last_query.replace(tzinfo=None)).days
                    if days_since_query > self.STALE_DAYS:
                        priority = priority * self.REDUCE_OLD_NO_QUERIES

                # Clamp to 1-10 range
                priority = max(1, min(10, int(priority)))

                logger.debug(
                    f"Priority score calculated | manufacturer={manufacturer} | "
                    f"model={model_pattern} | score={priority} | "
                    f"total_queries={total_queries} | recent={recent_queries}"
                )

                return priority

        except Exception as e:
            logger.error(f"Failed to calculate priority score: {e}")
            return base_priority

    async def update_enrichment_priorities(self) -> Dict[str, int]:
        """
        Update all enrichment queue priorities based on current patterns.
        Should be run daily.

        Returns:
            Dict with updated and unchanged counts
        """
        updated = 0
        unchanged = 0

        try:
            async with self.db_pool.acquire() as conn:
                # Get all pending enrichment jobs
                jobs = await conn.fetch(
                    """
                    SELECT id, manufacturer, model_pattern, priority
                    FROM enrichment_queue
                    WHERE status IN ('pending', 'processing')
                    """
                )

                for job in jobs:
                    new_priority = await self.calculate_priority_score(
                        job['manufacturer'],
                        job['model_pattern']
                    )

                    if new_priority != job['priority']:
                        await conn.execute(
                            """
                            UPDATE enrichment_queue
                            SET priority = $1,
                                updated_at = NOW()
                            WHERE id = $2
                            """,
                            new_priority,
                            job['id']
                        )
                        updated += 1
                        logger.info(
                            f"Updated priority | job={job['id']} | "
                            f"{job['priority']} -> {new_priority}"
                        )
                    else:
                        unchanged += 1

            logger.info(
                f"Priority update complete | updated={updated} | unchanged={unchanged}"
            )
            return {'updated': updated, 'unchanged': unchanged}

        except Exception as e:
            logger.error(f"Failed to update enrichment priorities: {e}")
            return {'updated': 0, 'unchanged': 0, 'error': str(e)}

    async def get_pattern_stats(self) -> Dict[str, Any]:
        """
        Get overall query pattern statistics.

        Returns:
            Dict with pattern analysis stats
        """
        try:
            async with self.db_pool.acquire() as conn:
                stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_queries,
                        COUNT(DISTINCT manufacturer) as unique_manufacturers,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(*) FILTER (
                            WHERE queried_at > NOW() - INTERVAL '24 hours'
                        ) as queries_24h,
                        COUNT(*) FILTER (
                            WHERE queried_at > NOW() - INTERVAL '7 days'
                        ) as queries_7d
                    FROM query_patterns
                    """
                )

                top_mfrs = await self.get_manufacturer_popularity(days=30, limit=5)

                result = dict(stats) if stats else {}
                result['top_manufacturers'] = top_mfrs
                return result

        except Exception as e:
            logger.error(f"Failed to get pattern stats: {e}")
            return {}


async def daily_priority_update(db_pool: asyncpg.Pool) -> Dict[str, int]:
    """
    Standalone function to run daily priority updates.
    Can be called from a scheduler or cron job.

    Args:
        db_pool: Database connection pool

    Returns:
        Dict with update results
    """
    analyzer = QueryPatternAnalyzer(db_pool)
    return await analyzer.update_enrichment_priorities()
