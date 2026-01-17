"""
Unit Tests for Groq Industrial Photo Screening Service

PHOTO-TEST-001: Comprehensive unit tests with mocked Groq API.
Tests screening logic, confidence thresholds, and error handling.
"""

import pytest
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rivet_pro.core.models.screening import ScreeningResult, IndustrialCategory
from rivet_pro.core.services.screening_service import (
    screen_industrial_photo,
    should_proceed_to_ocr,
    CONFIDENCE_THRESHOLD,
    SCREENING_MODEL,
    SCREENING_COST_PER_IMAGE,
    _get_rejection_message,
)


# =============================================================================
# ScreeningResult Model Tests
# =============================================================================

class TestScreeningResultModel:
    """Tests for ScreeningResult dataclass."""

    def test_successful_industrial_result(self):
        """Test successful industrial equipment classification."""
        result = ScreeningResult(
            is_industrial=True,
            confidence=0.92,
            category="vfd",
            reason="VFD nameplate detected with Allen-Bradley logo"
        )

        assert result.is_successful
        assert result.passes_threshold
        assert result.confidence == 0.92
        assert result.category == "vfd"
        assert "Industrial equipment detected" in result.get_user_message()

    def test_non_industrial_result(self):
        """Test non-industrial classification."""
        result = ScreeningResult(
            is_industrial=False,
            confidence=0.15,
            category=None,
            reason="Image shows food items"
        )

        assert result.is_successful
        assert not result.passes_threshold
        assert "doesn't appear to be industrial equipment" in result.get_user_message()

    def test_low_confidence_industrial(self):
        """Test industrial classification with low confidence."""
        result = ScreeningResult(
            is_industrial=True,
            confidence=0.65,  # Below 0.80 threshold
            category="motor",
            reason="Possibly a motor but image is blurry"
        )

        assert result.is_successful
        assert not result.passes_threshold  # Below threshold
        assert "Low confidence" in result.get_user_message()
        assert "clearer" in result.get_user_message()

    def test_error_result(self):
        """Test error state handling."""
        result = ScreeningResult(error="API timeout after 30 seconds")

        assert not result.is_successful
        assert not result.passes_threshold
        assert "failed" in result.get_user_message().lower()
        assert "timeout" in result.get_user_message().lower()

    def test_to_dict_serialization(self):
        """Test JSON serialization."""
        result = ScreeningResult(
            is_industrial=True,
            confidence=0.88,
            category="plc",
            reason="Allen-Bradley PLC detected",
            processing_time_ms=1250,
            cost_usd=0.001,
        )

        data = result.to_dict()

        assert data["is_industrial"] is True
        assert data["confidence"] == 0.88
        assert data["category"] == "plc"
        assert data["passes_threshold"] is True
        assert data["processing_time_ms"] == 1250
        assert data["cost_usd"] == 0.001
        assert "timestamp" in data

    def test_rejection_message_custom(self):
        """Test custom rejection message."""
        result = ScreeningResult(
            is_industrial=False,
            confidence=0.10,
            rejection_message="Custom rejection: This is a cat photo"
        )

        assert result.get_user_message() == "Custom rejection: This is a cat photo"

    def test_all_categories(self):
        """Test all valid industrial categories."""
        categories = ["plc", "vfd", "motor", "pump", "control_panel", "sensor", "other"]

        for cat in categories:
            result = ScreeningResult(
                is_industrial=True,
                confidence=0.90,
                category=cat
            )
            assert result.is_successful
            assert result.passes_threshold

    def test_str_representation(self):
        """Test string representation."""
        result = ScreeningResult(
            is_industrial=True,
            confidence=0.85,
            category="vfd"
        )

        str_rep = str(result)
        assert "PASS" in str_rep
        assert "85%" in str_rep
        assert "vfd" in str_rep


# =============================================================================
# Rejection Message Tests
# =============================================================================

