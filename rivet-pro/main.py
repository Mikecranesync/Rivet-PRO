"""
RIVET Pro - Main Application Entrypoint

Industrial maintenance AI assistant for equipment identification and manual delivery.
"""

import logging
import asyncio
from telegram import Update

from config.settings import get_settings
from adapters.telegram.bot import create_bot
from infra.database import test_connection


# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


async def main():
    """
    Application entry point.

    Phase 1: Walking Skeleton
    - Load settings from environment
    - Test database connection
    - Start Telegram bot
    """
    logger.info("="* 60)
    logger.info("RIVET Pro - Starting Application")
    logger.info("="* 60)

    # Load settings
    try:
        settings = get_settings()
        logger.info("✓ Settings loaded from environment")
        logger.info(f"  - Orchestrator: {settings.orchestrator_provider}/{settings.orchestrator_model}")
        logger.info(f"  - Beta Mode: {settings.beta_mode}")
    except Exception as e:
        logger.error(f"✗ Failed to load settings: {e}")
        logger.error("  Make sure .env file exists with required variables")
        return

    # Test database connection
    logger.info("-" * 60)
    db_ok = await test_connection(settings.database_url)
    if not db_ok:
        logger.warning("⚠ Database connection failed - continuing anyway (Phase 1)")
    logger.info("-" * 60)

    # Create and run Telegram bot
    try:
        app = create_bot(settings.telegram_bot_token)

        logger.info("=" * 60)
        logger.info("🤖 RIVET Pro bot is now running...")
        logger.info("   Send a message to test!")
        logger.info("=" * 60)

        # Run bot with polling
        await app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

    except Exception as e:
        logger.error(f"✗ Bot startup failed: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down RIVET Pro...")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        raise
