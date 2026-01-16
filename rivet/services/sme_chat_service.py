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

import json
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
        # Note: asyncpg requires JSONB to be passed as a JSON string
        equipment_json = json.dumps(equipment_context) if equipment_context else None
        query = """
            INSERT INTO sme_chat_sessions (telegram_chat_id, sme_vendor, status, equipment_context)
            VALUES ($1, $2, 'active', $3::jsonb)
            RETURNING session_id, telegram_chat_id, sme_vendor, status, equipment_context,
                      created_at, last_message_at, closed_at
        """
        result = await self.db.fetch_one(
            query,
            telegram_chat_id,
            sme_vendor.lower(),
            equipment_json
        )

        session = self._result_to_session(result)

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

        # Get personality (sme_vendor is already a string due to use_enum_values=True)
        personality = get_personality(session.sme_vendor)

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
            manufacturer=session.sme_vendor,  # Already a string due to use_enum_values=True
            conversation_history=history,
            equipment_context=session.equipment_context,
            limit=5
        )

        # Calculate RAG confidence
        rag_confidence = calculate_rag_confidence(atoms)
        confidence_level = self._get_confidence_level(rag_confidence)

        # Route based on confidence level
        llm_response = await self._route_by_confidence(
            confidence_level=confidence_level,
            rag_confidence=rag_confidence,
            atoms=atoms,
            formatted_context=formatted_context,
            personality=personality,
            user_message=user_message,
            conversation_history=history,
            equipment_context=session.equipment_context
        )

        # Extract safety warnings
        safety_warnings = self._extract_safety_warnings(llm_response.text)

        # Extract sources from atoms
        sources = extract_sources_from_atoms(atoms)

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

        return self._result_to_session(result)

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

        return self._result_to_session(result)

    def _result_to_session(self, result: Dict[str, Any]) -> SMEChatSession:
        """Convert database result to SMEChatSession model."""
        # Parse equipment_context if returned as string (asyncpg JSONB behavior varies)
        eq_context = result['equipment_context']
        if isinstance(eq_context, str):
            eq_context = json.loads(eq_context)

        return SMEChatSession(
            session_id=result['session_id'],
            telegram_chat_id=result['telegram_chat_id'],
            sme_vendor=SMEVendor(result['sme_vendor']),
            status=SessionStatus(result['status']),
            equipment_context=eq_context,
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

    # ===== Confidence-Based Routing =====

    async def _route_by_confidence(
        self,
        confidence_level: ConfidenceLevel,
        rag_confidence: float,
        atoms: List[Dict[str, Any]],
        formatted_context: str,
        personality: SMEPersonality,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        equipment_context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Route chat query based on RAG confidence level.

        - HIGH (>=0.85): Direct KB answer with SME voice styling
        - MEDIUM (0.70-0.85): Full SME synthesis from RAG context
        - LOW (<0.70): Generate clarifying questions

        Args:
            confidence_level: Calculated confidence level
            rag_confidence: Raw confidence score
            atoms: Retrieved knowledge atoms
            formatted_context: Pre-formatted RAG context
            personality: SME personality
            user_message: User's question
            conversation_history: Recent conversation
            equipment_context: Optional equipment context

        Returns:
            LLMResponse with appropriate response based on confidence
        """
        logger.info(
            f"[SME Chat] Routing: confidence={rag_confidence:.0%}, "
            f"level={confidence_level.value}, atoms={len(atoms)}"
        )

        if confidence_level == ConfidenceLevel.HIGH:
            return await self._format_direct_kb_answer(
                atoms=atoms,
                personality=personality,
                user_message=user_message
            )
        elif confidence_level == ConfidenceLevel.MEDIUM:
            return await self._generate_sme_synthesis(
                personality=personality,
                user_message=user_message,
                rag_context=formatted_context,
                conversation_history=conversation_history,
                equipment_context=equipment_context
            )
        else:  # LOW confidence
            return await self._generate_clarifying_questions(
                personality=personality,
                user_message=user_message,
                atoms=atoms,
                equipment_context=equipment_context
            )

    async def _format_direct_kb_answer(
        self,
        atoms: List[Dict[str, Any]],
        personality: SMEPersonality,
        user_message: str
    ) -> LLMResponse:
        """
        Format direct KB answer with minimal LLM processing.

        Used for HIGH confidence (>=0.85) when RAG has excellent match.
        Combines top atom content with SME voice styling.
        """
        if not atoms:
            # Fallback to synthesis if no atoms
            return await self._generate_response(
                f"As {personality.name}, briefly answer: {user_message}"
            )

        # Get top atom content
        top_atom = atoms[0]
        atom_content = top_atom.get('content', '')[:1500]
        atom_title = top_atom.get('title', 'Knowledge Base')

        # Build minimal prompt for voice styling
        prompt = f"""You are {personality.name}, {personality.tagline}.

Add minimal SME voice styling to this knowledge base answer. Keep it brief and technical.
DO NOT add new information - just style the existing content with your voice.

Knowledge Base Content ({atom_title}):
{atom_content}

User Question: {user_message}

Respond as {personality.name} with ONE of your thinking phrases, then the answer, then ONE closing phrase.
Keep it concise - the KB content is authoritative."""

        try:
            response = await self.llm_router.generate(
                prompt=prompt,
                capability=ModelCapability.SIMPLE,  # Use cheaper model for styling
                max_tokens=800,
                temperature=0.3  # Low temperature for consistency
            )
            logger.info(f"[SME Chat] Direct KB answer: {len(response.text)} chars")
            return response
        except Exception as e:
            logger.error(f"[SME Chat] Direct KB formatting failed: {e}")
            # Return raw KB content as fallback
            return LLMResponse(
                text=f"{atom_content}\n\n_Source: {atom_title}_",
                cost_usd=0.0,
                model="fallback",
                provider="none"
            )

    async def _generate_sme_synthesis(
        self,
        personality: SMEPersonality,
        user_message: str,
        rag_context: str,
        conversation_history: List[Dict[str, str]],
        equipment_context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Generate full SME synthesis from RAG context.

        Used for MEDIUM confidence (0.70-0.85) when RAG has relevant but
        not exact matches. LLM synthesizes comprehensive answer.
        """
        # Use existing _build_chat_prompt and _generate_response
        full_prompt = self._build_chat_prompt(
            personality=personality,
            user_message=user_message,
            rag_context=rag_context,
            conversation_history=conversation_history,
            equipment_context=equipment_context
        )
        return await self._generate_response(full_prompt)

    async def _generate_clarifying_questions(
        self,
        personality: SMEPersonality,
        user_message: str,
        atoms: List[Dict[str, Any]],
        equipment_context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Generate clarifying questions when confidence is low.

        Used for LOW confidence (<0.70) when RAG doesn't have good matches.
        Asks user for more specific information to provide better answer.
        """
        # Extract what partial info we have
        partial_topics = []
        for atom in atoms[:3]:
            if atom.get('title'):
                partial_topics.append(atom['title'])

        # Build prompt for clarifying questions
        equipment_info = ""
        if equipment_context:
            if equipment_context.get('model'):
                equipment_info = f"Equipment: {equipment_context['model']}"

        prompt = f"""You are {personality.name}, {personality.tagline}.

The user asked a question but I don't have enough information to give a confident answer.

User Question: {user_message}
{equipment_info}

Related topics I found (but not confident matches):
{', '.join(partial_topics) if partial_topics else 'None found'}

Generate a helpful response that:
1. Acknowledge you understood the question
2. Explain what additional information would help (2-3 specific clarifying questions)
3. Offer what general guidance you can based on the question
4. Stay in character as {personality.name}

Keep it conversational and helpful, not frustrating."""

        try:
            response = await self.llm_router.generate(
                prompt=prompt,
                capability=ModelCapability.SIMPLE,  # Clarifying questions are simpler
                max_tokens=600,
                temperature=0.5
            )
            logger.info(f"[SME Chat] Clarifying questions generated")
            return response
        except Exception as e:
            logger.error(f"[SME Chat] Clarifying questions failed: {e}")
            # Return basic fallback
            fallback = (
                f"I'd like to help, but I need a bit more information. "
                f"Could you tell me:\n"
                f"- What specific equipment or system you're working with?\n"
                f"- What symptoms or error codes you're seeing?\n"
                f"- What you've already tried?\n\n"
                f"This will help me give you more accurate guidance."
            )
            return LLMResponse(
                text=fallback,
                cost_usd=0.0,
                model="fallback",
                provider="none"
            )


__all__ = ["SMEChatService"]
