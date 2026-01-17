"""
Tests for DeepSeek Component Extraction Service

PHOTO-DEEP-001: DeepSeek Component Specification Extraction
"""

import pytest
import hashlib
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from rivet_pro.core.models.extraction import ExtractionResult
from rivet_pro.core.models.screening import ScreeningResult
from rivet_pro.core.services.extraction_service import (
    compute_photo_hash,
    extract_component_specs,
    get_cached_extraction,
    save_extraction_to_cache,
    MIN_SCREENING_CONFIDENCE,
)


class TestExtractionResult:
    """Tests for ExtractionResult dataclass."""

    def test_successful_result(self):
        """Test successful extraction result properties."""
        result = ExtractionResult(
            manufacturer="Allen-Bradley",
            model_number="1756-L72S",
            serial_number="ABC123",
            specs={"voltage": "24V", "current": "2A"},
            raw_text="Allen-Bradley 1756-L72S",
            confidence=0.92,
        )

        assert result.is_successful
        assert result.has_model_info
        assert "Allen-Bradley" in str(result)
        assert "1756-L72S" in str(result)

    def test_failed_result(self):
        """Test failed extraction result properties."""
        result = ExtractionResult(error="API timeout")

        assert not result.is_successful
        assert not result.has_model_info
        assert "error" in str(result).lower()

    def test_cached_result(self):
        """Test cached result indicator."""
        result = ExtractionResult(
            manufacturer="Siemens",
            model_number="6ES7-511",
            confidence=0.85,
            from_cache=True,
        )

        assert result.from_cache
        assert "CACHED" in str(result)

    def test_to_dict(self):
        """Test JSON serialization."""
        result = ExtractionResult(
            manufacturer="ABB",
            model_number="ACS550",
            specs={"voltage": "480V", "hp": "50HP"},
            confidence=0.88,
        )

        data = result.to_dict()

        assert data["manufacturer"] == "ABB"
        assert data["model_number"] == "ACS550"
        assert data["specs"]["voltage"] == "480V"
        assert data["confidence"] == 0.88
        assert "timestamp" in data

    def test_user_message_success(self):
        """Test user-friendly message for successful extraction."""
        result = ExtractionResult(
            manufacturer="Yaskawa",
            model_number="A1000",
            specs={"voltage": "480V", "horsepower": "25HP"},
            confidence=0.90,
        )

        message = result.get_user_message()

        assert "Yaskawa" in message
        assert "A1000" in message
        assert "480V" in message

    def test_user_message_failure(self):
        """Test user-friendly message for failed extraction."""
        result = ExtractionResult(error="Connection timeout")

        message = result.get_user_message()

        assert "failed" in message.lower()
        assert "timeout" in message.lower()


class TestPhotoHash:
    """Tests for photo hash computation."""

    def test_compute_hash(self):
        """Test hash computation returns valid SHA256."""
        image_data = b"test image bytes"
        hash_result = compute_photo_hash(image_data)

        assert len(hash_result) == 64  # SHA256 produces 64 hex chars
        assert hash_result == hashlib.sha256(image_data).hexdigest()

    def test_hash_deterministic(self):
        """Test same input produces same hash."""
        image_data = b"identical image data"

        hash1 = compute_photo_hash(image_data)
        hash2 = compute_photo_hash(image_data)

        assert hash1 == hash2

    def test_hash_unique(self):
        """Test different inputs produce different hashes."""
        hash1 = compute_photo_hash(b"image one")
        hash2 = compute_photo_hash(b"image two")

        assert hash1 != hash2


class TestCaching:
    """Tests for cache get/save operations."""

    @pytest.mark.asyncio
    async def test_get_cached_extraction_hit(self):
        """Test cache hit returns cached result."""
        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = {
            "manufacturer": "Rockwell",
            "model_number": "PF525",
            "serial_number": "SN123",
            "specs": {"voltage": "480V"},
            "raw_text": "PowerFlex 525",
            "confidence": 0.89,
            "model_used": "deepseek-chat",
        }

        result = await get_cached_extraction(mock_db, "abc123hash")

        assert result is not None
        assert result.manufacturer == "Rockwell"
        assert result.model_number == "PF525"
        assert result.from_cache is True
        assert result.cost_usd == 0.0  # No cost for cached result

        # Verify hit count was updated
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_extraction_miss(self):
        """Test cache miss returns None."""
        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None

        result = await get_cached_extraction(mock_db, "nonexistent_hash")

        assert result is None

    @pytest.mark.asyncio
    async def test_save_extraction_to_cache(self):
        """Test saving extraction to cache."""
        mock_db = AsyncMock()

        result = ExtractionResult(
            manufacturer="Danfoss",
            model_number="VLT5000",
            specs={"voltage": "380V"},
            confidence=0.87,
            processing_time_ms=1500,
            cost_usd=0.002,
        )

        await save_extraction_to_cache(mock_db, "test_hash", result)

        # Verify insert was called
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert "INSERT INTO photo_analysis_cache" in call_args[0][0]


class TestExtractionService:
    """Tests for main extraction service."""

    @pytest.mark.asyncio
    async def test_screening_below_threshold(self):
        """Test rejection when screening confidence below threshold."""
        screening = ScreeningResult(
            is_industrial=True,
            confidence=0.75,  # Below 0.80 threshold
        )

        image_b64 = base64.b64encode(b"test").decode()
        result = await extract_component_specs(image_b64, screening)

        assert result.error is not None
        assert "threshold" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_base64(self):
        """Test handling of invalid base64 input."""
        screening = ScreeningResult(
            is_industrial=True,
            confidence=0.85,
        )

        result = await extract_component_specs("not_valid_base64!!!", screening)

        assert result.error is not None
        assert "base64" in result.error.lower()

    @pytest.mark.asyncio
    async def test_cache_hit_returns_early(self):
        """Test that cache hit skips API call."""
        screening = ScreeningResult(
            is_industrial=True,
            confidence=0.90,
        )

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = {
            "manufacturer": "Siemens",
            "model_number": "S7-1500",
            "serial_number": None,
            "specs": {},
            "raw_text": "Siemens S7-1500",
            "confidence": 0.88,
            "model_used": "deepseek-chat",
        }

        # Simple test image
        image_data = b"test image bytes for caching"
        image_b64 = base64.b64encode(image_data).decode()

        result = await extract_component_specs(image_b64, screening, db=mock_db)

        assert result.from_cache is True
        assert result.manufacturer == "Siemens"
        assert result.cost_usd == 0.0  # No API cost

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.extraction_service.settings")
    async def test_missing_api_key(self, mock_settings):
        """Test error when DeepSeek API key not configured."""
        mock_settings.deepseek_api_key = None

        screening = ScreeningResult(
            is_industrial=True,
            confidence=0.85,
        )

        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None  # Cache miss

        image_b64 = base64.b64encode(b"test image").decode()
        result = await extract_component_specs(image_b64, screening, db=mock_db)

        assert result.error is not None
        assert "DEEPSEEK_API_KEY" in result.error


class TestConfidenceAdjustment:
    """Tests for confidence adjustment based on text quality."""

    def test_result_confidence_property(self):
        """Test confidence values are properly stored."""
        result = ExtractionResult(confidence=0.85)
        assert result.confidence == 0.85

    def test_low_confidence_result(self):
        """Test handling of low confidence extractions."""
        result = ExtractionResult(
            manufacturer="Unknown",
            confidence=0.45,
        )

        assert result.is_successful  # Still successful, just low confidence
        assert result.confidence < 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
