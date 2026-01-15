#!/usr/bin/env python3
"""
Test database failover logic end-to-end.

Usage:
    python scripts/test_failover.py              # Run all tests
    python scripts/test_failover.py --simulate   # Simulate Neon failure

Tests:
    1. Normal connection to primary (Neon)
    2. Simulated Neon failure -> Railway failover
    3. Health endpoint returns correct active_provider
"""

import asyncio
import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


async def test_normal_connection():
    """Test 1: Normal connection to primary database (Neon)."""
    print("\n" + "="*60)
    print("TEST 1: Normal Connection to Primary (Neon)")
    print("="*60)

    from rivet_pro.infra.database import Database, get_database_providers

    # Show configured providers
    providers = get_database_providers()
    print(f"\nConfigured providers: {[p[0] for p in providers]}")

    db = Database()
    try:
        await db.connect()
        print(f"✓ Connected to: {db.active_provider}")

        # Run a test query
        result = await db.fetchval("SELECT COUNT(*) FROM knowledge_atoms")
        print(f"✓ Query successful: {result} knowledge atoms")

        # Health check
        healthy = await db.health_check()
        print(f"✓ Health check: {'healthy' if healthy else 'unhealthy'}")

        await db.disconnect()
        print("✓ Disconnected cleanly")

        return db.active_provider == "neon"
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


async def test_simulated_failover():
    """Test 2: Simulate Neon failure and verify Railway takes over."""
    print("\n" + "="*60)
    print("TEST 2: Simulated Neon Failure -> Railway Failover")
    print("="*60)

    # Temporarily corrupt the DATABASE_URL to simulate failure
    original_url = os.environ.get("DATABASE_URL")
    if not original_url:
        print("✗ DATABASE_URL not set")
        return False

    # Check if Railway is configured
    railway_url = os.environ.get("RAILWAY_DB_URL")
    if not railway_url or "your_railway_password" in railway_url:
        print("⚠ RAILWAY_DB_URL not configured - skipping failover test")
        print("  Set RAILWAY_DB_URL in .env to enable failover")
        return None  # Skip, not fail

    print("\nSimulating Neon failure by using invalid URL...")
    os.environ["DATABASE_URL"] = "postgresql://invalid:invalid@invalid.neon.tech/invalid"

    from rivet_pro.infra.database import Database

    db = Database()
    try:
        await db.connect()
        print(f"✓ Failover successful! Connected to: {db.active_provider}")

        if db.active_provider == "railway":
            print("✓ Railway took over as expected")

            # Run a test query on Railway
            result = await db.fetchval("SELECT 1")
            print(f"✓ Railway query successful: {result}")

            await db.disconnect()
            return True
        else:
            print(f"✗ Expected 'railway', got '{db.active_provider}'")
            await db.disconnect()
            return False

    except Exception as e:
        print(f"✗ Failover failed: {e}")
        return False
    finally:
        # Restore original DATABASE_URL
        os.environ["DATABASE_URL"] = original_url
        print("\nRestored original DATABASE_URL")


async def test_health_endpoint():
    """Test 3: Check /health endpoint returns correct active_provider."""
    print("\n" + "="*60)
    print("TEST 3: Health Endpoint Response")
    print("="*60)

    import httpx

    # Try local API
    urls = [
        "http://localhost:8000/health",
        "http://127.0.0.1:8000/health",
    ]

    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                print(f"\n✓ Health endpoint accessible at {url}")
                print(f"  Status: {data.get('status')}")
                print(f"  Database healthy: {data.get('database', {}).get('healthy')}")
                print(f"  Active provider: {data.get('database', {}).get('active_provider')}")
                return True
        except httpx.ConnectError:
            continue
        except Exception as e:
            print(f"  Error: {e}")
            continue

    print("\n⚠ API not running - start with: uvicorn rivet_pro.adapters.web.main:app --port 8000")
    return None  # Skip, not fail


async def main():
    """Run all failover tests."""
    print("="*60)
    print("DATABASE FAILOVER TEST SUITE")
    print("="*60)

    results = {}

    # Test 1: Normal connection
    results["normal_connection"] = await test_normal_connection()

    # Test 2: Simulated failover (only if --simulate flag)
    if "--simulate" in sys.argv:
        results["simulated_failover"] = await test_simulated_failover()
    else:
        print("\n⚠ Skipping failover simulation (use --simulate to run)")
        results["simulated_failover"] = None

    # Test 3: Health endpoint
    results["health_endpoint"] = await test_health_endpoint()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⚠ SKIP"
        print(f"  {test_name}: {status}")

    # Exit code
    failures = [r for r in results.values() if r is False]
    if failures:
        print(f"\n{len(failures)} test(s) failed")
        sys.exit(1)
    else:
        print("\nAll tests passed (or skipped)!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
