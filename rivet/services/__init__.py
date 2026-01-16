"""
Rivet Services

Service layer for knowledge management, embeddings, and SME chat.
"""

from rivet.services.knowledge_service import KnowledgeService
from rivet.services.embedding_service import EmbeddingService, cosine_similarity
from rivet.services.sme_rag_service import (
    SMERagService,
    calculate_rag_confidence,
    extract_sources_from_atoms,
)

__all__ = [
    "KnowledgeService",
    "EmbeddingService",
    "cosine_similarity",
    "SMERagService",
    "calculate_rag_confidence",
    "extract_sources_from_atoms",
]
