"""
Unit Tests for DeepSeek Component Extraction Service

PHOTO-TEST-001: Comprehensive unit tests with mocked DeepSeek API.
Tests extraction logic, caching, confidence penalties, and error handling.
"""

import pytest
import base64
import json
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rivet_pro.core.models.extraction import ExtractionResult
from rivet_pro.core.models.screening import ScreeningResult
from rivet_pro.core.services.extraction_service import (
    compute_photo_hash,
    extract_component_specs,
    get_cached_extraction,
    save_extraction_to_cache,
    MIN_SCREENING_CONFIDENCE,
    EXTRACTION_MODEL,
    EXTRACTION_COST_PER_IMAGE,
)


# =============================================================================
# ExtractionResult Model Tests
# =============================================================================

class TestExtractionResultModel:
    """Tests for ExtractionResult dataclass."""

    def test_successful_result(self):
        """Test successful extraction result properties."""
        result = ExtractionResult(
            manufacturer="Allen-Bradley",
            model_number="1756-L72S",
            serial_number="ABC123456",
            specs={
                "voltage": "24V DC",
                "current": "2A",
                "horsepower": None,
            },
            raw_text="Allen-Bradley ControlLogix 1756-L72S",
            confidence=0.92,
        )

        assert result.is_successful
        assert result.has_model_info
        assert result.manufacturer == "Allen-Bradley"
        assert result.model_number == "1756-L72S"
        assert "Allen-Bradley" in str(result)

    def test_failed_result(self):
        """Test failed extraction result."""
        result = ExtractionResult(error="API timeout after 30 seconds")

        assert not result.is_successful
        assert not result.has_model_info
        assert "timeout" in result.get_user_message().lower()

    def test_cached_result_indicator(self):
        """Test cached result indicator in string representation."""
        result = ExtractionResult(
            manufacturer="Siemens",
            model_number="6ES7-511",
            confidence=0.85,
            from_cache=True,
            cost_usd=0.0,  # No cost for cached
        )

        assert result.from_cache
        assert "CACHED" in str(result)
        assert result.cost_usd == 0.0

    def test_to_dict_serialization(self):
        """Test JSON serialization."""
        result = ExtractionResult(
            manufacturer="ABB",
            model_number="ACS550",
            specs={"voltage": "480V", "horsepower": "50HP"},
            confidence=0.88,
            processing_time_ms=2100,
            cost_usd=0.002,
        )

        data = result.to_dict()

        assert data["manufacturer"] == "ABB"
        assert data["model_number"] == "ACS550"
        assert data["specs"]["voltage"] == "480V"
        assert data["confidence"] == 0.88
        assert data["processing_time_ms"] == 2100
        assert data["cost_usd"] == 0.002
        assert "timestamp" in data

    def test_user_message_success(self):
        """Test user-friendly message for successful extraction."""
        result = ExtractionResult(
            manufacturer="Yaskawa",
            model_number="A1000",
            serial_number="SN12345",
            specs={"voltage": "480V", "horsepower": "25HP", "rpm": "1750"},
            confidence=0.90,
        )

        message = result.get_user_message()

        assert "Yaskawa" in message
        assert "A1000" in message
        assert "480V" in message
        assert "25HP" in message

    def test_user_message_failure(self):
        """Test user-friendly message for failed extraction."""
        result = ExtractionResult(error="Connection timeout")

        message = result.get_user_message()

        assert "failed" in message.lower()
        assert "timeout" in message.lower()

    def test_partial_extraction(self):
        """Test extraction with only manufacturer (no model)."""
        result = ExtractionResult(
            manufacturer="Rockwell",
            model_number=None,
            confidence=0.60,
        )

        assert result.has_model_info  # Manufacturer counts
        assert result.is_successful

    def test_no_info_extraction(self):
        """Test extraction with no useful information."""
        result = ExtractionResult(
            manufacturer=None,
            model_number=None,
            confidence=0.30,
        )

        assert not result.has_model_info
        # Still "successful" if no error, but has_model_info is False


