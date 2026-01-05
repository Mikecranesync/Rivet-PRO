"""
Telegram bot adapter for Rivet Pro.
Handles all Telegram-specific interaction logic.
"""

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from rivet_pro.config.settings import settings
from rivet_pro.infra.observability import get_logger
from rivet_pro.infra.database import Database
from rivet_pro.core.services.equipment_service import EquipmentService

logger = get_logger(__name__)


class TelegramBot:
    """
    Telegram bot adapter.
    Manages bot lifecycle and message routing.
    """

    def __init__(self):
        self.application: Application = None
        self.db = Database()
        self.equipment_service = None  # Initialized after db connects

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /start command.
        This is the only slash command - used for initial registration.
        """
        user = update.effective_user
        logger.info(f"User started bot | user_id={user.id} | username={user.username}")

        welcome_message = (
            f"👋 Hey {user.first_name}, I'm RIVET.\n\n"
            "Send me a photo of any equipment nameplate and I'll find you the manual. "
            "Try it now 👇"
        )

        await update.message.reply_text(welcome_message)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle all incoming messages (text, photos, etc.).
        This is the main entry point for user interaction.
        """
        user = update.effective_user
        message = update.message

        # Log the interaction
        content_type = "text"
        if message.photo:
            content_type = "photo"
        elif message.document:
            content_type = "document"

        logger.info(
            f"Received message | user_id={user.id} | type={content_type} | "
            f"text={'...' if message.text and len(message.text) > 50 else message.text}"
        )

        # Route based on message type
        try:
            if message.photo:
                await self._handle_photo(update, context)
            elif message.text:
                await self._handle_text(update, context)
            else:
                await update.message.reply_text(
                    "I can help with photos of equipment nameplates or questions about equipment. "
                    "Try sending me a photo!"
                )
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await update.message.reply_text(
                "⚠️ Something went wrong processing your request. Please try again."
            )

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle photo messages with OCR analysis and streaming responses.
        """
        from rivet_pro.core.services import analyze_image

        user_id = str(update.effective_user.id)

        # Send initial message with streaming
        msg = await update.message.reply_text("🔍 Analyzing nameplate...")

        try:
            # Download photo (get highest resolution)
            photo = await update.message.photo[-1].get_file()
            photo_bytes = await photo.download_as_bytearray()

            logger.info(f"Downloaded photo | user_id={user_id} | size={len(photo_bytes)} bytes")

            # Update message: OCR in progress
            await msg.edit_text("🔍 Analyzing nameplate...\n⏳ Reading text from image...")

            # Run OCR analysis
            result = await analyze_image(
                image_bytes=photo_bytes,
                user_id=user_id
            )

            # Handle OCR errors
            if hasattr(result, 'error') and result.error:
                await msg.edit_text(
                    f"❌ {result.error}\n\n"
                    "Try taking a clearer photo with good lighting and focus on the nameplate."
                )
                return

            # Create or match equipment in CMMS
            equipment_id = None
            equipment_number = None
            is_new = False

            try:
                equipment_id, equipment_number, is_new = await self.equipment_service.match_or_create_equipment(
                    manufacturer=result.manufacturer,
                    model_number=result.model_number,
                    serial_number=result.serial_number,
                    equipment_type=getattr(result, 'equipment_type', None),
                    location=None,  # Can be added later via conversation
                    user_id=f"telegram_{user_id}"
                )
                logger.info(
                    f"Equipment {'created' if is_new else 'matched'} | "
                    f"equipment_number={equipment_number} | user_id={user_id}"
                )
            except Exception as e:
                logger.error(f"Failed to create/match equipment: {e}", exc_info=True)
                # Continue anyway - OCR succeeded even if CMMS failed

            # Format successful OCR result
            confidence_emoji = "✅" if result.confidence >= 0.85 else "⚠️"

            # Use HTML formatting (more robust than Markdown for special characters)
            response = (
                f"{confidence_emoji} <b>Equipment Identified</b>\n\n"
                f"<b>Manufacturer:</b> {result.manufacturer}\n"
                f"<b>Model:</b> {result.model_number or 'Not detected'}\n"
                f"<b>Serial:</b> {result.serial_number or 'Not detected'}\n"
                f"<b>Confidence:</b> {result.confidence:.0%}\n"
            )

            # Add equipment number if created/matched
            if equipment_number:
                status = "🆕 Created" if is_new else "✓ Matched"
                response += f"\n<b>Equipment:</b> {equipment_number} ({status})\n"

            # Add component type if detected
            if hasattr(result, 'component_type') and result.component_type:
                response += f"<b>Type:</b> {result.component_type}\n"

            await msg.edit_text(response, parse_mode="HTML")

            logger.info(
                f"OCR complete | user_id={user_id} | "
                f"manufacturer={result.manufacturer} | "
                f"model={result.model_number} | "
                f"confidence={result.confidence:.2%}"
            )

        except Exception as e:
            logger.error(f"Error in photo handler: {e}", exc_info=True)
            await msg.edit_text(
                "❌ Failed to analyze photo. Please try again with a clearer image."
            )

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle text messages with SME routing.
        """
        from rivet_pro.core.services import route_to_sme

        user_id = str(update.effective_user.id)
        user_message = update.message.text

        # Send initial message
        msg = await update.message.reply_text("🤔 Analyzing your question...")

        try:
            # Route to appropriate SME
            await msg.edit_text("🤔 Analyzing your question...\n⏳ Consulting expert...")

            response = await route_to_sme(
                user_message=user_message,
                user_id=user_id
            )

            # Format response
            await msg.edit_text(response)

            logger.info(
                f"SME routing complete | user_id={user_id} | "
                f"question_length={len(user_message)}"
            )

        except Exception as e:
            logger.error(f"Error in text handler: {e}", exc_info=True)
            await msg.edit_text(
                "❌ I had trouble understanding your question. "
                "Try asking about a specific equipment model or issue."
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle errors in the bot.
        """
        logger.error(f"Update {update} caused error: {context.error}")

        # Try to notify the user if possible
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Our team has been notified."
            )

    def build(self) -> Application:
        """
        Build and configure the Telegram application.

        Returns:
            Configured Application instance
        """
        logger.info("Building Telegram bot application")

        # Create application
        self.application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .build()
        )

        # Register handlers
        self.application.add_handler(
            CommandHandler("start", self.start_command)
        )

        self.application.add_handler(
            MessageHandler(
                filters.ALL & ~filters.COMMAND,
                self.handle_message
            )
        )

        # Register error handler
        self.application.add_error_handler(self.error_handler)

        logger.info("Telegram bot application built successfully")

        return self.application

    async def start(self) -> None:
        """
        Start the bot using polling (for development).
        """
        if self.application is None:
            self.build()

        logger.info("Starting Telegram bot with polling...")

        # Connect to database
        await self.db.connect()
        self.equipment_service = EquipmentService(self.db)
        logger.info("Database and equipment service initialized")

        # Initialize the application
        await self.application.initialize()
        await self.application.start()

        # Start polling
        await self.application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

        logger.info("✅ Telegram bot is running and polling for updates")

    async def stop(self) -> None:
        """
        Stop the bot gracefully.
        """
        if self.application is None:
            return

        logger.info("Stopping Telegram bot...")

        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

        # Disconnect database
        if self.db:
            await self.db.disconnect()

        logger.info("Telegram bot stopped")


# Singleton bot instance
telegram_bot = TelegramBot()
