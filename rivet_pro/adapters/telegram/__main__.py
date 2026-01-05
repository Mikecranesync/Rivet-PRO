"""
Run the Telegram bot.

Usage:
    python -m rivet_pro.adapters.telegram
"""

import asyncio
import signal
from rivet_pro.adapters.telegram.bot import telegram_bot
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


async def main():
    """Main entry point for the Telegram bot."""
    bot = telegram_bot

    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("=" * 60)
        logger.info("Starting RIVET Pro Telegram Bot")
        logger.info("=" * 60)

        await bot.start()

        # Keep the bot running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        logger.info("Shutting down bot...")
        await bot.stop()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
