"""
Launch All Rivet Telegram Bots

Starts all 3 Telegram bots in separate processes:
1. RIVET Local Dev (@rivet_local_dev_bot) - Full testing environment
2. Rivet (Main) (@RivetCeo_bot) - Production AI assistant
3. Rivet CMMS (@RivetCMMS_bot) - Equipment & work order management

Usage:
    python run_bots.py

To stop all bots, press Ctrl+C
"""

import subprocess
import sys
import time
import signal
from pathlib import Path

# Bot configurations
BOTS = [
    {
        "name": "RIVET Local Dev",
        "module": "rivet.integrations.telegram",
        "username": "@rivet_local_dev_bot",
        "description": "Full testing environment (all features)",
    },
    {
        "name": "Rivet (Main)",
        "module": "rivet.integrations.telegram_rivet_bot",
        "username": "@RivetCeo_bot",
        "description": "Production AI assistant (OCR, troubleshooting, queries)",
    },
    {
        "name": "Rivet CMMS",
        "module": "rivet.integrations.telegram_cmms_bot",
        "username": "@RivetCMMS_bot",
        "description": "Equipment & work order management",
    },
]

processes = []


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n⏹️  Stopping all bots...")
    for bot, proc in processes:
        print(f"  Stopping {bot['name']}...")
        proc.terminate()

    # Wait for processes to terminate
    time.sleep(1)

    # Force kill if still running
    for bot, proc in processes:
        if proc.poll() is None:
            proc.kill()

    print("✅ All bots stopped.\n")
    sys.exit(0)


def main():
    """Launch all Telegram bots."""
    print("=" * 60)
    print("🚀 RIVET Multi-Bot Launcher")
    print("=" * 60)
    print()

    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Check if we're in the right directory
    if not Path("rivet").exists():
        print("❌ Error: rivet/ directory not found!")
        print("Please run this script from the Rivet-PRO root directory.")
        sys.exit(1)

    print(f"Starting {len(BOTS)} bots...\n")

    for i, bot in enumerate(BOTS, 1):
        print(f"[{i}/{len(BOTS)}] Launching {bot['name']} ({bot['username']})...")
        print(f"     Module: {bot['module']}")
        print(f"     Features: {bot['description']}")

        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", bot["module"]],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            processes.append((bot, proc))
            print(f"     ✅ Started (PID: {proc.pid})")
        except Exception as e:
            print(f"     ❌ Failed to start: {e}")

        print()
        time.sleep(1)  # Stagger startup to avoid rate limits

    if not processes:
        print("❌ No bots started successfully!")
        return

    print("=" * 60)
    print(f"✅ All {len(processes)} bots running!")
    print("=" * 60)
    print()
    print("📊 Bot Status:")
    for bot, proc in processes:
        status = "Running" if proc.poll() is None else "Stopped"
        print(f"  • {bot['name']:20} {bot['username']:25} [{status}]")
    print()
    print("💡 Press Ctrl+C to stop all bots")
    print()

    # Monitor bots
    try:
        while True:
            time.sleep(1)

            # Check if any bot has crashed
            for bot, proc in processes:
                if proc.poll() is not None:
                    returncode = proc.returncode
                    print(f"\n⚠️  {bot['name']} exited unexpectedly (code: {returncode})")

                    # Get error output
                    stderr = proc.stderr.read() if proc.stderr else ""
                    if stderr:
                        print(f"Error output:\n{stderr[:500]}")

                    # Remove from process list
                    processes.remove((bot, proc))

                    if not processes:
                        print("\n❌ All bots have stopped!")
                        sys.exit(1)

    except KeyboardInterrupt:
        # Handled by signal_handler
        pass


if __name__ == "__main__":
    main()
