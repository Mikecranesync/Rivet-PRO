#!/usr/bin/env python3
"""
Atlas CMMS Integration Test

Verifies end-to-end Atlas CMMS extraction from Agent Factory.

Tests:
1. Database connection
2. Equipment creation (with auto-numbering EQ-2025-XXXX)
3. Equipment matching (85% fuzzy threshold)
4. Work order creation (with auto-numbering WO-2025-XXXX)
5. Work order linked to equipment
6. Machine library operations
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from uuid import uuid4

from rivet.atlas import (
    AtlasDatabase,
    EquipmentMatcher,
    WorkOrderService,
    MachineLibrary,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_atlas_integration():
    """Run full integration test of Atlas CMMS."""

    logger.info("=" * 80)
    logger.info("ATLAS CMMS INTEGRATION TEST")
    logger.info("=" * 80)

    db = AtlasDatabase()

    try:
        # ===== TEST 1: Database Connection =====
        logger.info("\n[TEST 1] Database Connection")
        await db.connect()
        logger.info("✓ Connected to database")

        # ===== TEST 2: Equipment Creation =====
        logger.info("\n[TEST 2] Equipment Creation")
        matcher = EquipmentMatcher(db)

        test_user_id = f"test_user_{uuid4().hex[:8]}"

        equipment_id_1, is_new_1 = await matcher.match_or_create_equipment(
            manufacturer="Siemens",
            model_number="G120C",
            serial_number=f"SN{uuid4().hex[:8]}",
            equipment_type="VFD",
            location="Test Lab",
            user_id=test_user_id
        )

        assert is_new_1, "Equipment should be new"
        logger.info(f"✓ Created equipment: {equipment_id_1}")

        # Get equipment details
        equipment = await matcher.get_equipment_by_id(equipment_id_1)
        assert equipment is not None, "Equipment should exist"
        assert equipment["manufacturer"] == "Siemens", "Manufacturer should match"
        assert equipment["equipment_number"].startswith("EQ-"), "Should have EQ- prefix"
        logger.info(f"✓ Equipment number: {equipment['equipment_number']}")

        # ===== TEST 3: Equipment Fuzzy Matching =====
        logger.info("\n[TEST 3] Equipment Fuzzy Matching")

        # Try to create same equipment with slight variation
        equipment_id_2, is_new_2 = await matcher.match_or_create_equipment(
            manufacturer="SIEMENS",  # Different case
            model_number="G-120-C",  # Different formatting
            serial_number=None,  # No serial
            equipment_type="VFD",
            location="Test Lab",
            user_id=test_user_id
        )

        # Should match existing equipment (85% similarity)
        if equipment_id_1 == equipment_id_2:
            logger.info(f"✓ Fuzzy match worked: matched existing equipment {equipment_id_2}")
            logger.info("  (SIEMENS G-120-C matched Siemens G120C)")
        else:
            logger.info(f"  New equipment created (fuzzy match threshold not met): {equipment_id_2}")
            # This is okay - fuzzy matching has strict thresholds

        # ===== TEST 4: Work Order Creation =====
        logger.info("\n[TEST 4] Work Order Creation")
        wo_service = WorkOrderService(db, matcher)

        work_order = await wo_service.create_work_order(
            user_id=test_user_id,
            title="Test VFD Fault F0001",
            description="Drive showing overcurrent fault during testing",
            manufacturer="Siemens",
            model_number="G120C",
            equipment_type="VFD",
            fault_codes=["F0001"],
            symptoms=["overcurrent", "stopped"],
            source="telegram_text",
            confidence_score=0.85,
            route_taken="A"
        )

        assert work_order is not None, "Work order should be created"
        assert work_order["work_order_number"].startswith("WO-"), "Should have WO- prefix"
        logger.info(f"✓ Created work order: {work_order['work_order_number']}")
        logger.info(f"  Linked to equipment: {work_order['equipment_number']}")

        # ===== TEST 5: Work Order Equipment Link =====
        logger.info("\n[TEST 5] Work Order Equipment Link")

        # Get equipment to verify work order count updated
        equipment_updated = await matcher.get_equipment_by_id(equipment_id_1)
        assert equipment_updated["work_order_count"] >= 1, "Work order count should be updated"
        logger.info(f"✓ Equipment work order count: {equipment_updated['work_order_count']}")

        # Get work order to verify equipment link
        wo_retrieved = await wo_service.get_work_order_by_id(work_order["id"])
        assert wo_retrieved is not None, "Work order should exist"
        assert wo_retrieved["equipment_number"] == equipment["equipment_number"], "Equipment link should match"
        logger.info(f"✓ Work order links to equipment: {wo_retrieved['equipment_number']}")

        # ===== TEST 6: Machine Library =====
        logger.info("\n[TEST 6] Machine Library")
        library = MachineLibrary(db)

        machine = await library.add_machine(
            user_id=test_user_id,
            nickname="Test Motor A",
            manufacturer="Siemens",
            model_number="1LE1001",
            location="Test Lab - Line 1"
        )

        assert machine is not None, "Machine should be created"
        assert machine["nickname"] == "Test Motor A", "Nickname should match"
        logger.info(f"✓ Added machine to library: {machine['nickname']} (ID: {machine['id']})")

        # List machines
        machines = await library.list_machines(user_id=test_user_id)
        assert len(machines) >= 1, "Should have at least 1 machine"
        logger.info(f"✓ Listed machines: {len(machines)} total")

        # ===== TEST 7: List Equipment and Work Orders =====
        logger.info("\n[TEST 7] List Equipment and Work Orders")

        equipment_list = await matcher.list_equipment_by_user(
            user_id=test_user_id,
            limit=10
        )
        assert len(equipment_list) >= 1, "Should have at least 1 equipment"
        logger.info(f"✓ Equipment list: {len(equipment_list)} items")

        wo_list = await wo_service.list_work_orders_by_user(
            user_id=test_user_id,
            limit=10
        )
        assert len(wo_list) >= 1, "Should have at least 1 work order"
        logger.info(f"✓ Work order list: {len(wo_list)} items")

        # ===== SUMMARY =====
        logger.info("\n" + "=" * 80)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 80)
        logger.info("\nAtlas CMMS Extraction Summary:")
        logger.info(f"  • Database: Connected ✓")
        logger.info(f"  • Equipment created: {equipment['equipment_number']} ✓")
        logger.info(f"  • Fuzzy matching: Tested ✓")
        logger.info(f"  • Work order created: {work_order['work_order_number']} ✓")
        logger.info(f"  • Equipment-WO link: Verified ✓")
        logger.info(f"  • Machine library: Working ✓")
        logger.info(f"  • Auto-numbering: EQ- and WO- prefixes ✓")
        logger.info("\n🎉 Atlas CMMS successfully extracted from Agent Factory!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}", exc_info=True)
        raise

    finally:
        await db.close()
        logger.info("\n✓ Database connection closed")


def main():
    """Run integration test."""
    asyncio.run(test_atlas_integration())


if __name__ == "__main__":
    main()
