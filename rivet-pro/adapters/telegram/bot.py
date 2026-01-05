"""
Telegram Bot Adapter

Platform-specific Telegram implementation using python-telegram-bot v20+.
Follows clean architecture - this is a thin adapter layer.
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command - Initial user registration.

    This is the ONLY slash command in the bot (per spec).
    All other interactions are conversational.
    """
    user = update.effective_user
    logger.info(f"New user started bot: {user.id} (@{user.username})")

    welcome_message = (
        f"Hey, I'm RIVET. Send me a photo of any equipment nameplate "
        f"and I'll find you the manual. Try it now 👇"
    )

    await update.message.reply_text(welcome_message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages.

    Phase 1: Simply respond "I'm alive"
    Future: Route to orchestrator for intelligent response
    """
    user_id = update.effective_user.id
    message_text = update.message.text

    logger.info(f"Message from user {user_id}: {message_text[:50]}...")

    # Phase 1: Basic alive response
    await update.message.reply_text("I'm alive 🤖")

    # TODO Phase 6: Replace with orchestrator
    # from core.reasoning.orchestrator import Orchestrator
    # orchestrator = Orchestrator()
    # response = await orchestrator.process(message_text, user_id, context)
    # await update.message.reply_text(response.text)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle photo messages.

    Phase 1: Acknowledge receipt
    Future: Route to OCR pipeline
    """
    user_id = update.effective_user.id
    logger.info(f"Photo received from user {user_id}")

    # Phase 1: Basic acknowledgment
    await update.message.reply_text("Photo received! 📸 (OCR coming in Phase 2)")

    # TODO Phase 2: Implement OCR pipeline
    # from core.ocr.pipeline import OCRPipeline
    # ocr = OCRPipeline()
    # photo = update.message.photo[-1]
    # file = await context.bot.get_file(photo.file_id)
    # photo_bytes = await file.download_as_bytearray()
    # result = await ocr.extract(bytes(photo_bytes))
    # await update.message.reply_text(f"Extracted: {result.text}")


def create_bot(token: str) -> Application:
    """
    Create and configure the Telegram bot application.

    Args:
        token: Telegram bot token from BotFather

    Returns:
        Configured Application instance

    Example:
        >>> app = create_bot("123456:ABC-DEF...")
        >>> await app.run_polling()
    """
    logger.info("Creating Telegram bot application...")

    # Build application
    app = Application.builder().token(token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("✓ Telegram bot configured successfully")

    return app
