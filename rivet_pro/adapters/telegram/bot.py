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
from rivet_pro.core.services.work_order_service import WorkOrderService

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
        self.work_order_service = None  # Initialized after db connects

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

    async def equip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /equip command.

        Usage:
          /equip list - List your equipment
          /equip search <query> - Search equipment
          /equip view <equipment_number> - View equipment details
        """
        user_id = f"telegram_{update.effective_user.id}"
        args = context.args or []

        try:
            if not args or args[0] == "list":
                # List equipment
                equipment_list = await self.db.execute_query_async(
                    """
                    SELECT
                        equipment_number,
                        manufacturer,
                        model_number,
                        work_order_count
                    FROM cmms_equipment
                    WHERE owned_by_user_id = $1
                    ORDER BY created_at DESC
                    LIMIT 10
                    """,
                    (user_id,)
                )

                if not equipment_list:
                    await update.message.reply_text(
                        "📦 *Your Equipment*\n\n"
                        "No equipment found. Send me a photo of a nameplate to get started!",
                        parse_mode="Markdown"
                    )
                    return

                response = "📦 *Your Equipment* (most recent 10)\n\n"
                for eq in equipment_list:
                    wo_count = eq['work_order_count']
                    response += f"• `{eq['equipment_number']}` - {eq['manufacturer']} {eq['model_number'] or ''}\n"
                    response += f"  └─ {wo_count} work order{'s' if wo_count != 1 else ''}\n"

                response += "\n💡 Use `/equip view <number>` to see details"
                await update.message.reply_text(response, parse_mode="Markdown")

            elif args[0] == "search":
                if len(args) < 2:
                    await update.message.reply_text(
                        "Usage: `/equip search <query>`\nExample: `/equip search siemens`",
                        parse_mode="Markdown"
                    )
                    return

                query = " ".join(args[1:])
                results = await self.db.execute_query_async(
                    """
                    SELECT
                        equipment_number,
                        manufacturer,
                        model_number,
                        serial_number
                    FROM cmms_equipment
                    WHERE owned_by_user_id = $1
                      AND (
                          manufacturer ILIKE $2
                          OR model_number ILIKE $2
                          OR serial_number ILIKE $2
                      )
                    LIMIT 10
                    """,
                    (user_id, f"%{query}%")
                )

                if not results:
                    await update.message.reply_text(f"🔍 No equipment found matching: *{query}*", parse_mode="Markdown")
                    return

                response = f"🔍 *Search Results for: {query}*\n\n"
                for eq in results:
                    response += f"• `{eq['equipment_number']}` - {eq['manufacturer']} {eq['model_number'] or ''}\n"

                await update.message.reply_text(response, parse_mode="Markdown")

            elif args[0] == "view":
                if len(args) < 2:
                    await update.message.reply_text(
                        "Usage: `/equip view <equipment_number>`\nExample: `/equip view EQ-2026-000001`",
                        parse_mode="Markdown"
                    )
                    return

                equipment_number = args[1]
                equipment = await self.db.execute_query_async(
                    """
                    SELECT *
                    FROM cmms_equipment
                    WHERE owned_by_user_id = $1 AND equipment_number = $2
                    """,
                    (user_id, equipment_number),
                    fetch_mode="one"
                )

                if not equipment:
                    await update.message.reply_text(f"❌ Equipment `{equipment_number}` not found", parse_mode="Markdown")
                    return

                eq = equipment[0]
                response = f"📦 *Equipment Details*\n\n"
                response += f"*Number:* `{eq['equipment_number']}`\n"
                response += f"*Manufacturer:* {eq['manufacturer']}\n"
                response += f"*Model:* {eq['model_number'] or 'N/A'}\n"
                response += f"*Serial:* {eq['serial_number'] or 'N/A'}\n"
                response += f"*Type:* {eq['equipment_type'] or 'N/A'}\n"
                response += f"*Location:* {eq['location'] or 'Not specified'}\n"
                response += f"*Work Orders:* {eq['work_order_count']}\n"
                response += f"*Last Fault:* {eq['last_reported_fault'] or 'None'}\n"

                await update.message.reply_text(response, parse_mode="Markdown")

            else:
                await update.message.reply_text(
                    "📦 *Equipment Commands*\n\n"
                    "`/equip list` - List your equipment\n"
                    "`/equip search <query>` - Search equipment\n"
                    "`/equip view <number>` - View details",
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Error in /equip command: {e}", exc_info=True)
            await update.message.reply_text("❌ An error occurred. Please try again.")

    async def wo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /wo command.

        Usage:
          /wo list - List your work orders
          /wo view <work_order_number> - View work order details
        """
        user_id = f"telegram_{update.effective_user.id}"
        args = context.args or []

        try:
            if not args or args[0] == "list":
                # List work orders
                work_orders = await self.work_order_service.list_work_orders_by_user(
                    user_id=user_id,
                    limit=10
                )

                if not work_orders:
                    await update.message.reply_text(
                        "🔧 *Your Work Orders*\n\n"
                        "No work orders found.",
                        parse_mode="Markdown"
                    )
                    return

                response = "🔧 *Your Work Orders* (most recent 10)\n\n"
                for wo in work_orders:
                    status_emoji = {
                        "open": "🟢",
                        "in_progress": "🟡",
                        "completed": "✅",
                        "cancelled": "🔴"
                    }.get(wo['status'], "⚪")

                    priority_emoji = {
                        "low": "🔵",
                        "medium": "🟡",
                        "high": "🟠",
                        "critical": "🔴"
                    }.get(wo['priority'], "⚪")

                    response += f"{status_emoji} `{wo['work_order_number']}` {priority_emoji}\n"
                    response += f"  {wo['title']}\n"
                    response += f"  └─ Equipment: `{wo['equipment_number']}`\n"

                response += "\n💡 Use `/wo view <number>` to see details"
                await update.message.reply_text(response, parse_mode="Markdown")

            elif args[0] == "view":
                if len(args) < 2:
                    await update.message.reply_text(
                        "Usage: `/wo view <work_order_number>`\nExample: `/wo view WO-2026-000001`",
                        parse_mode="Markdown"
                    )
                    return

                work_order_number = args[1]
                work_order = await self.db.execute_query_async(
                    """
                    SELECT *
                    FROM work_orders
                    WHERE user_id = $1 AND work_order_number = $2
                    """,
                    (user_id, work_order_number),
                    fetch_mode="one"
                )

                if not work_order:
                    await update.message.reply_text(f"❌ Work order `{work_order_number}` not found", parse_mode="Markdown")
                    return

                wo = work_order[0]
                status_emoji = {
                    "open": "🟢",
                    "in_progress": "🟡",
                    "completed": "✅",
                    "cancelled": "🔴"
                }.get(wo['status'], "⚪")

                response = f"🔧 *Work Order Details*\n\n"
                response += f"*Number:* `{wo['work_order_number']}`\n"
                response += f"*Status:* {status_emoji} {wo['status'].title()}\n"
                response += f"*Priority:* {wo['priority'].title()}\n"
                response += f"*Equipment:* `{wo['equipment_number']}`\n"
                response += f"*Title:* {wo['title']}\n"
                response += f"*Description:*\n{wo['description']}\n"

                if wo.get('fault_codes'):
                    response += f"*Fault Codes:* {', '.join(wo['fault_codes'])}\n"

                response += f"*Created:* {wo['created_at'].strftime('%Y-%m-%d %H:%M')}\n"

                await update.message.reply_text(response, parse_mode="Markdown")

            else:
                await update.message.reply_text(
                    "🔧 *Work Order Commands*\n\n"
                    "`/wo list` - List your work orders\n"
                    "`/wo view <number>` - View details",
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Error in /wo command: {e}", exc_info=True)
            await update.message.reply_text("❌ An error occurred. Please try again.")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /stats command.
        Show user statistics.
        """
        user_id = f"telegram_{update.effective_user.id}"

        try:
            # Get equipment count
            equipment_count = await self.db.fetchval(
                "SELECT COUNT(*) FROM cmms_equipment WHERE owned_by_user_id = $1",
                user_id
            )

            # Get work order stats
            wo_stats = await self.db.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'open') as open,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed
                FROM work_orders
                WHERE user_id = $1
                """,
                user_id
            )

            response = f"📊 *Your CMMS Stats*\n\n"
            response += f"📦 *Equipment:* {equipment_count or 0}\n\n"
            response += f"🔧 *Work Orders:*\n"
            response += f"  └─ 🟢 Open: {wo_stats['open'] if wo_stats else 0}\n"
            response += f"  └─ 🟡 In Progress: {wo_stats['in_progress'] if wo_stats else 0}\n"
            response += f"  └─ ✅ Completed: {wo_stats['completed'] if wo_stats else 0}\n"

            await update.message.reply_text(response, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /stats command: {e}", exc_info=True)
            await update.message.reply_text("❌ An error occurred. Please try again.")

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

        # Register command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("equip", self.equip_command))
        self.application.add_handler(CommandHandler("wo", self.wo_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))

        # Register message handler (for non-command messages)
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
        self.work_order_service = WorkOrderService(self.db)
        logger.info("Database and services initialized")

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
