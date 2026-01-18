"""
Manual RAG Service

Retrieves relevant manual chunks using vector similarity search.
Formats retrieved chunks with citations for LLM prompts.

Uses:
- EmbeddingService for query embedding generation
- manual_chunks table with pgvector for similarity search
- Page number and section title for citations
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

import asyncpg

from rivet.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class ManualChunkResult:
    """A retrieved chunk with similarity score."""
    chunk_id: UUID
    manual_id: UUID
    content: str
    page_number: int
    section_title: Optional[str]
    keywords: List[str]
    similarity: float  # 0.0 to 1.0, higher = more similar

    @property
    def citation(self) -> str:
        """Format citation string."""
        if self.section_title:
            return f"Page {self.page_number}, Section: {self.section_title}"
        return f"Page {self.page_number}"


@dataclass
class Citation:
    """A citation reference for the response."""
    page: int
    section: Optional[str] = None
    text_preview: str = ""
    confidence: float = 0.0


@dataclass
class RAGResult:
    """Result of RAG retrieval."""
    chunks: List[ManualChunkResult]
    formatted_context: str
    citations: List[Citation]
    top_similarity: float
    query_tokens_used: int = 0


class ManualRAGService:
    """
    RAG service for manual chunk retrieval.

    Features:
    - Vector similarity search with pgvector
    - Optional manual/manufacturer filtering
    - Citation formatting with page numbers
    - Query enhancement from conversation history
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Initialize RAG service.

        Args:
            db_pool: Database connection pool
            embedding_service: EmbeddingService instance. Created if None.
        """
        self.db_pool = db_pool
        self.embedding_service = embedding_service or EmbeddingService()

        logger.info("ManualRAGService initialized")

    async def retrieve_context(
        self,
        query: str,
        manual_id: Optional[UUID] = None,
        manufacturer: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.5,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> RAGResult:
        """
        Retrieve relevant manual chunks for a query.

        Args:
            query: User's question
            manual_id: Filter to specific manual (None = search all)
            manufacturer: Filter by manufacturer name (None = search all)
            top_k: Maximum chunks to return
            min_similarity: Minimum similarity score (0.0-1.0)
            conversation_history: Previous messages for query enhancement

        Returns:
            RAGResult with chunks, formatted context, and citations

        Example:
            result = await rag_service.retrieve_context(
                query="How do I reset to factory settings?",
                manual_id=some_uuid,
                top_k=5
            )
            context = result.formatted_context
        """
        logger.info(
            f"[Manual RAG] Query: {query[:50]}... | "
            f"manual_id={manual_id} | top_k={top_k}"
        )

        # Step 1: Enhance query with conversation context
        enhanced_query = self._enhance_query(query, conversation_history)

        # Step 2: Generate query embedding
        try:
            query_embedding = await self.embedding_service.generate_embedding(
                enhanced_query
            )
        except Exception as e:
            logger.error(f"[Manual RAG] Embedding failed: {e}")
            return self._empty_result()

        # Step 3: Vector search
        chunks = await self._vector_search(
            query_embedding=query_embedding,
            manual_id=manual_id,
            manufacturer=manufacturer,
            top_k=top_k,
            min_similarity=min_similarity
        )

        if not chunks:
            logger.info("[Manual RAG] No chunks found above threshold")
            return self._empty_result()

        # Step 4: Format results
        formatted_context = self._format_context(chunks)
        citations = self._extract_citations(chunks)
        top_similarity = max(c.similarity for c in chunks)

        logger.info(
            f"[Manual RAG] Retrieved {len(chunks)} chunks "
            f"(top similarity: {top_similarity:.2f})"
        )

        return RAGResult(
            chunks=chunks,
            formatted_context=formatted_context,
            citations=citations,
            top_similarity=top_similarity
        )

    async def _vector_search(
        self,
        query_embedding: List[float],
        manual_id: Optional[UUID],
        manufacturer: Optional[str],
        top_k: int,
        min_similarity: float
    ) -> List[ManualChunkResult]:
        """
        Execute vector similarity search against manual_chunks.

        Uses pgvector cosine distance: 1 - (embedding <=> query)
        """
        try:
            # Build embedding string for pgvector
            embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

            # Build query based on filters
            if manual_id:
                # Search specific manual
                query = """
                    SELECT
                        mc.id as chunk_id,
                        mc.manual_id,
                        mc.content,
                        mc.page_number,
                        mc.section_title,
                        mc.keywords,
                        1 - (mc.embedding <=> $1::vector) as similarity
                    FROM manual_chunks mc
                    WHERE mc.manual_id = $2
                      AND mc.embedding IS NOT NULL
                    ORDER BY mc.embedding <=> $1::vector
                    LIMIT $3
                """
                params = [embedding_str, manual_id, top_k]

            elif manufacturer:
                # Search by manufacturer (join through equipment_models)
                query = """
                    SELECT
                        mc.id as chunk_id,
                        mc.manual_id,
                        mc.content,
                        mc.page_number,
                        mc.section_title,
                        mc.keywords,
                        1 - (mc.embedding <=> $1::vector) as similarity
                    FROM manual_chunks mc
                    JOIN manuals m ON mc.manual_id = m.id
                    JOIN equipment_models em ON m.equipment_model_id = em.id
                    JOIN manufacturers mfr ON em.manufacturer_id = mfr.id
                    WHERE LOWER(mfr.name) = LOWER($2)
                      AND mc.embedding IS NOT NULL
                    ORDER BY mc.embedding <=> $1::vector
                    LIMIT $3
                """
                params = [embedding_str, manufacturer, top_k]

            else:
                # Search all manuals
                query = """
                    SELECT
                        mc.id as chunk_id,
                        mc.manual_id,
                        mc.content,
                        mc.page_number,
                        mc.section_title,
                        mc.keywords,
                        1 - (mc.embedding <=> $1::vector) as similarity
                    FROM manual_chunks mc
                    WHERE mc.embedding IS NOT NULL
                    ORDER BY mc.embedding <=> $1::vector
                    LIMIT $2
                """
                params = [embedding_str, top_k]

            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)

            # Filter by minimum similarity and convert to results
            chunks = []
            for row in rows:
                similarity = row['similarity']
                if similarity >= min_similarity:
                    chunks.append(ManualChunkResult(
                        chunk_id=row['chunk_id'],
                        manual_id=row['manual_id'],
                        content=row['content'],
                        page_number=row['page_number'] or 1,
                        section_title=row['section_title'],
                        keywords=row['keywords'] or [],
                        similarity=similarity
                    ))

            return chunks

        except Exception as e:
            logger.error(f"[Manual RAG] Vector search failed: {e}")
            return []

    def _enhance_query(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> str:
        """
        Enhance query with conversation context for better retrieval.

        Adds recent topics from conversation to improve embedding relevance.
        """
        if not conversation_history:
            return query

        parts = [query]

        # Add context from last 2 user messages
        recent_user_msgs = [
            msg for msg in conversation_history[-4:]
            if msg.get("role") == "user"
        ]

        for msg in recent_user_msgs:
            content = msg.get("content", "")[:100]
            if content and content != query:
                parts.append(f"Context: {content}")

        enhanced = " | ".join(parts)
        return enhanced[:2000]  # Limit for embedding

    def _format_context(self, chunks: List[ManualChunkResult]) -> str:
        """
        Format chunks as structured context for LLM prompt.

        Returns Markdown-formatted context with citations.
        """
        if not chunks:
            return self._no_context_message()

        lines = ["## Relevant Manual Sections\n"]

        for i, chunk in enumerate(chunks, 1):
            # Confidence indicator
            if chunk.similarity >= 0.85:
                conf = "[HIGH CONFIDENCE]"
            elif chunk.similarity >= 0.70:
                conf = "[MEDIUM CONFIDENCE]"
            else:
                conf = "[LOW CONFIDENCE]"

            # Section header with citation
            lines.append(f"### {i}. {chunk.citation} {conf}")
            lines.append("")

            # Content (truncate if very long)
            content = chunk.content
            if len(content) > 1500:
                content = content[:1500] + "..."

            lines.append(content)
            lines.append("")

            # Keywords if present
            if chunk.keywords:
                lines.append(f"*Keywords: {', '.join(chunk.keywords[:5])}*")
                lines.append("")

        return "\n".join(lines)

    def _extract_citations(self, chunks: List[ManualChunkResult]) -> List[Citation]:
        """Extract citation objects from chunks."""
        citations = []
        for chunk in chunks:
            citations.append(Citation(
                page=chunk.page_number,
                section=chunk.section_title,
                text_preview=chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content,
                confidence=chunk.similarity
            ))
        return citations

    def _empty_result(self) -> RAGResult:
        """Return empty result when no context found."""
        return RAGResult(
            chunks=[],
            formatted_context=self._no_context_message(),
            citations=[],
            top_similarity=0.0
        )

    def _no_context_message(self) -> str:
        """Message when no relevant context found."""
        return (
            "## Manual Context\n\n"
            "*No directly relevant sections found in the manual. "
            "Please try rephrasing your question or provide more specific details.*"
        )

    async def get_surrounding_chunks(
        self,
        chunk_id: UUID,
        window: int = 1
    ) -> List[ManualChunkResult]:
        """
        Get chunks before and after a specific chunk for expanded context.

        Args:
            chunk_id: The center chunk
            window: Number of chunks before/after to retrieve

        Returns:
            List of surrounding chunks (including center)
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get the center chunk info
                center = await conn.fetchrow(
                    "SELECT manual_id, chunk_index FROM manual_chunks WHERE id = $1",
                    chunk_id
                )

                if not center:
                    return []

                # Get surrounding chunks
                rows = await conn.fetch(
                    """
                    SELECT
                        id as chunk_id,
                        manual_id,
                        content,
                        page_number,
                        section_title,
                        keywords,
                        chunk_index
                    FROM manual_chunks
                    WHERE manual_id = $1
                      AND chunk_index BETWEEN $2 AND $3
                    ORDER BY chunk_index
                    """,
                    center['manual_id'],
                    center['chunk_index'] - window,
                    center['chunk_index'] + window
                )

                return [
                    ManualChunkResult(
                        chunk_id=row['chunk_id'],
                        manual_id=row['manual_id'],
                        content=row['content'],
                        page_number=row['page_number'] or 1,
                        section_title=row['section_title'],
                        keywords=row['keywords'] or [],
                        similarity=1.0  # Exact match for context expansion
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to get surrounding chunks: {e}")
            return []


# ===== Helper Functions =====

def calculate_rag_confidence(chunks: List[ManualChunkResult]) -> float:
    """
    Calculate overall RAG confidence from chunk similarities.

    Formula: (top_similarity * 0.6) + (avg_top3_similarity * 0.4)

    Args:
        chunks: List of chunks with similarity scores

    Returns:
        Confidence score (0.0-1.0)
    """
    if not chunks:
        return 0.0

    similarities = [chunk.similarity for chunk in chunks]
    top_similarity = max(similarities)

    # Average of top 3 (or all if fewer)
    top3 = sorted(similarities, reverse=True)[:3]
    avg_top3 = sum(top3) / len(top3) if top3 else 0.0

    confidence = (top_similarity * 0.6) + (avg_top3 * 0.4)
    return round(min(confidence, 1.0), 3)


def format_citations_for_response(citations: List[Citation]) -> str:
    """
    Format citations as a readable list for inclusion in response.

    Returns:
        Markdown-formatted citation list
    """
    if not citations:
        return ""

    lines = ["\n---\n**Sources:**"]
    for i, cit in enumerate(citations, 1):
        if cit.section:
            lines.append(f"- Page {cit.page}, {cit.section}")
        else:
            lines.append(f"- Page {cit.page}")

    return "\n".join(lines)


__all__ = [
    "ManualRAGService",
    "ManualChunkResult",
    "Citation",
    "RAGResult",
    "calculate_rag_confidence",
    "format_citations_for_response",
]
