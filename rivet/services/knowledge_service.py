"""
Knowledge Service

Service layer for managing knowledge atoms and knowledge gaps.
Provides CRUD operations, vector search, and gap detection for the 4-route orchestrator.

Based on:
- Database schema: migrations/009_knowledge_atoms.sql
- Data models: rivet/models/knowledge.py
- Routing spec: rivet_pro_skill_ai_routing.md
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from rivet.atlas.database import AtlasDatabase
from rivet.models.knowledge import (
    KnowledgeAtom,
    KnowledgeAtomCreate,
    KnowledgeAtomUpdate,
    KnowledgeGap,
    KnowledgeGapCreate,
    KnowledgeGapUpdate,
    KnowledgeSearchResult,
    AtomType,
    ResearchStatus
)

logger = logging.getLogger(__name__)


class KnowledgeService:
    """
    Service for managing knowledge atoms and gaps.

    Features:
    - Create, read, update knowledge atoms
    - Vector similarity search with pgvector
    - Knowledge gap tracking and prioritization
    - Research queue management
    - Usage statistics tracking
    """

    def __init__(self, db: Optional[AtlasDatabase] = None):
        """
        Initialize knowledge service.

        Args:
            db: AtlasDatabase instance. If None, creates new instance.
        """
        self.db = db or AtlasDatabase()

    # ===== Knowledge Atom Operations =====

    async def create_atom(
        self,
        atom: KnowledgeAtomCreate,
        embedding: List[float]
    ) -> UUID:
        """
        Create new knowledge atom with embedding.

        Args:
            atom: Atom data (Pydantic model)
            embedding: Vector embedding (1536 dimensions for OpenAI text-embedding-3-small)

        Returns:
            UUID of created atom

        Example:
            atom_id = await knowledge_service.create_atom(
                KnowledgeAtomCreate(
                    type="fault",
                    manufacturer="Siemens",
                    title="F0002 - Overvoltage",
                    content="...",
                    confidence=0.95
                ),
                embedding=[0.123, -0.456, ...]  # 1536 dims
            )
        """
        # Validate embedding dimensions
        if len(embedding) != 1536:
            raise ValueError(f"Embedding must be 1536 dimensions, got {len(embedding)}")

        query = """
            INSERT INTO knowledge_atoms (
                type, manufacturer, model, equipment_type,
                title, content, source_url,
                confidence, human_verified, embedding
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::vector)
            RETURNING atom_id
        """

        result = await self.db.fetch_one(
            query,
            atom.type.value,
            atom.manufacturer,
            atom.model,
            atom.equipment_type,
            atom.title,
            atom.content,
            atom.source_url,
            atom.confidence,
            atom.human_verified,
            str(embedding)  # pgvector accepts string representation
        )

        atom_id = result['atom_id']
        logger.info(f"Created knowledge atom: {atom_id} ({atom.type}, {atom.title[:50]})")
        return atom_id

    async def get_atom(self, atom_id: UUID) -> Optional[KnowledgeAtom]:
        """
        Get knowledge atom by ID (without embedding).

        Args:
            atom_id: Atom UUID

        Returns:
            KnowledgeAtom or None if not found
        """
        query = """
            SELECT
                atom_id, type, manufacturer, model, equipment_type,
                title, content, source_url,
                confidence, human_verified, usage_count,
                created_at, last_verified
            FROM knowledge_atoms
            WHERE atom_id = $1
        """

        result = await self.db.fetch_one(query, atom_id)
        if not result:
            return None

        return KnowledgeAtom(**result)

    async def update_atom(
        self,
        atom_id: UUID,
        updates: KnowledgeAtomUpdate
    ) -> bool:
        """
        Update knowledge atom.

        Args:
            atom_id: Atom UUID
            updates: Fields to update (only provided fields are updated)

        Returns:
            True if updated, False if atom not found
        """
        # Build dynamic UPDATE query for provided fields only
        update_fields = updates.model_dump(exclude_unset=True)
        if not update_fields:
            return True  # No updates

        set_clauses = []
        params = []
        param_index = 1

        for field, value in update_fields.items():
            set_clauses.append(f"{field} = ${param_index}")
            params.append(value.value if hasattr(value, 'value') else value)
            param_index += 1

        params.append(atom_id)
        query = f"""
            UPDATE knowledge_atoms
            SET {', '.join(set_clauses)}
            WHERE atom_id = ${param_index}
            RETURNING atom_id
        """

        result = await self.db.fetch_one(query, *params)
        if result:
            logger.info(f"Updated atom: {atom_id}")
            return True
        return False

    async def increment_usage(self, atom_id: UUID) -> None:
        """
        Increment usage count for an atom (called when atom is returned to user).

        Args:
            atom_id: Atom UUID
        """
        query = """
            UPDATE knowledge_atoms
            SET usage_count = usage_count + 1
            WHERE atom_id = $1
        """
        await self.db.execute(query, atom_id, fetch_mode="none")

    async def vector_search(
        self,
        query_embedding: List[float],
        manufacturer: Optional[str] = None,
        equipment_type: Optional[str] = None,
        atom_types: Optional[List[AtomType]] = None,
        min_confidence: float = 0.0,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic vector search using pgvector cosine similarity.

        Args:
            query_embedding: Query vector (1536 dimensions)
            manufacturer: Optional manufacturer filter
            equipment_type: Optional equipment type filter
            atom_types: Optional list of atom types to search (e.g., ['fault', 'procedure'])
            min_confidence: Minimum confidence threshold (default 0.0)
            limit: Maximum results to return (default 5)

        Returns:
            List of dicts with atom data + similarity_score

        Example:
            results = await knowledge_service.vector_search(
                query_embedding=[0.1, -0.2, ...],
                manufacturer="Siemens",
                atom_types=[AtomType.FAULT],
                limit=3
            )
            # [{'atom_id': '...', 'title': '...', 'similarity_score': 0.92}, ...]
        """
        # Validate embedding dimensions
        if len(query_embedding) != 1536:
            raise ValueError(f"Query embedding must be 1536 dimensions, got {len(query_embedding)}")

        # Build dynamic WHERE clause
        where_clauses = ["confidence >= $2"]
        params = [str(query_embedding), min_confidence]
        param_index = 3

        if manufacturer:
            where_clauses.append(f"manufacturer = ${param_index}")
            params.append(manufacturer)
            param_index += 1

        if equipment_type:
            where_clauses.append(f"equipment_type = ${param_index}")
            params.append(equipment_type)
            param_index += 1

        if atom_types:
            placeholders = ", ".join([f"${i}" for i in range(param_index, param_index + len(atom_types))])
            where_clauses.append(f"type IN ({placeholders})")
            params.extend([t.value for t in atom_types])
            param_index += len(atom_types)

        where_clause = " AND ".join(where_clauses)

        # Add limit parameter
        params.append(limit)

        # Vector search query with cosine similarity
        # Lower distance = higher similarity (we'll convert to similarity_score below)
        query = f"""
            SELECT
                atom_id, type, manufacturer, model, equipment_type,
                title, content, source_url,
                confidence, human_verified, usage_count,
                created_at, last_verified,
                (1 - (embedding <=> $1::vector)) AS similarity_score
            FROM knowledge_atoms
            WHERE {where_clause}
            ORDER BY embedding <=> $1::vector
            LIMIT ${param_index}
        """

        results = await self.db.fetch_all(query, *params)
        logger.info(f"Vector search returned {len(results)} results (limit={limit})")

        return results

    # ===== Knowledge Gap Operations =====

    async def create_or_update_gap(
        self,
        gap: KnowledgeGapCreate
    ) -> UUID:
        """
        Create new knowledge gap or increment occurrence_count if duplicate.

        Uses unique index on (query, manufacturer, model) for pending gaps.

        Args:
            gap: Gap data (Pydantic model)

        Returns:
            UUID of created/updated gap
        """
        # First, try to find existing pending gap with same query/manufacturer/model
        existing = await self.db.fetch_one(
            """
            SELECT gap_id, occurrence_count
            FROM knowledge_gaps
            WHERE query = $1
              AND COALESCE(manufacturer, '') = COALESCE($2, '')
              AND COALESCE(model, '') = COALESCE($3, '')
              AND research_status = 'pending'
            """,
            gap.query,
            gap.manufacturer,
            gap.model
        )

        if existing:
            # Increment occurrence count (priority auto-updates via trigger)
            gap_id = existing['gap_id']
            new_count = existing['occurrence_count'] + 1

            await self.db.execute(
                """
                UPDATE knowledge_gaps
                SET occurrence_count = $1
                WHERE gap_id = $2
                """,
                new_count,
                gap_id,
                fetch_mode="none"
            )
            logger.info(f"Incremented gap occurrence: {gap_id} (count={new_count})")
            return gap_id

        # Create new gap (priority auto-calculated via trigger)
        result = await self.db.fetch_one(
            """
            INSERT INTO knowledge_gaps (
                query, manufacturer, model, confidence_score, research_status
            )
            VALUES ($1, $2, $3, $4, $5)
            RETURNING gap_id
            """,
            gap.query,
            gap.manufacturer,
            gap.model,
            gap.confidence_score,
            gap.research_status.value
        )

        gap_id = result['gap_id']
        logger.info(f"Created knowledge gap: {gap_id} (query: {gap.query[:50]})")
        return gap_id

    async def get_pending_research_queue(
        self,
        limit: int = 10
    ) -> List[KnowledgeGap]:
        """
        Get high-priority pending/in_progress gaps for research worker.

        Args:
            limit: Maximum gaps to return (default 10)

        Returns:
            List of KnowledgeGap sorted by priority DESC
        """
        query = """
            SELECT
                gap_id, query, manufacturer, model, confidence_score,
                occurrence_count, priority, research_status,
                resolved_atom_id, created_at, resolved_at
            FROM knowledge_gaps
            WHERE research_status IN ('pending', 'in_progress')
            ORDER BY priority DESC, created_at ASC
            LIMIT $1
        """

        results = await self.db.fetch_all(query, limit)
        return [KnowledgeGap(**row) for row in results]

    async def mark_gap_resolved(
        self,
        gap_id: UUID,
        atom_id: UUID
    ) -> None:
        """
        Mark knowledge gap as completed with resolved atom.

        Args:
            gap_id: Gap UUID
            atom_id: Atom UUID that fills this gap
        """
        query = """
            UPDATE knowledge_gaps
            SET research_status = 'completed',
                resolved_atom_id = $1,
                resolved_at = NOW()
            WHERE gap_id = $2
        """
        await self.db.execute(query, atom_id, gap_id, fetch_mode="none")
        logger.info(f"Marked gap resolved: {gap_id} -> atom {atom_id}")

    async def update_gap_status(
        self,
        gap_id: UUID,
        status: ResearchStatus
    ) -> None:
        """
        Update research status for a gap.

        Args:
            gap_id: Gap UUID
            status: New research status
        """
        query = """
            UPDATE knowledge_gaps
            SET research_status = $1
            WHERE gap_id = $2
        """
        await self.db.execute(query, status.value, gap_id, fetch_mode="none")

    # ===== Statistics =====

    async def count_atoms(self) -> int:
        """Get total count of knowledge atoms."""
        result = await self.db.fetch_one("SELECT COUNT(*) as count FROM knowledge_atoms")
        return result['count']

    async def count_verified_atoms(self) -> int:
        """Get count of human-verified atoms."""
        result = await self.db.fetch_one(
            "SELECT COUNT(*) as count FROM knowledge_atoms WHERE human_verified = TRUE"
        )
        return result['count']

    async def count_pending_gaps(self) -> int:
        """Get count of pending research gaps."""
        result = await self.db.fetch_one(
            "SELECT COUNT(*) as count FROM knowledge_gaps WHERE research_status = 'pending'"
        )
        return result['count']

    async def avg_atom_confidence(self) -> float:
        """Get average confidence score across all atoms."""
        result = await self.db.fetch_one(
            "SELECT AVG(confidence) as avg_confidence FROM knowledge_atoms"
        )
        return round(result['avg_confidence'] or 0.0, 3)

    async def get_top_atoms_by_usage(self, limit: int = 10) -> List[KnowledgeAtom]:
        """
        Get most frequently used atoms.

        Args:
            limit: Number of atoms to return

        Returns:
            List of KnowledgeAtom sorted by usage_count DESC
        """
        query = """
            SELECT
                atom_id, type, manufacturer, model, equipment_type,
                title, content, source_url,
                confidence, human_verified, usage_count,
                created_at, last_verified
            FROM knowledge_atoms
            WHERE usage_count > 0
            ORDER BY usage_count DESC, confidence DESC
            LIMIT $1
        """
        results = await self.db.fetch_all(query, limit)
        return [KnowledgeAtom(**row) for row in results]
