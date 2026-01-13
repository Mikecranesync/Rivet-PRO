#!/usr/bin/env python3
"""Verify manual matching setup is complete."""

import asyncio
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rivet_pro.infra.database import Database
from rivet_pro.config.settings import settings


async def verify_setup():
    """Verify all manual matching components are ready."""
    print("=" * 60)
    print("MANUAL MATCHING SETUP VERIFICATION")
    print("=" * 60)
    
    errors = []
    
    # 1. Check environment variables
    print("\n1. Checking environment variables...")
    required_keys = [
        'ANTHROPIC_API_KEY',
        'GROQ_API_KEY', 
        'GOOGLE_API_KEY',
        'TELEGRAM_BOT_TOKEN',
        'DATABASE_URL'
    ]
    
    for key in required_keys:
        value = getattr(settings, key.lower().replace('_key', '_api_key').replace('telegram_bot_token', 'telegram_bot_token'), None)
        if not value:
            errors.append(f"Missing environment variable: {key}")
            print(f"   X {key}: NOT FOUND")
        else:
            print(f"   OK {key}: configured")
    
    # 2. Check Python dependencies
    print("\n2. Checking Python dependencies...")
    try:
        import PyPDF2
        print(f"   OK PyPDF2: version {PyPDF2.__version__}")
    except ImportError:
        errors.append("PyPDF2 not installed")
        print("   X PyPDF2: NOT INSTALLED")
    
    try:
        from rivet_pro.core.services.manual_matcher_service import ManualMatcherService
        print("   OK ManualMatcherService: imported")
    except ImportError as e:
        errors.append(f"ManualMatcherService import failed: {e}")
        print(f"   X ManualMatcherService: {e}")
    
    try:
        from rivet_pro.workers.manual_gap_filler import ManualGapFiller
        print("   OK ManualGapFiller: imported")
    except ImportError as e:
        errors.append(f"ManualGapFiller import failed: {e}")
        print(f"   X ManualGapFiller: {e}")
    
    # 3. Check database tables
    print("\n3. Checking database tables...")
    db = Database()
    
    try:
        await db.connect()
        
        # Check equipment_manual_searches
        result = await db.fetchrow("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'equipment_manual_searches'
            )
        """)
        
        if result['exists']:
            print("   OK equipment_manual_searches: table exists")
        else:
            errors.append("equipment_manual_searches table missing")
            print("   X equipment_manual_searches: TABLE MISSING")
        
        # Check manual_cache columns
        columns = await db.fetch("""
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_name = 'manual_cache'
                AND column_name IN ('llm_validated', 'llm_confidence', 'manual_type', 'atom_id')
        """)
        
        found_columns = [c['column_name'] for c in columns]
        expected_columns = ['llm_validated', 'llm_confidence', 'manual_type', 'atom_id']
        
        for col in expected_columns:
            if col in found_columns:
                print(f"   OK manual_cache.{col}: column exists")
            else:
                errors.append(f"manual_cache.{col} column missing")
                print(f"   X manual_cache.{col}: COLUMN MISSING")
        
    except Exception as e:
        errors.append(f"Database check failed: {e}")
        print(f"   X Database: {e}")
    finally:
        await db.disconnect()
    
    # 4. Check bot integration
    print("\n4. Checking bot integration...")
    try:
        from rivet_pro.adapters.telegram.bot import telegram_bot
        
        # Check if manual command is registered
        handlers = telegram_bot.application.handlers
        manual_cmd_found = any(
            h.__class__.__name__ == 'CommandHandler' and 'manual' in str(h)
            for handler_group in handlers.values()
            for h in handler_group
        )
        
        if manual_cmd_found:
            print("   OK /manual command: registered")
        else:
            print("   ? /manual command: may not be registered (check manually)")
        
    except Exception as e:
        errors.append(f"Bot integration check failed: {e}")
        print(f"   X Bot: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"VERIFICATION FAILED: {len(errors)} error(s)")
        print("=" * 60)
        for error in errors:
            print(f"  - {error}")
        return 1
    else:
        print("VERIFICATION PASSED: All checks successful!")
        print("=" * 60)
        print("\nManual matching system is ready to deploy.")
        print("\nNext steps:")
        print("  1. Restart the bot: python -m rivet_pro.adapters.telegram")
        print("  2. Test with equipment photo")
        print("  3. Verify manual notification received")
        print("  4. Test /manual command")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(verify_setup())
    sys.exit(exit_code)
