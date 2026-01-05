"""
Equipment router for CMMS equipment management.
Leverages existing EquipmentService for all operations.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from rivet_pro.adapters.web.dependencies import get_current_user, get_db, UserInDB
from rivet_pro.core.services.equipment_service import EquipmentService
from rivet_pro.infra.database import Database
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

router = APIRouter()


class EquipmentCreate(BaseModel):
    """Equipment creation request."""
    manufacturer: str
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    equipment_type: Optional[str] = None
    location: Optional[str] = None


class EquipmentUpdate(BaseModel):
    """Equipment update request."""
    location: Optional[str] = None
    status: Optional[str] = None


class EquipmentResponse(BaseModel):
    """Equipment response model."""
    id: UUID
    equipment_number: str
    manufacturer: str
    model_number: Optional[str]
    serial_number: Optional[str]
    equipment_type: Optional[str]
    location: Optional[str]
    work_order_count: int
    last_reported_fault: Optional[str]
    owned_by_user_id: str
    created_at: str
    updated_at: str


@router.post("/", response_model=dict)
async def create_equipment(
    request: EquipmentCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Create or match equipment.

    Uses fuzzy matching to avoid duplicates. Returns equipment ID and whether it was newly created.
    """
    service = EquipmentService(db)

    try:
        equipment_id, equipment_number, is_new = await service.match_or_create_equipment(
            manufacturer=request.manufacturer,
            model_number=request.model_number,
            serial_number=request.serial_number,
            equipment_type=request.equipment_type,
            location=request.location,
            user_id=str(current_user.id)
        )

        # Fetch full equipment details
        equipment = await service.get_equipment_by_id(equipment_id)

        if not equipment:
            raise HTTPException(status_code=500, detail="Equipment created but not found")

        logger.info(
            f"Equipment {'created' if is_new else 'matched'} | "
            f"equipment_number={equipment_number} | user={current_user.email}"
        )

        return {
            "equipment": equipment,
            "is_new": is_new
        }

    except Exception as e:
        logger.error(f"Failed to create equipment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[dict])
async def list_equipment(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    manufacturer: Optional[str] = Query(None),
    equipment_type: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    List equipment for current user.

    Supports filtering by manufacturer and equipment type.
    """
    service = EquipmentService(db)

    try:
        # Build query with filters
        query = """
            SELECT
                id,
                equipment_number,
                manufacturer,
                model_number,
                serial_number,
                equipment_type,
                location,
                work_order_count,
                last_reported_fault,
                owned_by_user_id,
                created_at,
                updated_at
            FROM cmms_equipment
            WHERE owned_by_user_id = $1
        """
        params = [str(current_user.id)]
        param_count = 1

        if manufacturer:
            param_count += 1
            query += f" AND manufacturer ILIKE ${param_count}"
            params.append(f"%{manufacturer}%")

        if equipment_type:
            param_count += 1
            query += f" AND equipment_type ILIKE ${param_count}"
            params.append(f"%{equipment_type}%")

        query += " ORDER BY created_at DESC LIMIT $" + str(param_count + 1)
        params.append(limit)

        query += " OFFSET $" + str(param_count + 2)
        params.append(offset)

        equipment_list = await db.execute_query_async(
            query,
            params=tuple(params)
        )

        return equipment_list or []

    except Exception as e:
        logger.error(f"Failed to list equipment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{equipment_id}", response_model=dict)
async def get_equipment(
    equipment_id: UUID,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get equipment details by ID.

    Only returns equipment owned by current user.
    """
    service = EquipmentService(db)

    try:
        equipment = await service.get_equipment_by_id(equipment_id)

        if not equipment:
            raise HTTPException(status_code=404, detail="Equipment not found")

        # Verify ownership
        if equipment["owned_by_user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this equipment"
            )

        return equipment

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get equipment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{equipment_id}", response_model=dict)
async def update_equipment(
    equipment_id: UUID,
    request: EquipmentUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Update equipment details.

    Only owner can update equipment.
    """
    service = EquipmentService(db)

    try:
        # Verify ownership
        equipment = await service.get_equipment_by_id(equipment_id)
        if not equipment:
            raise HTTPException(status_code=404, detail="Equipment not found")

        if equipment["owned_by_user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to update this equipment")

        # Build update query
        updates = []
        params = []
        param_count = 0

        if request.location is not None:
            param_count += 1
            updates.append(f"location = ${param_count}")
            params.append(request.location)

        if request.status is not None:
            param_count += 1
            updates.append(f"status = ${param_count}")
            params.append(request.status)

        if not updates:
            return equipment  # No updates requested

        # Add updated_at
        updates.append("updated_at = NOW()")

        # Execute update
        param_count += 1
        query = f"""
            UPDATE cmms_equipment
            SET {', '.join(updates)}
            WHERE id = ${param_count}
            RETURNING *
        """
        params.append(equipment_id)

        result = await db.execute_query_async(query, tuple(params), fetch_mode="one")

        if not result:
            raise HTTPException(status_code=500, detail="Update failed")

        logger.info(f"Equipment updated | equipment_number={result[0]['equipment_number']} | user={current_user.email}")

        return result[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update equipment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/fuzzy")
async def fuzzy_search_equipment(
    query: str = Query(..., min_length=2),
    limit: int = Query(20, le=100),
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Fuzzy search equipment by manufacturer, model, or serial number.

    Returns equipment owned by current user.
    """
    try:
        # Search across manufacturer, model, and serial
        sql_query = """
            SELECT
                id,
                equipment_number,
                manufacturer,
                model_number,
                serial_number,
                equipment_type,
                location,
                work_order_count
            FROM cmms_equipment
            WHERE owned_by_user_id = $1
              AND (
                  manufacturer ILIKE $2
                  OR model_number ILIKE $2
                  OR serial_number ILIKE $2
                  OR equipment_type ILIKE $2
              )
            ORDER BY work_order_count DESC, created_at DESC
            LIMIT $3
        """

        results = await db.execute_query_async(
            sql_query,
            (str(current_user.id), f"%{query}%", limit)
        )

        return results or []

    except Exception as e:
        logger.error(f"Failed to search equipment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
