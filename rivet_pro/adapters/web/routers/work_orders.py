"""
Work order router for CMMS work order management.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from rivet_pro.adapters.web.dependencies import get_current_user, get_db, UserInDB
from rivet_pro.core.services.work_order_service import WorkOrderService
from rivet_pro.infra.database import Database
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

router = APIRouter()


class WorkOrderCreate(BaseModel):
    """Work order creation request."""
    title: str
    description: str
    equipment_id: Optional[UUID] = None  # If provided, use existing equipment
    manufacturer: Optional[str] = None  # For auto-create equipment
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    equipment_type: Optional[str] = None
    location: Optional[str] = None
    fault_codes: Optional[List[str]] = None
    symptoms: Optional[List[str]] = None
    priority: str = "medium"


class WorkOrderUpdate(BaseModel):
    """Work order update request."""
    status: Optional[str] = None
    notes: Optional[str] = None


class WorkOrderResponse(BaseModel):
    """Work order response model."""
    id: UUID
    work_order_number: str
    equipment_id: UUID
    equipment_number: str
    title: str
    description: str
    status: str
    priority: str
    fault_codes: Optional[List[str]]
    symptoms: Optional[List[str]]
    created_at: str
    updated_at: str
    completed_at: Optional[str]


@router.post("/", response_model=dict)
async def create_work_order(
    request: WorkOrderCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Create a new work order.

    Equipment-first architecture:
    - If equipment_id provided, uses that equipment
    - Otherwise, creates/matches equipment from manufacturer, model, serial

    Requires either:
    - equipment_id, OR
    - manufacturer (at minimum)
    """
    service = WorkOrderService(db)

    # Validate inputs
    if not request.equipment_id and not request.manufacturer:
        raise HTTPException(
            status_code=400,
            detail="Must provide either equipment_id or manufacturer"
        )

    try:
        work_order = await service.create_work_order(
            user_id=str(current_user.id),
            title=request.title,
            description=request.description,
            manufacturer=request.manufacturer,
            model_number=request.model_number,
            serial_number=request.serial_number,
            equipment_type=request.equipment_type,
            location=request.location,
            fault_codes=request.fault_codes,
            symptoms=request.symptoms,
            source="web",
            priority=request.priority,
            equipment_id=request.equipment_id
        )

        logger.info(
            f"Work order created | WO={work_order['work_order_number']} | user={current_user.email}"
        )

        return work_order

    except Exception as e:
        logger.error(f"Failed to create work order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[dict])
async def list_work_orders(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    List work orders for current user.

    Optionally filter by status (open, in_progress, completed, cancelled).
    """
    service = WorkOrderService(db)

    try:
        work_orders = await service.list_work_orders_by_user(
            user_id=str(current_user.id),
            limit=limit,
            status=status
        )

        return work_orders

    except Exception as e:
        logger.error(f"Failed to list work orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{work_order_id}", response_model=dict)
async def get_work_order(
    work_order_id: UUID,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get work order details by ID.

    Only returns work orders owned by current user.
    """
    service = WorkOrderService(db)

    try:
        work_order = await service.get_work_order_by_id(work_order_id)

        if not work_order:
            raise HTTPException(status_code=404, detail="Work order not found")

        # Verify ownership
        if work_order["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this work order"
            )

        return work_order

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get work order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{work_order_id}", response_model=dict)
async def update_work_order(
    work_order_id: UUID,
    request: WorkOrderUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Update work order status and/or add notes.

    Allowed status transitions:
    - open → in_progress → completed
    - Any → cancelled
    """
    service = WorkOrderService(db)

    try:
        # Verify ownership
        work_order = await service.get_work_order_by_id(work_order_id)

        if not work_order:
            raise HTTPException(status_code=404, detail="Work order not found")

        if work_order["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to update this work order")

        # Update status
        if request.status:
            # Validate status transitions
            valid_statuses = ["open", "in_progress", "completed", "cancelled"]
            if request.status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                )

            await service.update_status(
                work_order_id=work_order_id,
                status=request.status,
                notes=request.notes
            )

            logger.info(
                f"Work order updated | WO={work_order['work_order_number']} | "
                f"status={request.status} | user={current_user.email}"
            )

        # Fetch updated work order
        updated_work_order = await service.get_work_order_by_id(work_order_id)

        return updated_work_order

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update work order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment/{equipment_id}/work-orders", response_model=List[dict])
async def list_work_orders_by_equipment(
    equipment_id: UUID,
    limit: int = Query(50, le=200),
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    List work orders for specific equipment.

    Returns work orders for equipment owned by current user.
    """
    from rivet_pro.core.services.equipment_service import EquipmentService

    service = WorkOrderService(db)
    equipment_service = EquipmentService(db)

    try:
        # Verify equipment ownership
        equipment = await equipment_service.get_equipment_by_id(equipment_id)

        if not equipment:
            raise HTTPException(status_code=404, detail="Equipment not found")

        if equipment["owned_by_user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this equipment's work orders"
            )

        # List work orders
        work_orders = await service.list_work_orders_by_equipment(
            equipment_id=equipment_id,
            limit=limit
        )

        return work_orders

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list work orders for equipment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
