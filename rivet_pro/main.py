"""
Rivet Pro - Main Application Entrypoint

This is the walking skeleton for Rivet Pro.
Phase 1: Basic bot that responds to messages and tests database connection.
"""

import asyncio
import signal
from rivet_pro.config.settings import settings
from rivet_pro.infra.database import db
from rivet_pro.infra.observability import get_logger
from rivet_pro.adapters.telegram.bot import telegram_bot

logger = get_logger(__name__)


class RivetProApplication:
    """
    Main application orchestrator.
    Manages lifecycle of all components.
    """

    def __init__(self):
        self.shutdown_event = asyncio.Event()

    async def startup(self) -> None:
        """
        Initialize all application components.
        """
        logger.info("=" * 80)
        logger.info("Starting Rivet Pro")
        logger.info("=" * 80)
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Log Level: {settings.log_level}")
        logger.info(f"Beta Mode: {settings.beta_mode}")
        logger.info("=" * 80)

        # Connect to database
        try:
            await db.connect()

            # Test database connection
            is_healthy = await db.health_check()
            if is_healthy:
                logger.info("✅ Database health check passed")
            else:
                logger.error("❌ Database health check failed")
                raise RuntimeError("Database is not healthy")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            logger.warning("Continuing without database (for testing only)")

        # Start Telegram bot
        await telegram_bot.start()

        logger.info("=" * 80)
        logger.info("✅ Rivet Pro is running")
        logger.info("=" * 80)

    async def shutdown(self) -> None:
        """
        Gracefully shutdown all application components.
        """
        logger.info("=" * 80)
        logger.info("Shutting down Rivet Pro")
        logger.info("=" * 80)

        # Stop Telegram bot
        await telegram_bot.stop()

        # Close database connection
        await db.disconnect()

        logger.info("=" * 80)
        logger.info("✅ Rivet Pro shutdown complete")
        logger.info("=" * 80)

    async def run(self) -> None:
        """
        Run the application until shutdown signal is received.
        """
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.handle_shutdown())
            )

        # Startup
        await self.startup()

        # Wait for shutdown signal
        await self.shutdown_event.wait()

        # Shutdown
        await self.shutdown()

    async def handle_shutdown(self) -> None:
        """
        Handle shutdown signal.
        """
        logger.info("Shutdown signal received")
        self.shutdown_event.set()


async def main():
    """
    Main entry point.
    """
    app = RivetProApplication()

    try:
        await app.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        raise
    finally:
        # Ensure cleanup happens
        if not app.shutdown_event.is_set():
            await app.shutdown()


if __name__ == "__main__":
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
