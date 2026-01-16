"""
Unit Tests for SME Chat Service

Tests with mocked database and LLM for isolated unit testing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from datetime import datetime

from rivet.services.sme_chat_service import SMEChatService
from rivet.models.sme_chat import (
    SMEChatSession,
    SMEChatResponse,
    SMEVendor,
    SessionStatus,
    MessageRole,
    ConfidenceLevel,
)
from rivet.integrations.llm import LLMResponse


# ===== Fixtures =====

@pytest.fixture
def mock_db():
    """Create mock database with proper AtlasDatabase interface."""
    db = MagicMock()
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock()
    db.execute = AsyncMock()
    # AtlasDatabase attributes that might be accessed
    db.pool = MagicMock()
    db._connected = True
    db.connect = AsyncMock()
    db.close = AsyncMock()
    return db


@pytest.fixture
def mock_rag_service():
    """Create mock RAG service."""
    rag = MagicMock()
    rag.get_relevant_context = AsyncMock(return_value=(
        [
            {
                "atom_id": uuid4(),
                "title": "Test Atom",
                "content": "Test content for the atom",
                "source_url": "https://example.com/manual",
                "similarity": 0.85,
            }
        ],
        "## Relevant Knowledge Base Context\n\nTest formatted context"
    ))
    rag.increment_atom_usage = AsyncMock()
    return rag


@pytest.fixture
def mock_llm_router():
    """Create mock LLM router."""
    router = MagicMock()
    router.generate = AsyncMock(return_value=LLMResponse(
        text="This is a test response from the SME.",
        cost_usd=0.001,
        model="test-model",
        provider="test-provider"
    ))
    return router


@pytest.fixture
def sme_service(mock_db, mock_rag_service, mock_llm_router):
    """Create SMEChatService with mocked dependencies."""
    # Use patch to avoid settings/config loading issues
    with patch('rivet.services.sme_chat_service.AtlasDatabase'):
        service = SMEChatService(db=mock_db, rag_service=mock_rag_service)
        service.llm_router = mock_llm_router
        return service


@pytest.fixture
def sample_session_id():
    """Sample session UUID."""
    return uuid4()


@pytest.fixture
def sample_session_data(sample_session_id):
    """Sample session database row."""
    return {
        "session_id": sample_session_id,
        "telegram_chat_id": 12345678,
        "sme_vendor": "siemens",
        "status": "active",
        "equipment_context": {"model": "G120C"},
        "created_at": datetime.now(),
        "last_message_at": datetime.now(),
        "closed_at": None,
    }


# ===== Test Start Session =====

class TestStartSession:
    """Test start_session method."""

    @pytest.mark.asyncio
    async def test_start_session_creates_record(self, sme_service, mock_db, sample_session_id):
        """Test that start_session creates a database record."""
        mock_db.fetch_one.side_effect = [
            # First call: create session
            {
                "session_id": sample_session_id,
                "telegram_chat_id": 12345678,
                "sme_vendor": "siemens",
                "status": "active",
                "equipment_context": None,
                "created_at": datetime.now(),
                "last_message_at": datetime.now(),
                "closed_at": None,
            },
            # Second call: add system message
            {"message_id": uuid4()},
        ]

        session = await sme_service.start_session(
            telegram_chat_id=12345678,
            sme_vendor="siemens"
        )

        assert session.session_id == sample_session_id
        assert session.telegram_chat_id == 12345678
        assert session.sme_vendor == SMEVendor.SIEMENS
        assert session.status == SessionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_start_session_adds_system_message(self, sme_service, mock_db, sample_session_id):
        """Test that start_session adds system message with personality."""
        mock_db.fetch_one.side_effect = [
            # First call: create session
            {
                "session_id": sample_session_id,
                "telegram_chat_id": 12345678,
                "sme_vendor": "siemens",
                "status": "active",
                "equipment_context": None,
                "created_at": datetime.now(),
                "last_message_at": datetime.now(),
                "closed_at": None,
            },
            # Second call: add message
            {"message_id": uuid4()},
        ]

        await sme_service.start_session(
            telegram_chat_id=12345678,
            sme_vendor="siemens"
        )

        # Verify _add_message was called (via fetch_one for INSERT)
        assert mock_db.fetch_one.call_count >= 2

    @pytest.mark.asyncio
    async def test_start_session_with_equipment_context(self, sme_service, mock_db, sample_session_id):
        """Test start_session with equipment context."""
        equipment = {"model": "G120C", "serial": "ABC123"}
        mock_db.fetch_one.side_effect = [
            # First call: create session
            {
                "session_id": sample_session_id,
                "telegram_chat_id": 12345678,
                "sme_vendor": "siemens",
                "status": "active",
                "equipment_context": equipment,
                "created_at": datetime.now(),
                "last_message_at": datetime.now(),
                "closed_at": None,
            },
            # Second call: add system message
            {"message_id": uuid4()},
        ]

        session = await sme_service.start_session(
            telegram_chat_id=12345678,
            sme_vendor="siemens",
            equipment_context=equipment
        )

        assert session.equipment_context == equipment


# ===== Test Chat =====

class TestChat:
    """Test chat method."""

    @pytest.mark.asyncio
    async def test_chat_returns_response(
        self, sme_service, mock_db, mock_rag_service, mock_llm_router, sample_session_id, sample_session_data
    ):
        """Test chat returns properly formatted response."""
        # Setup mocks
        mock_db.fetch_one.side_effect = [
            sample_session_data,  # get_session
            {"message_id": uuid4()},  # add user message
            {"message_id": uuid4()},  # add assistant message
        ]
        mock_db.fetch_all.return_value = []  # conversation history

        response = await sme_service.chat(
            session_id=sample_session_id,
            user_message="What causes F0002 fault?"
        )

        assert isinstance(response, SMEChatResponse)
        assert response.response  # Has response text
        assert response.confidence >= 0.0
        assert response.sme_name == "Hans"  # Siemens SME
        assert response.sme_vendor == SMEVendor.SIEMENS

    @pytest.mark.asyncio
    async def test_chat_includes_all_fields(
        self, sme_service, mock_db, sample_session_id, sample_session_data
    ):
        """Test chat response has all required fields."""
        mock_db.fetch_one.side_effect = [
            sample_session_data,
            {"message_id": uuid4()},
            {"message_id": uuid4()},
        ]
        mock_db.fetch_all.return_value = []

        response = await sme_service.chat(
            session_id=sample_session_id,
            user_message="Test question"
        )

        # Check all fields exist
        assert hasattr(response, 'response')
        assert hasattr(response, 'confidence')
        assert hasattr(response, 'confidence_level')
        assert hasattr(response, 'sources')
        assert hasattr(response, 'rag_atoms_used')
        assert hasattr(response, 'safety_warnings')
        assert hasattr(response, 'cost_usd')
        assert hasattr(response, 'sme_name')
        assert hasattr(response, 'sme_vendor')

    @pytest.mark.asyncio
    async def test_chat_session_not_found_raises_error(self, sme_service, mock_db, sample_session_id):
        """Test chat raises error if session not found."""
        mock_db.fetch_one.return_value = None

        with pytest.raises(ValueError, match="Session not found"):
            await sme_service.chat(
                session_id=sample_session_id,
                user_message="Test"
            )

    @pytest.mark.asyncio
    async def test_chat_inactive_session_raises_error(self, sme_service, mock_db, sample_session_id):
        """Test chat raises error if session is not active."""
        mock_db.fetch_one.return_value = {
            "session_id": sample_session_id,
            "telegram_chat_id": 12345678,
            "sme_vendor": "siemens",
            "status": "closed",  # Not active
            "equipment_context": None,
            "created_at": datetime.now(),
            "last_message_at": datetime.now(),
            "closed_at": datetime.now(),
        }

        with pytest.raises(ValueError, match="Session not active"):
            await sme_service.chat(
                session_id=sample_session_id,
                user_message="Test"
            )


# ===== Test Close Session =====

class TestCloseSession:
    """Test close_session method."""

    @pytest.mark.asyncio
    async def test_close_session_updates_status(self, sme_service, mock_db, sample_session_id):
        """Test close_session updates status to closed."""
        mock_db.fetch_one.return_value = {"session_id": sample_session_id}

        result = await sme_service.close_session(sample_session_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_close_session_not_found(self, sme_service, mock_db, sample_session_id):
        """Test close_session returns False if session not found."""
        mock_db.fetch_one.return_value = None

        result = await sme_service.close_session(sample_session_id)

        assert result is False


# ===== Test Confidence Level =====

class TestConfidenceLevel:
    """Test confidence level calculation."""

    def test_high_confidence(self, sme_service):
        """Test HIGH confidence for >= 0.85."""
        assert sme_service._get_confidence_level(0.85) == ConfidenceLevel.HIGH
        assert sme_service._get_confidence_level(0.90) == ConfidenceLevel.HIGH
        assert sme_service._get_confidence_level(1.0) == ConfidenceLevel.HIGH

    def test_medium_confidence(self, sme_service):
        """Test MEDIUM confidence for 0.70-0.85."""
        assert sme_service._get_confidence_level(0.70) == ConfidenceLevel.MEDIUM
        assert sme_service._get_confidence_level(0.75) == ConfidenceLevel.MEDIUM
        assert sme_service._get_confidence_level(0.84) == ConfidenceLevel.MEDIUM

    def test_low_confidence(self, sme_service):
        """Test LOW confidence for < 0.70."""
        assert sme_service._get_confidence_level(0.69) == ConfidenceLevel.LOW
        assert sme_service._get_confidence_level(0.50) == ConfidenceLevel.LOW
        assert sme_service._get_confidence_level(0.0) == ConfidenceLevel.LOW


# ===== Test Safety Warning Extraction =====

class TestSafetyWarnings:
    """Test safety warning extraction."""

    def test_extract_voltage_warning(self, sme_service):
        """Test voltage warning extraction."""
        text = "Be careful of 480V power supply"
        warnings = sme_service._extract_safety_warnings(text)
        assert any("VOLTAGE" in w for w in warnings)

    def test_extract_loto_warning(self, sme_service):
        """Test LOTO warning extraction."""
        text = "Follow lockout tagout procedures"
        warnings = sme_service._extract_safety_warnings(text)
        assert any("LOTO" in w for w in warnings)

    def test_extract_arc_flash_warning(self, sme_service):
        """Test arc flash warning extraction."""
        text = "Arc flash hazard present"
        warnings = sme_service._extract_safety_warnings(text)
        assert any("ARC FLASH" in w for w in warnings)

    def test_no_warnings_for_safe_text(self, sme_service):
        """Test no warnings for text without hazards."""
        text = "The programming is complete."
        warnings = sme_service._extract_safety_warnings(text)
        assert len(warnings) == 0


# ===== Test Get Session =====

class TestGetSession:
    """Test get_session and get_active_session methods."""

    @pytest.mark.asyncio
    async def test_get_session_returns_session(self, sme_service, mock_db, sample_session_id, sample_session_data):
        """Test get_session returns session model."""
        mock_db.fetch_one.return_value = sample_session_data

        session = await sme_service.get_session(sample_session_id)

        assert session is not None
        assert session.session_id == sample_session_id
        assert isinstance(session, SMEChatSession)

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, sme_service, mock_db, sample_session_id):
        """Test get_session returns None if not found."""
        mock_db.fetch_one.return_value = None

        session = await sme_service.get_session(sample_session_id)

        assert session is None

    @pytest.mark.asyncio
    async def test_get_active_session(self, sme_service, mock_db, sample_session_data):
        """Test get_active_session returns active session for chat."""
        mock_db.fetch_one.return_value = sample_session_data

        session = await sme_service.get_active_session(telegram_chat_id=12345678)

        assert session is not None
        assert session.status == SessionStatus.ACTIVE
