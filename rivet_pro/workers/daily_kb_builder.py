#!/usr/bin/env python3
"""
Daily KB Builder - RIVET Pro

Runs daily at 2:00 AM UTC to build and maintain knowledge base:
1. Scrape new PDFs from OEM sources
2. Build knowledge atoms from PDFs
3. Upload atoms to Neon PostgreSQL
4. Validate embeddings and quality
5. Generate daily stats report
6. Run quality checker

Based on Agent Factory's scheduler_kb_daily.py, adapted for:
- Neon PostgreSQL (replacing Supabase)
- Slack notifications (replacing Telegram)
- RIVET Pro project structure

Usage:
    # Run once (manual or via GitHub Actions)
    python -m rivet_pro.workers.daily_kb_builder

    # Schedule via GitHub Actions at 2:00 AM UTC

Environment Variables:
    DATABASE_URL - Neon PostgreSQL connection string
    SLACK_WEBHOOK_URL - Slack webhook for notifications
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Try imports
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg not installed")


# =============================================================================
# OEM PDF Sources - Maintenance Equipment Manuals
# =============================================================================

PDF_SOURCES: Dict[str, List[str]] = {
    "rockwell_automation": [
        # PowerFlex Drives
        "https://literature.rockwellautomation.com/idc/groups/literature/documents/um/520-um001_-en-e.pdf",
        "https://literature.rockwellautomation.com/idc/groups/literature/documents/um/750-um001_-en-p.pdf",
        # ControlLogix PLCs
        "https://literature.rockwellautomation.com/idc/groups/literature/documents/um/1756-um001_-en-p.pdf",
    ],
    "siemens": [
        # SINAMICS Drives
        "https://support.industry.siemens.com/cs/document/109761276/sinamics-g120c-operating-instructions",
        # S7-1200 PLCs
        "https://support.industry.siemens.com/cs/document/109759862/s7-1200-system-manual",
    ],
    "abb": [
        # ACS580 Drives
        "https://search.abb.com/library/Download.aspx?DocumentID=3AUA0000081917&LanguageCode=en",
    ],
}


class DailyKBBuilder:
    """
    Daily knowledge base building and maintenance.

    Orchestrates 6 phases:
    1. PDF scraping from OEM sources
    2. Knowledge atom generation
    3. Upload to Neon PostgreSQL
    4. Embedding validation
    5. Daily report generation
    6. Quality check
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        slack_webhook_url: Optional[str] = None,
    ):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")

        self.db_pool = None
        self.started_at = datetime.utcnow()

        # Stats tracking
        self.stats = {
            "scrape": {},
            "build": {},
            "upload": {},
            "validate": {},
            "quality": {},
        }

    async def run(self) -> int:
        """Run the complete daily KB building pipeline."""
        logger.info("=" * 70)
        logger.info("RIVET PRO DAILY KB BUILDER")
        logger.info(f"Started: {self.started_at.strftime('%Y-%m-%d %H:%M UTC')}")
        logger.info("=" * 70)

        if not ASYNCPG_AVAILABLE:
            logger.error("asyncpg not installed")
            return 1

        if not self.database_url:
            logger.error("DATABASE_URL not configured")
            return 1

        try:
            # Connect to database
            self.db_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5
            )
            logger.info("Connected to Neon PostgreSQL")

            # Phase 1: Scrape PDFs
            self.stats["scrape"] = await self._phase_1_scrape_pdfs()

            # Phase 2: Build atoms
            self.stats["build"], atoms = await self._phase_2_build_atoms()

            # Phase 3: Upload to database
            self.stats["upload"] = await self._phase_3_upload_atoms(atoms)

            # Phase 4: Validate
            self.stats["validate"] = await self._phase_4_validate()

            # Phase 6: Quality check (runs before report)
            self.stats["quality"] = await self._phase_6_quality_check(
                self.stats["upload"].get("uploaded", 0)
            )

            # Phase 5: Generate report
            report = self._phase_5_generate_report()

            # Send success notification
            await self._send_slack(f"Daily KB Builder Complete\n\n{report}")

            # Log completion
            duration = (datetime.utcnow() - self.started_at).total_seconds()
            logger.info("=" * 70)
            logger.info("DAILY KB BUILDER - COMPLETE")
            logger.info(f"Duration: {duration:.1f} seconds")
            logger.info("=" * 70)

            return 0

        except Exception as e:
            logger.error(f"CRITICAL ERROR: {e}", exc_info=True)
            await self._send_slack(f"Daily KB Builder FAILED\n\nError: {str(e)}")
            return 1

        finally:
            if self.db_pool:
                await self.db_pool.close()

    async def _phase_1_scrape_pdfs(self) -> Dict[str, Any]:
        """
        Phase 1: Scrape PDFs from OEM sources.

        For RIVET Pro, this queues URLs to the Redis job queue
        rather than downloading PDFs directly.
        """
        logger.info("=" * 60)
        logger.info("PHASE 1: QUEUEING PDF SOURCES")
        logger.info("=" * 60)

        total_urls = 0
        queued = 0

        for manufacturer, urls in PDF_SOURCES.items():
            logger.info(f"\n[{manufacturer.upper()}] {len(urls)} URLs")

            for url in urls:
                total_urls += 1

                # Check if already processed
                async with self.db_pool.acquire() as conn:
                    import hashlib
                    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]

                    existing = await conn.fetchval(
                        "SELECT id FROM source_fingerprints WHERE fingerprint = $1",
                        url_hash
                    )

                    if existing:
                        logger.info(f"  Skipping (already processed): {url[:60]}...")
                        continue

                    # Queue for processing
                    await conn.execute(
                        """
                        INSERT INTO kb_ingest_jobs (url, source_type, priority)
                        VALUES ($1, 'pdf', 70)
                        ON CONFLICT (url_hash) DO NOTHING
                        """,
                        url
                    )
                    queued += 1
                    logger.info(f"  Queued: {url[:60]}...")

        stats = {
            "total_urls": total_urls,
            "queued": queued,
            "skipped": total_urls - queued,
        }

        logger.info(f"\nPHASE 1 COMPLETE: {stats}")
        return stats

    async def _phase_2_build_atoms(self) -> Tuple[Dict[str, Any], List[Dict]]:
        """
        Phase 2: Build knowledge atoms from queued sources.

        Note: In the full implementation, this would use the IngestionChain
        to process PDFs into knowledge atoms. For now, this is a placeholder
        that returns empty atoms (the 24/7 worker handles actual ingestion).
        """
        logger.info("=" * 60)
        logger.info("PHASE 2: BUILDING KNOWLEDGE ATOMS")
        logger.info("=" * 60)

        # In full implementation:
        # 1. Fetch pending jobs from kb_ingest_jobs
        # 2. Run IngestionChain on each
        # 3. Generate atoms with embeddings

        # For now, report on what's pending
        async with self.db_pool.acquire() as conn:
            pending = await conn.fetchval(
                "SELECT COUNT(*) FROM kb_ingest_jobs WHERE status = 'pending'"
            )
            processing = await conn.fetchval(
                "SELECT COUNT(*) FROM kb_ingest_jobs WHERE status = 'processing'"
            )
            completed = await conn.fetchval(
                "SELECT COUNT(*) FROM kb_ingest_jobs WHERE status = 'completed'"
            )

        stats = {
            "pending_jobs": pending,
            "processing_jobs": processing,
            "completed_jobs": completed,
            "total_atoms": 0,  # Placeholder
        }

        logger.info(f"Job queue status: {pending} pending, {processing} processing, {completed} completed")
        logger.info(f"\nPHASE 2 COMPLETE: {stats}")

        return stats, []  # Return empty atoms list for now

    async def _phase_3_upload_atoms(self, atoms: List[Dict]) -> Dict[str, Any]:
        """
        Phase 3: Upload atoms to Neon PostgreSQL.

        Note: The 24/7 worker handles actual uploads. This phase
        reports on recent upload activity.
        """
        logger.info("=" * 60)
        logger.info("PHASE 3: UPLOAD STATUS")
        logger.info("=" * 60)

        async with self.db_pool.acquire() as conn:
            # Count atoms added in last 24 hours
            recent_atoms = await conn.fetchval(
                """
                SELECT COUNT(*) FROM knowledge_atoms
                WHERE created_at > NOW() - INTERVAL '24 hours'
                """
            )

            # Count total atoms
            total_atoms = await conn.fetchval(
                "SELECT COUNT(*) FROM knowledge_atoms"
            )

        stats = {
            "uploaded": len(atoms),  # From this run (0 for now)
            "recent_24h": recent_atoms,
            "total": total_atoms,
            "failed": 0,
            "skipped": 0,
        }

        logger.info(f"Atoms added last 24h: {recent_atoms}")
        logger.info(f"Total atoms in KB: {total_atoms}")
        logger.info(f"\nPHASE 3 COMPLETE: {stats}")

        return stats

    async def _phase_4_validate(self) -> Dict[str, Any]:
        """
        Phase 4: Validate embeddings and quality.
        """
        logger.info("=" * 60)
        logger.info("PHASE 4: VALIDATION")
        logger.info("=" * 60)

        async with self.db_pool.acquire() as conn:
            # Count atoms with embeddings
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM knowledge_atoms"
            )

            with_embeddings = await conn.fetchval(
                "SELECT COUNT(*) FROM knowledge_atoms WHERE embedding IS NOT NULL"
            )

            # Count low quality atoms
            low_quality = await conn.fetchval(
                """
                SELECT COUNT(*) FROM knowledge_atoms
                WHERE quality_score IS NOT NULL AND quality_score < 0.5
                """
            )

        embedding_rate = (with_embeddings / total * 100) if total > 0 else 0

        stats = {
            "total_atoms": total,
            "with_embeddings": with_embeddings,
            "embedding_rate": f"{embedding_rate:.1f}%",
            "low_quality": low_quality or 0,
        }

        logger.info(f"Total atoms: {total}")
        logger.info(f"With embeddings: {with_embeddings} ({embedding_rate:.1f}%)")
        logger.info(f"Low quality: {low_quality or 0}")
        logger.info(f"\nPHASE 4 COMPLETE: {stats}")

        return stats

    async def _phase_6_quality_check(self, uploaded_count: int) -> Dict[str, Any]:
        """
        Phase 6: Run quality checks on recently uploaded atoms.
        """
        logger.info("=" * 60)
        logger.info("PHASE 6: QUALITY CHECK")
        logger.info("=" * 60)

        # Query recent atoms for quality metrics
        async with self.db_pool.acquire() as conn:
            # Check atoms from last 24 hours
            recent_stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN quality_score >= 0.7 THEN 1 END) as passed,
                    COUNT(CASE WHEN quality_score >= 0.5 AND quality_score < 0.7 THEN 1 END) as warnings,
                    COUNT(CASE WHEN quality_score < 0.5 THEN 1 END) as failed,
                    AVG(quality_score) as avg_score
                FROM knowledge_atoms
                WHERE created_at > NOW() - INTERVAL '24 hours'
                """
            )

        stats = {
            "quality_checked": recent_stats["total"] or 0,
            "quality_passed": recent_stats["passed"] or 0,
            "quality_warnings": recent_stats["warnings"] or 0,
            "quality_failed": recent_stats["failed"] or 0,
            "avg_confidence": round(recent_stats["avg_score"] or 0, 3),
            "citations_checked": 0,  # Placeholder
            "citations_valid": 0,
            "citations_broken": 0,
        }

        logger.info(f"Quality check: {stats['quality_passed']}/{stats['quality_checked']} passed")
        logger.info(f"Warnings: {stats['quality_warnings']}, Failed: {stats['quality_failed']}")
        logger.info(f"\nPHASE 6 COMPLETE: {stats}")

        return stats

    def _phase_5_generate_report(self) -> str:
        """
        Phase 5: Generate daily report.
        """
        logger.info("=" * 60)
        logger.info("PHASE 5: GENERATING REPORT")
        logger.info("=" * 60)

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        report = f"""Daily KB Building Report
{timestamp}

