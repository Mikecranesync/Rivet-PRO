"""
Simple cross-platform script to start the Rivet Pro Telegram bot.

Includes a health check HTTP server for Fly.io monitoring.

Usage:
    python run_bot.py
"""

import asyncio
import sys
import os
import httpx
from aiohttp import web
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Health check state
health_state = {
    "started_at": None,
    "bot_running": False,
    "last_heartbeat": None,
}

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


# Health check HTTP handlers
async def health_handler(request):
    """Health check endpoint for Fly.io monitoring."""
    uptime = None
    if health_state["started_at"]:
        uptime = (datetime.utcnow() - health_state["started_at"]).total_seconds()

    status = {
        "status": "healthy" if health_state["bot_running"] else "starting",
        "bot_running": health_state["bot_running"],
        "started_at": health_state["started_at"].isoformat() if health_state["started_at"] else None,
        "uptime_seconds": uptime,
        "last_heartbeat": health_state["last_heartbeat"].isoformat() if health_state["last_heartbeat"] else None,
    }

    # Return 200 if bot is running, 503 if still starting
    http_status = 200 if health_state["bot_running"] else 503
    return web.json_response(status, status=http_status)


async def root_handler(request):
    """Root endpoint - redirect to health."""
    return web.json_response({
        "service": "rivet-cmms-bot",
        "version": "1.0.0",
        "health_check": "/health"
    })


async def start_health_server():
    """Start the health check HTTP server."""
    app = web.Application()
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_handler)

    port = int(os.getenv("PORT", "8080"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Health check server running on port {port}")
    return runner


async def heartbeat_loop():
    """Update heartbeat timestamp periodically."""
    while True:
        health_state["last_heartbeat"] = datetime.utcnow()
        await asyncio.sleep(10)


async def main():
    """Start the Telegram bot with health check server."""
    health_runner = None
    heartbeat_task = None

    try:
        print("=" * 60)
        print("  RIVET Pro Telegram Bot")
        print("=" * 60)
        print()

        # Start health check server
        health_runner = await start_health_server()
        health_state["started_at"] = datetime.utcnow()

        # Start heartbeat loop
        heartbeat_task = asyncio.create_task(heartbeat_loop())

        # Start the bot
        await telegram_bot.start()
        health_state["bot_running"] = True

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
        health_state["bot_running"] = False

        # Cancel heartbeat
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        # Stop health server
        if health_runner:
            await health_runner.cleanup()

        # Stop bot
        await telegram_bot.stop()
        print("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
