"""
Manual QA Core Service

Orchestrates the PDF Manual Q&A system with text and vision pipelines.
Uses a global system prompt for consistent behavior across input types.

Features:
- Text pipeline: RAG retrieval + Groq/OpenAI generation
- Vision pipeline: Image OCR + text analysis (Phase 3)
- Conversation history for multi-turn context
- Citation tracking with page numbers
- Cost tracking via LLMRouter
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID

import asyncpg

from rivet_pro.core.services.manual_rag_service import (
    ManualRAGService,
    RAGResult,
    Citation,
    calculate_rag_confidence,
    format_citations_for_response,
)
from rivet_pro.adapters.llm.router import (
    LLMRouter,
    ModelCapability,
    get_llm_router,
)

logger = logging.getLogger(__name__)


# ===== Global System Prompt =====
# This prompt is used for ALL interactions to ensure consistent behavior

MANUAL_QA_SYSTEM_PROMPT = """You are a PDF Manual Assistant. Your role is to answer user questions about the provided user manual with consistency, accuracy, and clarity.

## Core Behaviors (Apply to ALL inputs):
- Answer ONLY from the manual content provided in the context below
- If information is not in the manual, explicitly state: "This information is not covered in the provided manual sections."
- Use the same professional tone regardless of input type
- Format answers with numbered steps or bullet points when applicable
- Always cite the manual section/page when providing information (e.g., "According to Page 12, Section 3.2...")

## Response Guidelines:
- Be direct and concise - technicians need quick answers
- Use technical terminology appropriate to the equipment
- Highlight safety warnings prominently when relevant
- If multiple manual sections are relevant, synthesize the information coherently

## When Information is Insufficient:
- Clearly state what information is missing
- Suggest what the user might look for (e.g., "This may be covered in the troubleshooting section")
- Never hallucinate or infer details beyond manual scope

## Never:
- Make up information not present in the provided context
- Assume user intent beyond what's explicitly asked
- Use external knowledge - only manual content + user query
- Provide generic advice when specific manual guidance exists"""


class InputType(Enum):
    """Type of user input."""
    TEXT = "text"
    IMAGE = "image"


@dataclass
class ManualQAResponse:
    """Response from the Q&A system."""
    answer: str
    citations: List[Citation]
    confidence: float  # 0.0-1.0 based on RAG retrieval
    sources_used: int
    cost_usd: float
    model_used: str
    from_vision: bool = False
    rag_context_preview: str = ""  # First 500 chars of context for debugging


@dataclass
class ConversationMessage:
    """A single message in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    citations: List[Citation] = field(default_factory=list)


