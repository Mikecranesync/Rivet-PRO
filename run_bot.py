"""
Simple cross-platform script to start the Rivet Pro Telegram bot.

Usage:
    python run_bot.py
"""

import asyncio
import sys
import os
import httpx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Wake Neon before startup validation (which connects to DB)
N8N_WAKE_URL = os.getenv("N8N_WAKE_URL", "https://mikecranesync.app.n8n.cloud/webhook/wake-neon")

def wake_neon():
    """Call n8n webhook to wake Neon database before connecting."""
    try:
        print("Waking Neon database...")
        response = httpx.get(N8N_WAKE_URL, timeout=30.0)
        if response.status_code == 200:
            print(f"  Neon awake: {response.json()}")
            return True
        else:
            print(f"  Wake webhook returned {response.status_code}, continuing anyway...")
            return True  # Continue even if webhook fails
    except Exception as e:
        print(f"  Wake webhook failed ({e}), continuing anyway...")
        return True  # Don't block startup if webhook is down

wake_neon()

# Run startup validation BEFORE importing bot (which connects to DB)
from rivet_pro.core.startup_validation import run_startup_validation
if not run_startup_validation():
    print("\nStartup validation failed. Exiting.")
    sys.exit(1)

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
