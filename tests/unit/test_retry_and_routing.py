"""
Unit Tests for Retry Logic and Confidence-Based Routing

PHOTO-TEST-001: Tests for retry logic with simulated transient failures
and confidence threshold routing logic.
"""

import pytest
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rivet_pro.core.models.screening import ScreeningResult
from rivet_pro.core.models.extraction import ExtractionResult
from rivet_pro.core.services.screening_service import (
    screen_industrial_photo,
    should_proceed_to_ocr,
    CONFIDENCE_THRESHOLD,
)
from rivet_pro.core.services.extraction_service import (
    extract_component_specs,
    MIN_SCREENING_CONFIDENCE,
)


# =============================================================================
# Retry Logic Tests - Simulated Transient Failures
# =============================================================================

class TestRetryLogicGroq:
    """Tests for retry behavior in Groq screening service."""

    @pytest.fixture
    def test_image_b64(self):
        """Create test image base64."""
        return base64.b64encode(b"test image for retry").decode()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    @patch("rivet_pro.core.services.screening_service.Groq")
    async def test_transient_connection_error(self, mock_groq_class, mock_settings, test_image_b64):
        """Test handling of transient connection errors."""
        mock_settings.groq_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ConnectionError("Connection reset by peer")
        mock_groq_class.return_value = mock_client

        result = await screen_industrial_photo(test_image_b64)

        assert not result.is_successful
        assert result.error is not None
        assert "connection" in result.error.lower()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    @patch("rivet_pro.core.services.screening_service.Groq")
    async def test_transient_timeout_error(self, mock_groq_class, mock_settings, test_image_b64):
        """Test handling of transient timeout errors."""
        mock_settings.groq_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = TimeoutError("Request timed out after 30s")
        mock_groq_class.return_value = mock_client

        result = await screen_industrial_photo(test_image_b64)

        assert not result.is_successful
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    @patch("rivet_pro.core.services.screening_service.Groq")
    async def test_transient_rate_limit_error(self, mock_groq_class, mock_settings, test_image_b64):
        """Test handling of rate limit errors."""
        mock_settings.groq_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_groq_class.return_value = mock_client

        result = await screen_industrial_photo(test_image_b64)

        assert not result.is_successful
        assert "rate limit" in result.error.lower()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    @patch("rivet_pro.core.services.screening_service.Groq")
    async def test_transient_500_error(self, mock_groq_class, mock_settings, test_image_b64):
        """Test handling of 500 server errors."""
        mock_settings.groq_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Internal Server Error (500)")
        mock_groq_class.return_value = mock_client

        result = await screen_industrial_photo(test_image_b64)

        assert not result.is_successful
        assert "500" in result.error or "server" in result.error.lower()


class TestRetryLogicDeepSeek:
    """Tests for retry behavior in DeepSeek extraction service."""

    @pytest.fixture
    def test_image_b64(self):
        return base64.b64encode(b"test image for deepseek retry").decode()

    @pytest.fixture
    def passing_screening(self):
        return ScreeningResult(is_industrial=True, confidence=0.90)

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    @patch("rivet_pro.core.services.extraction_service.OpenAI")
    async def test_transient_connection_error(self, mock_openai_class, mock_settings,
                                              passing_screening, test_image_b64):
        """Test handling of transient connection errors."""
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ConnectionError("Network unreachable")
        mock_openai_class.return_value = mock_client

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None  # Cache miss

        result = await extract_component_specs(test_image_b64, passing_screening, db=mock_db)

        assert not result.is_successful
        assert "network" in result.error.lower() or "connection" in result.error.lower()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    @patch("rivet_pro.core.services.extraction_service.OpenAI")
    async def test_transient_timeout_error(self, mock_openai_class, mock_settings,
                                           passing_screening, test_image_b64):
        """Test handling of transient timeout errors."""
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = TimeoutError("Request timeout")
        mock_openai_class.return_value = mock_client

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None

        result = await extract_component_specs(test_image_b64, passing_screening, db=mock_db)

        assert not result.is_successful
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    @patch("rivet_pro.core.services.extraction_service.OpenAI")
    async def test_transient_ssl_error(self, mock_openai_class, mock_settings,
                                       passing_screening, test_image_b64):
        """Test handling of SSL/TLS errors."""
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("SSL certificate verify failed")
        mock_openai_class.return_value = mock_client

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None

        result = await extract_component_specs(test_image_b64, passing_screening, db=mock_db)

        assert not result.is_successful
        assert "ssl" in result.error.lower()