PHASE 1: PDF Sources
- URLs Queued: {self.stats['scrape'].get('queued', 0)}
- Skipped (already processed): {self.stats['scrape'].get('skipped', 0)}

PHASE 2: Job Queue Status
- Pending: {self.stats['build'].get('pending_jobs', 0)}
- Processing: {self.stats['build'].get('processing_jobs', 0)}
- Completed: {self.stats['build'].get('completed_jobs', 0)}

PHASE 3: Upload Status
- Atoms added (24h): {self.stats['upload'].get('recent_24h', 0)}
- Total atoms in KB: {self.stats['upload'].get('total', 0)}

PHASE 4: Validation
- With embeddings: {self.stats['validate'].get('with_embeddings', 0)} ({self.stats['validate'].get('embedding_rate', '0%')})
- Low quality: {self.stats['validate'].get('low_quality', 0)}

PHASE 6: Quality Check
- Passed: {self.stats['quality'].get('quality_passed', 0)}/{self.stats['quality'].get('quality_checked', 0)}
- Warnings: {self.stats['quality'].get('quality_warnings', 0)}
- Failed: {self.stats['quality'].get('quality_failed', 0)}

Daily KB building complete!"""

        logger.info(f"\nPHASE 5 COMPLETE")
        return report

    async def _send_slack(self, message: str):
        """Send message to Slack."""
        if not self.slack_webhook_url:
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    self.slack_webhook_url,
                    json={"text": f"*RIVET Pro KB Builder*\n{message}"}
                )
        except Exception as e:
            logger.warning(f"Failed to send Slack message: {e}")


async def main():
    """Main entry point."""
    builder = DailyKBBuilder()
    return await builder.run()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
