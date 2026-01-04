"""
RIVET CMMS Telegram Bot

Specialized bot for Atlas CMMS equipment and work order management.
Uses @RivetCMMS_bot token (PUBLIC_TELEGRAM_BOT_TOKEN).

Features:
- Photo OCR → Equipment creation
- Equipment management (/equip search, create, view)
- Work order management (/wo create, list, view, complete)
- Technician registration
- NO general AI queries or troubleshooting (use main bot for that)
"""

import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from rivet.config import config
from rivet.integrations.atlas import AtlasClient, AtlasNotFoundError, AtlasValidationError
from rivet.integrations.telegram_shared import (
    create_photo_handler,
    create_start_handler,
    create_error_handler,
)

# Import handlers from main telegram.py to avoid duplication
from rivet.integrations.telegram import (
    equip_handler,
    wo_handler,
    callback_handler,
    handle_equipment_creation_flow,
    handle_wo_creation_flow,
)

logger = logging.getLogger("rivet.telegram.cmms_bot")


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - CMMS-specific help."""
    help_message = """
🏭 **Rivet CMMS - Equipment Management**

**Photo Analysis:**
📸 Send equipment photo to:
   • Identify manufacturer & model
   • Extract serial number & specs
   • Create equipment in database

**Equipment Commands:**
   `/equip search <query>` - Search equipment
   `/equip view <id>` - View details
   `/equip create` - Create new equipment

**Work Order Commands:**
   `/wo create <equipment_id>` - New work order
   `/wo list [status]` - List work orders
   `/wo view <id>` - View details
   `/wo complete <id>` - Mark complete

**Examples:**
• Send nameplate photo → Create equipment
• `/equip search motor` - Find motors
• `/wo create 123` - Create WO for equipment #123

**Other Features:**
For AI troubleshooting and queries, use @RivetCeo_bot
"""
    await update.message.reply_text(help_message, parse_mode="Markdown")


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    status_message = f"""
✅ **Bot Status**

🤖 **Bot:** Rivet CMMS
🏷️ **Version:** 1.0.0
🔌 **Status:** Online

**Capabilities:**
• Equipment Management ✓
• Work Order Management ✓
• Photo OCR ✓

**Database:** {"Connected" if config.database_url else "Not configured"}
"""
    await update.message.reply_text(status_message, parse_mode="Markdown")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages - Route to conversation flows.

    CMMS bot handles conversation flows for:
    - Equipment creation (multi-step)
    - Work order creation (multi-step)
    """
    user_id = update.effective_user.id
    text = update.message.text

    # Check for active conversation flows
    if 'equip_create_state' in context.user_data:
        await handle_equipment_creation_flow(update, context, text)
        return

    if 'wo_create_state' in context.user_data:
        await handle_wo_creation_flow(update, context, text)
        return

    # No active flow - provide guidance
    await update.message.reply_text(
        "💬 Type /help to see available commands.\n\n"
        "For AI troubleshooting, use @RivetCeo_bot",
        parse_mode="Markdown"
    )


# ============================================================================
# BOT SETUP
# ============================================================================

def setup_bot() -> Application:
    """
    Configure and return the Rivet CMMS bot application.
    """
    # Create application with CMMS bot token
    application = Application.builder().token(config.public_telegram_bot_token).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", create_start_handler("Rivet CMMS")))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("status", status_handler))

    # CMMS commands (imported from telegram.py)
    application.add_handler(CommandHandler("equip", equip_handler))
    application.add_handler(CommandHandler("wo", wo_handler))

    # Photo handler WITH equipment creation button
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            create_photo_handler(
                enable_equipment_creation=True,
                skip_quality_check=False,    # Keep validation
                min_confidence=0.5,          # Relaxed threshold
            )
        )
    )

    # Text messages → conversation flows
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Callback handler for inline buttons (imported from telegram.py)
    application.add_handler(CallbackQueryHandler(callback_handler))

    # Error handler
    application.add_error_handler(create_error_handler())

    logger.info("Rivet CMMS bot configured successfully")

    return application


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main entry point for Rivet CMMS Telegram bot.

    Run with: python -m rivet.integrations.telegram_cmms_bot
    """
    # Configure logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    # Log configuration status
    config.log_status()

    # Validate telegram token
    if not config.public_telegram_bot_token:
        logger.error("PUBLIC_TELEGRAM_BOT_TOKEN not set in environment!")
        return

    # Setup and run bot
    logger.info("Starting Rivet CMMS Telegram bot...")
    application = setup_bot()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
