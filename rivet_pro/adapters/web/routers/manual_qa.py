"""
Manual Q&A Router

FastAPI endpoints for the PDF Manual Q&A system.
Provides indexing, querying, and session management APIs.
"""

import base64
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field

from rivet_pro.adapters.web.dependencies import get_db
from rivet_pro.infra.database import Database
from rivet_pro.infra.observability import get_logger

# Services
from rivet_pro.core.services.manual_qa_service import ManualQAService, ManualQAResponse
from rivet_pro.core.services.manual_indexing_service import (
    ManualIndexingService,
    IndexingResult,
    index_pdf_directly,
)
from rivet_pro.core.services.manual_conversation_service import (
    ManualConversationService,
    PersistedSession,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/manual-qa", tags=["Manual Q&A"])


# ===== Request/Response Models =====

class IndexManualRequest(BaseModel):
    """Request to index an existing manual."""
    manual_id: UUID
    max_pages: int = Field(default=100, le=500)


class IndexUploadResponse(BaseModel):
    """Response after indexing a PDF."""
    manual_id: UUID
    chunks_created: int
    chunks_failed: int
    total_chars: int
    duration_seconds: float
    success: bool
    error: Optional[str] = None


class AskQuestionRequest(BaseModel):
    """Request to ask a question."""
    query: str = Field(..., min_length=3, max_length=2000)
    manual_id: Optional[UUID] = None
    session_id: Optional[UUID] = None


class CitationModel(BaseModel):
    """Citation reference."""
    page: int
    section: Optional[str] = None
    text_preview: str = ""
    confidence: float = 0.0


class AskQuestionResponse(BaseModel):
    """Response to a question."""
    answer: str
    citations: List[CitationModel]
    confidence: float
    sources_used: int
    cost_usd: float
    model_used: str
    from_vision: bool = False


class StartSessionRequest(BaseModel):
    """Request to start a Q&A session."""
    manual_id: Optional[UUID] = None
    user_id: Optional[int] = None


class SessionResponse(BaseModel):
    """Session information."""
    session_id: UUID
    manual_id: Optional[UUID]
    message_count: int
    total_cost_usd: float
    status: str


class SessionListResponse(BaseModel):
    """List of sessions."""
    sessions: List[SessionResponse]


# ===== Endpoints =====

@router.post("/index", response_model=IndexUploadResponse)
async def index_manual(
    request: IndexManualRequest,
    db: Database = Depends(get_db)
):
    """
    Index an existing manual record.

    Extracts text from the PDF, chunks it, generates embeddings,
    and stores in the database for RAG retrieval.
    """
    try:
        # Get manual file path
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT file_url FROM manuals WHERE id = $1",
                request.manual_id
            )

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Manual not found: {request.manual_id}"
                )

            file_path = row['file_url']
            if not file_path:
                raise HTTPException(
                    status_code=400,
                    detail="Manual has no file path"
                )

        # Index the manual
        indexer = ManualIndexingService(db.pool)
        result = await indexer.index_manual(
            manual_id=request.manual_id,
            pdf_path=file_path,
            max_pages=request.max_pages
        )

        return IndexUploadResponse(
            manual_id=result.manual_id,
            chunks_created=result.chunks_created,
            chunks_failed=result.chunks_failed,
            total_chars=result.total_chars,
            duration_seconds=result.duration_seconds,
            success=result.success,
            error=result.error
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Index failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", response_model=IndexUploadResponse)
async def upload_and_index_manual(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    db: Database = Depends(get_db)
):
    """
    Upload a PDF and index it in one step.

    Creates a new manual record and indexes the content.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    try:
        import tempfile
        import os

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Index the PDF
            result = await index_pdf_directly(
                db_pool=db.pool,
                pdf_path=tmp_path,
                title=title or file.filename.rsplit('.', 1)[0],
                source="user_upload"
            )

            return IndexUploadResponse(
                manual_id=result.manual_id,
                chunks_created=result.chunks_created,
                chunks_failed=result.chunks_failed,
                total_chars=result.total_chars,
                duration_seconds=result.duration_seconds,
                success=result.success,
                error=result.error
            )

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask", response_model=AskQuestionResponse)
async def ask_question(
    request: AskQuestionRequest,
    db: Database = Depends(get_db)
):
    """
    Ask a question about a manual.

    Uses RAG to retrieve relevant chunks and generates an answer.
    Optionally continues an existing session for multi-turn context.
    """
    try:
        service = ManualQAService(db.pool)

        response = await service.ask(
            query=request.query,
            manual_id=request.manual_id,
            session_id=request.session_id
        )

        # Convert citations to response model
        citations = [
            CitationModel(
                page=c.page,
                section=c.section,
                text_preview=c.text_preview,
                confidence=c.confidence
            )
            for c in response.citations
        ]

        return AskQuestionResponse(
            answer=response.answer,
            citations=citations,
            confidence=response.confidence,
            sources_used=response.sources_used,
            cost_usd=response.cost_usd,
            model_used=response.model_used,
            from_vision=response.from_vision
        )

    except Exception as e:
        logger.error(f"Ask failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/start", response_model=SessionResponse)
async def start_session(
    request: StartSessionRequest,
    db: Database = Depends(get_db)
):
    """
    Start a new Q&A session.

    Sessions track conversation history for multi-turn context.
    """
    try:
        conversation_service = ManualConversationService(db.pool)

        session_id = await conversation_service.create_session(
            manual_id=request.manual_id,
            user_id=request.user_id
        )

        return SessionResponse(
            session_id=session_id,
            manual_id=request.manual_id,
            message_count=0,
            total_cost_usd=0.0,
            status="active"
        )

    except Exception as e:
        logger.error(f"Start session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/ask", response_model=AskQuestionResponse)
async def ask_in_session(
    session_id: UUID,
    query: str = Query(..., min_length=3),
    db: Database = Depends(get_db)
):
    """
    Ask a question within an existing session.

    Uses conversation history for enhanced context.
    """
    try:
        service = ManualQAService(db.pool)
        conversation_service = ManualConversationService(db.pool)

        # Get session to find manual_id
        session = await conversation_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )

        if session.status != "active":
            raise HTTPException(
                status_code=400,
                detail=f"Session is {session.status}"
            )

        response = await service.ask(
            query=query,
            manual_id=session.manual_id,
            session_id=session_id
        )

        # Persist messages
        await conversation_service.add_message(
            session_id=session_id,
            role="user",
            content=query
        )
        await conversation_service.add_message(
            session_id=session_id,
            role="assistant",
            content=response.answer,
            citations=[{"page": c.page, "section": c.section} for c in response.citations],
            confidence=response.confidence,
            cost_usd=response.cost_usd,
            model_used=response.model_used,
            from_vision=response.from_vision,
            rag_chunks_used=response.sources_used,
            rag_top_similarity=response.confidence
        )

        # Convert citations
        citations = [
            CitationModel(
                page=c.page,
                section=c.section,
                text_preview=c.text_preview,
                confidence=c.confidence
            )
            for c in response.citations
        ]

        return AskQuestionResponse(
            answer=response.answer,
            citations=citations,
            confidence=response.confidence,
            sources_used=response.sources_used,
            cost_usd=response.cost_usd,
            model_used=response.model_used,
            from_vision=response.from_vision
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ask in session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    db: Database = Depends(get_db)
):
    """Get session information."""
    try:
        conversation_service = ManualConversationService(db.pool)

        session = await conversation_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )

        return SessionResponse(
            session_id=session.session_id,
            manual_id=session.manual_id,
            message_count=session.message_count,
            total_cost_usd=session.total_cost_usd,
            status=session.status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def end_session(
    session_id: UUID,
    db: Database = Depends(get_db)
):
    """End a Q&A session."""
    try:
        conversation_service = ManualConversationService(db.pool)

        success = await conversation_service.end_session(session_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found or already ended: {session_id}"
            )

        return {"status": "ended", "session_id": str(session_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"End session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=SessionListResponse)
async def list_user_sessions(
    user_id: int,
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    db: Database = Depends(get_db)
):
    """List sessions for a user."""
    try:
        conversation_service = ManualConversationService(db.pool)

        sessions = await conversation_service.get_user_sessions(
            user_id=user_id,
            status=status,
            limit=limit
        )

        return SessionListResponse(
            sessions=[
                SessionResponse(
                    session_id=s.session_id,
                    manual_id=s.manual_id,
                    message_count=s.message_count,
                    total_cost_usd=s.total_cost_usd,
                    status=s.status
                )
                for s in sessions
            ]
        )

    except Exception as e:
        logger.error(f"List sessions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
