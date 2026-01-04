"""
Shared Telegram Bot Handlers

Common handlers used across all RIVET Telegram bots:
- Photo handler (OCR)
- Start command
- Error handler
- Response formatters
"""

import asyncio
import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from rivet.config import config
from rivet.workflows.ocr import analyze_image
from rivet.models.ocr import OCRResult
from rivet.workflows.troubleshoot import TroubleshootResult
from rivet.integrations.atlas import AtlasClient, AtlasNotFoundError, AtlasValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# RESPONSE FORMATTERS
# ============================================================================

def format_ocr_response(result: OCRResult) -> str:
    """
    Format OCR result for Telegram display.
    """
    lines = ["📸 **Equipment Detected**\n"]

    if result.manufacturer:
        lines.append(f"🏭 **Manufacturer:** {result.manufacturer}")

    if result.model_number:
        lines.append(f"🔢 **Model:** {result.model_number}")

    if result.serial_number:
        lines.append(f"#️⃣ **Serial:** {result.serial_number}")

    if result.fault_code:
        lines.append(f"⚠️ **Fault Code:** {result.fault_code}")

    if result.voltage:
        lines.append(f"⚡ **Voltage:** {result.voltage}")

    if result.current:
        lines.append(f"🔌 **Current:** {result.current}")

    if result.equipment_type:
        lines.append(f"⚙️ **Type:** {result.equipment_type}")

    # Metadata
    lines.append(f"\n📊 **Confidence:** {result.confidence:.0%}")
    lines.append(f"🤖 **Provider:** {result.provider}")

    if result.raw_text:
        lines.append(f"\n📝 **Extracted Text:**\n```\n{result.raw_text[:200]}...\n```")

    return "\n".join(lines)


# ============================================================================
# HANDLER FACTORIES
# ============================================================================

