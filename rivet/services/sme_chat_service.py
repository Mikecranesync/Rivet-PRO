"""
SME Chat Service Core

Orchestrates SME chat sessions with personality, RAG, and LLM.
Handles session lifecycle (start, chat, close) and message persistence.

Uses:
- SMERagService for knowledge retrieval
- SME Personalities for voice/character
- LLMRouter for response generation
- Database for session/message persistence
"""

import logging
import re
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from rivet.services.sme_rag_service import SMERagService, calculate_rag_confidence, extract_sources_from_atoms
from rivet.prompts.sme.personalities import get_personality, build_system_prompt, SMEPersonality
from rivet.models.sme_chat import (
    SMEChatSession,
    SMEChatSessionCreate,
    SMEChatMessage,
    SMEChatMessageCreate,
    SMEChatResponse,
    SMEVendor,
    SessionStatus,
    MessageRole,
    ConfidenceLevel,
    get_sme_name,
)
from rivet.atlas.database import AtlasDatabase
from rivet.integrations.llm import LLMRouter, ModelCapability, LLMResponse

logger = logging.getLogger(__name__)


# Safety warning patterns to extract from LLM responses
SAFETY_PATTERNS = [
    (r"(?:high voltage|480v|240v|120v)", "HIGH VOLTAGE - De-energize before work"),
    (r"(?:loto|lockout|tagout)", "LOTO REQUIRED - Follow lockout/tagout procedures"),
    (r"(?:arc flash)", "ARC FLASH HAZARD - Wear proper PPE (NFPA 70E)"),
    (r"(?:safety system|f-cpu|guardlogix|safemove)", "SAFETY SYSTEM - Do not bypass safety functions"),
    (r"(?:rotating|pinch point|crush)", "MECHANICAL HAZARD - Guard in place before operation"),
    (r"(?:chemical|acid|caustic)", "CHEMICAL HAZARD - Wear proper PPE"),
]


