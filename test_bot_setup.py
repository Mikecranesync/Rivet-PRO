"""Quick test to verify bot setup works"""
import sys

try:
    print("Testing Rivet Main Bot setup...")
    from rivet.integrations.telegram_rivet_bot import setup_bot
    app = setup_bot()
    print("[OK] Rivet Main Bot setup successful")
    print(f"   Token configured: {bool(app.bot.token)}")
except Exception as e:
    print(f"[FAIL] Rivet Main Bot failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\nTesting CMMS Bot setup...")
    from rivet.integrations.telegram_cmms_bot import setup_bot as setup_cmms
    app2 = setup_cmms()
    print("[OK] CMMS Bot setup successful")
    print(f"   Token configured: {bool(app2.bot.token)}")
except Exception as e:
    print(f"[FAIL] CMMS Bot failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[OK] All bots configured correctly!")
print("\nTo start all bots: python run_bots.py")
