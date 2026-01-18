"""
Manual Conversation Service

Persists Q&A sessions and messages to the database.
Supports multi-turn conversations with history retrieval.

Uses:
- manual_qa_sessions table for session metadata
- manual_qa_messages table for message storage
- manual_qa_analytics table for query patterns
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class PersistedMessage:
    """A message retrieved from database."""
    message_id: UUID
    session_id: UUID
    role: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None
    cost_usd: Optional[float] = None
    model_used: Optional[str] = None
    from_vision: bool = False
    created_at: datetime = None


@dataclass
class PersistedSession:
    """A session retrieved from database."""
    session_id: UUID
    manual_id: Optional[UUID]
    user_id: Optional[int]
    created_at: datetime
    last_message_at: datetime
    message_count: int
    total_cost_usd: float
    avg_confidence: float
    status: str
    messages: List[PersistedMessage] = None


class ManualConversationService:
    """
    Service for persisting Q&A conversations to database.

    Features:
    - Session creation and management
    - Message storage with metadata
    - Conversation history retrieval
    - Session expiration
    - Query analytics
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize conversation service.

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        logger.info("ManualConversationService initialized")

    async def create_session(
        self,
        manual_id: Optional[UUID] = None,
        user_id: Optional[int] = None
    ) -> UUID:
        """
        Create a new Q&A session.

        Args:
            manual_id: Optional manual to associate with session
            user_id: Optional user identifier (Telegram chat ID, etc.)

        Returns:
            New session UUID
        """
        try:
            async with self.db_pool.acquire() as conn:
                session_id = await conn.fetchval(
                    """
                    INSERT INTO manual_qa_sessions (manual_id, user_id)
                    VALUES ($1, $2)
                    RETURNING session_id
                    """,
                    manual_id,
                    user_id
                )

            logger.info(f"Created session: {session_id}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    async def get_session(
        self,
        session_id: UUID,
        include_messages: bool = False,
        message_limit: int = 50
    ) -> Optional[PersistedSession]:
        """
        Get session by ID.

        Args:
            session_id: Session UUID
            include_messages: Whether to include message history
            message_limit: Maximum messages to retrieve

        Returns:
            PersistedSession or None if not found
        """
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT session_id, manual_id, user_id, created_at,
                           last_message_at, message_count, total_cost_usd,
                           avg_confidence, status
                    FROM manual_qa_sessions
                    WHERE session_id = $1
                    """,
                    session_id
                )

                if not row:
                    return None

                session = PersistedSession(
                    session_id=row['session_id'],
                    manual_id=row['manual_id'],
                    user_id=row['user_id'],
                    created_at=row['created_at'],
                    last_message_at=row['last_message_at'],
                    message_count=row['message_count'],
                    total_cost_usd=row['total_cost_usd'],
                    avg_confidence=row['avg_confidence'],
                    status=row['status'],
                    messages=[]
                )

                if include_messages:
                    session.messages = await self.get_messages(
                        session_id, limit=message_limit
                    )

                return session

        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        confidence: Optional[float] = None,
        cost_usd: Optional[float] = None,
        model_used: Optional[str] = None,
        from_vision: bool = False,
        rag_chunks_used: int = 0,
        rag_top_similarity: Optional[float] = None
    ) -> UUID:
        """
        Add a message to a session.

        Args:
            session_id: Session UUID
            role: 'user', 'assistant', or 'system'
            content: Message content
            citations: JSON-serializable citation data
            confidence: Response confidence (0.0-1.0)
            cost_usd: LLM cost for this message
            model_used: Model that generated response
            from_vision: Whether vision pipeline was used
            rag_chunks_used: Number of RAG chunks used
            rag_top_similarity: Highest similarity score

        Returns:
            New message UUID
        """
        import json

        try:
            async with self.db_pool.acquire() as conn:
                citations_json = json.dumps(citations) if citations else None

                message_id = await conn.fetchval(
                    """
                    INSERT INTO manual_qa_messages (
                        session_id, role, content, citations,
                        confidence, cost_usd, model_used, from_vision,
                        rag_chunks_used, rag_top_similarity
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING message_id
                    """,
                    session_id,
                    role,
                    content,
                    citations_json,
                    confidence,
                    cost_usd,
                    model_used,
                    from_vision,
                    rag_chunks_used,
                    rag_top_similarity
                )

                # Update session stats if this is an assistant message with cost
                if role == "assistant" and cost_usd:
                    await conn.execute(
                        """
                        UPDATE manual_qa_sessions
                        SET total_cost_usd = total_cost_usd + $2,
                            avg_confidence = (
                                (avg_confidence * (message_count - 1) + COALESCE($3, 0))
                                / GREATEST(message_count, 1)
                            )
                        WHERE session_id = $1
                        """,
                        session_id,
                        cost_usd,
                        confidence
                    )

            logger.debug(f"Added message {message_id} to session {session_id}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise

    async def get_messages(
        self,
        session_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[PersistedMessage]:
        """
        Get messages for a session.

        Args:
            session_id: Session UUID
            limit: Maximum messages to return
            offset: Number of messages to skip

        Returns:
            List of PersistedMessage objects (oldest first)
        """
        import json

        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT message_id, session_id, role, content,
                           citations, confidence, cost_usd, model_used,
                           from_vision, created_at
                    FROM manual_qa_messages
                    WHERE session_id = $1
                    ORDER BY created_at ASC
                    LIMIT $2 OFFSET $3
                    """,
                    session_id,
                    limit,
                    offset
                )

                messages = []
                for row in rows:
                    citations = None
                    if row['citations']:
                        try:
                            citations = json.loads(row['citations'])
                        except (json.JSONDecodeError, TypeError):
                            pass

                    messages.append(PersistedMessage(
                        message_id=row['message_id'],
                        session_id=row['session_id'],
                        role=row['role'],
                        content=row['content'],
                        citations=citations,
                        confidence=row['confidence'],
                        cost_usd=row['cost_usd'],
                        model_used=row['model_used'],
                        from_vision=row['from_vision'],
                        created_at=row['created_at']
                    ))

                return messages

        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []

    async def get_conversation_history(
        self,
        session_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Get conversation history in dict format for RAG enhancement.

        Args:
            session_id: Session UUID
            limit: Maximum exchanges to return

        Returns:
            List of {"role": "user"|"assistant", "content": "..."}
        """
        messages = await self.get_messages(session_id, limit=limit * 2)

        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
            if msg.role in ("user", "assistant")
        ]

    async def end_session(self, session_id: UUID) -> bool:
        """
        Mark a session as ended.

        Args:
            session_id: Session UUID

        Returns:
            True if session was ended, False if not found
        """
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE manual_qa_sessions
                    SET status = 'ended',
                        ended_at = NOW()
                    WHERE session_id = $1
                      AND status = 'active'
                    """,
                    session_id
                )
                updated = result.split()[-1] == "1"

            if updated:
                logger.info(f"Ended session: {session_id}")
            return updated

        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            return False

    async def get_user_sessions(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[PersistedSession]:
        """
        Get sessions for a user.

        Args:
            user_id: User identifier
            status: Filter by status ('active', 'ended', 'expired')
            limit: Maximum sessions to return

        Returns:
            List of sessions (most recent first)
        """
        try:
            async with self.db_pool.acquire() as conn:
                if status:
                    rows = await conn.fetch(
                        """
                        SELECT session_id, manual_id, user_id, created_at,
                               last_message_at, message_count, total_cost_usd,
                               avg_confidence, status
                        FROM manual_qa_sessions
                        WHERE user_id = $1 AND status = $2
                        ORDER BY last_message_at DESC
                        LIMIT $3
                        """,
                        user_id,
                        status,
                        limit
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT session_id, manual_id, user_id, created_at,
                               last_message_at, message_count, total_cost_usd,
                               avg_confidence, status
                        FROM manual_qa_sessions
                        WHERE user_id = $1
                        ORDER BY last_message_at DESC
                        LIMIT $2
                        """,
                        user_id,
                        limit
                    )

                return [
                    PersistedSession(
                        session_id=row['session_id'],
                        manual_id=row['manual_id'],
                        user_id=row['user_id'],
                        created_at=row['created_at'],
                        last_message_at=row['last_message_at'],
                        message_count=row['message_count'],
                        total_cost_usd=row['total_cost_usd'],
                        avg_confidence=row['avg_confidence'],
                        status=row['status']
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []

    async def log_query_analytics(
        self,
        manual_id: Optional[UUID],
        query_text: str,
        response_confidence: float,
        sources_found: int,
        query_embedding: Optional[List[float]] = None
    ) -> None:
        """
        Log query for analytics and pattern detection.

        Args:
            manual_id: Manual that was queried
            query_text: The user's query
            response_confidence: Confidence score of response
            sources_found: Number of relevant chunks found
            query_embedding: Optional pre-computed embedding
        """
        try:
            # Hash query for deduplication
            normalized_query = query_text.lower().strip()
            query_hash = hashlib.sha256(
                f"{manual_id}:{normalized_query}".encode()
            ).hexdigest()

            async with self.db_pool.acquire() as conn:
                # Check if similar query exists
                existing = await conn.fetchval(
                    """
                    SELECT id FROM manual_qa_analytics
                    WHERE query_hash = $1
                    """,
                    query_hash
                )

                if existing:
                    # Update existing record
                    await conn.execute(
                        """
                        UPDATE manual_qa_analytics
                        SET response_confidence = $2,
                            sources_found = $3,
                            created_at = NOW()
                        WHERE id = $1
                        """,
                        existing,
                        response_confidence,
                        sources_found
                    )
                else:
                    # Insert new record
                    embedding_str = None
                    if query_embedding:
                        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

                    await conn.execute(
                        """
                        INSERT INTO manual_qa_analytics (
                            manual_id, query_text, response_confidence,
                            sources_found, query_hash, query_embedding
                        ) VALUES ($1, $2, $3, $4, $5, $6::vector)
                        """,
                        manual_id,
                        query_text[:1000],  # Truncate long queries
                        response_confidence,
                        sources_found,
                        query_hash,
                        embedding_str
                    )

        except Exception as e:
            # Analytics logging should not fail main operation
            logger.warning(f"Failed to log query analytics: {e}")

    async def expire_old_sessions(self, hours: int = 24) -> int:
        """
        Expire sessions older than specified hours.

        Args:
            hours: Sessions inactive for this long will be expired

        Returns:
            Number of sessions expired
        """
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT expire_old_manual_qa_sessions($1)",
                    hours
                )
                logger.info(f"Expired {result} old sessions")
                return result or 0

        except Exception as e:
            logger.error(f"Failed to expire sessions: {e}")
            return 0


__all__ = [
    "ManualConversationService",
    "PersistedSession",
    "PersistedMessage",
]