@dataclass
class ManualQASession:
    """Active Q&A session with conversation history."""
    session_id: UUID
    manual_id: Optional[UUID]
    user_id: Optional[int]
    messages: List[ConversationMessage] = field(default_factory=list)
    total_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def conversation_history(self) -> List[Dict[str, str]]:
        """Convert messages to dict format for RAG enhancement."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages[-10:]  # Last 10 messages
        ]


class ManualQAService:
    """
    Core service for PDF Manual Q&A.

    Orchestrates:
    - Input routing (text vs image)
    - RAG context retrieval
    - LLM response generation
    - Conversation tracking
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        rag_service: Optional[ManualRAGService] = None,
        llm_router: Optional[LLMRouter] = None
    ):
        """
        Initialize QA service.

        Args:
            db_pool: Database connection pool
            rag_service: ManualRAGService instance. Created if None.
            llm_router: LLMRouter instance. Uses singleton if None.
        """
        self.db_pool = db_pool
        self.rag_service = rag_service or ManualRAGService(db_pool)
        self.llm_router = llm_router or get_llm_router()

        # In-memory session cache (for CLI/testing)
        # Production should use database sessions
        self._sessions: Dict[UUID, ManualQASession] = {}

        logger.info("ManualQAService initialized")

    async def ask(
        self,
        query: str,
        manual_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        image_data: Optional[bytes] = None,
        user_id: Optional[int] = None
    ) -> ManualQAResponse:
        """
        Answer a question about a manual.

        Args:
            query: User's question
            manual_id: Specific manual to search (None = search all)
            session_id: Existing session for conversation context
            image_data: Optional image bytes for vision pipeline
            user_id: Optional user ID for tracking

        Returns:
            ManualQAResponse with answer, citations, and metadata

        Example:
            response = await qa_service.ask(
                query="How do I reset to factory settings?",
                manual_id=some_uuid
            )
            print(f"Answer: {response.answer}")
            print(f"Sources: {response.citations}")
        """
        start_time = datetime.utcnow()
        logger.info(f"[Manual QA] Query: {query[:50]}...")

        # Get or create session
        session = self._get_or_create_session(session_id, manual_id, user_id)

        # Route input
        input_type = self._route_input(query, image_data)

        if input_type == InputType.IMAGE:
            # Vision pipeline (Phase 3 - placeholder for now)
            response = await self._process_image_query(query, image_data, session)
        else:
            # Text pipeline (primary)
            response = await self._process_text_query(query, session)

        # Update session
        session.messages.append(ConversationMessage(
            role="user",
            content=query
        ))
        session.messages.append(ConversationMessage(
            role="assistant",
            content=response.answer,
            citations=response.citations
        ))
        session.total_cost_usd += response.cost_usd

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"[Manual QA] Complete | "
            f"confidence={response.confidence:.2f} | "
            f"sources={response.sources_used} | "
            f"cost=${response.cost_usd:.4f} | "
            f"duration={duration:.2f}s"
        )

        return response

    async def _process_text_query(
        self,
        query: str,
        session: ManualQASession
    ) -> ManualQAResponse:
        """
        Process text-only query using RAG pipeline.

        Steps:
        1. Retrieve relevant chunks from manual
        2. Build prompt with system instructions + context
        3. Generate response with LLM
        4. Extract citations
        """
        # Step 1: RAG retrieval
        rag_result = await self.rag_service.retrieve_context(
            query=query,
            manual_id=session.manual_id,
            conversation_history=session.conversation_history,
            top_k=5,
            min_similarity=0.4
        )

        # Step 2: Build prompt
        prompt = self._build_prompt(
            query=query,
            rag_context=rag_result.formatted_context,
            conversation_history=session.conversation_history
        )

        # Step 3: Generate response
        try:
            llm_response = await self.llm_router.generate(
                prompt=prompt,
                capability=ModelCapability.MODERATE,
                max_tokens=1500,
                temperature=0.3  # Lower temperature for factual answers
            )

            answer = llm_response.text
            cost = llm_response.cost_usd
            model = llm_response.model

        except Exception as e:
            logger.error(f"[Manual QA] LLM generation failed: {e}")
            answer = (
                "I apologize, but I encountered an error generating a response. "
                "Please try again or rephrase your question."
            )
            cost = 0.0
            model = "error"

        # Step 4: Calculate confidence and build response
        confidence = calculate_rag_confidence(rag_result.chunks)

        # Add citation footer to answer if we have sources
        if rag_result.citations:
            citation_footer = format_citations_for_response(rag_result.citations)
            answer = answer + citation_footer

        return ManualQAResponse(
            answer=answer,
            citations=rag_result.citations,
            confidence=confidence,
            sources_used=len(rag_result.chunks),
            cost_usd=cost,
            model_used=model,
            from_vision=False,
            rag_context_preview=rag_result.formatted_context[:500]
        )

    async def _process_image_query(
        self,
        query: str,
        image_data: bytes,
        session: ManualQASession
    ) -> ManualQAResponse:
        """
        Process image query using vision pipeline.

        Phase 3 implementation - for now returns placeholder.
        Will use ScreeningService + DeepSeek Vision.
        """
        logger.info("[Manual QA] Image query received - vision pipeline not yet implemented")

        return ManualQAResponse(
            answer=(
                "Vision processing is not yet implemented. "
                "Please describe what you see in the image or ask a text-based question."
            ),
            citations=[],
            confidence=0.0,
            sources_used=0,
            cost_usd=0.0,
            model_used="none",
            from_vision=True,
            rag_context_preview=""
        )

    def _route_input(
        self,
        query: str,
        image_data: Optional[bytes]
    ) -> InputType:
        """Determine input type (text or image)."""
        if image_data and len(image_data) > 100:  # Minimum image size check
            return InputType.IMAGE
        return InputType.TEXT

    def _build_prompt(
        self,
        query: str,
        rag_context: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Build complete prompt for LLM with system instructions and context.

        Structure:
        1. System prompt (global behavior)
        2. Manual context (RAG results)
        3. Conversation history (if multi-turn)
        4. Current question
        """
        parts = [
            MANUAL_QA_SYSTEM_PROMPT,
            "",
            "---",
            "",
            rag_context,
            "",
            "---",
            "",
        ]

        # Add recent conversation context (last 2 exchanges)
        if len(conversation_history) >= 2:
            parts.append("## Recent Conversation")
            for msg in conversation_history[-4:]:
                role = "User" if msg["role"] == "user" else "Assistant"
                content = msg["content"][:300]  # Truncate for prompt size
                parts.append(f"**{role}:** {content}")
            parts.append("")
            parts.append("---")
            parts.append("")

        # Current question
        parts.append(f"## Current Question")
        parts.append(f"User: {query}")
        parts.append("")
        parts.append("Please provide a helpful, accurate answer based on the manual context above.")

        return "\n".join(parts)

    def _get_or_create_session(
        self,
        session_id: Optional[UUID],
        manual_id: Optional[UUID],
        user_id: Optional[int]
    ) -> ManualQASession:
        """Get existing session or create new one."""
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        # Create new session
        import uuid
        new_session_id = session_id or uuid.uuid4()

        session = ManualQASession(
            session_id=new_session_id,
            manual_id=manual_id,
            user_id=user_id
        )

        self._sessions[new_session_id] = session
        return session

    def get_session(self, session_id: UUID) -> Optional[ManualQASession]:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def end_session(self, session_id: UUID) -> None:
        """End and remove a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"[Manual QA] Session ended: {session_id}")


# ===== Convenience Functions =====

async def quick_ask(
    db_pool: asyncpg.Pool,
    query: str,
    manual_id: Optional[UUID] = None
) -> str:
    """
    Quick one-off question without session management.

    Args:
        db_pool: Database connection pool
        query: Question to ask
        manual_id: Optional specific manual

    Returns:
        Answer text (no metadata)
    """
    service = ManualQAService(db_pool)
    response = await service.ask(query=query, manual_id=manual_id)
    return response.answer


__all__ = [
    "ManualQAService",
    "ManualQAResponse",
    "ManualQASession",
    "ConversationMessage",
    "InputType",
    "MANUAL_QA_SYSTEM_PROMPT",
    "quick_ask",
]
