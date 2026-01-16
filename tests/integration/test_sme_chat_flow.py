"""
Integration Tests for SME Chat Flow

Tests the full SME chat flow from session start to response generation.
Uses real database connection but mocks LLM for deterministic results.

Run with: pytest tests/integration/test_sme_chat_flow.py -v
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Skip if database not available
pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set"
)

from rivet.services.sme_chat_service import SMEChatService
from rivet.services.sme_rag_service import SMERagService
from rivet.atlas.database import AtlasDatabase
from rivet.models.sme_chat import (
    SMEChatSession,
    SMEChatResponse,
    SMEVendor,
    SessionStatus,
    ConfidenceLevel,
)
from rivet.prompts.sme.personalities import get_personality
from rivet.integrations.llm import LLMResponse


# ===== Fixtures =====

@pytest.fixture
async def db():
    """Create real database connection."""
    database = AtlasDatabase()
    await database.connect()
    yield database
    await database.close()


@pytest.fixture
def mock_llm_router():
    """Create mock LLM router for deterministic responses."""
    router = MagicMock()
    router.generate = AsyncMock(return_value=LLMResponse(
        text="Based on my experience with Siemens drives, the F0002 fault typically indicates an undervoltage condition. Check your DC bus voltage and ensure the input power is stable. IMPORTANT: Always follow LOTO procedures before inspecting the drive. The most common causes are: 1) Power supply issues, 2) DC link capacitor problems, 3) Input fuse issues.",
        cost_usd=0.002,
        model="claude-3-haiku",
        provider="anthropic"
    ))
    return router


@pytest.fixture
def mock_rag_service():
    """Create mock RAG service with realistic data."""
    rag = MagicMock(spec=SMERagService)
    rag.get_relevant_context = AsyncMock(return_value=(
        [
            {
                "atom_id": uuid4(),
                "title": "SINAMICS G120 Fault Codes",
                "content": "F0002: DC link undervoltage. The DC link voltage has dropped below the minimum threshold. Check input power supply and DC link capacitors.",
                "source_url": "https://support.siemens.com/manual/g120/faults",
                "similarity": 0.92,
            },
            {
                "atom_id": uuid4(),
                "title": "SINAMICS Troubleshooting Guide",
                "content": "For undervoltage faults, verify: 1) Input voltage is within specs, 2) No loose connections, 3) DC link capacitors are healthy.",
                "source_url": "https://support.siemens.com/manual/g120/troubleshooting",
                "similarity": 0.85,
            },
        ],
        "## Relevant Knowledge Base Context\n\n**SINAMICS G120 Fault Codes** (92% match)\nF0002: DC link undervoltage. The DC link voltage has dropped below the minimum threshold.\n\n**SINAMICS Troubleshooting Guide** (85% match)\nFor undervoltage faults, verify input voltage, connections, and DC link capacitors."
    ))
    rag.increment_atom_usage = AsyncMock()
    return rag


@pytest.fixture
async def sme_service(db, mock_rag_service, mock_llm_router):
    """Create SMEChatService with real DB but mocked LLM and RAG."""
    service = SMEChatService(db=db, rag_service=mock_rag_service)
    service.llm_router = mock_llm_router
    return service


@pytest.fixture
def unique_chat_id():
    """Generate unique Telegram chat ID for test isolation."""
    # Use timestamp-based ID to avoid collisions
    import time
    return int(time.time() * 1000) % 2147483647  # Keep within int32 range


# ===== Test: Start Session with Siemens Personality =====

class TestSiemensSession:
    """Test SME chat session with Siemens (Hans) personality."""

    @pytest.mark.asyncio
    async def test_start_session_creates_siemens_session(self, sme_service, unique_chat_id):
        """Test: /chat siemens creates session with Hans personality."""
        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="siemens"
        )

        assert session is not None
        assert session.telegram_chat_id == unique_chat_id
        assert session.sme_vendor == "siemens"  # Stored as string due to use_enum_values
        assert session.status == "active"

        # Verify Hans personality would be used
        personality = get_personality("siemens")
        assert personality.name == "Hans"

    @pytest.mark.asyncio
    async def test_chat_returns_hans_response(self, sme_service, unique_chat_id):
        """Test: Ask question and verify Hans personality in response."""
        # Start session
        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="siemens"
        )

        # Ask a question
        response = await sme_service.chat(
            session_id=session.session_id,
            user_message="What causes F0002 fault on a SINAMICS G120?"
        )

        # Verify response structure
        assert isinstance(response, SMEChatResponse)
        assert response.response  # Has content
        assert response.sme_name == "Hans"
        assert response.sme_vendor == "siemens"
        assert response.confidence >= 0.0
        assert response.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_chat_extracts_safety_warnings(self, sme_service, unique_chat_id):
        """Test: Safety warnings are extracted from response."""
        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="siemens"
        )

        response = await sme_service.chat(
            session_id=session.session_id,
            user_message="How do I troubleshoot the drive?"
        )

        # The mock response contains "LOTO procedures" which should trigger warning
        assert response.safety_warnings is not None
        assert any("LOTO" in w for w in response.safety_warnings)


# ===== Test: Multi-Turn Conversation =====

class TestMultiTurnConversation:
    """Test multi-turn conversation preserves context."""

    @pytest.mark.asyncio
    async def test_multi_turn_preserves_context(self, sme_service, unique_chat_id, mock_rag_service):
        """Test: Multi-turn conversation maintains session context."""
        # Start session
        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="siemens",
            equipment_context={"model": "G120C", "serial": "SN12345"}
        )

        # First message
        response1 = await sme_service.chat(
            session_id=session.session_id,
            user_message="What causes F0002 fault?"
        )
        assert response1.response

        # Second message (follow-up)
        response2 = await sme_service.chat(
            session_id=session.session_id,
            user_message="How do I fix that?"
        )
        assert response2.response

        # RAG service should have been called with conversation history
        # (verify via mock call history)
        assert mock_rag_service.get_relevant_context.call_count == 2

        # Second call should include conversation history
        second_call_args = mock_rag_service.get_relevant_context.call_args_list[1]
        conv_history = second_call_args.kwargs.get('conversation_history', [])
        # History should include at least the first user message
        assert len(conv_history) >= 1


# ===== Test: RAG Integration =====

class TestRAGIntegration:
    """Test RAG atoms are retrieved and used."""

    @pytest.mark.asyncio
    async def test_rag_atoms_included_in_response(self, sme_service, unique_chat_id):
        """Test: RAG atoms are retrieved and sources are included."""
        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="siemens"
        )

        response = await sme_service.chat(
            session_id=session.session_id,
            user_message="What causes F0002 fault?"
        )

        # Sources should be extracted from RAG atoms
        assert response.sources is not None
        assert len(response.sources) > 0

        # RAG atoms used should be tracked
        assert response.rag_atoms_used is not None
        assert len(response.rag_atoms_used) > 0

    @pytest.mark.asyncio
    async def test_confidence_reflects_rag_quality(self, sme_service, unique_chat_id):
        """Test: Confidence level reflects RAG match quality."""
        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="siemens"
        )

        response = await sme_service.chat(
            session_id=session.session_id,
            user_message="What causes F0002 fault?"
        )

        # Mock returns 0.92 and 0.85 similarity
        # Confidence formula: (top * 0.6) + (avg_top3 * 0.4)
        # Expected: (0.92 * 0.6) + (0.885 * 0.4) = 0.552 + 0.354 = 0.906
        # This should be HIGH confidence (>= 0.85)
        assert response.confidence >= 0.70  # At least MEDIUM
        assert response.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]


# ===== Test: Session Lifecycle =====

class TestSessionLifecycle:
    """Test session start, chat, and close lifecycle."""

    @pytest.mark.asyncio
    async def test_close_session(self, sme_service, unique_chat_id):
        """Test: /endchat closes session."""
        # Start session
        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="siemens"
        )

        # Close session
        result = await sme_service.close_session(session.session_id)
        assert result is True

        # Verify session is closed
        closed_session = await sme_service.get_session(session.session_id)
        assert closed_session.status == "closed"

    @pytest.mark.asyncio
    async def test_chat_on_closed_session_raises_error(self, sme_service, unique_chat_id):
        """Test: Chatting on closed session raises error."""
        # Start and close session
        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="siemens"
        )
        await sme_service.close_session(session.session_id)

        # Try to chat on closed session
        with pytest.raises(ValueError, match="Session not active"):
            await sme_service.chat(
                session_id=session.session_id,
                user_message="This should fail"
            )

    @pytest.mark.asyncio
    async def test_get_active_session(self, sme_service, unique_chat_id):
        """Test: Get active session for chat ID."""
        # Start session
        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="rockwell"
        )

        # Get active session
        active = await sme_service.get_active_session(unique_chat_id)
        assert active is not None
        assert active.session_id == session.session_id
        assert active.sme_vendor == "rockwell"


# ===== Test: Different Vendors =====

class TestDifferentVendors:
    """Test different vendor personalities."""

    @pytest.mark.asyncio
    async def test_rockwell_session(self, sme_service, unique_chat_id):
        """Test: Rockwell session uses Mike personality."""
        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="rockwell"
        )

        response = await sme_service.chat(
            session_id=session.session_id,
            user_message="How do I configure Studio 5000?"
        )

        assert response.sme_name == "Mike"
        assert response.sme_vendor == "rockwell"

    @pytest.mark.asyncio
    async def test_abb_session(self, sme_service, unique_chat_id):
        """Test: ABB session uses Erik personality."""
        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="abb"
        )

        response = await sme_service.chat(
            session_id=session.session_id,
            user_message="What are ACS880 parameters?"
        )

        assert response.sme_name == "Erik"
        assert response.sme_vendor == "abb"


# ===== Test: Equipment Context =====

class TestEquipmentContext:
    """Test equipment context from OCR workflow."""

    @pytest.mark.asyncio
    async def test_session_with_equipment_context(self, sme_service, unique_chat_id):
        """Test: Session preserves equipment context from OCR."""
        equipment = {
            "model": "SINAMICS G120C",
            "serial": "6SL3210-1PE21-8UL0",
            "recent_faults": ["F0002", "F0001"]
        }

        session = await sme_service.start_session(
            telegram_chat_id=unique_chat_id,
            sme_vendor="siemens",
            equipment_context=equipment
        )

        assert session.equipment_context is not None
        assert session.equipment_context["model"] == "SINAMICS G120C"
        assert "F0002" in session.equipment_context["recent_faults"]


# ===== Cleanup Test Data =====

@pytest.fixture(autouse=True)
async def cleanup_test_sessions(db, unique_chat_id):
    """Clean up test sessions after each test."""
    yield
    # Cleanup: close any sessions created during test
    try:
        await db.execute(
            "DELETE FROM sme_chat_messages WHERE session_id IN (SELECT session_id FROM sme_chat_sessions WHERE telegram_chat_id = $1)",
            unique_chat_id,
            fetch_mode="none"
        )
        await db.execute(
            "DELETE FROM sme_chat_sessions WHERE telegram_chat_id = $1",
            unique_chat_id,
            fetch_mode="none"
        )
    except Exception:
        pass  # Ignore cleanup errors
