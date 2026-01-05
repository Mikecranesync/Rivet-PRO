"""
Simple script to start the Telegram bot.

Usage:
    python start_bot.py
"""

import asyncio
from adapters.telegram.bot import telegram_bot
from infra.observability import get_logger

logger = get_logger(__name__)


async def main():
    """Start the Telegram bot."""
    try:
        logger.info("=" * 60)
        logger.info("🤖 Starting RIVET Pro Telegram Bot")
        logger.info("=" * 60)

        await telegram_bot.start()

        # Keep running
        logger.info("✅ Bot is now running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
    finally:
        await telegram_bot.stop()
        logger.info("✅ Bot stopped successfully")


if __name__ == "__main__":
    asyncio.run(main())
