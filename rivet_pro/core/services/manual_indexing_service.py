"""
Manual Indexing Service

Processes PDFs and stores chunks with embeddings in the database.
Handles batch embedding generation and database insertion.

Uses:
- PDFChunkerService for text extraction and chunking
- EmbeddingService for vector embedding generation
- manual_chunks table for storage (from migration 002)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID

import asyncpg

from rivet_pro.core.services.pdf_chunker_service import PDFChunkerService, ManualChunk
from rivet.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class IndexingResult:
    """Result of manual indexing operation."""
    manual_id: UUID
    chunks_created: int
    chunks_failed: int
    total_chars: int
    total_tokens_estimated: int
    duration_seconds: float
    success: bool
    error: Optional[str] = None


@dataclass
class IndexingStatus:
    """Current indexing status for a manual."""
    manual_id: UUID
    is_indexed: bool
    chunk_count: int
    indexed_at: Optional[datetime] = None
    embedding_model: Optional[str] = None


class ManualIndexingService:
    """
    Service for indexing PDF manuals into vector database.

    Features:
    - PDF to chunks with PDFChunkerService
    - Batch embedding generation
    - Upsert to manual_chunks table
    - Progress tracking and error handling
    """

    EMBEDDING_MODEL = "text-embedding-3-small"
    BATCH_SIZE = 50  # Chunks per embedding batch

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        embedding_service: Optional[EmbeddingService] = None,
        chunker: Optional[PDFChunkerService] = None
    ):
        """
        Initialize indexing service.

        Args:
            db_pool: Database connection pool
            embedding_service: EmbeddingService instance. Created if None.
            chunker: PDFChunkerService instance. Created if None.
        """
        self.db_pool = db_pool
        self.embedding_service = embedding_service or EmbeddingService()
        self.chunker = chunker or PDFChunkerService()

        logger.info("ManualIndexingService initialized")

    async def index_manual(
        self,
        manual_id: UUID,
        pdf_path: str,
        max_pages: int = 100
    ) -> IndexingResult:
        """
        Index a PDF manual: extract text, chunk, embed, and store.

        Args:
            manual_id: UUID of the manual record in manuals table
            pdf_path: Path to the PDF file
            max_pages: Maximum pages to process

        Returns:
            IndexingResult with statistics
        """
        start_time = datetime.utcnow()
        logger.info(f"[Index] Starting manual indexing | manual_id={manual_id}")

        try:
            # Step 1: Verify manual exists
            manual = await self._get_manual(manual_id)
            if not manual:
                return IndexingResult(
                    manual_id=manual_id,
                    chunks_created=0,
                    chunks_failed=0,
                    total_chars=0,
                    total_tokens_estimated=0,
                    duration_seconds=0,
                    success=False,
                    error=f"Manual not found: {manual_id}"
                )

            # Step 2: Chunk PDF
            chunks = await self.chunker.chunk_pdf(pdf_path, max_pages)
            if not chunks:
                return IndexingResult(
                    manual_id=manual_id,
                    chunks_created=0,
                    chunks_failed=0,
                    total_chars=0,
                    total_tokens_estimated=0,
                    duration_seconds=0,
                    success=False,
                    error="No text extracted from PDF"
                )

            logger.info(f"[Index] Extracted {len(chunks)} chunks from PDF")

            # Step 3: Generate embeddings in batches
            chunks_with_embeddings = await self._generate_embeddings_batch(chunks)

            # Step 4: Store chunks in database
            created, failed = await self._store_chunks(manual_id, chunks_with_embeddings)

            # Step 5: Update manual record
            await self._mark_indexed(manual_id)

            # Calculate stats
            duration = (datetime.utcnow() - start_time).total_seconds()
            total_chars = sum(len(c.content) for c in chunks)
            total_tokens = total_chars // 4

            result = IndexingResult(
                manual_id=manual_id,
                chunks_created=created,
                chunks_failed=failed,
                total_chars=total_chars,
                total_tokens_estimated=total_tokens,
                duration_seconds=duration,
                success=True
            )

            logger.info(
                f"[Index] Complete | manual_id={manual_id} | "
                f"chunks={created} | duration={duration:.1f}s"
            )

            return result

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"[Index] Failed | manual_id={manual_id} | error={e}")

            return IndexingResult(
                manual_id=manual_id,
                chunks_created=0,
                chunks_failed=0,
                total_chars=0,
                total_tokens_estimated=0,
                duration_seconds=duration,
                success=False,
                error=str(e)
            )

    async def reindex_manual(self, manual_id: UUID) -> IndexingResult:
        """
        Re-index a manual by deleting existing chunks and re-processing.

        Args:
            manual_id: UUID of the manual

        Returns:
            IndexingResult
        """
        # Get manual file path
        manual = await self._get_manual(manual_id)
        if not manual:
            return IndexingResult(
                manual_id=manual_id,
                chunks_created=0,
                chunks_failed=0,
                total_chars=0,
                total_tokens_estimated=0,
                duration_seconds=0,
                success=False,
                error=f"Manual not found: {manual_id}"
            )

        file_url = manual.get('file_url')
        if not file_url or not Path(file_url).exists():
            return IndexingResult(
                manual_id=manual_id,
                chunks_created=0,
                chunks_failed=0,
                total_chars=0,
                total_tokens_estimated=0,
                duration_seconds=0,
                success=False,
                error=f"PDF file not found: {file_url}"
            )

        # Delete existing chunks
        deleted = await self.delete_manual_chunks(manual_id)
        logger.info(f"[Reindex] Deleted {deleted} existing chunks")

        # Re-index
        return await self.index_manual(manual_id, file_url)

    async def delete_manual_chunks(self, manual_id: UUID) -> int:
        """
        Delete all chunks for a manual.

        Args:
            manual_id: UUID of the manual

        Returns:
            Number of chunks deleted
        """
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM manual_chunks WHERE manual_id = $1",
                    manual_id
                )
                # Parse "DELETE N" response
                deleted = int(result.split()[-1])
                logger.info(f"Deleted {deleted} chunks for manual {manual_id}")
                return deleted

        except Exception as e:
            logger.error(f"Failed to delete chunks: {e}")
            return 0

    async def get_indexing_status(self, manual_id: UUID) -> Optional[IndexingStatus]:
        """
        Get indexing status for a manual.

        Args:
            manual_id: UUID of the manual

        Returns:
            IndexingStatus or None if manual not found
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get manual info
                manual = await conn.fetchrow(
                    """
                    SELECT id, indexed_at, embedding_model
                    FROM manuals WHERE id = $1
                    """,
                    manual_id
                )

                if not manual:
                    return None

                # Count chunks
                chunk_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM manual_chunks WHERE manual_id = $1",
                    manual_id
                )

                return IndexingStatus(
                    manual_id=manual_id,
                    is_indexed=manual['indexed_at'] is not None,
                    chunk_count=chunk_count or 0,
                    indexed_at=manual['indexed_at'],
                    embedding_model=manual['embedding_model']
                )

        except Exception as e:
            logger.error(f"Failed to get indexing status: {e}")
            return None

    async def _get_manual(self, manual_id: UUID) -> Optional[Dict[str, Any]]:
        """Get manual record from database."""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM manuals WHERE id = $1",
                    manual_id
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get manual: {e}")
            return None

    async def _generate_embeddings_batch(
        self,
        chunks: List[ManualChunk]
    ) -> List[tuple]:
        """
        Generate embeddings for chunks in batches.

        Returns:
            List of (chunk, embedding) tuples
        """
        results = []
        texts = [chunk.content for chunk in chunks]

        # Process in batches
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch_texts = texts[i:i + self.BATCH_SIZE]
            batch_chunks = chunks[i:i + self.BATCH_SIZE]

            logger.debug(
                f"[Index] Embedding batch {i // self.BATCH_SIZE + 1}/"
                f"{(len(texts) + self.BATCH_SIZE - 1) // self.BATCH_SIZE}"
            )

            try:
                embeddings = await self.embedding_service.generate_batch_embeddings(
                    batch_texts
                )

                for chunk, embedding in zip(batch_chunks, embeddings):
                    results.append((chunk, embedding))

            except Exception as e:
                logger.error(f"Embedding batch failed: {e}")
                # Add chunks with None embeddings for failed batch
                for chunk in batch_chunks:
                    results.append((chunk, None))

        return results

    async def _store_chunks(
        self,
        manual_id: UUID,
        chunks_with_embeddings: List[tuple]
    ) -> tuple:
        """
        Store chunks in database.

        Returns:
            (created_count, failed_count)
        """
        created = 0
        failed = 0

        try:
            async with self.db_pool.acquire() as conn:
                # Use a transaction for batch insert
                async with conn.transaction():
                    for chunk, embedding in chunks_with_embeddings:
                        if embedding is None:
                            failed += 1
                            continue

                        try:
                            # Convert embedding list to pgvector format
                            embedding_str = f"[{','.join(str(x) for x in embedding)}]"

                            await conn.execute(
                                """
                                INSERT INTO manual_chunks (
                                    manual_id, content, page_number, chunk_index,
                                    embedding, section_title, keywords
                                ) VALUES ($1, $2, $3, $4, $5::vector, $6, $7)
                                ON CONFLICT (manual_id, chunk_index)
                                DO UPDATE SET
                                    content = EXCLUDED.content,
                                    page_number = EXCLUDED.page_number,
                                    embedding = EXCLUDED.embedding,
                                    section_title = EXCLUDED.section_title,
                                    keywords = EXCLUDED.keywords
                                """,
                                manual_id,
                                chunk.content,
                                chunk.page_number,
                                chunk.chunk_index,
                                embedding_str,
                                chunk.section_title,
                                chunk.keywords
                            )
                            created += 1

                        except Exception as e:
                            logger.warning(
                                f"Failed to store chunk {chunk.chunk_index}: {e}"
                            )
                            failed += 1

        except Exception as e:
            logger.error(f"Database transaction failed: {e}")
            failed = len(chunks_with_embeddings)

        return created, failed

    async def _mark_indexed(self, manual_id: UUID) -> None:
        """Mark manual as indexed in database."""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE manuals
                    SET indexed_at = NOW(),
                        embedding_model = $2
                    WHERE id = $1
                    """,
                    manual_id,
                    self.EMBEDDING_MODEL
                )
        except Exception as e:
            logger.warning(f"Failed to mark manual as indexed: {e}")


# ===== Helper Functions =====

async def index_pdf_directly(
    db_pool: asyncpg.Pool,
    pdf_path: str,
    title: str,
    source: str = "user_upload",
    equipment_model_id: Optional[UUID] = None
) -> IndexingResult:
    """
    Convenience function to index a PDF directly (creates manual record).

    Args:
        db_pool: Database connection pool
        pdf_path: Path to PDF file
        title: Manual title
        source: Source type ('user_upload', 'web_search', 'manufacturer')
        equipment_model_id: Optional link to equipment_models table

    Returns:
        IndexingResult
    """
    # Create manual record
    path = Path(pdf_path)
    if not path.exists():
        return IndexingResult(
            manual_id=UUID('00000000-0000-0000-0000-000000000000'),
            chunks_created=0,
            chunks_failed=0,
            total_chars=0,
            total_tokens_estimated=0,
            duration_seconds=0,
            success=False,
            error=f"PDF not found: {pdf_path}"
        )

    try:
        async with db_pool.acquire() as conn:
            manual_id = await conn.fetchval(
                """
                INSERT INTO manuals (
                    equipment_model_id, title, file_url,
                    file_size_bytes, source
                ) VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                equipment_model_id,
                title,
                str(path.absolute()),
                path.stat().st_size,
                source
            )

        # Index the manual
        indexer = ManualIndexingService(db_pool)
        return await indexer.index_manual(manual_id, pdf_path)

    except Exception as e:
        logger.error(f"Failed to create manual record: {e}")
        return IndexingResult(
            manual_id=UUID('00000000-0000-0000-0000-000000000000'),
            chunks_created=0,
            chunks_failed=0,
            total_chars=0,
            total_tokens_estimated=0,
            duration_seconds=0,
            success=False,
            error=str(e)
        )


__all__ = [
    "ManualIndexingService",
    "IndexingResult",
    "IndexingStatus",
    "index_pdf_directly",
]
