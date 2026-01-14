#!/usr/bin/env python3
"""
Manual Gap Filler - Background job to find manuals for equipment (MANUAL-004).

Run via cron: 0 2 * * * python scripts/run_manual_gap_filler.py

Identifies high-priority equipment without manuals and searches for them proactively.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rivet_pro.core.database import Database
from rivet_pro.workers.manual_gap_filler import ManualGapFiller
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


async def main():
    """Entry point for manual gap filler."""
    logger.info("=" * 80)
    logger.info("Manual Gap Filler - Starting")
    logger.info("=" * 80)

    db = Database()

    try:
        await db.connect()
        logger.info("Database connected")

        filler = ManualGapFiller(db)
        results = await filler.fill_gaps_daily(limit=10)

        logger.info("=" * 80)
        logger.info("Manual Gap Filler - Results")
        logger.info("=" * 80)
        logger.info(f"Total processed: {results['total_processed']}")
        logger.info(f"Manuals found: {results['manuals_found']}")
        logger.info(f"Manuals validated: {results['manuals_validated']}")
        logger.info(f"Gaps resolved: {results['gaps_resolved']}")
        logger.info(f"Errors: {results['errors']}")
        logger.info("=" * 80)

        print(f"✅ Processed {results['total_processed']} equipment")
        print(f"📘 Found {results['manuals_found']} manuals")
        print(f"✅ Validated {results['manuals_validated']} manuals")
        print(f"🔍 Resolved {results['gaps_resolved']} knowledge gaps")

        if results['errors'] > 0:
            print(f"❌ Errors: {results['errors']}")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Manual gap filler failed: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        return 1

    finally:
        await db.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