def create_photo_handler(
    enable_equipment_creation: bool = True,
    skip_quality_check: bool = False,
    min_confidence: float = 0.5,  # Lowered from implicit 0.7
):
    """
    Returns photo handler for OCR analysis.

    Args:
        enable_equipment_creation: If True, adds "Create Equipment?" button
        skip_quality_check: If True, skips image quality validation
        min_confidence: Minimum OCR confidence (default 0.5, was 0.7)
    """
    async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle photo messages - Equipment OCR analysis.

        Flow:
        1. Download photo from Telegram
        2. Validate image quality
        3. Call analyze_image()
        4. Format and send results
        """
        user_id = update.effective_user.id
        username = update.effective_user.username or "User"

        logger.info(
            f"[PHOTO_START] Photo received from user {user_id} (@{username})",
            extra={"user_id": user_id, "username": username}
        )

        # Send typing indicator
        await update.message.chat.send_action(action="typing")
        logger.debug(f"[PHOTO] Sent typing indicator to user {user_id}")

        PHOTO_DOWNLOAD_TIMEOUT = 30  # seconds

        try:
            # Download photo (get highest resolution)
            photo = update.message.photo[-1]
            photo_size = f"{photo.width}x{photo.height}"

            logger.info(
                f"[PHOTO_DOWNLOAD] Starting download. Size: {photo_size}, Timeout: {PHOTO_DOWNLOAD_TIMEOUT}s",
                extra={"user_id": user_id, "file_id": photo.file_id, "resolution": photo_size}
            )

            try:
                # Get file metadata with timeout
                file = await asyncio.wait_for(
                    context.bot.get_file(photo.file_id),
                    timeout=PHOTO_DOWNLOAD_TIMEOUT
                )

                logger.debug(f"[PHOTO_DOWNLOAD] Got metadata. File size: {file.file_size} bytes")

                # Download bytes with timeout
                photo_bytes = await asyncio.wait_for(
                    file.download_as_bytearray(),
                    timeout=PHOTO_DOWNLOAD_TIMEOUT
                )

                logger.info(
                    f"[PHOTO_DOWNLOAD] ✓ Downloaded successfully. "
                    f"Size: {len(photo_bytes)} bytes ({len(photo_bytes) / 1024:.1f} KB)",
                    extra={"user_id": user_id, "file_id": photo.file_id, "bytes": len(photo_bytes)}
                )

            except asyncio.TimeoutError:
                logger.error(
                    f"[PHOTO_DOWNLOAD] Timeout after {PHOTO_DOWNLOAD_TIMEOUT}s",
                    extra={"user_id": user_id, "timeout_seconds": PHOTO_DOWNLOAD_TIMEOUT}
                )
                await update.message.reply_text(
                    f"❌ **Photo Download Timeout**\n\n"
                    f"The download took too long (>{PHOTO_DOWNLOAD_TIMEOUT}s).\n\n"
                    f"Please try again or send a smaller image.",
                    parse_mode="Markdown"
                )
                return  # Exit handler early

            # Call OCR workflow
            logger.info(f"[PHOTO_OCR] Calling analyze_image workflow for user {user_id}")

            result: OCRResult = await analyze_image(
                image_bytes=bytes(photo_bytes),
                user_id=str(user_id),
                skip_quality_check=skip_quality_check,
                min_confidence=min_confidence,
            )

            logger.info(
                f"[PHOTO_OCR] ✓ OCR completed. Provider: {result.provider}, "
                f"Confidence: {result.confidence:.0%}, Error: {result.error or 'None'}",
                extra={
                    "user_id": user_id,
                    "provider": result.provider,
                    "confidence": result.confidence,
                    "has_error": bool(result.error)
                }
            )

            # Format response
            response = format_ocr_response(result)

            # Add "Create Equipment?" button if OCR successful and feature enabled
            if enable_equipment_creation and (result.manufacturer or result.model_number):
                # Store OCR data for callback
                context.user_data['pending_equipment'] = {
                    "manufacturer": result.manufacturer,
                    "model": result.model_number,
                    "serial": result.serial_number,
                    "type": result.equipment_type,
                    "voltage": result.voltage,
                    "current": result.current
                }

                # Add inline keyboard
                keyboard = [[
                    InlineKeyboardButton("✓ Create Equipment", callback_data="create_equip"),
                    InlineKeyboardButton("✗ Skip", callback_data="skip_equip")
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(response, parse_mode="Markdown", reply_markup=reply_markup)
            else:
                # No manufacturer/model found, or feature disabled, send without buttons
                await update.message.reply_text(response, parse_mode="Markdown")

            logger.info(
                f"OCR result sent to user {user_id}",
                extra={
                    "user_id": user_id,
                    "manufacturer": result.manufacturer,
                    "model": result.model_number,
                    "confidence": result.confidence,
                    "cost_usd": result.cost_usd,
                },
            )

        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"[PHOTO_ERROR] Processing failed: {error_type}: {e}",
                exc_info=True,
                extra={"user_id": user_id, "error_type": error_type}
            )

            # Classify error for better user message
            error_str = str(e).lower()
            if "timeout" in error_str:
                user_message = (
                    "❌ **Photo Download Timeout**\n\n"
                    "The download took too long. Please try again or send a smaller image."
                )
            elif "quality" in error_str or "too dark" in error_str or "overexposed" in error_str:
                user_message = (
                    f"❌ **Image Quality Issue**\n\n{str(e)}\n\n"
                    f"Tips: Use natural lighting, avoid reflections, get closer to text"
                )
            else:
                user_message = f"❌ **Error**: {str(e)}\n\nPlease try again or contact support."

            try:
                await update.message.reply_text(user_message, parse_mode="Markdown")
            except Exception as reply_error:
                logger.error(f"[PHOTO_ERROR] Failed to send error message: {reply_error}")

    return photo_handler


def create_start_handler(bot_name: str = "RIVET Pro"):
    """
    Returns start command handler with custom bot name.

    Args:
        bot_name: Name to display in welcome message
    """
    async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /start command - User onboarding + Atlas CMMS registration.
        """
        user_id = update.effective_user.id
        username = update.effective_user.username or f"user{user_id}"
        first_name = update.effective_user.first_name or ""
        last_name = update.effective_user.last_name or ""

        logger.info(f"New user started bot: {user_id} (@{username})")

        # Register user in Atlas CMMS
        try:
            async with AtlasClient() as client:
                await client.create_user({
                    "email": f"{username}@telegram.local",
                    "firstName": first_name or username,
                    "lastName": last_name,
                    "password": str(user_id),
                    "role": "TECHNICIAN"
                })
                logger.info(f"Registered user {username} in Atlas CMMS")
        except AtlasValidationError:
            # User likely already exists
            logger.info(f"User {username} already exists in Atlas CMMS")
        except Exception as e:
            # Don't block onboarding if Atlas registration fails
            logger.warning(f"Atlas registration failed for {username}: {e}")

        welcome_message = f"""
👋 **Welcome to {bot_name}**, {username}!

I'm your industrial maintenance AI assistant.

**What I can do:**
📸 **Photo Analysis** - Send me equipment photos and I'll identify:
   • Manufacturer & model
   • Serial numbers
   • Fault codes
   • Technical specs

💬 **Troubleshooting** - Ask me questions about:
   • Siemens, Rockwell, ABB, Schneider, Mitsubishi, Fanuc
   • PLC programming
   • VFD configuration
   • Equipment diagnostics

**Get started:**
1. Send a photo of equipment nameplate
2. Or ask a troubleshooting question

Type /help for more commands.
"""

        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    return start_handler


def create_error_handler():
    """
    Returns error handler for bot errors.
    """
    async def error_handler(update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle errors in the bot.
        """
        logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)

        if update and update.effective_message:
            error_message = """
❌ **Oops! Something went wrong.**

Our team has been notified. Please try again in a moment.

If the issue persists, contact support: @rivet_support
"""
            await update.effective_message.reply_text(error_message, parse_mode="Markdown")

    return error_handler