class TestRejectionMessages:
    """Tests for _get_rejection_message helper function."""

    def test_food_rejection(self):
        """Test rejection message for food images."""
        msg = _get_rejection_message("Image shows food and plates")
        assert "food" in msg.lower()
        assert "equipment" in msg.lower()

    def test_pet_rejection(self):
        """Test rejection message for pet images."""
        msg = _get_rejection_message("Image shows a cat")
        assert "equipment" in msg.lower()

    def test_person_rejection(self):
        """Test rejection message for person/selfie images."""
        msg = _get_rejection_message("Image shows a person selfie")
        assert "equipment" in msg.lower()

    def test_document_rejection(self):
        """Test rejection message for document images."""
        msg = _get_rejection_message("Image shows a document or paper")
        assert "document" in msg.lower()

    def test_vehicle_rejection(self):
        """Test rejection message for vehicle images."""
        msg = _get_rejection_message("Image shows a car")
        assert "industrial" in msg.lower()

    def test_default_rejection(self):
        """Test default rejection message."""
        msg = _get_rejection_message("Unknown image content")
        assert "industrial equipment" in msg.lower()


# =============================================================================
# Mocked Groq API Tests
# =============================================================================

class TestGroqScreeningMocked:
    """Tests for screen_industrial_photo with mocked Groq API."""

    @pytest.fixture
    def mock_groq_response(self):
        """Create mock Groq API response."""
        def _create_response(is_industrial=True, confidence=0.92, category="vfd", reason="VFD detected"):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "is_industrial": is_industrial,
                "confidence": confidence,
                "category": category,
                "reason": reason
            })
            return mock_response
        return _create_response

    @pytest.fixture
    def test_image_b64(self):
        """Create test image base64."""
        return base64.b64encode(b"test image bytes for screening").decode()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    @patch("groq.Groq")
    async def test_successful_industrial_screening(self, mock_groq_class, mock_settings, mock_groq_response, test_image_b64):
        """Test successful screening of industrial equipment."""
        mock_settings.groq_api_key = "test-api-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_groq_response(
            is_industrial=True,
            confidence=0.92,
            category="vfd",
            reason="VFD nameplate detected"
        )
        mock_groq_class.return_value = mock_client

        result = await screen_industrial_photo(test_image_b64)

        assert result.is_successful
        assert result.is_industrial
        assert result.confidence == 0.92
        assert result.category == "vfd"
        assert result.passes_threshold
        assert result.cost_usd == SCREENING_COST_PER_IMAGE

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    @patch("groq.Groq")
    async def test_non_industrial_screening(self, mock_groq_class, mock_settings, mock_groq_response, test_image_b64):
        """Test screening of non-industrial image."""
        mock_settings.groq_api_key = "test-api-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_groq_response(
            is_industrial=False,
            confidence=0.15,
            category=None,
            reason="Image shows food items"
        )
        mock_groq_class.return_value = mock_client

        result = await screen_industrial_photo(test_image_b64)

        assert result.is_successful
        assert not result.is_industrial
        assert not result.passes_threshold
        assert result.rejection_message is not None

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    @patch("groq.Groq")
    async def test_low_confidence_screening(self, mock_groq_class, mock_settings, mock_groq_response, test_image_b64):
        """Test screening with low confidence (below threshold)."""
        mock_settings.groq_api_key = "test-api-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_groq_response(
            is_industrial=True,
            confidence=0.65,  # Below 0.80 threshold
            category="motor",
            reason="Possibly a motor but blurry"
        )
        mock_groq_class.return_value = mock_client

        result = await screen_industrial_photo(test_image_b64)

        assert result.is_successful
        assert result.is_industrial
        assert result.confidence == 0.65
        assert not result.passes_threshold  # Below threshold

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    async def test_missing_api_key(self, mock_settings, test_image_b64):
        """Test error when Groq API key is missing."""
        mock_settings.groq_api_key = None

        result = await screen_industrial_photo(test_image_b64)

        assert not result.is_successful
        assert result.error is not None
        assert "GROQ_API_KEY" in result.error

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    @patch("groq.Groq")
    async def test_api_timeout_error(self, mock_groq_class, mock_settings, test_image_b64):
        """Test handling of API timeout."""
        mock_settings.groq_api_key = "test-api-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = TimeoutError("API request timed out")
        mock_groq_class.return_value = mock_client

        result = await screen_industrial_photo(test_image_b64)

        assert not result.is_successful
        assert result.error is not None
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    @patch("groq.Groq")
    async def test_json_parse_error(self, mock_groq_class, mock_settings, test_image_b64):
        """Test handling of malformed JSON response."""
        mock_settings.groq_api_key = "test-api-key"
        mock_settings.langfuse_public_key = None

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is not valid JSON {{{]]"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = await screen_industrial_photo(test_image_b64)

        # Should handle gracefully with fallback
        assert result.confidence == 0.0
        assert not result.is_industrial

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    @patch("groq.Groq")
    async def test_json_in_markdown_code_block(self, mock_groq_class, mock_settings, test_image_b64):
        """Test parsing JSON wrapped in markdown code blocks."""
        mock_settings.groq_api_key = "test-api-key"
        mock_settings.langfuse_public_key = None

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
    "is_industrial": true,
    "confidence": 0.88,
    "category": "plc",
    "reason": "PLC detected"
}
```'''

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = await screen_industrial_photo(test_image_b64)

        assert result.is_successful
        assert result.is_industrial
        assert result.confidence == 0.88
        assert result.category == "plc"

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.settings")
    @patch("groq.Groq")
    async def test_invalid_category_normalization(self, mock_groq_class, mock_settings, mock_groq_response, test_image_b64):
        """Test that invalid categories are normalized to 'other'."""
        mock_settings.groq_api_key = "test-api-key"
        mock_settings.langfuse_public_key = None

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "is_industrial": True,
            "confidence": 0.85,
            "category": "unknown_category",  # Invalid category
            "reason": "Some equipment"
        })

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = await screen_industrial_photo(test_image_b64)

        assert result.is_successful
        assert result.category == "other"  # Should be normalized


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestShouldProceedToOCR:
    """Tests for should_proceed_to_ocr convenience function."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.screen_industrial_photo")
    async def test_should_proceed_true(self, mock_screen):
        """Test should_proceed returns True for passing result."""
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.92,
            category="vfd"
        )

        should_proceed, result = await should_proceed_to_ocr("test_b64")

        assert should_proceed is True
        assert result.passes_threshold

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.screen_industrial_photo")
    async def test_should_proceed_false_non_industrial(self, mock_screen):
        """Test should_proceed returns False for non-industrial."""
        mock_screen.return_value = ScreeningResult(
            is_industrial=False,
            confidence=0.10
        )

        should_proceed, result = await should_proceed_to_ocr("test_b64")

        assert should_proceed is False
        assert not result.passes_threshold

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.screening_service.screen_industrial_photo")
    async def test_should_proceed_false_low_confidence(self, mock_screen):
        """Test should_proceed returns False for low confidence."""
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.65  # Below threshold
        )

        should_proceed, result = await should_proceed_to_ocr("test_b64")

        assert should_proceed is False
        assert not result.passes_threshold


# =============================================================================
# Confidence Threshold Tests
# =============================================================================

class TestConfidenceThresholds:
    """Tests for confidence threshold boundary conditions."""

    def test_exactly_at_threshold(self):
        """Test result exactly at 0.80 threshold passes."""
        result = ScreeningResult(
            is_industrial=True,
            confidence=0.80  # Exactly at threshold
        )
        assert result.passes_threshold

    def test_just_below_threshold(self):
        """Test result just below threshold fails."""
        result = ScreeningResult(
            is_industrial=True,
            confidence=0.79  # Just below
        )
        assert not result.passes_threshold

    def test_just_above_threshold(self):
        """Test result just above threshold passes."""
        result = ScreeningResult(
            is_industrial=True,
            confidence=0.81
        )
        assert result.passes_threshold

    def test_threshold_constant(self):
        """Test threshold constant value."""
        assert CONFIDENCE_THRESHOLD == 0.80

    def test_model_constant(self):
        """Test model constant value."""
        assert "llama" in SCREENING_MODEL.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
