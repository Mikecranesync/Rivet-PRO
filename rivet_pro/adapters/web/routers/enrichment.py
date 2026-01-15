"""
Enrichment Dashboard API - AUTO-KB-013

Admin endpoints for monitoring and managing the autonomous KB enrichment system.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from rivet_pro.infra.database import db
from rivet_pro.adapters.web.dependencies import get_current_user, admin_required
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/dashboard")
async def get_enrichment_dashboard(
    current_user: dict = Depends(admin_required)
):
    """
    Get enrichment dashboard overview.

    Returns:
    - Current queue depth by priority
    - Top families being enriched
    - Enrichment worker status
    - Recent completions and failures
    """
    try:
        # Queue depth by priority
        queue_by_priority = await db.fetch(
            """
            SELECT
                priority,
                status,
                COUNT(*) as count
            FROM enrichment_queue
            GROUP BY priority, status
            ORDER BY priority DESC, status
            """
        )

        # Top families being enriched (currently processing)
        top_families = await db.fetch(
            """
            SELECT
                manufacturer,
                model_pattern,
                priority,
                user_query_count,
                status,
                created_at
            FROM enrichment_queue
            WHERE status IN ('pending', 'processing')
            ORDER BY priority DESC, user_query_count DESC
            LIMIT 10
            """
        )

        # Worker status (last heartbeat)
        worker_status = await db.fetch(
            """
            SELECT
                worker_id,
                timestamp,
                metrics
            FROM enrichment_stats
            WHERE stat_type = 'worker_heartbeat'
            ORDER BY timestamp DESC
            LIMIT 5
            """
        )

        # Recent completions
        recent_completed = await db.fetch(
            """
            SELECT
                manufacturer,
                model_pattern,
                completed_at,
                family_size,
                manuals_indexed
            FROM enrichment_queue
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 10
            """
        )

        # Recent failures
        recent_failures = await db.fetch(
            """
            SELECT
                manufacturer,
                model_pattern,
                updated_at as failed_at,
                error_message
            FROM enrichment_queue
            WHERE status = 'failed'
            ORDER BY updated_at DESC
            LIMIT 5
            """
        )

        # Summary stats
        summary = await db.fetchrow(
            """
            SELECT
                COUNT(*) as total_jobs,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'processing') as processing,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) FILTER (
                    WHERE status = 'completed'
                ) as avg_completion_seconds
            FROM enrichment_queue
            """
        )

        return {
            'summary': dict(summary) if summary else {},
            'queue_by_priority': [dict(r) for r in queue_by_priority],
            'top_families': [dict(r) for r in top_families],
            'worker_status': [dict(r) for r in worker_status],
            'recent_completed': [dict(r) for r in recent_completed],
            'recent_failures': [dict(r) for r in recent_failures],
            'generated_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get enrichment dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue")
async def get_enrichment_queue(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority_min: Optional[int] = Query(None, description="Minimum priority"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(admin_required)
):
    """
    Get enrichment queue with filtering.
    """
    try:
        # Build dynamic query
        conditions = []
        params = []
        param_count = 0

        if status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status)

        if priority_min is not None:
            param_count += 1
            conditions.append(f"priority >= ${param_count}")
            params.append(priority_min)

        if manufacturer:
            param_count += 1
            conditions.append(f"LOWER(manufacturer) = LOWER(${param_count})")
            params.append(manufacturer)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Add limit and offset
        param_count += 1
        limit_param = param_count
        param_count += 1
        offset_param = param_count
        params.extend([limit, offset])

        query = f"""
            SELECT
                id,
                manufacturer,
                model_pattern,
                priority,
                user_query_count,
                status,
                worker_id,
                created_at,
                updated_at,
                completed_at,
                error_message
            FROM enrichment_queue
            WHERE {where_clause}
            ORDER BY priority DESC, created_at ASC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """

        rows = await db.fetch(query, *params)

        # Get total count
        count_query = f"""
            SELECT COUNT(*) FROM enrichment_queue
            WHERE {where_clause}
        """
        total = await db.fetchval(count_query, *params[:-2])

        return {
            'items': [dict(r) for r in rows],
            'total': total,
            'limit': limit,
            'offset': offset
        }

    except Exception as e:
        logger.error(f"Failed to get enrichment queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workers")
async def get_worker_status(
    current_user: dict = Depends(admin_required)
):
    """
    Get enrichment worker status and health.
    """
    try:
        # Get active workers (heartbeat in last 10 minutes)
        workers = await db.fetch(
            """
            SELECT DISTINCT ON (worker_id)
                worker_id,
                timestamp as last_heartbeat,
                metrics
            FROM enrichment_stats
            WHERE stat_type = 'worker_heartbeat'
              AND timestamp > NOW() - INTERVAL '10 minutes'
            ORDER BY worker_id, timestamp DESC
            """
        )

        # Get worker performance stats
        performance = await db.fetch(
            """
            SELECT
                worker_id,
                COUNT(*) as jobs_completed,
                AVG(EXTRACT(EPOCH FROM (completed_at - updated_at))) as avg_job_seconds
            FROM enrichment_queue
            WHERE status = 'completed'
              AND worker_id IS NOT NULL
              AND completed_at > NOW() - INTERVAL '24 hours'
            GROUP BY worker_id
            """
        )

        return {
            'active_workers': [dict(w) for w in workers],
            'performance_24h': [dict(p) for p in performance],
            'total_active': len(workers)
        }

    except Exception as e:
        logger.error(f"Failed to get worker status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queue/{job_id}/priority")
async def update_job_priority(
    job_id: int,
    priority: int = Query(..., ge=1, le=10, description="New priority (1-10)"),
    current_user: dict = Depends(admin_required)
):
    """
    Update priority of an enrichment job.
    """
    try:
        result = await db.execute(
            """
            UPDATE enrichment_queue
            SET priority = $1, updated_at = NOW()
            WHERE id = $2 AND status IN ('pending', 'processing')
            RETURNING id
            """,
            priority,
            job_id
        )

        if not result:
            raise HTTPException(status_code=404, detail="Job not found or already completed")

        logger.info(f"Updated job {job_id} priority to {priority} by {current_user.get('id')}")

        return {'success': True, 'job_id': job_id, 'new_priority': priority}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job priority: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queue/{job_id}/retry")
async def retry_failed_job(
    job_id: int,
    current_user: dict = Depends(admin_required)
):
    """
    Retry a failed enrichment job.
    """
    try:
        result = await db.execute(
            """
            UPDATE enrichment_queue
            SET status = 'pending',
                error_message = NULL,
                worker_id = NULL,
                updated_at = NOW()
            WHERE id = $1 AND status = 'failed'
            RETURNING id
            """,
            job_id
        )

        if not result:
            raise HTTPException(status_code=404, detail="Job not found or not in failed status")

        logger.info(f"Retrying job {job_id} requested by {current_user.get('id')}")

        return {'success': True, 'job_id': job_id, 'new_status': 'pending'}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/daily")
async def get_daily_stats(
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(admin_required)
):
    """
    Get daily enrichment statistics.
    """
    try:
        stats = await db.fetch(
            """
            SELECT
                DATE(created_at) as date,
                COUNT(*) as jobs_created,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                SUM(manuals_indexed) FILTER (WHERE status = 'completed') as manuals_indexed
            FROM enrichment_queue
            WHERE created_at > NOW() - ($1 || ' days')::INTERVAL
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            """,
            str(days)
        )

        return {
            'daily_stats': [dict(s) for s in stats],
            'period_days': days
        }

    except Exception as e:
        logger.error(f"Failed to get daily stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manuals/stats")
async def get_manual_stats(
    current_user: dict = Depends(admin_required)
):
    """
    Get statistics about downloaded manuals.
    """
    try:
        stats = await db.fetchrow(
            """
            SELECT
                COUNT(*) as total_manuals,
                COUNT(*) FILTER (WHERE text_content IS NOT NULL) as with_text,
                COUNT(*) FILTER (WHERE embedding_vector IS NOT NULL) as with_embedding,
                COUNT(*) FILTER (WHERE s3_key IS NOT NULL) as backed_up_to_s3,
                COALESCE(SUM(size_bytes), 0) as total_size_bytes,
                COUNT(DISTINCT manufacturer) as unique_manufacturers
            FROM manual_files
            """
        )

        top_manufacturers = await db.fetch(
            """
            SELECT
                manufacturer,
                COUNT(*) as manual_count,
                SUM(size_bytes) as total_size
            FROM manual_files
            GROUP BY manufacturer
            ORDER BY manual_count DESC
            LIMIT 10
            """
        )

        result = dict(stats) if stats else {}
        result['top_manufacturers'] = [dict(m) for m in top_manufacturers]

        # Human readable size
        total_bytes = result.get('total_size_bytes', 0) or 0
        if total_bytes > 1_000_000_000:
            result['total_size_human'] = f"{total_bytes / 1_000_000_000:.2f} GB"
        elif total_bytes > 1_000_000:
            result['total_size_human'] = f"{total_bytes / 1_000_000:.2f} MB"
        else:
            result['total_size_human'] = f"{total_bytes / 1000:.2f} KB"

        return result

    except Exception as e:
        logger.error(f"Failed to get manual stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