class TestRetryLogicClaude:
    """Tests for retry behavior in Claude analysis service."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.claude_analyzer.settings")
    @patch("rivet_pro.core.services.claude_analyzer.Anthropic")
    async def test_transient_overloaded_error(self, mock_anthropic_class, mock_settings):
        """Test handling of Claude overloaded errors."""
        from rivet_pro.core.services.claude_analyzer import ClaudeAnalyzer
        from uuid import uuid4

        mock_settings.anthropic_api_key = "test-key"

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Overloaded_error")
        mock_anthropic_class.return_value = mock_client

        analyzer = ClaudeAnalyzer()
        result = await analyzer.analyze_with_kb(
            equipment_id=uuid4(),
            specs={"manufacturer": "Test"},
            history=[],
            kb_context=[]
        )

        # Should return fallback result
        assert result.model == "fallback"

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.claude_analyzer.settings")
    @patch("rivet_pro.core.services.claude_analyzer.Anthropic")
    async def test_transient_api_error(self, mock_anthropic_class, mock_settings):
        """Test handling of generic API errors."""
        from rivet_pro.core.services.claude_analyzer import ClaudeAnalyzer
        from uuid import uuid4

        mock_settings.anthropic_api_key = "test-key"

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error: Internal error")
        mock_anthropic_class.return_value = mock_client

        analyzer = ClaudeAnalyzer()
        result = await analyzer.analyze_with_kb(
            equipment_id=uuid4(),
            specs={"manufacturer": "Test"},
            history=[],
            kb_context=[]
        )

        assert result.model == "fallback"


# =============================================================================
# Confidence Threshold Routing Tests
# =============================================================================

class TestConfidenceThresholds:
    """Tests for confidence threshold constants and boundary conditions."""

    def test_screening_threshold_value(self):
        """Test screening threshold is exactly 0.80."""
        assert CONFIDENCE_THRESHOLD == 0.80

    def test_extraction_threshold_value(self):
        """Test extraction minimum confidence is 0.80."""
        assert MIN_SCREENING_CONFIDENCE == 0.80

    def test_threshold_boundary_exactly_at(self):
        """Test confidence exactly at threshold passes."""
        result = ScreeningResult(
            is_industrial=True,
            confidence=0.80
        )
        assert result.passes_threshold

    def test_threshold_boundary_just_below(self):
        """Test confidence just below threshold fails."""
        result = ScreeningResult(
            is_industrial=True,
            confidence=0.7999
        )
        assert not result.passes_threshold

    def test_threshold_boundary_just_above(self):
        """Test confidence just above threshold passes."""
        result = ScreeningResult(
            is_industrial=True,
            confidence=0.8001
        )
        assert result.passes_threshold


class TestRoutingLogic:
    """Tests for pipeline routing based on confidence."""

    @pytest.fixture
    def test_image_b64(self):
        return base64.b64encode(b"test image for routing").decode()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.screen_industrial_photo")
    async def test_high_confidence_proceeds(self, mock_screen, test_image_b64):
        """Test high confidence image proceeds to OCR."""
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.95,
            category="vfd"
        )

        should_proceed, result = await should_proceed_to_ocr(test_image_b64)

        assert should_proceed is True
        assert result.passes_threshold

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.screen_industrial_photo")
    async def test_low_confidence_rejected(self, mock_screen, test_image_b64):
        """Test low confidence image is rejected."""
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.65,
            category="motor"
        )

        should_proceed, result = await should_proceed_to_ocr(test_image_b64)

        assert should_proceed is False
        assert not result.passes_threshold

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.screen_industrial_photo")
    async def test_non_industrial_rejected(self, mock_screen, test_image_b64):
        """Test non-industrial image is rejected regardless of confidence."""
        mock_screen.return_value = ScreeningResult(
            is_industrial=False,
            confidence=0.95  # High confidence it's NOT industrial
        )

        should_proceed, result = await should_proceed_to_ocr(test_image_b64)

        assert should_proceed is False

    @pytest.mark.asyncio
    async def test_extraction_rejects_low_screening(self):
        """Test extraction rejects if screening confidence was too low."""
        low_screening = ScreeningResult(
            is_industrial=True,
            confidence=0.75  # Below threshold
        )

        image_b64 = base64.b64encode(b"test").decode()
        result = await extract_component_specs(image_b64, low_screening)

        assert result.error is not None
        assert "threshold" in result.error.lower()

    @pytest.mark.asyncio
    async def test_extraction_accepts_high_screening(self):
        """Test extraction accepts if screening confidence passes."""
        high_screening = ScreeningResult(
            is_industrial=True,
            confidence=0.85
        )

        # Will fail due to missing API key, but should NOT fail on threshold check
        image_b64 = base64.b64encode(b"test").decode()

        with patch("rivet_pro.core.services.extraction_service.settings") as mock_settings:
            mock_settings.deepseek_api_key = None

            mock_db = AsyncMock()
            mock_db.fetchrow.return_value = None

            result = await extract_component_specs(image_b64, high_screening, db=mock_db)

            # Should fail on API key, not threshold
            assert result.error is not None
            assert "threshold" not in result.error.lower()
            assert "DEEPSEEK_API_KEY" in result.error


class TestRoutingFlowIntegration:
    """Integration tests for full routing flow."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    @patch("rivet_pro.core.services.extraction_service.OpenAI")
    async def test_full_pipeline_high_confidence(self, mock_openai_class, mock_settings):
        """Test full pipeline with high confidence screening."""
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        # Mock DeepSeek response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "manufacturer": "Allen-Bradley",
            "model_number": "PF525",
            "serial_number": None,
            "specs": {"voltage": "480V"},
            "raw_text": "Allen-Bradley PowerFlex 525",
            "confidence": 0.90,
            "text_quality_issues": []
        })
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Create high-confidence screening result
        screening = ScreeningResult(
            is_industrial=True,
            confidence=0.92,
            category="vfd"
        )

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None  # Cache miss

        image_b64 = base64.b64encode(b"test image").decode()
        result = await extract_component_specs(image_b64, screening, db=mock_db)

        assert result.is_successful
        assert result.manufacturer == "Allen-Bradley"
        assert result.model_number == "PF525"

    @pytest.mark.asyncio
    async def test_full_pipeline_low_confidence_blocked(self):
        """Test full pipeline blocks on low confidence screening."""
        # Create low-confidence screening result
        screening = ScreeningResult(
            is_industrial=True,
            confidence=0.70,  # Below 0.80 threshold
            category="motor"
        )

        image_b64 = base64.b64encode(b"test image").decode()
        result = await extract_component_specs(image_b64, screening)

        # Should be rejected at threshold check, not API call
        assert not result.is_successful
        assert "threshold" in result.error.lower()


