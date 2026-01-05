"""
Statistics and dashboard router.
Provides aggregated data for CMMS dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from rivet_pro.adapters.web.dependencies import get_current_user, get_db, UserInDB
from rivet_pro.infra.database import Database
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

router = APIRouter()


class OverviewStats(BaseModel):
    """Overview statistics for dashboard."""
    equipment_count: int
    work_orders_open: int
    work_orders_in_progress: int
    work_orders_completed: int
    top_manufacturers: List[dict]
    top_faults: List[dict]


class EquipmentHealthItem(BaseModel):
    """Equipment health item."""
    id: str
    equipment_number: str
    manufacturer: str
    model_number: Optional[str]
    work_order_count: int
    last_reported_fault: Optional[str]
    health_score: float  # 0-100, calculated from work order frequency


class WorkOrderTrend(BaseModel):
    """Work order trend data point."""
    date: str
    created_count: int
    completed_count: int


@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get dashboard overview statistics.

    Includes:
    - Total equipment count
    - Work order counts by status
    - Top manufacturers
    - Top reported faults
    """
    try:
        user_id = str(current_user.id)

        # Equipment count
        equipment_count = await db.fetchval(
            "SELECT COUNT(*) FROM cmms_equipment WHERE owned_by_user_id = $1",
            user_id
        )

        # Work order counts by status
        wo_stats = await db.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'open') as open_count,
                COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress_count,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_count
            FROM work_orders
            WHERE user_id = $1
        """, user_id)

        # Top manufacturers (by equipment count)
        top_manufacturers = await db.fetch("""
            SELECT
                manufacturer,
                COUNT(*) as equipment_count
            FROM cmms_equipment
            WHERE owned_by_user_id = $1
            GROUP BY manufacturer
            ORDER BY equipment_count DESC
            LIMIT 5
        """, user_id)

        # Top faults (from work orders)
        top_faults = await db.fetch("""
            SELECT
                unnest(fault_codes) as fault_code,
                COUNT(*) as occurrence_count
            FROM work_orders
            WHERE user_id = $1
              AND fault_codes IS NOT NULL
              AND cardinality(fault_codes) > 0
            GROUP BY fault_code
            ORDER BY occurrence_count DESC
            LIMIT 10
        """, user_id)

        return OverviewStats(
            equipment_count=equipment_count or 0,
            work_orders_open=wo_stats['open_count'] if wo_stats else 0,
            work_orders_in_progress=wo_stats['in_progress_count'] if wo_stats else 0,
            work_orders_completed=wo_stats['completed_count'] if wo_stats else 0,
            top_manufacturers=[dict(m) for m in top_manufacturers] if top_manufacturers else [],
            top_faults=[dict(f) for f in top_faults] if top_faults else []
        )

    except Exception as e:
        logger.error(f"Failed to get overview stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment-health", response_model=List[EquipmentHealthItem])
async def get_equipment_health(
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get equipment health scores.

    Equipment with more work orders have lower health scores.
    Sorted by health score (ascending = worst first).
    """
    try:
        user_id = str(current_user.id)

        # Get equipment with health scores
        # Health score: 100 - (work_order_count * 10), min 0
        equipment = await db.fetch("""
            SELECT
                id,
                equipment_number,
                manufacturer,
                model_number,
                work_order_count,
                last_reported_fault,
                GREATEST(0, 100 - (work_order_count * 10)) as health_score
            FROM cmms_equipment
            WHERE owned_by_user_id = $1
            ORDER BY health_score ASC, work_order_count DESC
            LIMIT 50
        """, user_id)

        if not equipment:
            return []

        return [
            EquipmentHealthItem(
                id=str(eq['id']),
                equipment_number=eq['equipment_number'],
                manufacturer=eq['manufacturer'],
                model_number=eq['model_number'],
                work_order_count=eq['work_order_count'],
                last_reported_fault=eq['last_reported_fault'],
                health_score=float(eq['health_score'])
            )
            for eq in equipment
        ]

    except Exception as e:
        logger.error(f"Failed to get equipment health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/work-order-trends", response_model=List[WorkOrderTrend])
async def get_work_order_trends(
    days: int = 30,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get work order trends over time.

    Shows created vs completed work orders per day for the last N days.
    """
    try:
        user_id = str(current_user.id)

        # Get daily work order counts
        trends = await db.fetch("""
            WITH date_series AS (
                SELECT generate_series(
                    CURRENT_DATE - INTERVAL '1 day' * $2,
                    CURRENT_DATE,
                    INTERVAL '1 day'
                )::date as date
            )
            SELECT
                ds.date::text,
                COUNT(DISTINCT wo_created.id) as created_count,
                COUNT(DISTINCT wo_completed.id) as completed_count
            FROM date_series ds
            LEFT JOIN work_orders wo_created ON
                wo_created.user_id = $1
                AND DATE(wo_created.created_at) = ds.date
            LEFT JOIN work_orders wo_completed ON
                wo_completed.user_id = $1
                AND wo_completed.status = 'completed'
                AND DATE(wo_completed.updated_at) = ds.date
            GROUP BY ds.date
            ORDER BY ds.date ASC
        """, user_id, days - 1)

        if not trends:
            return []

        return [
            WorkOrderTrend(
                date=trend['date'],
                created_count=trend['created_count'] or 0,
                completed_count=trend['completed_count'] or 0
            )
            for trend in trends
        ]

    except Exception as e:
        logger.error(f"Failed to get work order trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_user_summary(
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get quick summary for current user.

    Simple stats for display in navigation or user profile.
    """
    try:
        user_id = str(current_user.id)

        # Get counts
        equipment_count = await db.fetchval(
            "SELECT COUNT(*) FROM cmms_equipment WHERE owned_by_user_id = $1",
            user_id
        )

        wo_open = await db.fetchval(
            "SELECT COUNT(*) FROM work_orders WHERE user_id = $1 AND status IN ('open', 'in_progress')",
            user_id
        )

        wo_completed = await db.fetchval(
            "SELECT COUNT(*) FROM work_orders WHERE user_id = $1 AND status = 'completed'",
            user_id
        )

        return {
            "user": {
                "id": str(current_user.id),
                "email": current_user.email,
                "full_name": current_user.full_name
            },
            "stats": {
                "equipment": equipment_count or 0,
                "work_orders_active": wo_open or 0,
                "work_orders_completed": wo_completed or 0
            }
        }

    except Exception as e:
        logger.error(f"Failed to get user summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
