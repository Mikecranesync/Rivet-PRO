"""Script to update orchestrator_bot.py with enhanced logging and timeout handling"""

import re

def update_orchestrator():
    with open('orchestrator_bot.py', 'r') as f:
        content = f.read()

    # Add username and timeout constant
    old_start = 'user_id = update.effective_user.id\n\n    # Start trace'
    new_start = '''user_id = update.effective_user.id
    username = update.effective_user.username or "User"

    PHOTO_DOWNLOAD_TIMEOUT = 30  # seconds

    # Start trace'''

    content = content.replace(old_start, new_start)

    # Update initial logging
    old_log = 'logger.info(f"[{user_id}] Photo received")'
    new_log = '''logger.info(
        f"[PHOTO_START] Photo received from user {user_id} (@{username})",
        extra={"user_id": user_id, "username": username}
    )'''

    content = content.replace(old_log, new_log)

    # Add enhanced download logging - find the section
    old_download_start = '# Step 1: Download photo (highest resolution)\n        photo = update.message.photo[-1]'
    new_download_start = '''# Step 1: Download photo (highest resolution)
        photo = update.message.photo[-1]
        photo_size = f"{photo.width}x{photo.height}"

        logger.info(
            f"[PHOTO_DOWNLOAD] Starting download. Size: {photo_size}, Timeout: {PHOTO_DOWNLOAD_TIMEOUT}s",
            extra={"user_id": user_id, "file_id": photo.file_id, "resolution": photo_size}
        )'''

    content = content.replace(old_download_start, new_download_start)

    # Replace photo_file = await photo.get_file() with timeout version
    old_get_file = '        photo_file = await photo.get_file()'
    new_get_file = '''
        try:
            # Get file metadata with timeout
            photo_file = await asyncio.wait_for(
                photo.get_file(),
                timeout=PHOTO_DOWNLOAD_TIMEOUT
            )

            logger.debug(f"[PHOTO_DOWNLOAD] Got metadata. File size: {photo_file.file_size} bytes")'''

    content = content.replace(old_get_file, new_get_file)

    # Add timeout exception handler before the try/finally for temp file
    old_temp = '''        # Create temp file
        temp_image_path = None
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_image:
            await photo_file.download_to_drive(temp_image.name)
            temp_image_path = temp_image.name'''

    new_temp = '''
            # Create temp file and download with timeout
            temp_image_path = None
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_image:
                await asyncio.wait_for(
                    photo_file.download_to_drive(temp_image.name),
                    timeout=PHOTO_DOWNLOAD_TIMEOUT
                )
                temp_image_path = temp_image.name

            logger.info(
                f"[PHOTO_DOWNLOAD] ✓ Downloaded successfully.",
                extra={"user_id": user_id, "file_id": photo.file_id}
            )

        except asyncio.TimeoutError:
            logger.error(
                f"[PHOTO_DOWNLOAD] Timeout after {PHOTO_DOWNLOAD_TIMEOUT}s",
                extra={"user_id": user_id, "timeout_seconds": PHOTO_DOWNLOAD_TIMEOUT}
            )
            await update.message.reply_text(
                f"❌ **Photo Download Timeout**\\n\\n"
                f"The download took too long (>{PHOTO_DOWNLOAD_TIMEOUT}s).\\n\\n"
                f"Please try again or send a smaller image.",
                parse_mode="Markdown"
            )
            return  # Exit handler early'''

    content = content.replace(old_temp, new_temp)

    # Add OCR start logging
    old_ocr = '# Step 3: Use OCR Pipeline (GPT-4o primary, Gemini fallback)\n            ocr_start = time.time()'
    new_ocr = '''# Step 3: Use OCR Pipeline (GPT-4o primary, Gemini fallback)
            logger.info(f"[PHOTO_OCR] Calling analyze_photo workflow for user {user_id}")

            ocr_start = time.time()'''

    content = content.replace(old_ocr, new_ocr)

    # Enhance OCR result logging
    old_ocr_log = '''logger.info(
                f"[{user_id}] OCR result: manufacturer={ocr_result.manufacturer}, "
                f"model={ocr_result.model_number}, confidence={ocr_result.confidence:.2f}, "
                f"provider={ocr_result.provider}"
            )'''

    new_ocr_log = '''logger.info(
                f"[PHOTO_OCR] ✓ OCR completed. Provider: {ocr_result.provider}, "
                f"Confidence: {ocr_result.confidence:.0%}, Error: {ocr_result.error or 'None'}",
                extra={
                    "user_id": user_id,
                    "provider": ocr_result.provider,
                    "confidence": ocr_result.confidence,
                    "has_error": bool(ocr_result.error),
                    "manufacturer": ocr_result.manufacturer,
                    "model": ocr_result.model_number
                }
            )'''

    content = content.replace(old_ocr_log, new_ocr_log)

    with open('orchestrator_bot.py', 'w') as f:
        f.write(content)

    print("✓ Enhanced logging and timeout handling added to orchestrator_bot.py")

if __name__ == "__main__":
    update_orchestrator()