# =============================================================================
# Photo Hash Tests
# =============================================================================

class TestPhotoHash:
    """Tests for photo hash computation."""

    def test_compute_hash_valid(self):
        """Test hash computation returns valid SHA256."""
        image_data = b"test image bytes for hashing"
        hash_result = compute_photo_hash(image_data)

        assert len(hash_result) == 64  # SHA256 produces 64 hex chars
        assert hash_result == hashlib.sha256(image_data).hexdigest()

    def test_hash_deterministic(self):
        """Test same input produces same hash."""
        image_data = b"identical image data for testing"

        hash1 = compute_photo_hash(image_data)
        hash2 = compute_photo_hash(image_data)

        assert hash1 == hash2

    def test_hash_unique_for_different_images(self):
        """Test different inputs produce different hashes."""
        hash1 = compute_photo_hash(b"image one content")
        hash2 = compute_photo_hash(b"image two content")

        assert hash1 != hash2

    def test_hash_empty_image(self):
        """Test hash of empty data."""
        hash_result = compute_photo_hash(b"")
        assert len(hash_result) == 64  # Still valid SHA256


# =============================================================================
# Cache Tests
# =============================================================================

class TestCacheOperations:
    """Tests for cache get/save operations."""

    @pytest.mark.asyncio
    async def test_get_cached_extraction_hit(self):
        """Test cache hit returns cached result."""
        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = {
            "manufacturer": "Rockwell",
            "model_number": "PF525",
            "serial_number": "SN123",
            "specs": {"voltage": "480V", "hp": "10"},
            "raw_text": "PowerFlex 525 AC Drive",
            "confidence": 0.89,
            "model_used": "deepseek-chat",
        }

        result = await get_cached_extraction(mock_db, "abc123hash")

        assert result is not None
        assert result.manufacturer == "Rockwell"
        assert result.model_number == "PF525"
        assert result.from_cache is True
        assert result.cost_usd == 0.0  # No cost for cached result
        assert result.processing_time_ms == 0

        # Verify hit count was updated
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert "hit_count" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_cached_extraction_miss(self):
        """Test cache miss returns None."""
        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None

        result = await get_cached_extraction(mock_db, "nonexistent_hash")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_extraction_db_error(self):
        """Test cache lookup handles database errors gracefully."""
        mock_db = AsyncMock()
        mock_db.fetchrow.side_effect = Exception("Database connection failed")

        result = await get_cached_extraction(mock_db, "test_hash")

        assert result is None  # Should return None, not raise

    @pytest.mark.asyncio
    async def test_save_extraction_to_cache(self):
        """Test saving extraction to cache."""
        mock_db = AsyncMock()

        result = ExtractionResult(
            manufacturer="Danfoss",
            model_number="VLT5000",
            serial_number="SN456",
            specs={"voltage": "380V", "current": "15A"},
            raw_text="Danfoss VLT 5000",
            confidence=0.87,
            processing_time_ms=1500,
            cost_usd=0.002,
        )

        await save_extraction_to_cache(mock_db, "test_hash_123", result)

        # Verify insert was called
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert "INSERT INTO photo_analysis_cache" in call_args[0][0]
        assert "ON CONFLICT" in call_args[0][0]  # Upsert

    @pytest.mark.asyncio
    async def test_save_extraction_db_error(self):
        """Test cache save handles database errors gracefully."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database write failed")

        result = ExtractionResult(
            manufacturer="Test",
            model_number="TEST123",
            confidence=0.80,
        )

        # Should not raise
        await save_extraction_to_cache(mock_db, "test_hash", result)


# =============================================================================
# Extraction Service Tests
# =============================================================================

class TestExtractionService:
    """Tests for main extraction service."""

    @pytest.fixture
    def passing_screening(self):
        """Create passing screening result."""
        return ScreeningResult(
            is_industrial=True,
            confidence=0.85,
            category="vfd",
        )

    @pytest.fixture
    def failing_screening(self):
        """Create failing screening result."""
        return ScreeningResult(
            is_industrial=True,
            confidence=0.75,  # Below threshold
        )

    @pytest.fixture
    def test_image_b64(self):
        """Create test image base64."""
        return base64.b64encode(b"test image bytes for extraction").decode()

    @pytest.fixture
    def mock_deepseek_response(self):
        """Create mock DeepSeek API response."""
        def _create_response(manufacturer="Allen-Bradley", model_number="1756-L72S",
                           serial_number=None, specs=None, confidence=0.90):
            if specs is None:
                specs = {"voltage": "24V DC", "current": "2A"}
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "manufacturer": manufacturer,
                "model_number": model_number,
                "serial_number": serial_number,
                "specs": specs,
                "raw_text": f"{manufacturer} {model_number}",
                "confidence": confidence,
                "text_quality_issues": []
            })
            return mock_response
        return _create_response

    @pytest.mark.asyncio
    async def test_screening_below_threshold_rejected(self, failing_screening, test_image_b64):
        """Test rejection when screening confidence below threshold."""
        result = await extract_component_specs(test_image_b64, failing_screening)

        assert result.error is not None
        assert "threshold" in result.error.lower()
        assert result.processing_time_ms == 0

    @pytest.mark.asyncio
    async def test_invalid_base64_rejected(self, passing_screening):
        """Test handling of invalid base64 input."""
        result = await extract_component_specs("not_valid_base64!!!", passing_screening)

        assert result.error is not None
        assert "base64" in result.error.lower()

    @pytest.mark.asyncio
    async def test_cache_hit_returns_early(self, passing_screening, test_image_b64):
        """Test that cache hit skips API call."""
        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = {
            "manufacturer": "Siemens",
            "model_number": "S7-1500",
            "serial_number": None,
            "specs": {"voltage": "24V"},
            "raw_text": "Siemens S7-1500 PLC",
            "confidence": 0.88,
            "model_used": "deepseek-chat",
        }

        result = await extract_component_specs(test_image_b64, passing_screening, db=mock_db)

        assert result.from_cache is True
        assert result.manufacturer == "Siemens"
        assert result.cost_usd == 0.0  # No API cost

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    async def test_missing_api_key_error(self, mock_settings, passing_screening, test_image_b64):
        """Test error when DeepSeek API key not configured."""
        mock_settings.deepseek_api_key = None

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None  # Cache miss

        result = await extract_component_specs(test_image_b64, passing_screening, db=mock_db)

        assert result.error is not None
        assert "DEEPSEEK_API_KEY" in result.error

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    @patch("rivet_pro.core.services.extraction_service.OpenAI")
    async def test_successful_extraction(self, mock_openai_class, mock_settings,
                                         passing_screening, test_image_b64, mock_deepseek_response):
        """Test successful extraction with mocked API."""
        mock_settings.deepseek_api_key = "test-deepseek-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_deepseek_response(
            manufacturer="Yaskawa",
            model_number="A1000",
            specs={"voltage": "480V", "horsepower": "25HP"},
            confidence=0.92
        )
        mock_openai_class.return_value = mock_client

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None  # Cache miss

        result = await extract_component_specs(test_image_b64, passing_screening, db=mock_db)

        assert result.is_successful
        assert result.manufacturer == "Yaskawa"
        assert result.model_number == "A1000"
        assert result.confidence == 0.92
        assert result.cost_usd == EXTRACTION_COST_PER_IMAGE

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    @patch("rivet_pro.core.services.extraction_service.OpenAI")
    async def test_api_timeout_error(self, mock_openai_class, mock_settings,
                                     passing_screening, test_image_b64):
        """Test handling of API timeout."""
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = TimeoutError("Request timed out")
        mock_openai_class.return_value = mock_client

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None

        result = await extract_component_specs(test_image_b64, passing_screening, db=mock_db)

        assert not result.is_successful
        assert result.error is not None
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    @patch("rivet_pro.core.services.extraction_service.OpenAI")
    async def test_json_parse_error(self, mock_openai_class, mock_settings,
                                    passing_screening, test_image_b64):
        """Test handling of malformed JSON response."""
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON {{{}"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None

        result = await extract_component_specs(test_image_b64, passing_screening, db=mock_db)

        assert result.error is not None
        assert "parse" in result.error.lower()


# =============================================================================
# Confidence Penalty Tests
# =============================================================================

class TestConfidencePenalties:
    """Tests for confidence adjustment based on text quality issues."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    @patch("rivet_pro.core.services.extraction_service.OpenAI")
    async def test_blurry_text_penalty(self, mock_openai_class, mock_settings):
        """Test confidence reduction for blurry text."""
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "manufacturer": "Siemens",
            "model_number": "6ES7",
            "serial_number": None,
            "specs": {},
            "raw_text": "Siemens 6ES7",
            "confidence": 0.90,
            "text_quality_issues": ["blurry"]  # -0.15 penalty
        })

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        screening = ScreeningResult(is_industrial=True, confidence=0.85)
        image_b64 = base64.b64encode(b"test").decode()

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None

        result = await extract_component_specs(image_b64, screening, db=mock_db)

        assert result.confidence == 0.75  # 0.90 - 0.15

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    @patch("rivet_pro.core.services.extraction_service.OpenAI")
    async def test_partial_visibility_penalty(self, mock_openai_class, mock_settings):
        """Test confidence reduction for partial text visibility."""
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "manufacturer": "ABB",
            "model_number": "ACS",
            "serial_number": None,
            "specs": {},
            "raw_text": "ABB ACS",
            "confidence": 0.85,
            "text_quality_issues": ["partial"]  # -0.20 penalty
        })

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        screening = ScreeningResult(is_industrial=True, confidence=0.85)
        image_b64 = base64.b64encode(b"test").decode()

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None

        result = await extract_component_specs(image_b64, screening, db=mock_db)

        assert result.confidence == 0.65  # 0.85 - 0.20

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    @patch("rivet_pro.core.services.extraction_service.OpenAI")
    async def test_multiple_quality_issues(self, mock_openai_class, mock_settings):
        """Test confidence reduction for multiple quality issues."""
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "manufacturer": "Unknown",
            "model_number": None,
            "serial_number": None,
            "specs": {},
            "raw_text": "Blurry text",
            "confidence": 0.80,
            "text_quality_issues": ["blurry", "dirty", "glare"]  # -0.15 -0.10 -0.10 = -0.35
        })

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        screening = ScreeningResult(is_industrial=True, confidence=0.85)
        image_b64 = base64.b64encode(b"test").decode()

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None

        result = await extract_component_specs(image_b64, screening, db=mock_db)

        # 0.80 - 0.35 = 0.45, but should be capped at minimum 0.30
        assert result.confidence >= 0.30

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    @patch("rivet_pro.core.services.extraction_service.OpenAI")
    async def test_confidence_minimum_floor(self, mock_openai_class, mock_settings):
        """Test confidence doesn't go below 0.30 floor."""
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.langfuse_public_key = None

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "manufacturer": None,
            "model_number": None,
            "serial_number": None,
            "specs": {},
            "raw_text": "",
            "confidence": 0.50,
            "text_quality_issues": ["blurry", "partial", "faded", "dirty", "glare"]  # Massive penalty
        })

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        screening = ScreeningResult(is_industrial=True, confidence=0.85)
        image_b64 = base64.b64encode(b"test").decode()

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None

        result = await extract_component_specs(image_b64, screening, db=mock_db)

        assert result.confidence == 0.30  # Floor


# =============================================================================
# Screening Threshold Tests
# =============================================================================

class TestScreeningThresholds:
    """Tests for minimum screening confidence threshold."""

    def test_min_confidence_constant(self):
        """Test minimum confidence constant value."""
        assert MIN_SCREENING_CONFIDENCE == 0.80

    def test_model_constant(self):
        """Test model constant value."""
        assert EXTRACTION_MODEL == "deepseek-chat"

    def test_cost_constant(self):
        """Test cost constant value."""
        assert EXTRACTION_COST_PER_IMAGE == 0.002


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
