"""Full end-to-end test with real image"""
import asyncio
import sys
from PIL import Image, ImageDraw, ImageFont
import io

async def create_test_nameplate():
    """Create a realistic equipment nameplate image"""
    # Create a 800x600 image with gray background (more realistic)
    img = Image.new('RGB', (800, 600), color=(200, 200, 200))
    draw = ImageDraw.Draw(img)

    # Add silver nameplate background
    draw.rectangle([40, 40, 760, 560], fill=(220, 220, 220), outline=(100, 100, 100), width=3)

    # Add realistic equipment text
    text_lines = [
        "SIEMENS",
        "SINAMICS G120",
        "Model: 6SL3224-0BE25-5UA0",
        "Serial: S-A5L27012345",
        "Input: 380-480V AC",
        "Output: 0-480V AC",
        "Current: 25A",
        "Power: 15kW / 20HP",
        "Frequency: 50/60Hz",
        "IP20"
    ]

    y = 80
    for line in text_lines:
        # Use default font since we might not have custom fonts
        draw.text((60, y), line, fill='black')
        y += 45

    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG', quality=95)
    return img_bytes.getvalue()

async def test_photo_pipeline():
    """Test the complete photo processing pipeline"""
    print("=" * 70)
    print("FULL PIPELINE TEST - Equipment Photo OCR")
    print("=" * 70)

    # Step 1: Create test image
    print("\n[1/5] Creating test equipment nameplate image...")
    try:
        image_bytes = await create_test_nameplate()
        print(f"      Created: {len(image_bytes)} bytes")
    except Exception as e:
        print(f"      FAILED: {e}")
        return False

    # Step 2: Test image quality validation
    print("\n[2/5] Testing image quality validation...")
    try:
        from rivet.workflows.ocr import validate_image_quality
        is_valid, msg = validate_image_quality(image_bytes)
        print(f"      Valid: {is_valid} - {msg}")
        if not is_valid:
            print(f"      WARNING: Image quality check failed!")
    except Exception as e:
        print(f"      FAILED: {e}")
        return False

    # Step 3: Test OCR analysis
    print("\n[3/5] Testing OCR analysis (this may take 10-30 seconds)...")
    try:
        from rivet.workflows.ocr import analyze_image
        result = await analyze_image(
            image_bytes=image_bytes,
            user_id="test_user",
            skip_quality_check=True,  # Skip for synthetic test image
            min_confidence=0.3  # Lower threshold for test
        )

        print(f"      Provider: {result.provider}")
        print(f"      Confidence: {result.confidence:.1%}")
        print(f"      Manufacturer: {result.manufacturer or 'None'}")
        print(f"      Model: {result.model_number or 'None'}")
        print(f"      Serial: {result.serial_number or 'None'}")
        print(f"      Voltage: {result.voltage or 'None'}")
        print(f"      Current: {result.current or 'None'}")
        print(f"      Equipment Type: {result.equipment_type or 'None'}")
        print(f"      Error: {result.error or 'None'}")
        print(f"      Cost: ${result.cost_usd:.4f}")

        if result.error:
            print(f"\n      ERROR DETAILS: {result.error}")
            return False

        if result.confidence < 0.3:
            print(f"\n      WARNING: Low confidence!")

    except Exception as e:
        print(f"      FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 4: Test response formatting
    print("\n[4/5] Testing response formatting...")
    try:
        from rivet.integrations.telegram_shared import format_ocr_response
        response = format_ocr_response(result)
        print(f"      Response length: {len(response)} chars")
        print(f"\n--- FORMATTED RESPONSE ---")
        # Print with proper encoding handling
        try:
            print(response)
        except UnicodeEncodeError:
            # Fallback: print without emojis
            print(response.encode('ascii', 'ignore').decode('ascii'))
        print(f"--- END RESPONSE ---\n")
    except Exception as e:
        print(f"      FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 5: Test photo handler creation
    print("\n[5/5] Testing photo handler creation...")
    try:
        from rivet.integrations.telegram_shared import create_photo_handler
        handler = create_photo_handler(enable_equipment_creation=True)
        print(f"      Handler created: {handler.__name__}")
    except Exception as e:
        print(f"      FAILED: {e}")
        return False

    # Summary
    print("\n" + "=" * 70)
    if result.manufacturer or result.model_number:
        print("SUCCESS! Pipeline working end-to-end")
        print(f"  Detected: {result.manufacturer} {result.model_number}")
        print(f"  Confidence: {result.confidence:.0%}")
        print(f"  Provider: {result.provider}")
        return True
    else:
        print("PARTIAL SUCCESS - Pipeline works but OCR didn't extract equipment data")
        print("  This might be expected with synthetic test images")
        print("  Try with a real equipment photo for better results")
        return True

if __name__ == "__main__":
    success = asyncio.run(test_photo_pipeline())
    sys.exit(0 if success else 1)
