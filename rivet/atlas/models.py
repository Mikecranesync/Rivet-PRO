"""
Atlas CMMS Data Models

Pydantic models for Equipment, Work Orders, and related entities.
Based on database schemas in migrations/001_cmms_equipment.sql and 002_work_orders.sql.
"""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ===== Enums =====

class CriticalityLevel(str, Enum):
    """Equipment criticality for prioritization."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SourceType(str, Enum):
    """How the work order was created."""
    TELEGRAM_TEXT = "telegram_text"
    TELEGRAM_VOICE = "telegram_voice"
    TELEGRAM_PHOTO = "telegram_photo"
    TELEGRAM_PRINT_QA = "telegram_print_qa"
    TELEGRAM_MANUAL_GAP = "telegram_manual_gap"


class RouteType(str, Enum):
    """RIVET orchestrator routing (4-route confidence-based system)."""
    A = "A"  # Direct SME answer (high confidence)
    B = "B"  # Enriched answer (medium confidence)
    C = "C"  # Research required (low confidence)
    D = "D"  # Clarification needed (ambiguous)


class WorkOrderStatus(str, Enum):
    """Work order lifecycle status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PriorityLevel(str, Enum):
    """Work order priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ===== Equipment Models =====

class EquipmentBase(BaseModel):
    """Base equipment fields (for creation/updates)."""
    manufacturer: str = Field(..., min_length=1, max_length=255, description="Equipment manufacturer (e.g. Siemens, Rockwell)")
    model_number: Optional[str] = Field(None, description="Model/part number")
    serial_number: Optional[str] = Field(None, description="Serial number")
    equipment_type: Optional[str] = Field(None, description="Equipment category (e.g. VFD, Motor, PLC)")
    location: Optional[str] = Field(None, description="Physical location")
    department: Optional[str] = Field(None, description="Department/area")
    criticality: CriticalityLevel = Field(CriticalityLevel.MEDIUM, description="Criticality level")
    description: Optional[str] = Field(None, description="Additional notes")
    photo_file_id: Optional[str] = Field(None, description="Telegram photo file ID")
    installation_date: Optional[date] = Field(None, description="Date installed")
    owned_by_user_id: Optional[str] = Field(None, description="Telegram user ID who owns this equipment")
    machine_id: Optional[UUID] = Field(None, description="Link to user_machines table")

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "manufacturer": "Siemens",
                "model_number": "G120C-2.2kW",
                "serial_number": "SN123456789",
                "equipment_type": "VFD",
                "location": "Building A - Line 3",
                "criticality": "high"
            }
        }
    )


class Equipment(EquipmentBase):
    """Full equipment record (from database)."""
    id: UUID
    equipment_number: str = Field(..., description="Auto-generated ID (EQ-2025-0001)")

    # Statistics (auto-updated by database triggers)
    work_order_count: int = Field(0, description="Total work orders for this equipment")
    total_downtime_hours: float = Field(0.0, description="Cumulative downtime")
    last_reported_fault: Optional[str] = Field(None, description="Most recent fault code")
    last_work_order_at: Optional[datetime] = Field(None, description="Last WO timestamp")
    last_maintenance_date: Optional[date] = Field(None, description="Last maintenance")

    # Audit fields
    created_at: datetime
    updated_at: datetime
    first_reported_by: Optional[str] = Field(None, description="Telegram user who first reported")

    model_config = ConfigDict(from_attributes=True)


class EquipmentCreate(EquipmentBase):
    """Equipment creation payload."""
    first_reported_by: Optional[str] = None


class EquipmentUpdate(BaseModel):
    """Equipment update payload (all fields optional)."""
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    equipment_type: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    criticality: Optional[CriticalityLevel] = None
    description: Optional[str] = None
    photo_file_id: Optional[str] = None
    installation_date: Optional[date] = None
    last_maintenance_date: Optional[date] = None
    owned_by_user_id: Optional[str] = None
    machine_id: Optional[UUID] = None

    model_config = ConfigDict(use_enum_values=True)


# ===== Work Order Models =====

class WorkOrderBase(BaseModel):
    """Base work order fields (for creation/updates)."""
    user_id: str = Field(..., description="Telegram user ID")
    telegram_username: Optional[str] = Field(None, description="Telegram @username")
    source: SourceType = Field(..., description="How this WO was created")

    # Equipment linkage (equipment_id is mandatory - equipment-first architecture)
    equipment_id: Optional[UUID] = Field(None, description="Link to cmms_equipment.id")

    # Issue details
    title: str = Field(..., min_length=1, max_length=500, description="Brief issue summary")
    description: str = Field(..., min_length=1, description="Detailed description")
    fault_codes: Optional[List[str]] = Field(None, max_length=20, description="Fault codes from equipment (max 20)")
    symptoms: Optional[List[str]] = Field(None, max_length=50, description="Observed symptoms (max 50)")

    # AI response metadata
    answer_text: Optional[str] = Field(None, description="AI-generated answer")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="AI confidence (0-1)")
    route_taken: Optional[RouteType] = Field(None, description="RIVET route used")
    suggested_actions: Optional[List[str]] = Field(None, max_length=20, description="Recommended steps (max 20)")
    safety_warnings: Optional[List[str]] = Field(None, max_length=20, description="Safety precautions (max 20)")
    cited_kb_atoms: Optional[List[str]] = Field(None, max_length=50, description="Knowledge base sources (max 50)")
    manual_links: Optional[List[str]] = Field(None, max_length=20, description="Manual references (max 20)")

    # Status & Priority
    status: WorkOrderStatus = Field(WorkOrderStatus.OPEN, description="Current status")
    priority: PriorityLevel = Field(PriorityLevel.MEDIUM, description="Priority level")

    # Audit trail
    trace_id: Optional[UUID] = Field(None, description="RequestTrace link")
    conversation_id: Optional[UUID] = Field(None, description="Multi-turn conversation ID")
    research_triggered: bool = Field(False, description="Did this trigger research?")
    enrichment_triggered: bool = Field(False, description="Did this trigger enrichment?")
    created_by_agent: Optional[str] = Field(None, description="Agent that created this (e.g. siemens_agent)")

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "user_id": "123456789",
                "telegram_username": "@technician",
                "source": "telegram_text",
                "equipment_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "VFD fault F0001",
                "description": "Drive showing overcurrent fault, motor stopped",
                "fault_codes": ["F0001"],
                "status": "open",
                "priority": "high"
            }
        }
    )


class WorkOrder(WorkOrderBase):
    """Full work order record (from database)."""
    id: UUID
    work_order_number: str = Field(..., description="Auto-generated ID (WO-2025-0001)")

    # Denormalized equipment fields (for query performance)
    equipment_number: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    equipment_type: Optional[str] = None
    machine_id: Optional[UUID] = None
    location: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WorkOrderCreate(WorkOrderBase):
    """Work order creation payload."""
    pass


class WorkOrderUpdate(BaseModel):
    """Work order update payload (all fields optional)."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1)
    status: Optional[WorkOrderStatus] = None
    priority: Optional[PriorityLevel] = None
    fault_codes: Optional[List[str]] = Field(None, max_length=20)
    symptoms: Optional[List[str]] = Field(None, max_length=50)
    answer_text: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    route_taken: Optional[RouteType] = None
    suggested_actions: Optional[List[str]] = Field(None, max_length=20)
    safety_warnings: Optional[List[str]] = Field(None, max_length=20)
    cited_kb_atoms: Optional[List[str]] = Field(None, max_length=50)
    manual_links: Optional[List[str]] = Field(None, max_length=20)
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=True)


# ===== Technician Model =====

class Technician(BaseModel):
    """Technician record (from database)."""
    id: UUID
    telegram_user_id: str
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    specialization: Optional[str] = Field(None, description="E.g. 'Siemens VFDs', 'PLCs'")
    organization: Optional[str] = None
    is_active: bool = Field(True, description="Active technician")
    created_at: datetime
    updated_at: datetime
    last_activity_at: Optional[datetime] = None
    work_order_count: int = Field(0, description="Total work orders created")

    model_config = ConfigDict(from_attributes=True)


class TechnicianCreate(BaseModel):
    """Technician creation payload."""
    telegram_user_id: str
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    specialization: Optional[str] = None
    organization: Optional[str] = None


class TechnicianUpdate(BaseModel):
    """Technician update payload (all fields optional)."""
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    specialization: Optional[str] = None
    organization: Optional[str] = None
    is_active: Optional[bool] = None
    last_activity_at: Optional[datetime] = None
