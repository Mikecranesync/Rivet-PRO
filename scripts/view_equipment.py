"""
Quick script to view CMMS equipment records.

Usage:
    python scripts/view_equipment.py
"""

import asyncio
import sys
from pathlib import Path

# Add rivet_pro to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rivet_pro.infra.database import Database
from rivet_pro.config.settings import settings


async def view_equipment():
    """View all equipment in CMMS."""
    db = Database()

    try:
        print("Connecting to database...")
        await db.connect()
        print("✅ Connected\n")

        # Get all equipment
        equipment = await db.execute_query_async("""
            SELECT
                equipment_number,
                manufacturer,
                model_number,
                serial_number,
                equipment_type,
                location,
                work_order_count,
                last_reported_fault,
                owned_by_user_id,
                created_at,
                updated_at
            FROM cmms_equipment
            ORDER BY created_at DESC
        """)

        if not equipment:
            print("No equipment found in CMMS.")
            return

        print(f"Found {len(equipment)} equipment record(s):\n")
        print("=" * 100)

        for idx, eq in enumerate(equipment, 1):
            print(f"\n#{idx} | {eq['equipment_number']}")
            print("-" * 100)
            print(f"  Manufacturer:  {eq['manufacturer']}")
            print(f"  Model:         {eq['model_number'] or 'N/A'}")
            print(f"  Serial:        {eq['serial_number'] or 'N/A'}")
            print(f"  Type:          {eq['equipment_type'] or 'N/A'}")
            print(f"  Location:      {eq['location'] or 'Not specified'}")
            print(f"  Work Orders:   {eq['work_order_count']}")
            print(f"  Last Fault:    {eq['last_reported_fault'] or 'None'}")
            print(f"  Owner:         {eq['owned_by_user_id']}")
            print(f"  Created:       {eq['created_at']}")
            print(f"  Updated:       {eq['updated_at']}")

        print("\n" + "=" * 100)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()
        print("\n✅ Database connection closed")


if __name__ == "__main__":
    asyncio.run(view_equipment())
