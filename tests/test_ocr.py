"""
OCR Workflow Tests

Tests the multi-provider OCR pipeline.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from rivet.models.ocr import OCRResult, calculate_confidence, normalize_manufacturer
from rivet.workflows.ocr import analyze_image, parse_json_response, validate_image_quality


class TestOCRModels:
    """Test OCR data models."""

    def test_normalize_manufacturer_aliases(self):
        """Test manufacturer alias normalization."""
        assert normalize_manufacturer("Rockwell Automation") == "allen_bradley"
        assert normalize_manufacturer("Allen-Bradley") == "allen_bradley"
        assert normalize_manufacturer("Square D") == "schneider_electric"
        assert normalize_manufacturer("Siemens") == "siemens"
        assert normalize_manufacturer("ABB") == "abb"
        assert normalize_manufacturer("Unknown Corp") == "unknown_corp"
        assert normalize_manufacturer(None) is None

    def test_calculate_confidence(self):
        """Test confidence calculation."""
        # Full data = high confidence
        data = {
            "manufacturer": "Siemens",
            "model_number": "S7-1200",
            "serial_number": "12345",
            "voltage": "24VDC",
            "phase": "1",
        }
        conf = calculate_confidence(data, "This is some OCR text with enough content")
        assert conf >= 0.8

        # Minimal data = low confidence
        data = {"manufacturer": "Unknown"}
        conf = calculate_confidence(data, "short")
        assert conf < 0.5

    def test_ocr_result_to_dict(self):
        """Test OCR result serialization."""
        result = OCRResult(
            manufacturer="siemens",
            model_number="S7-1200",
            confidence=0.85,
            provider="gemini",
        )
        d = result.to_dict()
        assert d["manufacturer"] == "siemens"
        assert d["model_number"] == "S7-1200"
        assert d["confidence"] == 0.85

    def test_ocr_result_normalize(self):
        """Test OCR result normalization."""
        result = OCRResult(
            manufacturer="Allen-Bradley",
            model_number="1756-L71",
        )
        result.normalize()
        assert result.manufacturer == "allen_bradley"
        assert result.model_number == "1756L71"


class TestJSONParsing:
    """Test JSON response parsing."""

    def test_parse_clean_json(self):
        """Test parsing clean JSON."""
        text = '{"manufacturer": "Siemens", "model_number": "S7-1200", "confidence": 0.9}'
        data = parse_json_response(text)
        assert data["manufacturer"] == "Siemens"
        assert data["confidence"] == 0.9

    def test_parse_markdown_json(self):
        """Test parsing JSON with markdown fences."""
        text = '```json\n{"manufacturer": "ABB", "model_number": "ACS880"}\n```'
        data = parse_json_response(text)
        assert data["manufacturer"] == "ABB"

    def test_parse_invalid_json(self):
        """Test graceful handling of invalid JSON."""
        text = "This is not JSON at all"
        data = parse_json_response(text)
        assert data["confidence"] == 0.0
        assert "raw_text" in data


class TestImageValidation:
    """Test image quality validation."""

    def test_validate_small_image(self):
        """Test rejection of small images."""
        # Create a tiny 10x10 image
        from PIL import Image
        import io

        img = Image.new("RGB", (100, 100), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()

        is_valid, msg = validate_image_quality(image_bytes)
        assert not is_valid
        assert "too small" in msg.lower()

    def test_validate_good_image(self):
        """Test acceptance of good images."""
        from PIL import Image
        import io

        # Create a 500x500 image with medium brightness
        img = Image.new("RGB", (500, 500), color=(128, 128, 128))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()

        is_valid, msg = validate_image_quality(image_bytes)
        assert is_valid


class TestOCRWorkflow:
    """Test the full OCR workflow."""

    @pytest.mark.asyncio
    async def test_analyze_image_success(self):
        """Test successful image analysis."""
        # Mock the LLM router
        mock_response = """
        {
            "manufacturer": "Siemens",
            "model_number": "G120C",
            "equipment_type": "vfd",
            "voltage": "480V",
            "confidence": 0.9,
            "raw_text": "SIEMENS G120C 480V 15HP"
        }
        """

        with patch("rivet.workflows.ocr.get_llm_router") as mock_router:
            router_instance = MagicMock()
            router_instance.get_available_providers.return_value = ["gemini"]
            router_instance.call_vision = AsyncMock(return_value=(mock_response, 0.001))
            mock_router.return_value = router_instance

            # Create test image
            from PIL import Image
            import io
            img = Image.new("RGB", (500, 500), color=(128, 128, 128))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()

            result = await analyze_image(image_bytes, user_id="test123")

            assert result.is_successful
            assert result.manufacturer == "siemens"  # Normalized
            assert result.model_number == "G120C"
            assert result.equipment_type == "vfd"

    @pytest.mark.asyncio
    async def test_analyze_image_quality_fail(self):
        """Test quality check failure."""
        # Tiny image should fail
        from PIL import Image
        import io

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()

        result = await analyze_image(image_bytes)

        assert not result.is_successful
        assert result.error is not None
        assert "too small" in result.error.lower()
