"""
Knowledge Base Data Models

Pydantic models for KnowledgeAtom and KnowledgeGap entities.
Based on database schema in migrations/009_knowledge_atoms.sql.

These models support the 4-route AI orchestrator system (rivet_pro_skill_ai_routing.md):
- Route 1 (LOOKUP): High-confidence atoms (>0.8) returned directly
- Route 2 (RESEARCH): Medium-confidence atoms (0.4-0.8) trigger gap logging
- Route 3 (CLARIFY): Low-confidence (<0.4) triggers clarification questions
- Route 4 (ESCALATE): Safety-critical routing
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator


# ===== Enums =====

class AtomType(str, Enum):
    """Type of knowledge atom for categorization."""
    FAULT = "fault"              # Error codes and fault diagnostics
    PROCEDURE = "procedure"       # Step-by-step how-to guides
    SPEC = "spec"                # Technical specifications
    PART = "part"                # Component information
    TIP = "tip"                  # Best practices and tribal knowledge
    SAFETY = "safety"            # Safety warnings and procedures


class ResearchStatus(str, Enum):
    """Status of knowledge gap research."""
    PENDING = "pending"          # Awaiting research
    IN_PROGRESS = "in_progress"  # Research worker processing
    COMPLETED = "completed"       # Resolved with new atom created
    FAILED = "failed"            # Research failed or no quality sources found


# ===== Knowledge Atom Models =====

class KnowledgeAtomBase(BaseModel):
    """Base knowledge atom fields (for creation/updates)."""
    type: AtomType = Field(..., description="Type of knowledge (fault, procedure, spec, part, tip, safety)")
    manufacturer: Optional[str] = Field(None, max_length=255, description="Equipment manufacturer (optional)")
    model: Optional[str] = Field(None, max_length=255, description="Specific model (optional)")
    equipment_type: Optional[str] = Field(None, max_length=100, description="Equipment category (e.g., drive, plc, sensor)")

    title: str = Field(..., min_length=5, max_length=500, description="Concise title (e.g., 'F0002 - Overvoltage Fault')")
    content: str = Field(..., min_length=20, description="Detailed knowledge content")
    source_url: Optional[str] = Field(None, max_length=1000, description="Source URL (manual, forum, documentation)")

    confidence: float = Field(0.5, ge=0.0, le=1.0, description="Confidence score (0.0=unverified, 1.0=manufacturer-confirmed)")
    human_verified: bool = Field(False, description="Has this been verified by a human expert?")

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "type": "fault",
                "manufacturer": "Siemens",
                "model": "G120C",
                "title": "F0002 - Overvoltage Fault",
                "content": "F0002 indicates DC bus overvoltage. Common causes: (1) Regen energy not dissipated, (2) Input voltage spike, (3) Faulty braking resistor.",
                "source_url": "https://support.siemens.com/cs/document/67854244",
                "confidence": 0.95,
                "human_verified": True
            }
        }
    )

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is within bounds."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return round(v, 3)  # Round to 3 decimal places


class KnowledgeAtomCreate(KnowledgeAtomBase):
    """Model for creating new knowledge atoms (no ID yet)."""
    pass


class KnowledgeAtomUpdate(BaseModel):
    """Model for updating existing knowledge atoms (all fields optional)."""
    type: Optional[AtomType] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    equipment_type: Optional[str] = None
    title: Optional[str] = Field(None, min_length=5, max_length=500)
    content: Optional[str] = Field(None, min_length=20)
    source_url: Optional[str] = Field(None, max_length=1000)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    human_verified: Optional[bool] = None

    model_config = ConfigDict(use_enum_values=True)


class KnowledgeAtom(KnowledgeAtomBase):
    """Full knowledge atom record (from database)."""
    atom_id: UUID = Field(..., description="Unique atom identifier")

    # Vector embedding (typically not returned in API responses for performance)
    embedding: Optional[List[float]] = Field(None, exclude=True, description="1536-dim vector for semantic search")

    # Usage statistics
    usage_count: int = Field(0, description="How many times this atom was returned to users")

    # Timestamps
    created_at: datetime = Field(..., description="When this atom was created")
    last_verified: datetime = Field(..., description="Last verification/update timestamp")

    # Computed field for client display
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Cosine similarity from vector search (populated at query time)")

    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True  # Enable ORM mode for database records
    )


# ===== Knowledge Gap Models =====

class KnowledgeGapBase(BaseModel):
    """Base knowledge gap fields (for creation/updates)."""
    query: str = Field(..., min_length=3, description="User query that had low confidence")
    manufacturer: Optional[str] = Field(None, max_length=255, description="Manufacturer from OCR or context")
    model: Optional[str] = Field(None, max_length=255, description="Model from OCR or context")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="What confidence did we have? (triggers if <0.7)")
    research_status: ResearchStatus = Field(ResearchStatus.PENDING, description="Research workflow status")

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "query": "How to reset fault F9999 on XYZ-3000 drive?",
                "manufacturer": "Unknown Corp",
                "model": "XYZ-3000",
                "confidence_score": 0.25,
                "research_status": "pending"
            }
        }
    )


class KnowledgeGapCreate(KnowledgeGapBase):
    """Model for creating new knowledge gaps."""
    pass


class KnowledgeGapUpdate(BaseModel):
    """Model for updating knowledge gaps (typically status changes)."""
    research_status: Optional[ResearchStatus] = None
    resolved_atom_id: Optional[UUID] = Field(None, description="Atom created to fill this gap")

    model_config = ConfigDict(use_enum_values=True)


class KnowledgeGap(KnowledgeGapBase):
    """Full knowledge gap record (from database)."""
    gap_id: UUID = Field(..., description="Unique gap identifier")

    # Auto-incremented on duplicate queries
    occurrence_count: int = Field(1, ge=1, description="How many times this gap was encountered")

    # Auto-calculated priority (higher = more urgent)
    # priority = occurrence_count × (1 - confidence) × vendor_boost
    priority: float = Field(..., ge=0.0, description="Research priority (auto-calculated)")

    # Resolution tracking
    resolved_atom_id: Optional[UUID] = Field(None, description="Atom created to fill this gap")

    # Timestamps
    created_at: datetime = Field(..., description="First occurrence timestamp")
    resolved_at: Optional[datetime] = Field(None, description="When research completed")

    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True
    )


# ===== Search Result Models =====

class KnowledgeSearchResult(BaseModel):
    """Enriched search result with confidence calculation."""
    atom: KnowledgeAtom = Field(..., description="The knowledge atom")
    final_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence with manufacturer/model boosts applied")
    boosts_applied: dict = Field(default_factory=dict, description="Which boosts were applied (manufacturer, model, human_verified)")

    model_config = ConfigDict(use_enum_values=True)


class KnowledgeSearchResponse(BaseModel):
    """Full search response with routing decision."""
    query: str = Field(..., description="Original user query")
    top_results: List[KnowledgeSearchResult] = Field(default_factory=list, description="Top matching atoms")
    max_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Highest confidence among results")
    recommended_route: str = Field(..., description="A (lookup), B (sme), C (research/clarify), or D (escalate)")
    gap_logged: bool = Field(False, description="Was a knowledge gap logged?")

    model_config = ConfigDict(use_enum_values=True)
