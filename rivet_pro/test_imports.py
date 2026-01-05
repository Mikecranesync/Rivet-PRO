"""
Quick test to verify all imports and basic bot functionality.
Run this before deployment to catch issues early.
"""

import sys
from pathlib import Path

# Add rivet_pro to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    try:
        # Test core services
        from rivet_pro.core.services import analyze_image, route_to_sme
        print("✅ Core services imported successfully")

        # Test config
        from rivet_pro.config.settings import settings
        print(f"✅ Settings loaded (bot token: {'*' * 20}{settings.telegram_bot_token[-10:]})")

        # Test observability
        from rivet_pro.infra.observability import get_logger
        logger = get_logger(__name__)
        print("✅ Observability/logging working")

        # Test Telegram bot
        from rivet_pro.adapters.telegram.bot import telegram_bot
        print("✅ Telegram bot imported successfully")

        # Test database (if available)
        try:
            from rivet_pro.infra.database import get_db
            print("✅ Database module imported successfully")
        except ImportError as e:
            print(f"⚠️  Database module not found: {e}")

        print("\n✅ All critical imports successful!")
        print("\nReady to run:")
        print("  python start_bot.py")

        return True

    except ImportError as e:
        print(f"\n❌ Import failed: {e}")
        print("\nMake sure you've installed dependencies:")
        print("  pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_env_vars():
    """Test that required environment variables are set."""
    print("\nTesting environment variables...")

    from rivet_pro.config.settings import settings

    required = {
        "telegram_bot_token": settings.telegram_bot_token,
        "database_url": settings.database_url,
        "groq_api_key": settings.groq_api_key,
        "google_api_key": settings.google_api_key,
    }

    all_set = True
    for key, value in required.items():
        if value and str(value) != "None":
            print(f"  ✅ {key}: {'*' * 20}{str(value)[-10:]}")
        else:
            print(f"  ❌ {key}: NOT SET")
            all_set = False

    if all_set:
        print("\n✅ All required environment variables set!")
    else:
        print("\n⚠️  Some environment variables missing - check .env file")

    return all_set


if __name__ == "__main__":
    print("=" * 60)
    print("RIVET PRO - Import & Configuration Test")
    print("=" * 60)
    print()

    imports_ok = test_imports()
    env_ok = test_env_vars()

    if imports_ok and env_ok:
        print("\n🚀 Ready for deployment!")
        sys.exit(0)
    else:
        print("\n⚠️  Fix issues above before deploying")
        sys.exit(1)
