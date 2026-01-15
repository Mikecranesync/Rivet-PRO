"""
Semantic Search Service - AUTO-KB-008

Generate embeddings and perform semantic search over manual content.
Uses OpenAI embeddings or falls back to sentence-transformers.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

import asyncpg

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Try sentence-transformers as fallback
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


class SemanticSearchService:
    """
    Service for generating embeddings and semantic search.

    Uses OpenAI text-embedding-ada-002 by default (1536 dimensions).
    Falls back to sentence-transformers if OpenAI unavailable.
    """

    OPENAI_MODEL = "text-embedding-ada-002"
    OPENAI_DIMENSIONS = 1536

    # Sentence transformers model (fallback)
    ST_MODEL = "all-MiniLM-L6-v2"
    ST_DIMENSIONS = 384

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize semantic search service.

        Args:
            db_pool: Database connection pool
            openai_api_key: OpenAI API key (optional)
        """
        self.db_pool = db_pool
        self._st_model = None

        # Configure OpenAI if available
        if openai_api_key and HAS_OPENAI:
            openai.api_key = openai_api_key
            self.use_openai = True
            self.embedding_dim = self.OPENAI_DIMENSIONS
            logger.info("Using OpenAI embeddings")
        elif HAS_SENTENCE_TRANSFORMERS:
            self.use_openai = False
            self.embedding_dim = self.ST_DIMENSIONS
            logger.info("Using sentence-transformers embeddings")
        else:
            self.use_openai = False
            self.embedding_dim = 0
            logger.warning("No embedding provider available!")

    def _get_st_model(self):
        """Lazy load sentence-transformers model."""
        if self._st_model is None and HAS_SENTENCE_TRANSFORMERS:
            self._st_model = SentenceTransformer(self.ST_MODEL)
        return self._st_model

    async def generate_embedding(
        self,
        text: str,
        max_length: int = 8000
    ) -> Optional[List[float]]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed
            max_length: Maximum text length (truncate if longer)

        Returns:
            List of floats (embedding vector) or None
        """
        if not text:
            return None

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]

        try:
            if self.use_openai:
                return await self._openai_embedding(text)
            else:
                return self._st_embedding(text)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def _openai_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using OpenAI API."""
        try:
            response = await asyncio.to_thread(
                openai.Embedding.create,
                input=text,
                model=self.OPENAI_MODEL
            )
            return response['data'][0]['embedding']
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            return None

    def _st_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using sentence-transformers."""
        model = self._get_st_model()
        if model is None:
            return None

        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Sentence-transformers error: {e}")
            return None

    async def embed_manual(
        self,
        manufacturer: str,
        model: str,
        manual_type: str = "user_manual"
    ) -> bool:
        """
        Generate and store embedding for a manual.

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model
            manual_type: Type of manual

        Returns:
            True if successful
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get text content
                row = await conn.fetchrow(
                    """
                    SELECT text_content
                    FROM manual_files
                    WHERE LOWER(manufacturer) = LOWER($1)
                      AND LOWER(model) = LOWER($2)
                      AND manual_type = $3
                    """,
                    manufacturer,
                    model,
                    manual_type
                )

                if not row or not row['text_content']:
                    logger.warning(f"No text content for {manufacturer} {model}")
                    return False

                # Generate embedding
                embedding = await self.generate_embedding(row['text_content'])
                if not embedding:
                    return False

                # Store embedding (as JSON array for now, pgvector later)
                await conn.execute(
                    """
                    UPDATE manual_files
                    SET embedding_vector = $1::float[],
                        embedding_model = $2,
                        embedding_generated_at = NOW()
                    WHERE LOWER(manufacturer) = LOWER($3)
                      AND LOWER(model) = LOWER($4)
                      AND manual_type = $5
                    """,
                    embedding,
                    self.OPENAI_MODEL if self.use_openai else self.ST_MODEL,
                    manufacturer,
                    model,
                    manual_type
                )

                logger.info(
                    f"Stored embedding | manufacturer={manufacturer} | "
                    f"model={model} | dim={len(embedding)}"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to embed manual: {e}")
            return False

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search manuals using semantic similarity.

        Args:
            query: Search query text
            limit: Maximum results to return
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of matching manuals with similarity scores
        """
        # Generate query embedding
        query_embedding = await self.generate_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []

        try:
            async with self.db_pool.acquire() as conn:
                # Check if pgvector is available
                has_pgvector = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )

                if has_pgvector:
                    # Use pgvector cosine similarity
                    results = await conn.fetch(
                        """
                        SELECT
                            manufacturer,
                            model,
                            manual_type,
                            filename,
                            1 - (embedding_vector::vector <=> $1::vector) as similarity
                        FROM manual_files
                        WHERE embedding_vector IS NOT NULL
                        ORDER BY embedding_vector::vector <=> $1::vector
                        LIMIT $2
                        """,
                        query_embedding,
                        limit
                    )
                else:
                    # Fallback: Calculate cosine similarity in Python
                    rows = await conn.fetch(
                        """
                        SELECT
                            manufacturer,
                            model,
                            manual_type,
                            filename,
                            embedding_vector
                        FROM manual_files
                        WHERE embedding_vector IS NOT NULL
                        """
                    )

                    # Calculate similarities
                    scored = []
                    for row in rows:
                        if row['embedding_vector']:
                            sim = self._cosine_similarity(
                                query_embedding,
                                row['embedding_vector']
                            )
                            if sim >= threshold:
                                scored.append({
                                    'manufacturer': row['manufacturer'],
                                    'model': row['model'],
                                    'manual_type': row['manual_type'],
                                    'filename': row['filename'],
                                    'similarity': sim
                                })

                    # Sort and limit
                    scored.sort(key=lambda x: x['similarity'], reverse=True)
                    results = scored[:limit]

                # Format results
                formatted = []
                for row in results:
                    r = dict(row) if hasattr(row, 'keys') else row
                    if r.get('similarity', 0) >= threshold:
                        formatted.append({
                            'manufacturer': r['manufacturer'],
                            'model': r['model'],
                            'manual_type': r['manual_type'],
                            'filename': r.get('filename'),
                            'similarity': float(r['similarity'])
                        })

                logger.info(
                    f"Semantic search | query='{query[:50]}...' | "
                    f"results={len(formatted)}"
                )
                return formatted

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def embed_all_manuals(self) -> Dict[str, int]:
        """
        Generate embeddings for all manuals without embeddings.

        Returns:
            Dict with success and failure counts
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get manuals without embeddings
                rows = await conn.fetch(
                    """
                    SELECT manufacturer, model, manual_type
                    FROM manual_files
                    WHERE text_content IS NOT NULL
                      AND embedding_vector IS NULL
                    """
                )

            success = 0
            failed = 0

            for row in rows:
                result = await self.embed_manual(
                    row['manufacturer'],
                    row['model'],
                    row['manual_type']
                )
                if result:
                    success += 1
                else:
                    failed += 1

            logger.info(
                f"Batch embedding complete | success={success} | failed={failed}"
            )
            return {'success': success, 'failed': failed}

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            return {'success': 0, 'failed': 0, 'error': str(e)}
