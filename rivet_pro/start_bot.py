"""
Simple script to start the Telegram bot.

Usage:
    python start_bot.py
"""

import asyncio
import fcntl
import sys
from pathlib import Path
from rivet_pro.adapters.telegram.bot import telegram_bot
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

# Lock file to prevent multiple instances
LOCK_FILE = Path("/tmp/rivet_bot.lock")


async def main():
    """Start the Telegram bot."""
    lock_file = None

    try:
        # Acquire exclusive lock to prevent multiple instances
        lock_file = open(LOCK_FILE, 'w')
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_file.write(str(sys.argv[0]))
            lock_file.flush()
            logger.info("🔒 Bot lock acquired")
        except BlockingIOError:
            logger.error("❌ Another bot instance is already running!")
            logger.error(f"❌ Lock file: {LOCK_FILE}")
            logger.error("❌ Please stop the other instance first or use:")
            logger.error("❌   systemctl restart rivet-bot")
            sys.exit(1)

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

        # Release lock
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
                LOCK_FILE.unlink(missing_ok=True)
                logger.info("🔓 Bot lock released")
            except Exception as e:
                logger.warning(f"⚠️  Failed to release lock: {e}")


if __name__ == "__main__":
    asyncio.run(main())
