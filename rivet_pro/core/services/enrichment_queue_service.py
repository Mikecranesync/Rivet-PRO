"""
Enrichment Queue Service - AUTO-KB-001

Manages the enrichment work queue for autonomous knowledge base enrichment.
Provides methods to add jobs, get next job, and update job status.
"""

import asyncpg
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID

logger = logging.getLogger(__name__)


class EnrichmentQueueService:
    """Service for managing autonomous enrichment work queue"""

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize service with database pool

        Args:
            db_pool: asyncpg connection pool
        """
        self.db_pool = db_pool

    async def add_to_queue(
        self,
        manufacturer: str,
        model_pattern: str,
        priority: int = 5,
        user_query_count: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[UUID]:
        """
        Add a new enrichment job to the queue

        Args:
            manufacturer: Equipment manufacturer
            model_pattern: Model pattern to search (e.g., "S7-*", "2080*")
            priority: Job priority (1-10, higher = more urgent)
            user_query_count: Number of user queries that triggered this
            metadata: Additional job metadata

        Returns:
            UUID of created job, or None if job already exists
        """
        try:
            # Check if similar job already exists and is pending/processing
            async with self.db_pool.acquire() as conn:
                existing = await conn.fetchrow(
                    """
                    SELECT id, user_query_count, priority
                    FROM enrichment_queue
                    WHERE manufacturer = $1
                      AND model_pattern = $2
                      AND status IN ('pending', 'processing')
                    """,
                    manufacturer,
                    model_pattern
                )

                if existing:
                    # Job exists - increment user_query_count and boost priority
                    new_query_count = existing['user_query_count'] + user_query_count
                    new_priority = min(10, existing['priority'] + 1)  # Cap at 10

                    await conn.execute(
                        """
                        UPDATE enrichment_queue
                        SET user_query_count = $1,
                            priority = $2
                        WHERE id = $3
                        """,
                        new_query_count,
                        new_priority,
                        existing['id']
                    )

                    logger.info(
                        f"Enrichment job already exists for {manufacturer} {model_pattern}. "
                        f"Updated: query_count={new_query_count}, priority={new_priority}"
                    )
                    return existing['id']

                # Create new job
                job_id = await conn.fetchval(
                    """
                    INSERT INTO enrichment_queue (
                        manufacturer,
                        model_pattern,
                        priority,
                        user_query_count,
                        status,
                        metadata
                    ) VALUES ($1, $2, $3, $4, 'pending', $5)
                    RETURNING id
                    """,
                    manufacturer,
                    model_pattern,
                    priority,
                    user_query_count,
                    metadata or {}
                )

                logger.info(
                    f"Added enrichment job to queue: {manufacturer} {model_pattern} "
                    f"(priority={priority}, id={job_id})"
                )
                return job_id

        except Exception as e:
            logger.error(f"Failed to add enrichment job: {e}", exc_info=True)
            return None

    async def get_next_job(self) -> Optional[Dict[str, Any]]:
        """
        Get the next pending job from the queue (highest priority first)

        Returns:
            Job dict with id, manufacturer, model_pattern, priority, etc.
            or None if queue is empty
        """
        try:
            async with self.db_pool.acquire() as conn:
                job = await conn.fetchrow(
                    """
                    SELECT
                        id,
                        manufacturer,
                        model_pattern,
                        priority,
                        user_query_count,
                        metadata,
                        created_at
                    FROM enrichment_queue
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    """,
                )

                return dict(job) if job else None

        except Exception as e:
            logger.error(f"Failed to get next job from queue: {e}", exc_info=True)
            return None

    async def update_job_status(
        self,
        job_id: UUID,
        status: str,
        worker_id: Optional[str] = None,
        family_size: Optional[int] = None,
        manuals_indexed: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update job status and metadata

        Args:
            job_id: Job UUID
            status: New status (pending, processing, completed, failed)
            worker_id: Worker processing this job
            family_size: Number of models in family
            manuals_indexed: Number of manuals indexed
            error_message: Error message if failed
            metadata: Updated metadata

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            async with self.db_pool.acquire() as conn:
                updates = []
                values = []
                param_idx = 1

                # Build dynamic UPDATE query
                updates.append(f"status = ${param_idx}")
                values.append(status)
                param_idx += 1

                if status == 'processing' and worker_id:
                    updates.append(f"started_at = NOW()")
                    updates.append(f"worker_id = ${param_idx}")
                    values.append(worker_id)
                    param_idx += 1

                if status in ('completed', 'failed'):
                    updates.append(f"completed_at = NOW()")

                if family_size is not None:
                    updates.append(f"family_size = ${param_idx}")
                    values.append(family_size)
                    param_idx += 1

                if manuals_indexed is not None:
                    updates.append(f"manuals_indexed = ${param_idx}")
                    values.append(manuals_indexed)
                    param_idx += 1

                if error_message:
                    updates.append(f"error_message = ${param_idx}")
                    values.append(error_message)
                    param_idx += 1

                if metadata:
                    updates.append(f"metadata = ${param_idx}")
                    values.append(metadata)
                    param_idx += 1

                # Add job_id as final parameter
                values.append(job_id)

                query = f"""
                    UPDATE enrichment_queue
                    SET {', '.join(updates)}
                    WHERE id = ${param_idx}
                """

                await conn.execute(query, *values)

                logger.info(f"Updated job {job_id} status to {status}")
                return True

        except Exception as e:
            logger.error(f"Failed to update job status: {e}", exc_info=True)
            return False

    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics for monitoring

        Returns:
            Dict with queue depth, average priority, oldest job age, etc.
        """
        try:
            async with self.db_pool.acquire() as conn:
                stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                        COUNT(*) FILTER (WHERE status = 'processing') as processing_count,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
                        COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
                        AVG(priority) FILTER (WHERE status = 'pending') as avg_priority,
                        MIN(created_at) FILTER (WHERE status = 'pending') as oldest_pending,
                        SUM(manuals_indexed) as total_manuals_indexed,
                        SUM(family_size) as total_family_members
                    FROM enrichment_queue
                    """
                )

                result = dict(stats)

                # Calculate age of oldest pending job
                if result['oldest_pending']:
                    age = datetime.now(result['oldest_pending'].tzinfo) - result['oldest_pending']
                    result['oldest_pending_age_minutes'] = int(age.total_seconds() / 60)
                else:
                    result['oldest_pending_age_minutes'] = 0

                return result

        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}", exc_info=True)
            return {}

    async def get_pending_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get list of pending jobs (for dashboard/monitoring)

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of job dicts
        """
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        id,
                        manufacturer,
                        model_pattern,
                        priority,
                        user_query_count,
                        created_at,
                        metadata
                    FROM enrichment_queue
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT $1
                    """,
                    limit
                )

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get pending jobs: {e}", exc_info=True)
            return []

    async def cleanup_old_jobs(self, days_old: int = 30) -> int:
        """
        Remove completed/failed jobs older than specified days

        Args:
            days_old: Remove jobs completed/failed more than this many days ago

        Returns:
            Number of jobs removed
        """
        try:
            async with self.db_pool.acquire() as conn:
                cutoff = datetime.now() - timedelta(days=days_old)

                result = await conn.execute(
                    """
                    DELETE FROM enrichment_queue
                    WHERE status IN ('completed', 'failed')
                      AND completed_at < $1
                    """,
                    cutoff
                )

                # Parse "DELETE N" result
                count = int(result.split()[-1])
                logger.info(f"Cleaned up {count} old enrichment jobs")
                return count

        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}", exc_info=True)
            return 0

    async def worker_status(self) -> Dict[str, Any]:
        """
        Get worker health status for monitoring

        Returns:
            Dict with is_running, last_heartbeat, jobs_processed_today, etc.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get latest heartbeat
                heartbeat = await conn.fetchrow(
                    """
                    SELECT
                        worker_id,
                        timestamp,
                        metrics
                    FROM enrichment_stats
                    WHERE stat_type = 'worker_heartbeat'
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """
                )

                # Get jobs processed today
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                jobs_today = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM enrichment_queue
                    WHERE status = 'completed'
                      AND completed_at >= $1
                    """,
                    today_start
                )

                # Get current processing job
                current_job = await conn.fetchrow(
                    """
                    SELECT
                        id,
                        manufacturer,
                        model_pattern,
                        started_at
                    FROM enrichment_queue
                    WHERE status = 'processing'
                    ORDER BY started_at DESC
                    LIMIT 1
                    """
                )

                # Get queue depth
                queue_depth = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM enrichment_queue
                    WHERE status = 'pending'
                    """
                )

                result = {
                    'is_running': False,
                    'last_heartbeat': None,
                    'jobs_processed_today': jobs_today or 0,
                    'current_job': None,
                    'queue_depth': queue_depth or 0
                }

                if heartbeat:
                    last_heartbeat_time = heartbeat['timestamp']
                    age = datetime.now(last_heartbeat_time.tzinfo) - last_heartbeat_time
                    result['is_running'] = age.total_seconds() < 600  # < 10 minutes = running
                    result['last_heartbeat'] = last_heartbeat_time.isoformat()
                    result['worker_id'] = heartbeat['worker_id']

                if current_job:
                    result['current_job'] = {
                        'id': str(current_job['id']),
                        'manufacturer': current_job['manufacturer'],
                        'model_pattern': current_job['model_pattern'],
                        'started_at': current_job['started_at'].isoformat()
                    }

                return result

        except Exception as e:
            logger.error(f"Failed to get worker status: {e}", exc_info=True)
            return {
                'is_running': False,
                'error': str(e)
            }
