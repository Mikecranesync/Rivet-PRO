"""
RIVET Pro Models

Pydantic models for all RIVET Pro entities.
"""

from rivet.models.knowledge import (
    AtomType,
    ResearchStatus,
    KnowledgeAtomBase,
    KnowledgeAtomCreate,
    KnowledgeAtomUpdate,
    KnowledgeAtom,
    KnowledgeGapBase,
    KnowledgeGapCreate,
    KnowledgeGapUpdate,
    KnowledgeGap,
    KnowledgeSearchResult,
    KnowledgeSearchResponse,
)

from rivet.models.sme_chat import (
    SMEVendor,
    SessionStatus,
    MessageRole,
    ConfidenceLevel,
    SMEChatSessionBase,
    SMEChatSessionCreate,
    SMEChatSession,
    SMEChatMessageBase,
    SMEChatMessageCreate,
    SMEChatMessage,
    SMEChatResponse,
    ConversationContext,
    RAGContext,
    get_confidence_badge,
    get_sme_name,
    get_sme_title,
)

__all__ = [
    # Knowledge models
    "AtomType",
    "ResearchStatus",
    "KnowledgeAtomBase",
    "KnowledgeAtomCreate",
    "KnowledgeAtomUpdate",
    "KnowledgeAtom",
    "KnowledgeGapBase",
    "KnowledgeGapCreate",
    "KnowledgeGapUpdate",
    "KnowledgeGap",
    "KnowledgeSearchResult",
    "KnowledgeSearchResponse",
    # SME Chat models
    "SMEVendor",
    "SessionStatus",
    "MessageRole",
    "ConfidenceLevel",
    "SMEChatSessionBase",
    "SMEChatSessionCreate",
    "SMEChatSession",
    "SMEChatMessageBase",
    "SMEChatMessageCreate",
    "SMEChatMessage",
    "SMEChatResponse",
    "ConversationContext",
    "RAGContext",
    "get_confidence_badge",
    "get_sme_name",
    "get_sme_title",
]