class SMEChatService:
    """
    Service for managing SME chat sessions.

    Features:
    - Session lifecycle management (start, chat, close)
    - Personality-driven responses
    - RAG-enhanced context
    - Safety warning extraction
    - Confidence-based response quality
    """

    def __init__(
        self,
        db: Optional[AtlasDatabase] = None,
        rag_service: Optional[SMERagService] = None,
    ):
        """
        Initialize SME chat service.

        Args:
            db: AtlasDatabase instance. Created if None.
            rag_service: SMERagService instance. Created if None.
        """
        self.db = db or AtlasDatabase()
        self.rag_service = rag_service or SMERagService(db=self.db)
        self.llm_router = LLMRouter()

        logger.info("SMEChatService initialized")

    async def start_session(
        self,
        telegram_chat_id: int,
        sme_vendor: str,
        equipment_context: Optional[Dict[str, Any]] = None
    ) -> SMEChatSession:
        """
        Start a new SME chat session.

        Creates session record and adds system message with personality.

        Args:
            telegram_chat_id: Telegram chat ID
            sme_vendor: Vendor key (siemens, rockwell, etc.)
            equipment_context: Optional equipment context from OCR

        Returns:
            SMEChatSession model

        Example:
            session = await service.start_session(
                telegram_chat_id=12345678,
                sme_vendor="siemens",
                equipment_context={"model": "G120C"}
            )
        """
        logger.info(f"[SME Chat] Starting session: vendor={sme_vendor}, chat_id={telegram_chat_id}")

        # Close any existing active session for this chat
        await self._close_existing_session(telegram_chat_id)

        # Get personality for system message
        personality = get_personality(sme_vendor)
        system_prompt = build_system_prompt(personality, equipment_context)

        # Create session record
        query = """
            INSERT INTO sme_chat_sessions (telegram_chat_id, sme_vendor, status, equipment_context)
            VALUES ($1, $2, 'active', $3)
            RETURNING session_id, telegram_chat_id, sme_vendor, status, equipment_context,
                      created_at, last_message_at, closed_at
        """
        result = await self.db.fetch_one(
            query,
            telegram_chat_id,
            sme_vendor.lower(),
            equipment_context
        )

        session = SMEChatSession(
            session_id=result['session_id'],
            telegram_chat_id=result['telegram_chat_id'],
            sme_vendor=SMEVendor(result['sme_vendor']),
            status=SessionStatus(result['status']),
            equipment_context=result['equipment_context'],
            created_at=result['created_at'],
            last_message_at=result['last_message_at'],
            closed_at=result['closed_at'],
        )

        # Add system message with personality
        await self._add_message(
            session_id=session.session_id,
            role=MessageRole.SYSTEM,
            content=system_prompt
        )

        logger.info(f"[SME Chat] Session started: {session.session_id} ({personality.name})")
        return session

    async def chat(
        self,
        session_id: UUID,
        user_message: str
    ) -> SMEChatResponse:
        """
        Process user message and generate SME response.

        Flow:
        1. Load session and history
        2. Store user message
        3. Get RAG context
        4. Build prompt with personality + RAG + history
        5. Generate LLM response
        6. Extract safety warnings
        7. Store assistant message
        8. Return formatted response

        Args:
            session_id: Session UUID
            user_message: User's question/message

        Returns:
            SMEChatResponse with answer, confidence, sources, warnings

        Raises:
            ValueError: If session not found or not active
        """
        logger.info(f"[SME Chat] Processing message for session {session_id}")

        # Load session
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        if session.status != SessionStatus.ACTIVE:
            raise ValueError(f"Session not active: {session_id} (status={session.status})")

        # Get personality
        personality = get_personality(session.sme_vendor.value)

        # Store user message
        await self._add_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=user_message
        )

        # Get conversation history
        history = await self._get_conversation_history(session_id, limit=10)

        # Get RAG context
        atoms, formatted_context = await self.rag_service.get_relevant_context(
            query=user_message,
            manufacturer=session.sme_vendor.value,
            conversation_history=history,
            equipment_context=session.equipment_context,
            limit=5
        )

        # Calculate RAG confidence
        rag_confidence = calculate_rag_confidence(atoms)

        # Build full prompt
        full_prompt = self._build_chat_prompt(
            personality=personality,
            user_message=user_message,
            rag_context=formatted_context,
            conversation_history=history,
            equipment_context=session.equipment_context
        )

        # Generate LLM response
        llm_response = await self._generate_response(full_prompt)

        # Extract safety warnings
        safety_warnings = self._extract_safety_warnings(llm_response.text)

        # Extract sources from atoms
        sources = extract_sources_from_atoms(atoms)

        # Determine confidence level
        confidence_level = self._get_confidence_level(rag_confidence)

        # Get atom IDs for storage
        atom_ids = [atom['atom_id'] for atom in atoms if atom.get('atom_id')]

        # Store assistant message
        await self._add_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=llm_response.text,
            confidence=rag_confidence,
            rag_atoms_used=atom_ids,
            cost_usd=llm_response.cost_usd,
            safety_warnings=safety_warnings,
            sources=sources
        )

        # Increment usage for atoms that were used
        if atom_ids:
            await self.rag_service.increment_atom_usage(atom_ids)

        # Build response
        response = SMEChatResponse(
            response=llm_response.text,
            confidence=rag_confidence,
            confidence_level=confidence_level,
            sources=sources,
            rag_atoms_used=atom_ids,
            safety_warnings=safety_warnings,
            cost_usd=llm_response.cost_usd,
            sme_name=personality.name,
            sme_vendor=session.sme_vendor,
        )

        logger.info(
            f"[SME Chat] Response generated: confidence={rag_confidence:.0%}, "
            f"sources={len(sources)}, warnings={len(safety_warnings)}, "
            f"cost=${llm_response.cost_usd:.4f}"
        )

        return response

    async def close_session(self, session_id: UUID) -> bool:
        """
        Close an active SME chat session.

        Args:
            session_id: Session UUID

        Returns:
            True if closed, False if not found
        """
        query = """
            UPDATE sme_chat_sessions
            SET status = 'closed', closed_at = NOW()
            WHERE session_id = $1 AND status = 'active'
            RETURNING session_id
        """
        result = await self.db.fetch_one(query, session_id)

        if result:
            logger.info(f"[SME Chat] Session closed: {session_id}")
            return True

        logger.warning(f"[SME Chat] Session not found or already closed: {session_id}")
        return False

    async def get_session(self, session_id: UUID) -> Optional[SMEChatSession]:
        """Get session by ID."""
        query = """
            SELECT session_id, telegram_chat_id, sme_vendor, status, equipment_context,
                   created_at, last_message_at, closed_at
            FROM sme_chat_sessions
            WHERE session_id = $1
        """
        result = await self.db.fetch_one(query, session_id)
        if not result:
            return None

        return SMEChatSession(
            session_id=result['session_id'],
            telegram_chat_id=result['telegram_chat_id'],
            sme_vendor=SMEVendor(result['sme_vendor']),
            status=SessionStatus(result['status']),
            equipment_context=result['equipment_context'],
            created_at=result['created_at'],
            last_message_at=result['last_message_at'],
            closed_at=result['closed_at'],
        )

    async def get_active_session(self, telegram_chat_id: int) -> Optional[SMEChatSession]:
        """Get active session for a chat ID, if any."""
        query = """
            SELECT session_id, telegram_chat_id, sme_vendor, status, equipment_context,
                   created_at, last_message_at, closed_at
            FROM sme_chat_sessions
            WHERE telegram_chat_id = $1 AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """
        result = await self.db.fetch_one(query, telegram_chat_id)
        if not result:
            return None

        return SMEChatSession(
            session_id=result['session_id'],
            telegram_chat_id=result['telegram_chat_id'],
            sme_vendor=SMEVendor(result['sme_vendor']),
            status=SessionStatus(result['status']),
            equipment_context=result['equipment_context'],
            created_at=result['created_at'],
            last_message_at=result['last_message_at'],
            closed_at=result['closed_at'],
        )

    # ===== Private Methods =====

    async def _close_existing_session(self, telegram_chat_id: int) -> None:
        """Close any existing active session for a chat."""
        query = """
            UPDATE sme_chat_sessions
            SET status = 'closed', closed_at = NOW()
            WHERE telegram_chat_id = $1 AND status = 'active'
        """
        await self.db.execute(query, telegram_chat_id, fetch_mode="none")

    async def _add_message(
        self,
        session_id: UUID,
        role: MessageRole,
        content: str,
        confidence: Optional[float] = None,
        rag_atoms_used: Optional[List[UUID]] = None,
        cost_usd: Optional[float] = None,
        safety_warnings: Optional[List[str]] = None,
        sources: Optional[List[str]] = None
    ) -> UUID:
        """Add message to session."""
        query = """
            INSERT INTO sme_chat_messages (
                session_id, role, content, confidence, rag_atoms_used,
                cost_usd, safety_warnings, sources
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING message_id
        """
        result = await self.db.fetch_one(
            query,
            session_id,
            role.value,
            content,
            confidence,
            rag_atoms_used,
            cost_usd,
            safety_warnings,
            sources
        )
        return result['message_id']

    async def _get_conversation_history(
        self,
        session_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """Get recent conversation history for context."""
        query = """
            SELECT role, content
            FROM sme_chat_messages
            WHERE session_id = $1 AND role != 'system'
            ORDER BY created_at DESC
            LIMIT $2
        """
        results = await self.db.fetch_all(query, session_id, limit)

        # Reverse to chronological order
        history = []
        for row in reversed(results):
            history.append({
                "role": row['role'],
                "content": row['content']
            })

        return history

    def _build_chat_prompt(
        self,
        personality: SMEPersonality,
        user_message: str,
        rag_context: str,
        conversation_history: List[Dict[str, str]],
        equipment_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build complete prompt for LLM."""
        parts = []

        # System-level personality instructions
        parts.append(f"You are {personality.name}, {personality.tagline}.")
        parts.append(personality.system_prompt_additions)
        parts.append(f"\nSafety emphasis: {personality.voice.safety_emphasis}")

        # Equipment context
        if equipment_context:
            parts.append("\n## Current Equipment Context")
            if equipment_context.get("model"):
                parts.append(f"- Model: {equipment_context['model']}")
            if equipment_context.get("serial"):
                parts.append(f"- Serial: {equipment_context['serial']}")
            if equipment_context.get("recent_faults"):
                parts.append(f"- Recent faults: {', '.join(equipment_context['recent_faults'])}")

        # RAG context
        parts.append(f"\n{rag_context}")

        # Conversation history
        if conversation_history:
            parts.append("\n## Recent Conversation")
            for msg in conversation_history[-6:]:  # Last 3 exchanges
                role_label = "User" if msg['role'] == 'user' else personality.name
                parts.append(f"{role_label}: {msg['content'][:300]}")

        # Current user message
        parts.append(f"\n## Current Question\nUser: {user_message}")

        # Response instructions
        parts.append(f"""
## Response Guidelines
1. Respond in character as {personality.name}
2. Use your characteristic phrases naturally
3. Provide technically accurate, actionable guidance
4. Include safety warnings when relevant (HIGH VOLTAGE, LOTO, etc.)
5. Reference the knowledge base context when available
6. If unsure, say so and suggest where to find more information
7. Keep response focused and practical for a field technician

{personality.name}:""")

        return "\n".join(parts)

    async def _generate_response(self, prompt: str) -> LLMResponse:
        """Generate response using LLM router."""
        try:
            response = await self.llm_router.generate(
                prompt=prompt,
                capability=ModelCapability.MODERATE,
                max_tokens=1500,
                temperature=0.7
            )
            return response
        except Exception as e:
            logger.error(f"[SME Chat] LLM generation failed: {e}")
            # Return fallback response
            return LLMResponse(
                text="I apologize, but I'm having trouble processing your request right now. Please try again in a moment, or try rephrasing your question.",
                cost_usd=0.0,
                model="fallback",
                provider="none"
            )

    def _extract_safety_warnings(self, response_text: str) -> List[str]:
        """Extract safety warnings from response text."""
        warnings = []
        response_lower = response_text.lower()

        for pattern, warning_text in SAFETY_PATTERNS:
            if re.search(pattern, response_lower):
                formatted_warning = f"⚠️ {warning_text}"
                if formatted_warning not in warnings:
                    warnings.append(formatted_warning)

        return warnings

    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Determine confidence level from score."""
        if confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.70:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW


__all__ = ["SMEChatService"]
