"""
Simple cross-platform script to start the Rivet Pro Telegram bot.

Usage:
    python run_bot.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from rivet_pro.adapters.telegram.bot import telegram_bot
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


async def main():
    """Start the Telegram bot."""
    try:
        print("=" * 60)
        print("  RIVET Pro Telegram Bot")
        print("=" * 60)
        print()

        await telegram_bot.start()

        print()
        print("Bot is now running. Press Ctrl+C to stop.")
        print()

        # Keep running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nError: {e}")
    finally:
        await telegram_bot.stop()
        print("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
