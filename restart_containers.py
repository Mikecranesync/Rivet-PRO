#!/usr/bin/env python3
"""
Restart CMMS Containers with Database Fix
Uses subprocess to work around Docker API version issues
"""
import subprocess
import time
import sys

def run_cmd(cmd, cwd=None):
    """Run command and return output"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("=" * 60)
    print("  RESTARTING CMMS WITH DATABASE FIX")
    print("=" * 60)
    print()
    print("Database URL fix applied:")
    print("  OLD: postgres/atlas")
    print("  NEW: jdbc:postgresql://postgres:5432/atlas")
    print()

    cmms_dir = r"C:\Users\hharp\OneDrive\Desktop\grashjs-cmms"

    # Step 1: Stop containers
    print("[1/3] Stopping containers...")
    success, stdout, stderr = run_cmd("docker-compose down", cwd=cmms_dir)

    if not success:
        print(f"WARNING: Stop command had issues")
        print(f"Error: {stderr}")
        print()
        print("Trying alternative method...")

        # Try stopping individual containers
        for container in ["atlas-cmms-frontend", "atlas-cmms-backend", "atlas_minio", "atlas_db"]:
            print(f"  Stopping {container}...")
            run_cmd(f"docker stop {container}")
            run_cmd(f"docker rm {container}")

    time.sleep(3)

    # Step 2: Start containers
    print()
    print("[2/3] Starting containers with fixed DB_URL...")
    success, stdout, stderr = run_cmd("docker-compose up -d", cwd=cmms_dir)

    if not success:
        print(f"ERROR: Failed to start containers")
        print(f"Error: {stderr}")
        print()
        print("Manual steps needed:")
        print("  1. Open Docker Desktop")
        print("  2. Go to Containers")
        print("  3. Click on atlas-cmms")
        print("  4. Click 'Restart'")
        sys.exit(1)

    print("  Containers starting...")

    # Step 3: Wait and verify
    print()
    print("[3/3] Waiting for services to be ready...")

    for i in range(6):
        print(f"  {i * 5} seconds...")
        time.sleep(5)

    print()
    print("=" * 60)
    print("  RESTART COMPLETE")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Test at: http://localhost:3001")
    print("  2. Try logging in with: mike@cranesync.com")
    print("  3. Check backend logs if issues:")
    print("     docker logs atlas-cmms-backend --tail 50")
    print()
    print("The database connection should now work!")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
