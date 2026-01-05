"""
Test script to verify Phase 1 walking skeleton setup.
Run this to check that all core components are properly configured.
"""

import asyncio
import sys
from pathlib import Path

# Add rivet_pro to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_imports():
    """Test that all core modules can be imported."""
    print("=" * 80)
    print("Testing Module Imports")
    print("=" * 80)

    try:
        from rivet_pro.config.settings import settings
        print("✅ Settings module loaded")

        from rivet_pro.infra.observability import get_logger
        print("✅ Logging module loaded")

        from rivet_pro.infra.database import db
        print("✅ Database module loaded")

        from rivet_pro.adapters.telegram.bot import telegram_bot
        print("✅ Telegram bot module loaded")

        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


async def test_settings():
    """Test that settings can be loaded."""
    print("\n" + "=" * 80)
    print("Testing Settings Configuration")
    print("=" * 80)

    try:
        from rivet_pro.config.settings import settings

        print(f"Environment: {settings.environment}")
        print(f"Log Level: {settings.log_level}")
        print(f"Beta Mode: {settings.beta_mode}")

        # Check critical settings
        if not settings.telegram_bot_token:
            print("⚠️  WARNING: TELEGRAM_BOT_TOKEN not set")
            return False

        if not settings.database_url:
            print("⚠️  WARNING: DATABASE_URL not set")
            return False

        print("✅ Settings configured correctly")
        return True

    except Exception as e:
        print(f"❌ Settings test failed: {e}")
        return False


async def test_database():
    """Test database connection."""
    print("\n" + "=" * 80)
    print("Testing Database Connection")
    print("=" * 80)

    try:
        from rivet_pro.infra.database import db

        # Try to connect
        await db.connect()
        print("✅ Database connection established")

        # Health check
        is_healthy = await db.health_check()
        if is_healthy:
            print("✅ Database health check passed")
        else:
            print("❌ Database health check failed")
            return False

        # Test query
        version = await db.fetchval("SELECT version()")
        print(f"PostgreSQL Version: {version[:80]}...")

        # Disconnect
        await db.disconnect()
        print("✅ Database disconnected cleanly")

        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        print("Make sure DATABASE_URL is set correctly in .env")
        return False


async def test_telegram_bot():
    """Test that Telegram bot can be initialized."""
    print("\n" + "=" * 80)
    print("Testing Telegram Bot")
    print("=" * 80)

    try:
        from rivet_pro.adapters.telegram.bot import telegram_bot

        # Build the application
        app = telegram_bot.build()
        print("✅ Telegram bot application built successfully")

        # Check handlers are registered
        if len(app.handlers) > 0:
            print(f"✅ {len(app.handlers)} handler groups registered")
        else:
            print("⚠️  WARNING: No handlers registered")

        return True

    except Exception as e:
        print(f"❌ Telegram bot test failed: {e}")
        print("Make sure TELEGRAM_BOT_TOKEN is set correctly in .env")
        return False


async def main():
    """Run all tests."""
    print("\n")
    print("🔧 Rivet Pro - Phase 1 Walking Skeleton Test")
    print("\n")

    results = []

    # Run tests
    results.append(await test_imports())
    results.append(await test_settings())
    results.append(await test_database())
    results.append(await test_telegram_bot())

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    passed = sum(results)
    total = len(results)

    print(f"Tests Passed: {passed}/{total}")

    if passed == total:
        print("\n✅ All tests passed! Walking skeleton is ready.")
        print("\nNext steps:")
        print("1. Run: python -m rivet_pro.main")
        print("2. Open Telegram and message your bot")
        print("3. You should receive an 'I'm alive' response")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        print("\nCommon issues:")
        print("- Missing .env file (copy from .env.example)")
        print("- Invalid TELEGRAM_BOT_TOKEN")
        print("- Invalid DATABASE_URL")
        print("- Missing dependencies (run: pip install -r requirements.txt)")

    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
