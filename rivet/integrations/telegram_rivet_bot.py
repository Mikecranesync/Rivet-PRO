"""
RIVET Telegram Bot (Main Production)

Production AI assistant bot for troubleshooting and equipment analysis.
Uses @RivetCeo_bot token (ORCHESTRATOR_BOT_TOKEN).

Features:
- Photo OCR and equipment detection
- Troubleshooting queries (manufacturer detection + SME routing)
- General AI queries
- Read-only equipment search
- NO equipment creation or work order management (use CMMS bot for that)
"""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from rivet.config import config
from rivet.workflows.troubleshoot import troubleshoot, TroubleshootResult
from rivet.integrations.telegram_shared import (
    create_photo_handler,
    create_start_handler,
    create_error_handler,
)

logger = logging.getLogger("rivet.telegram.rivet_bot")


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_message = """
🤖 **Rivet - AI Assistant Commands**

**Photo Analysis:**
📸 Send a photo of equipment nameplate to identify:
   • Manufacturer & model
   • Serial numbers
   • Fault codes
   • Technical specs

**Troubleshooting:**
💬 Send any troubleshooting question about:
   • Siemens, Rockwell, ABB, Schneider, Mitsubishi, Fanuc
   • PLC programming, VFD configuration
   • Equipment diagnostics

**Commands:**
/start - Welcome message
/help - Show this help
/status - Bot status

**CMMS Features:**
For equipment management and work orders, use @RivetCMMS_bot
"""
    await update.message.reply_text(help_message, parse_mode="Markdown")


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    status_message = f"""
✅ **Bot Status**

🤖 **Bot:** Rivet (Main Production)
🏷️ **Version:** 1.0.0
🔌 **Status:** Online

**Capabilities:**
• Photo OCR ✓
• Troubleshooting ✓
• AI Queries ✓

**LLM Providers Available:**
{chr(10).join(f"• {p}" for p in config.get_available_ocr_providers()) or "• None configured"}
"""
    await update.message.reply_text(status_message, parse_mode="Markdown")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages - Troubleshooting queries.

    Routes messages to the troubleshooting workflow with manufacturer detection
    and 4-route system (KB/SME/Research/General).
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    query = update.message.text

    logger.info(
        f"Query received from user {user_id}: {query[:100]}...",
        extra={"user_id": user_id},
    )

    # Send typing indicator
    await update.message.chat.send_action(action="typing")

    try:
        # Call troubleshooting workflow
        result: TroubleshootResult = await troubleshoot(
            query=query,
            user_id=str(user_id),
        )

        # Format response
        response = format_troubleshoot_response(result)

        # Send result
        await update.message.reply_text(response, parse_mode="Markdown")

        logger.info(
            f"Troubleshoot result sent to user {user_id}",
            extra={
                "user_id": user_id,
                "route": result.route,
                "confidence": result.confidence,
                "manufacturer": result.manufacturer,
                "cost_usd": result.cost_usd,
            },
        )

    except Exception as e:
        logger.error(
            f"Query processing failed for user {user_id}: {e}",
            exc_info=True,
            extra={"user_id": user_id},
        )

        error_message = """
❌ **Error Processing Query**

I encountered an error processing your question.
Please try rephrasing or contact support: @rivet_support
"""
        await update.message.reply_text(error_message, parse_mode="Markdown")


def format_troubleshoot_response(result: TroubleshootResult) -> str:
    """
    Format troubleshooting result for Telegram display.
    """
    lines = []

    # Route indicator
    route_emoji = {
        "kb": "📚",
        "sme": "👨‍🔧",
        "research": "🔬",
        "general": "🤖",
    }
    emoji = route_emoji.get(result.route, "💬")

    lines.append(f"{emoji} **Answer** (via {result.route.upper()} route)\n")

    # Main answer
    lines.append(result.answer)

    # Safety warnings
    if result.safety_warnings:
        lines.append("\n⚠️ **Safety Warnings:**")
        for warning in result.safety_warnings:
            lines.append(f"  • {warning}")

    # Metadata
    lines.append(f"\n📊 **Confidence:** {result.confidence:.0%}")

    if result.manufacturer:
        lines.append(f"🏭 **Manufacturer:** {result.manufacturer}")

    return "\n".join(lines)


# ============================================================================
# BOT SETUP
# ============================================================================

def setup_bot() -> Application:
    """
    Configure and return the Rivet (Main) bot application.
    """
    # Create application with Rivet main bot token
    application = Application.builder().token(config.orchestrator_bot_token).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", create_start_handler("Rivet")))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("status", status_handler))

    # Register message handlers
    # Photo handler WITHOUT equipment creation button (read-only)
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            create_photo_handler(
                enable_equipment_creation=False,
                skip_quality_check=False,
                min_confidence=0.5,
            )
        )
    )

    # Text messages → troubleshooting
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Register error handler
    application.add_error_handler(create_error_handler())

    logger.info("Rivet (Main) bot configured successfully")

    return application


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main entry point for Rivet (Main) Telegram bot.

    Run with: python -m rivet.integrations.telegram_rivet_bot
    """
    # Configure logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    # Log configuration status
    config.log_status()

    # Validate telegram token
    if not config.orchestrator_bot_token:
        logger.error("ORCHESTRATOR_BOT_TOKEN not set in environment!")
        return

    # Setup and run bot
    logger.info("Starting Rivet (Main) Telegram bot...")
    application = setup_bot()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
