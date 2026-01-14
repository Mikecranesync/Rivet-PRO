"""
Embedding Service

Service for generating vector embeddings using OpenAI text-embedding-3-small.
Used for semantic search in knowledge base and manual chunks.

Model: text-embedding-3-small
- Dimensions: 1536
- Cost: $0.02 per 1M tokens
- Performance: 62.3% MTEB score
- Max tokens: 8191 per request

Based on:
- OpenAI Embeddings API: https://platform.openai.com/docs/guides/embeddings
- Rivet spec: rivet_pro_skill_ai_routing.md
"""

import logging
import asyncio
from typing import List, Optional
import os

from openai import AsyncOpenAI, OpenAIError

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI.

    Features:
    - Single and batch embedding generation
    - Automatic retry on rate limits
    - Token usage tracking
    - Dimension validation
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.

        Raises:
            ValueError: If no API key provided
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "text-embedding-3-small"
        self.dimensions = 1536
        self.max_tokens_per_request = 8191

        # Rate limiting and retry config
        self.max_retries = 3
        self.retry_delay = 2.0  # seconds

        logger.info(f"EmbeddingService initialized with model: {self.model}")

    async def generate_embedding(
        self,
        text: str,
        retry_count: int = 0
    ) -> List[float]:
        """
        Generate embedding for single text.

        Args:
            text: Text to embed (max ~8000 tokens)
            retry_count: Internal retry counter

        Returns:
            List of 1536 floats representing the embedding vector

        Raises:
            ValueError: If text is empty
            OpenAIError: If API call fails after retries

        Example:
            embedding = await embedding_service.generate_embedding(
                "F0002 indicates overvoltage fault on Siemens G120C"
            )
            # [0.123, -0.456, 0.789, ..., 0.012]  # 1536 dimensions
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Truncate very long text (rough estimate: 1 token ≈ 4 chars)
        max_chars = self.max_tokens_per_request * 4
        if len(text) > max_chars:
            logger.warning(f"Text truncated from {len(text)} to {max_chars} chars")
            text = text[:max_chars]

        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"  # Return as floats (default)
            )

            embedding = response.data[0].embedding

            # Validate dimensions
            if len(embedding) != self.dimensions:
                raise ValueError(
                    f"Expected {self.dimensions} dimensions, got {len(embedding)}"
                )

            # Log token usage
            total_tokens = response.usage.total_tokens
            logger.debug(
                f"Generated embedding for text ({len(text)} chars, "
                f"{total_tokens} tokens)"
            )

            return embedding

        except OpenAIError as e:
            error_str = str(e)

            # Skip retries immediately on quota exhaustion (no point retrying)
            if "insufficient_quota" in error_str or "quota" in error_str.lower():
                logger.error(
                    f"OpenAI quota exceeded - skipping retries (no point waiting). "
                    f"Add funds at https://platform.openai.com/account/billing"
                )
                raise

            # Retry on rate limits or transient errors
            if retry_count < self.max_retries:
                logger.warning(
                    f"OpenAI API error (attempt {retry_count + 1}/{self.max_retries}): {e}"
                )
                await asyncio.sleep(self.retry_delay * (retry_count + 1))
                return await self.generate_embedding(text, retry_count + 1)

            logger.error(f"Failed to generate embedding after {self.max_retries} retries: {e}")
            raise

    async def generate_batch_embeddings(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch optimization).

        OpenAI allows up to 2048 inputs per request, but we use smaller batches
        for better error handling and rate limit management.

        Args:
            texts: List of texts to embed
            batch_size: Texts per API request (default 100)

        Returns:
            List of embeddings (1536 dimensions each), same order as input

        Example:
            embeddings = await embedding_service.generate_batch_embeddings([
                "F0002 - Overvoltage fault",
                "F0001 - Overcurrent fault",
                "Check motor load and cables"
            ])
            # [[0.1, -0.2, ...], [0.3, -0.4, ...], [0.5, -0.6, ...]]
        """
        if not texts:
            return []

        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(texts))
            batch = texts[start_idx:end_idx]

            logger.info(
                f"Processing batch {batch_num + 1}/{total_batches} "
                f"({len(batch)} texts)"
            )

            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    encoding_format="float"
                )

                # Extract embeddings in same order as input
                batch_embeddings = [item.embedding for item in response.data]

                # Validate dimensions for all embeddings
                for i, emb in enumerate(batch_embeddings):
                    if len(emb) != self.dimensions:
                        raise ValueError(
                            f"Embedding {i} has {len(emb)} dimensions, "
                            f"expected {self.dimensions}"
                        )

                all_embeddings.extend(batch_embeddings)

                # Log token usage
                total_tokens = response.usage.total_tokens
                logger.debug(
                    f"Batch {batch_num + 1} complete: {total_tokens} tokens used"
                )

                # Small delay between batches to avoid rate limits
                if batch_num < total_batches - 1:
                    await asyncio.sleep(0.1)

            except OpenAIError as e:
                logger.error(f"Failed to process batch {batch_num + 1}: {e}")
                # Fill with empty embeddings for failed batch to maintain order
                all_embeddings.extend([[0.0] * self.dimensions] * len(batch))

        logger.info(f"Generated {len(all_embeddings)} embeddings total")
        return all_embeddings

    async def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for search query.

        Convenience method that wraps generate_embedding() for readability.

        Args:
            query: User query text

        Returns:
            1536-dimensional embedding vector
        """
        return await self.generate_embedding(query)

    def estimate_tokens(self, text: str) -> int:
        """
        Rough estimate of token count (1 token ≈ 4 characters for English).

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def validate_embedding(self, embedding: List[float]) -> bool:
        """
        Validate embedding format.

        Args:
            embedding: Vector to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(embedding, list):
            return False
        if len(embedding) != self.dimensions:
            return False
        if not all(isinstance(x, (int, float)) for x in embedding):
            return False
        return True


# ===== Utility Functions =====

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Similarity score (0.0 to 1.0, higher = more similar)

    Note:
        pgvector uses cosine distance (1 - similarity) for ordering.
        This function is mainly for testing/debugging.
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have same dimensions")

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


async def precompute_embeddings_for_atoms(
    embedding_service: EmbeddingService,
    atoms: List[dict]
) -> List[dict]:
    """
    Utility function to generate embeddings for knowledge atoms.

    Args:
        embedding_service: EmbeddingService instance
        atoms: List of atom dicts with 'title' and 'content' fields

    Returns:
        Same list with 'embedding' field added to each atom

    Example:
        atoms = [
            {"title": "F0002", "content": "Overvoltage fault..."},
            {"title": "F0001", "content": "Overcurrent fault..."}
        ]
        atoms_with_embeddings = await precompute_embeddings_for_atoms(
            embedding_service, atoms
        )
    """
    # Combine title and content for embedding
    texts = [f"{atom['title']} {atom['content']}" for atom in atoms]

    embeddings = await embedding_service.generate_batch_embeddings(texts)

    for atom, embedding in zip(atoms, embeddings):
        atom['embedding'] = embedding

    return atoms
