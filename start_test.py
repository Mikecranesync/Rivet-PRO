"""Quick verification that bots can start"""
import subprocess
import time
import sys

def test_bot_startup(module_name, bot_name):
    """Test if a bot can start without errors"""
    print(f"\nTesting {bot_name}...")
    print(f"  Module: {module_name}")

    try:
        # Start the bot process
        proc = subprocess.Popen(
            [sys.executable, "-m", module_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait 3 seconds for initialization
        time.sleep(3)

        # Check if still running
        if proc.poll() is None:
            print(f"  [OK] {bot_name} started successfully (PID: {proc.pid})")
            proc.terminate()
            proc.wait(timeout=2)
            return True
        else:
            # Process crashed
            stdout, stderr = proc.communicate()
            print(f"  [FAIL] {bot_name} crashed on startup")
            if stderr:
                print(f"  Error: {stderr[:500]}")
            return False

    except Exception as e:
        print(f"  [FAIL] {bot_name} failed to start: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("BOT STARTUP VERIFICATION")
    print("=" * 60)

    results = {}

    # Test Rivet Main Bot
    results['rivet_main'] = test_bot_startup(
        "rivet.integrations.telegram_rivet_bot",
        "Rivet Main Bot (@RivetCeo_bot)"
    )

    # Test CMMS Bot
    results['cmms'] = test_bot_startup(
        "rivet.integrations.telegram_cmms_bot",
        "CMMS Bot (@RivetCMMS_bot)"
    )

    # Test Local Dev Bot
    results['local_dev'] = test_bot_startup(
        "rivet.integrations.telegram",
        "Local Dev Bot (@rivet_local_dev_bot)"
    )

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for bot, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {bot}")

    if all(results.values()):
        print("\n[SUCCESS] All bots can start! Ready to use.")
        print("\nTo start all bots:")
        print("  python run_bots.py")
        print("\nOr start individually:")
        print("  python -m rivet.integrations.telegram_rivet_bot")
        print("  python -m rivet.integrations.telegram_cmms_bot")
        print("  python -m rivet.integrations.telegram")
    else:
        print("\n[WARNING] Some bots failed to start. Check errors above.")

    sys.exit(0 if all(results.values()) else 1)
