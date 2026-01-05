"""
Test OCR flow by simulating a photo upload.
This allows testing the full pipeline without manual photo sends.
"""

import asyncio
import sys
from pathlib import Path

# Add rivet_pro to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rivet_pro.core.services.ocr_service import analyze_image
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


async def test_ocr_with_sample_image():
    """Test OCR pipeline with a sample equipment image."""

    print("=" * 60)
    print("OCR FLOW TEST")
    print("=" * 60)
    print()

    # Option 1: Download a sample nameplate image from the web
    import aiohttp

    # Sample nameplate images (publicly available)
    test_images = [
        "https://i.imgur.com/sample.jpg",  # Replace with actual test image URL
        # Or use a local test image
    ]

    print("📥 Downloading sample nameplate image...")

    try:
        async with aiohttp.ClientSession() as session:
            # For testing, we'll use a placeholder
            # In production, you'd use a real test image URL
            url = "https://picsum.photos/800/600"  # Random image for testing

            async with session.get(url) as response:
                if response.status == 200:
                    image_bytes = await response.read()
                    print(f"✅ Downloaded {len(image_bytes)} bytes")
                else:
                    print(f"❌ Failed to download: {response.status}")
                    return
    except Exception as e:
        print(f"❌ Download error: {e}")
        print("\n⚠️  Using mock test instead...")
        # Create a small test image
        image_bytes = b"test image data"

    print()
    print("🔍 Step 1: Calling analyze_image()...")

    try:
        result = await analyze_image(
            image_bytes=image_bytes,
            user_id="test_user_123"
        )

        print("✅ Step 2: OCR completed successfully!")
        print()
        print("=" * 60)
        print("OCR RESULT")
        print("=" * 60)
        print(f"Manufacturer: {result.manufacturer or 'Not detected'}")
        print(f"Model: {result.model_number or 'Not detected'}")
        print(f"Serial: {result.serial_number or 'Not detected'}")
        print(f"Component: {result.component_type or 'Not detected'}")
        print(f"Confidence: {result.confidence:.1%}")
        print(f"Provider: {result.provider_used or 'Unknown'}")
        print()

        if result.error:
            print(f"⚠️  Error: {result.error}")

        if result.raw_text:
            print(f"Raw OCR Text ({len(result.raw_text)} chars):")
            print("-" * 60)
            print(result.raw_text[:500])  # First 500 chars
            if len(result.raw_text) > 500:
                print(f"... ({len(result.raw_text) - 500} more chars)")

        print()
        print("=" * 60)
        print("✅ OCR FLOW TEST COMPLETE")
        print("=" * 60)

        return result

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ OCR FLOW TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_telegram_photo_handler():
    """Simulate the full Telegram photo handler flow."""

    print("=" * 60)
    print("TELEGRAM PHOTO HANDLER SIMULATION")
    print("=" * 60)
    print()

    # This simulates what happens when a user sends a photo to the bot
    print("📱 Step 1: User sends photo to bot")
    print("📥 Step 2: Bot downloads photo from Telegram")
    print("🔍 Step 3: Bot calls analyze_image()")
    print()

    # Simulate the photo bytes (in real scenario, this comes from Telegram)
    test_photo_bytes = b"simulated photo data"

    try:
        from rivet_pro.core.services import analyze_image

        print("⏳ Analyzing image...")
        result = await analyze_image(
            image_bytes=test_photo_bytes,
            user_id="8445149012"  # Your Telegram user ID
        )

        print()
        print("✅ Step 4: Image analyzed successfully!")
        print()
        print(f"   Manufacturer: {result.manufacturer}")
        print(f"   Model: {result.model_number}")
        print(f"   Confidence: {result.confidence:.0%}")
        print()
        print("📤 Step 5: Bot sends result back to user")
        print()
        print("Message that would be sent:")
        print("-" * 60)

        confidence_emoji = "🟢" if result.confidence >= 0.9 else "🟡" if result.confidence >= 0.7 else "🔴"

        message = (
            f"{confidence_emoji} **Equipment Identified**\n\n"
            f"**Manufacturer:** {result.manufacturer or 'Not detected'}\n"
            f"**Model:** {result.model_number or 'Not detected'}\n"
            f"**Serial:** {result.serial_number or 'Not detected'}\n"
            f"**Confidence:** {result.confidence:.0%}\n"
        )

        print(message)
        print("-" * 60)
        print()
        print("✅ TELEGRAM HANDLER SIMULATION COMPLETE")

    except Exception as e:
        print()
        print(f"❌ Error in handler simulation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🧪 Select test to run:")
    print("1. Test OCR with sample image")
    print("2. Simulate Telegram photo handler")
    print("3. Run both tests")
    print()

    choice = input("Enter choice (1-3): ").strip()

    if choice == "1":
        asyncio.run(test_ocr_with_sample_image())
    elif choice == "2":
        asyncio.run(test_telegram_photo_handler())
    elif choice == "3":
        asyncio.run(test_ocr_with_sample_image())
        print("\n" + "=" * 60 + "\n")
        asyncio.run(test_telegram_photo_handler())
    else:
        print("Invalid choice")
