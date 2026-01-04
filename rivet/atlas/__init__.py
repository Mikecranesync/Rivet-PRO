"""
Atlas CMMS - Complete maintenance management system for Rivet Pro.

Includes:
- Internal database (equipment, work orders, personal machine library)
- External Atlas API client (JWT auth, async HTTP)
- Equipment fuzzy matching (85% threshold)
- Work order auto-creation pipeline
"""

from rivet.atlas.database import AtlasDatabase
from rivet.atlas.models import (
    # Enums
    CriticalityLevel,
    SourceType,
    RouteType,
    WorkOrderStatus,
    PriorityLevel,
    # Equipment
    Equipment,
    EquipmentCreate,
    EquipmentUpdate,
    # Work Orders
    WorkOrder,
    WorkOrderCreate,
    WorkOrderUpdate,
    # Technician
    Technician,
    TechnicianCreate,
    TechnicianUpdate,
)
from rivet.atlas.equipment_matcher import EquipmentMatcher
from rivet.atlas.work_order_service import WorkOrderService
from rivet.atlas.machine_library import MachineLibrary
from rivet.atlas.technician_service import TechnicianService

__all__ = [
    "AtlasDatabase",
    "EquipmentMatcher",
    "WorkOrderService",
    "MachineLibrary",
    "TechnicianService",
    # Enums
    "CriticalityLevel",
    "SourceType",
    "RouteType",
    "WorkOrderStatus",
    "PriorityLevel",
    # Equipment
    "Equipment",
    "EquipmentCreate",
    "EquipmentUpdate",
    # Work Orders
    "WorkOrder",
    "WorkOrderCreate",
    "WorkOrderUpdate",
    # Technician
    "Technician",
    "TechnicianCreate",
    "TechnicianUpdate",
]
