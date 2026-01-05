"""Test photo handler with mock photo"""
import asyncio
import sys

async def test_photo_handler():
    """Test the photo handler with a minimal mock setup"""

    print("Testing photo handler...")

    # Test 1: Check if analyze_image works
    try:
        from rivet.workflows.ocr import analyze_image
        print("[OK] analyze_image imported")
    except Exception as e:
        print(f"[FAIL] Cannot import analyze_image: {e}")
        return False

    # Test 2: Check if we have API keys
    try:
        from rivet.config import config
        providers = config.get_available_ocr_providers()
        print(f"[OK] Available OCR providers: {providers}")
        if not providers:
            print("[WARN] No OCR providers configured!")
            print("       Add GROQ_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY to .env")
            return False
    except Exception as e:
        print(f"[FAIL] Config error: {e}")
        return False

    # Test 3: Try to analyze a minimal "image" (just some bytes)
    try:
        print("\nTesting OCR with dummy image...")
        # Create a minimal fake image (this will fail OCR but test the pipeline)
        fake_image = b"FAKE IMAGE DATA FOR TESTING"

        result = await analyze_image(
            image_bytes=fake_image,
            user_id="test_user",
            skip_quality_check=True  # Skip image validation for test
        )

        print(f"[OK] OCR completed")
        print(f"   Provider: {result.provider}")
        print(f"   Confidence: {result.confidence:.0%}")
        print(f"   Manufacturer: {result.manufacturer or 'None'}")
        print(f"   Error: {result.error or 'None'}")

        return True

    except Exception as e:
        print(f"[FAIL] OCR failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_photo_handler())
    sys.exit(0 if success else 1)
