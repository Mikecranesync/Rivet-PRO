"""
Tests for Industrial Photo Screening Service

Tests PHOTO-GROQ-001: Groq Vision Industrial Screening Service
"""

import asyncio
import base64
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rivet_pro.core.models.screening import ScreeningResult
from rivet_pro.core.services.screening_service import (
    screen_industrial_photo,
    should_proceed_to_ocr,
    CONFIDENCE_THRESHOLD,
    SCREENING_MODEL,
)


def test_screening_result_dataclass():
    """Test ScreeningResult dataclass properties."""
    # Test passing result
    result = ScreeningResult(
        is_industrial=True,
        confidence=0.92,
        category="vfd",
        reason="VFD nameplate detected"
    )
    assert result.passes_threshold is True
    assert result.is_successful is True
    assert "vfd" in result.get_user_message().lower() or "detected" in result.get_user_message().lower()
    print(f"PASS: Passing result: {result}")

    # Test failing result (not industrial)
    result = ScreeningResult(
        is_industrial=False,
        confidence=0.15,
        category=None,
        reason="Image shows food"
    )
    assert result.passes_threshold is False
    assert result.is_successful is True
    assert "equipment" in result.get_user_message().lower()
    print(f"PASS: Non-industrial result: {result}")

    # Test low confidence result
    result = ScreeningResult(
        is_industrial=True,
        confidence=0.65,
        category="motor",
        reason="Possibly a motor"
    )
    assert result.passes_threshold is False  # Below 0.80
    assert "Low confidence" in result.get_user_message() or "clearer" in result.get_user_message()
    print(f"PASS: Low confidence result: {result}")

    # Test error result
    result = ScreeningResult(error="API timeout")
    assert result.passes_threshold is False
    assert result.is_successful is False
    assert "failed" in result.get_user_message().lower()
    print(f"PASS: Error result: {result}")

    # Test to_dict
    result = ScreeningResult(
        is_industrial=True,
        confidence=0.88,
        category="plc",
        reason="Allen-Bradley PLC"
    )
    d = result.to_dict()
    assert d["is_industrial"] is True
    assert d["confidence"] == 0.88
    assert d["category"] == "plc"
    assert d["passes_threshold"] is True
    print(f"PASS: to_dict serialization works")


async def test_live_screening():
    """Test live screening with Groq API (requires GROQ_API_KEY)."""
    from dotenv import load_dotenv
    load_dotenv()

    # Check for API key
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not set - skipping live test")
        return

    # Create a proper test image (100x100 gray image)
    # This should be classified as NOT industrial
    from PIL import Image
    from io import BytesIO
    img = Image.new('RGB', (100, 100), color='gray')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    test_image_b64 = base64.b64encode(buffer.getvalue()).decode()

    print("\nTesting live screening with solid gray image...")
    result = await screen_industrial_photo(test_image_b64)

    print(f"Result: {result}")
    print(f"Processing time: {result.processing_time_ms}ms")
    print(f"Cost: ${result.cost_usd:.4f}")

    # Simple image should NOT pass threshold
    if result.is_successful:
        print(f"PASS: Screening completed successfully")
        print(f"   is_industrial: {result.is_industrial}")
        print(f"   confidence: {result.confidence:.0%}")
        print(f"   category: {result.category}")
        print(f"   reason: {result.reason}")
        print(f"   passes_threshold: {result.passes_threshold}")

        # Verify response time target (< 2 seconds)
        if result.processing_time_ms < 2000:
            print(f"PASS: Response time under 2s target: {result.processing_time_ms}ms")
        else:
            print(f"WARN: Response time exceeded 2s target: {result.processing_time_ms}ms")
    else:
        print(f"FAIL: Screening failed: {result.error}")


async def test_should_proceed_to_ocr():
    """Test convenience function."""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not set - skipping live test")
        return

    # Create a proper test image (100x100 gray image)
    from PIL import Image
    from io import BytesIO
    img = Image.new('RGB', (100, 100), color='gray')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    test_image_b64 = base64.b64encode(buffer.getvalue()).decode()

    print("\nTesting should_proceed_to_ocr...")
    should_proceed, result = await should_proceed_to_ocr(test_image_b64)

    print(f"Should proceed: {should_proceed}")
    print(f"User message: {result.get_user_message()}")

    if not should_proceed:
        print(f"PASS: Correctly rejected non-industrial image")


def main():
    """Run all tests."""
    print("=" * 60)
    print("PHOTO-GROQ-001: Groq Vision Industrial Screening Tests")
    print("=" * 60)

    # Unit tests
    print("\n--- Unit Tests ---")
    test_screening_result_dataclass()

    # Integration tests (require API key)
    print("\n--- Integration Tests ---")
    asyncio.run(test_live_screening())
    asyncio.run(test_should_proceed_to_ocr())

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
