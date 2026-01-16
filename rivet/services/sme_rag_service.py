"""
SME RAG Service

Retrieves relevant knowledge atoms filtered by manufacturer for SME chat sessions.
Builds enhanced queries from conversation context and formats atoms for LLM prompts.

Uses:
- EmbeddingService for query embedding generation
- KnowledgeService.vector_search for similarity search with manufacturer filter
- Conversation history for query enhancement
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from rivet.services.knowledge_service import KnowledgeService
from rivet.services.embedding_service import EmbeddingService
from rivet.models.sme_chat import ConversationContext, RAGContext
from rivet.atlas.database import AtlasDatabase

logger = logging.getLogger(__name__)


class SMERagService:
    """
    RAG service for SME chat context retrieval.

    Features:
    - Query enhancement from conversation history
    - Manufacturer-filtered vector search
    - Structured context formatting for LLM prompts
    - Confidence scoring based on similarity
    """

    def __init__(
        self,
        knowledge_service: Optional[KnowledgeService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        db: Optional[AtlasDatabase] = None
    ):
        """
        Initialize SME RAG service.

        Args:
            knowledge_service: KnowledgeService instance. Created if None.
            embedding_service: EmbeddingService instance. Created if None.
            db: AtlasDatabase instance. Shared with KnowledgeService if provided.
        """
        self.db = db or AtlasDatabase()
        self.knowledge_service = knowledge_service or KnowledgeService(db=self.db)
        self.embedding_service = embedding_service or EmbeddingService()

        logger.info("SMERagService initialized")

    async def get_relevant_context(
        self,
        query: str,
        manufacturer: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        equipment_context: Optional[Dict[str, Any]] = None,
        limit: int = 5,
        min_confidence: float = 0.5
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Retrieve relevant knowledge atoms for SME chat.

        Args:
            query: User's current question
            manufacturer: Manufacturer to filter by (e.g., "siemens", "rockwell")
            conversation_history: List of {"role": "user"|"assistant", "content": "..."}
            equipment_context: Equipment data from OCR or previous interactions
            limit: Maximum atoms to return
            min_confidence: Minimum similarity score (0.0-1.0)

        Returns:
            Tuple of (atoms_list, formatted_context_string)

        Example:
            atoms, context = await rag_service.get_relevant_context(
                query="What causes F0002 fault?",
                manufacturer="siemens",
                equipment_context={"model": "G120C"},
                limit=5
            )
        """
        logger.info(
            f"[SME RAG] Query: {query[:50]}... | "
            f"Manufacturer: {manufacturer} | Limit: {limit}"
        )

        # Step 1: Build enhanced query from context
        enhanced_query = self._build_enhanced_query(
            query=query,
            conversation_history=conversation_history,
            equipment_context=equipment_context
        )
        logger.debug(f"[SME RAG] Enhanced query: {enhanced_query[:100]}...")

        # Step 2: Generate embedding for enhanced query
        try:
            query_embedding = await self.embedding_service.generate_embedding(enhanced_query)
        except Exception as e:
            logger.error(f"[SME RAG] Failed to generate embedding: {e}")
            return [], self._format_no_context()

        # Step 3: Vector search with manufacturer filter
        try:
            results = await self.knowledge_service.vector_search(
                query_embedding=query_embedding,
                manufacturer=manufacturer.capitalize() if manufacturer else None,
                min_confidence=min_confidence,
                limit=limit
            )
        except Exception as e:
            logger.error(f"[SME RAG] Vector search failed: {e}")
            return [], self._format_no_context()

        if not results:
            logger.info("[SME RAG] No atoms found above confidence threshold")
            return [], self._format_no_context()

        # Step 4: Format results as structured context
        atoms_list = self._process_results(results)
        formatted_context = self._format_context(atoms_list, manufacturer)

        logger.info(
            f"[SME RAG] Retrieved {len(atoms_list)} atoms "
            f"(top similarity: {atoms_list[0].get('similarity', 0):.2f})"
        )

        return atoms_list, formatted_context

    def _build_enhanced_query(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        equipment_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build enhanced query from conversation context for better embedding.

        Combines:
        - Current query
        - Recent topics from conversation
        - Equipment model/fault codes from context
        """
        parts = [query]

        # Add equipment context
        if equipment_context:
            if equipment_context.get("model"):
                parts.append(f"Equipment: {equipment_context['model']}")
            if equipment_context.get("recent_faults"):
                faults = equipment_context["recent_faults"]
                if isinstance(faults, list):
                    parts.append(f"Faults: {', '.join(faults[:3])}")
                else:
                    parts.append(f"Fault: {faults}")

        # Add recent conversation context (last 2 exchanges)
        if conversation_history:
            recent = conversation_history[-4:]  # Last 2 user/assistant pairs
            for msg in recent:
                if msg.get("role") == "user":
                    content = msg.get("content", "")[:100]
                    if content and content != query:
                        parts.append(f"Related: {content}")

        enhanced = " | ".join(parts)
        return enhanced[:2000]  # Limit for embedding

    def _process_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process raw search results into structured atom list.

        Extracts:
        - atom_id, title, content, source_url
        - similarity score
        - manufacturer, model, type
        """
        atoms = []
        for result in results:
            atom = {
                "atom_id": result.get("atom_id"),
                "title": result.get("title", ""),
                "content": result.get("content", ""),
                "source_url": result.get("source_url"),
                "similarity": result.get("similarity_score", 0.0),
                "confidence": result.get("confidence", 0.0),
                "manufacturer": result.get("manufacturer"),
                "model": result.get("model"),
                "type": result.get("type"),
            }
            atoms.append(atom)
        return atoms

    def _format_context(
        self,
        atoms: List[Dict[str, Any]],
        manufacturer: Optional[str] = None
    ) -> str:
        """
        Format atoms as structured context string for LLM prompt.

        Returns Markdown-formatted context with:
        - Knowledge base header
        - Numbered atoms with title, content, source
        - Confidence indicators
        """
        if not atoms:
            return self._format_no_context()

        header = f"## Relevant Knowledge Base Context"
        if manufacturer:
            header += f" ({manufacturer.upper()})"
        header += "\n\n"

        entries = []
        for i, atom in enumerate(atoms, 1):
            # Confidence emoji
            sim = atom.get("similarity", 0)
            conf_indicator = "[HIGH]" if sim >= 0.85 else "[MEDIUM]" if sim >= 0.70 else "[LOW]"

            entry = f"### {i}. {atom['title']} {conf_indicator}\n"
            entry += f"{atom['content'][:500]}..."  # Truncate long content
            if atom.get("source_url"):
                entry += f"\n*Source: {atom['source_url']}*"
            entries.append(entry)

        return header + "\n\n".join(entries)

    def _format_no_context(self) -> str:
        """Return message when no relevant context found."""
        return (
            "## Knowledge Base Context\n\n"
            "*No directly relevant knowledge atoms found. "
            "Responding based on general expertise.*"
        )

    def build_rag_context(
        self,
        atoms: List[Dict[str, Any]],
        formatted_context: str
    ) -> RAGContext:
        """
        Build RAGContext Pydantic model from results.

        Args:
            atoms: List of processed atom dicts
            formatted_context: Formatted context string

        Returns:
            RAGContext model for chat response
        """
        atom_ids = [
            atom["atom_id"] for atom in atoms
            if atom.get("atom_id")
        ]

        top_confidence = max(
            (atom.get("similarity", 0) for atom in atoms),
            default=0.0
        )

        return RAGContext(
            atoms=atoms,
            formatted_context=formatted_context,
            top_confidence=top_confidence,
            atom_ids=atom_ids
        )

    async def increment_atom_usage(self, atom_ids: List[UUID]) -> None:
        """
        Increment usage count for atoms that were used in response.

        Args:
            atom_ids: List of atom UUIDs to increment
        """
        for atom_id in atom_ids:
            try:
                await self.knowledge_service.increment_usage(atom_id)
            except Exception as e:
                logger.warning(f"Failed to increment usage for {atom_id}: {e}")


# ===== Helper Functions =====

def calculate_rag_confidence(atoms: List[Dict[str, Any]]) -> float:
    """
    Calculate overall RAG confidence from atom similarities.

    Formula: (top_similarity * 0.6) + (avg_top3_similarity * 0.4)

    Args:
        atoms: List of atoms with similarity scores

    Returns:
        Confidence score (0.0-1.0)
    """
    if not atoms:
        return 0.0

    similarities = [atom.get("similarity", 0) for atom in atoms]
    top_similarity = max(similarities)

    # Average of top 3 (or all if fewer)
    top3 = sorted(similarities, reverse=True)[:3]
    avg_top3 = sum(top3) / len(top3) if top3 else 0.0

    confidence = (top_similarity * 0.6) + (avg_top3 * 0.4)
    return round(min(confidence, 1.0), 3)


def extract_sources_from_atoms(atoms: List[Dict[str, Any]]) -> List[str]:
    """
    Extract source citations from atoms.

    Args:
        atoms: List of atoms with source_url and title

    Returns:
        List of formatted source strings
    """
    sources = []
    for atom in atoms:
        if atom.get("source_url"):
            title = atom.get("title", "Unknown")
            sources.append(f"{title} - {atom['source_url']}")
        elif atom.get("title"):
            sources.append(atom["title"])
    return sources[:5]  # Limit to 5 sources


__all__ = [
    "SMERagService",
    "calculate_rag_confidence",
    "extract_sources_from_atoms",
]