# =============================================================================
# Category-Based Routing Tests
# =============================================================================

class TestCategoryRouting:
    """Tests for routing based on equipment category."""

    def test_all_categories_pass_threshold(self):
        """Test all industrial categories can pass threshold."""
        categories = ["plc", "vfd", "motor", "pump", "control_panel", "sensor", "other"]

        for category in categories:
            result = ScreeningResult(
                is_industrial=True,
                confidence=0.90,
                category=category
            )
            assert result.passes_threshold
            assert result.category == category

    def test_none_category_can_pass(self):
        """Test None category can still pass if industrial and high confidence."""
        result = ScreeningResult(
            is_industrial=True,
            confidence=0.85,
            category=None
        )
        assert result.passes_threshold


# =============================================================================
# Error State Routing Tests
# =============================================================================

class TestErrorStateRouting:
    """Tests for routing when errors occur."""

    def test_screening_error_blocks_pipeline(self):
        """Test screening error blocks pipeline progression."""
        result = ScreeningResult(error="API connection failed")

        assert not result.passes_threshold
        assert not result.is_successful

    @pytest.mark.asyncio
    async def test_extraction_with_errored_screening(self):
        """Test extraction rejects errored screening result."""
        error_screening = ScreeningResult(error="Screening failed")

        image_b64 = base64.b64encode(b"test").decode()
        result = await extract_component_specs(image_b64, error_screening)

        # Errored screening has confidence 0.0, so fails threshold
        assert result.error is not None
        assert "threshold" in result.error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
