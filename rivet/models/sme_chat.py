"""
SME Chat Data Models

Pydantic models for SME chat sessions and messages.
Based on database schema in migrations/026_sme_chat_sessions.sql.

These models support Phase 4: SME Chat with LLM Interaction:
- Multi-turn conversations with vendor-specific SME agents
- RAG-enhanced responses from knowledge_atoms
- Confidence-based routing (direct/synthesize/clarify)
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator


# ===== Enums =====

class SMEVendor(str, Enum):
    """Vendor SME personalities available."""
    SIEMENS = "siemens"      # Hans - German precision, methodical
    ROCKWELL = "rockwell"    # Mike - American practical, friendly
    ABB = "abb"              # Erik - Swiss/Swedish analytical, safety-conscious
    SCHNEIDER = "schneider"  # Pierre - French elegance, global perspective
    MITSUBISHI = "mitsubishi"  # Takeshi - Japanese precision, thorough
    FANUC = "fanuc"          # Ken - CNC expert, production-focused
    GENERIC = "generic"      # General industrial SME


class SessionStatus(str, Enum):
    """SME chat session status."""
    ACTIVE = "active"        # In active conversation
    CLOSED = "closed"        # User ended session via /endchat
    TIMEOUT = "timeout"      # Inactive for 30+ minutes


class MessageRole(str, Enum):
    """Chat message role."""
    SYSTEM = "system"        # System prompt with personality
    USER = "user"            # User message
    ASSISTANT = "assistant"  # SME response


class ConfidenceLevel(str, Enum):
    """Confidence routing level for responses."""
    HIGH = "high"            # >= 0.85 - Direct KB answer
    MEDIUM = "medium"        # 0.70-0.85 - SME synthesis
    LOW = "low"              # < 0.70 - Clarifying questions


# ===== Session Models =====

class SMEChatSessionBase(BaseModel):
    """Base SME chat session fields."""
    telegram_chat_id: int = Field(..., description="Telegram chat ID for this session")
    sme_vendor: SMEVendor = Field(..., description="Vendor SME personality (siemens=Hans, rockwell=Mike, etc.)")
    equipment_context: Optional[dict] = Field(None, description="Context from equipment workflow (model, serial, faults)")

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "telegram_chat_id": 12345678,
                "sme_vendor": "siemens",
                "equipment_context": {
                    "model": "G120C",
                    "serial": "ABC123",
                    "recent_faults": ["F0002", "F0001"]
                }
            }
        }
    )


class SMEChatSessionCreate(SMEChatSessionBase):
    """Model for creating new SME chat session."""
    pass


class SMEChatSession(SMEChatSessionBase):
    """Full SME chat session record (from database)."""
    session_id: UUID = Field(..., description="Unique session identifier")
    status: SessionStatus = Field(SessionStatus.ACTIVE, description="Session status")

    # Timestamps
    created_at: datetime = Field(..., description="Session start time")
    last_message_at: datetime = Field(..., description="Last message timestamp")
    closed_at: Optional[datetime] = Field(None, description="When session was closed")

    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True
    )


# ===== Message Models =====

class SMEChatMessageBase(BaseModel):
    """Base SME chat message fields."""
    role: MessageRole = Field(..., description="Message role (system/user/assistant)")
    content: str = Field(..., min_length=1, description="Message content")

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "role": "user",
                "content": "What causes F0002 fault on Siemens G120C?"
            }
        }
    )


class SMEChatMessageCreate(SMEChatMessageBase):
    """Model for creating new chat message."""
    session_id: UUID = Field(..., description="Session this message belongs to")

    # Optional metadata for assistant messages
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="RAG confidence score")
    rag_atoms_used: Optional[List[UUID]] = Field(None, description="Knowledge atom IDs used")
    cost_usd: Optional[float] = Field(None, ge=0.0, description="LLM cost for this message")
    safety_warnings: Optional[List[str]] = Field(None, description="Extracted safety warnings")
    sources: Optional[List[str]] = Field(None, description="Source citations from RAG")

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: Optional[float]) -> Optional[float]:
        """Ensure confidence is within bounds."""
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return round(v, 3) if v is not None else None


class SMEChatMessage(SMEChatMessageBase):
    """Full SME chat message record (from database)."""
    message_id: UUID = Field(..., description="Unique message identifier")
    session_id: UUID = Field(..., description="Session this message belongs to")

    # Response metadata (for assistant messages)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="RAG confidence score")
    rag_atoms_used: Optional[List[UUID]] = Field(None, description="Knowledge atom IDs used")
    cost_usd: Optional[float] = Field(None, ge=0.0, description="LLM cost")
    safety_warnings: Optional[List[str]] = Field(None, description="Safety warnings")
    sources: Optional[List[str]] = Field(None, description="Source citations")

    # Timestamp
    created_at: datetime = Field(..., description="Message timestamp")

    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True
    )


# ===== Response Models =====

class SMEChatResponse(BaseModel):
    """Response from SMEChatService.chat() method."""
    response: str = Field(..., description="SME response text with personality voice")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    confidence_level: ConfidenceLevel = Field(..., description="Confidence routing level")

    # Sources and context
    sources: List[str] = Field(default_factory=list, description="Source citations from RAG")
    rag_atoms_used: List[UUID] = Field(default_factory=list, description="Knowledge atom IDs used")

    # Safety and warnings
    safety_warnings: List[str] = Field(default_factory=list, description="Extracted safety warnings")

    # Metadata
    cost_usd: float = Field(0.0, ge=0.0, description="LLM cost for this response")
    sme_name: str = Field(..., description="SME personality name (e.g., 'Hans')")
    sme_vendor: SMEVendor = Field(..., description="Vendor type")

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "response": "Ah, the F0002 fault! This indicates DC bus overvoltage...",
                "confidence": 0.92,
                "confidence_level": "high",
                "sources": ["Siemens G120C Manual Chapter 5"],
                "rag_atoms_used": ["550e8400-e29b-41d4-a716-446655440000"],
                "safety_warnings": ["High voltage hazard - ensure proper lockout/tagout"],
                "cost_usd": 0.0023,
                "sme_name": "Hans",
                "sme_vendor": "siemens"
            }
        }
    )

    @classmethod
    def from_confidence(cls, confidence: float) -> ConfidenceLevel:
        """Determine confidence level from score."""
        if confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.70:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW


# ===== Conversation Context Models =====

class ConversationContext(BaseModel):
    """Context built from conversation history for RAG enhancement."""
    recent_topics: List[str] = Field(default_factory=list, description="Topics from recent messages")
    equipment_mentioned: Optional[str] = Field(None, description="Equipment model mentioned")
    fault_codes_mentioned: List[str] = Field(default_factory=list, description="Fault codes discussed")
    unresolved_questions: List[str] = Field(default_factory=list, description="Questions not yet answered")

    model_config = ConfigDict(use_enum_values=True)


class RAGContext(BaseModel):
    """RAG context for SME chat prompt building."""
    atoms: List[dict] = Field(default_factory=list, description="Retrieved knowledge atoms")
    formatted_context: str = Field("", description="Formatted context string for LLM prompt")
    top_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Highest atom confidence")
    atom_ids: List[UUID] = Field(default_factory=list, description="IDs of retrieved atoms")

    model_config = ConfigDict(use_enum_values=True)


# ===== Helper Functions =====

def get_confidence_badge(confidence: float) -> str:
    """Return emoji badge for confidence level."""
    if confidence >= 0.85:
        return "HIGH"  # Green circle
    elif confidence >= 0.70:
        return "MEDIUM"  # Yellow circle
    else:
        return "LOW"  # Orange circle


def get_sme_name(vendor: SMEVendor) -> str:
    """Return SME personality name for vendor."""
    names = {
        SMEVendor.SIEMENS: "Hans",
        SMEVendor.ROCKWELL: "Mike",
        SMEVendor.ABB: "Erik",
        SMEVendor.SCHNEIDER: "Pierre",
        SMEVendor.MITSUBISHI: "Takeshi",
        SMEVendor.FANUC: "Ken",
        SMEVendor.GENERIC: "Alex",
    }
    return names.get(vendor, "Alex")


def get_sme_title(vendor: SMEVendor) -> str:
    """Return SME title for vendor."""
    titles = {
        SMEVendor.SIEMENS: "Siemens Expert",
        SMEVendor.ROCKWELL: "Rockwell Expert",
        SMEVendor.ABB: "ABB Expert",
        SMEVendor.SCHNEIDER: "Schneider Expert",
        SMEVendor.MITSUBISHI: "Mitsubishi Expert",
        SMEVendor.FANUC: "FANUC Expert",
        SMEVendor.GENERIC: "Industrial Expert",
    }
    return titles.get(vendor, "Industrial Expert")
