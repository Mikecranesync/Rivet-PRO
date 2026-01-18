#!/usr/bin/env python3
"""
Weekly KB Maintenance - RIVET Pro

Runs weekly (Sundays at 12:00 AM UTC) for maintenance tasks:
1. Full KB reindexing
2. Deduplicate similar atoms (cosine similarity > 0.95)
3. Quality audit (flag low-quality atoms)
4. Generate weekly growth report

Based on Agent Factory's scheduler_kb_weekly.py, adapted for:
- Neon PostgreSQL (replacing Supabase)
- Slack notifications (replacing Telegram)
- RIVET Pro project structure

Usage:
    # Run once (manual or via GitHub Actions)
    python -m rivet_pro.workers.weekly_kb_maintenance

    # Schedule via GitHub Actions on Sundays at 00:00 UTC

Environment Variables:
    DATABASE_URL - Neon PostgreSQL connection string
    SLACK_WEBHOOK_URL - Slack webhook for notifications
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

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

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("numpy not installed - deduplication limited")


# Thresholds
DUPLICATE_THRESHOLD = 0.95  # Cosine similarity
LOW_QUALITY_THRESHOLD = 0.5


class WeeklyKBMaintenance:
    """
    Weekly knowledge base maintenance.

    Orchestrates 4 phases:
    1. Reindex knowledge base
    2. Deduplicate similar atoms
    3. Quality audit
    4. Growth report
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
        self.week_number = datetime.utcnow().isocalendar()[1]

        # Stats tracking
        self.stats = {
            "reindex": {},
            "deduplicate": {},
            "quality": {},
            "growth": {},
        }

    async def run(self) -> int:
        """Run the complete weekly maintenance pipeline."""
        logger.info("=" * 70)
        logger.info(f"RIVET PRO WEEKLY KB MAINTENANCE - Week {self.week_number}")
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

            # Phase 1: Reindex
            self.stats["reindex"] = await self._phase_1_reindex()

            # Phase 2: Deduplicate
            self.stats["deduplicate"] = await self._phase_2_deduplicate()

            # Phase 3: Quality audit
            self.stats["quality"] = await self._phase_3_quality_audit()

            # Phase 4: Growth report
            self.stats["growth"] = await self._phase_4_growth_report()

            # Generate report
            report = self._generate_report()

            # Send success notification
            await self._send_slack(f"Weekly KB Maintenance Complete\n\n{report}")

            # Log completion
            duration = (datetime.utcnow() - self.started_at).total_seconds()
            logger.info("=" * 70)
            logger.info("WEEKLY KB MAINTENANCE - COMPLETE")
            logger.info(f"Duration: {duration:.1f} seconds")
            logger.info("=" * 70)

            return 0

        except Exception as e:
            logger.error(f"CRITICAL ERROR: {e}", exc_info=True)
            await self._send_slack(f"Weekly KB Maintenance FAILED\n\nError: {str(e)}")
            return 1

        finally:
            if self.db_pool:
                await self.db_pool.close()

    async def _phase_1_reindex(self) -> Dict[str, Any]:
        """
        Phase 1: Verify indexes and gather statistics.

        Note: PostgreSQL automatically maintains indexes on INSERT/UPDATE.
        This phase gathers index health statistics.
        """
        logger.info("=" * 60)
        logger.info("PHASE 1: REINDEXING KNOWLEDGE BASE")
        logger.info("=" * 60)

        async with self.db_pool.acquire() as conn:
            # Count total atoms
            total_atoms = await conn.fetchval(
                "SELECT COUNT(*) FROM knowledge_atoms"
            )

            # Count atoms with embeddings
            with_embeddings = await conn.fetchval(
                "SELECT COUNT(*) FROM knowledge_atoms WHERE embedding IS NOT NULL"
            )

            # Check for orphaned records
            orphaned = await conn.fetchval(
                """
                SELECT COUNT(*) FROM kb_ingest_jobs
                WHERE status = 'processing'
                AND started_at < NOW() - INTERVAL '24 hours'
                """
            )

            # Reset stuck jobs
            if orphaned and orphaned > 0:
                await conn.execute(
                    """
                    UPDATE kb_ingest_jobs
                    SET status = 'pending', worker_id = NULL, started_at = NULL
                    WHERE status = 'processing'
                    AND started_at < NOW() - INTERVAL '24 hours'
                    """
                )
                logger.info(f"Reset {orphaned} stuck jobs to pending")

        coverage = (with_embeddings / total_atoms * 100) if total_atoms > 0 else 0

        stats = {
            "status": "complete",
            "total_atoms": total_atoms,
            "with_embeddings": with_embeddings,
            "index_coverage": f"{coverage:.1f}%",
            "stuck_jobs_reset": orphaned or 0,
        }

        logger.info(f"Total atoms: {total_atoms}")
        logger.info(f"With embeddings: {with_embeddings} ({coverage:.1f}%)")
        logger.info(f"\nPHASE 1 COMPLETE: {stats}")

        return stats

    async def _phase_2_deduplicate(self) -> Dict[str, Any]:
        """
        Phase 2: Find and flag duplicate atoms.

        Uses PostgreSQL's pgvector for efficient similarity search
        when available, otherwise falls back to sampling.
        """
        logger.info("=" * 60)
        logger.info("PHASE 2: DEDUPLICATING ATOMS")
        logger.info("=" * 60)

        duplicates_found = []

        async with self.db_pool.acquire() as conn:
            # Check if pgvector is available
            has_pgvector = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )

            if has_pgvector:
                # Use pgvector for efficient similarity search
                logger.info("Using pgvector for similarity search...")

                # Find potential duplicates using cosine distance
                duplicates = await conn.fetch(
                    """
                    WITH atom_pairs AS (
                        SELECT
                            a1.id as atom_a_id,
                            a1.atom_id as atom_a_atom_id,
                            a2.id as atom_b_id,
                            a2.atom_id as atom_b_atom_id,
                            1 - (a1.embedding <=> a2.embedding) as similarity
                        FROM knowledge_atoms a1
                        JOIN knowledge_atoms a2 ON a1.id < a2.id
                        WHERE a1.embedding IS NOT NULL
                        AND a2.embedding IS NOT NULL
                        AND 1 - (a1.embedding <=> a2.embedding) > $1
                        LIMIT 100
                    )
                    SELECT * FROM atom_pairs
                    ORDER BY similarity DESC
                    """,
                    DUPLICATE_THRESHOLD
                )

                for row in duplicates:
                    duplicates_found.append({
                        "atom_a_id": row["atom_a_id"],
                        "atom_b_id": row["atom_b_id"],
                        "atom_a_atom_id": row["atom_a_atom_id"],
                        "atom_b_atom_id": row["atom_b_atom_id"],
                        "similarity": float(row["similarity"]),
                    })

                logger.info(f"Found {len(duplicates_found)} duplicate pairs via pgvector")

            else:
                # Fallback: Sample-based comparison (limited)
                logger.info("pgvector not available, using sample-based deduplication...")

                # Get sample of atoms with embeddings
                atoms = await conn.fetch(
                    """
                    SELECT id, atom_id, embedding
                    FROM knowledge_atoms
                    WHERE embedding IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT 500
                    """
                )

                if NUMPY_AVAILABLE and len(atoms) > 1:
                    # Compare pairs
                    for i in range(len(atoms)):
                        for j in range(i + 1, min(i + 50, len(atoms))):
                            emb_a = atoms[i]["embedding"]
                            emb_b = atoms[j]["embedding"]

                            if emb_a and emb_b:
                                similarity = self._cosine_similarity(emb_a, emb_b)

                                if similarity > DUPLICATE_THRESHOLD:
                                    duplicates_found.append({
                                        "atom_a_id": atoms[i]["id"],
                                        "atom_b_id": atoms[j]["id"],
                                        "atom_a_atom_id": atoms[i]["atom_id"],
                                        "atom_b_atom_id": atoms[j]["atom_id"],
                                        "similarity": similarity,
                                    })

                logger.info(f"Found {len(duplicates_found)} duplicate pairs via sampling")

        # Log duplicates for review
        for dup in duplicates_found[:5]:
            logger.info(
                f"  Duplicate: {dup['atom_a_atom_id']} <-> {dup['atom_b_atom_id']} "
                f"(similarity: {dup['similarity']:.3f})"
            )

        stats = {
            "status": "complete",
            "atoms_checked": "pgvector" if has_pgvector else "sample",
            "duplicates_found": len(duplicates_found),
            "top_duplicates": duplicates_found[:10],
        }

        logger.info(f"\nPHASE 2 COMPLETE: {len(duplicates_found)} duplicates found")

        return stats

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not NUMPY_AVAILABLE:
            return 0.0

        a_np = np.array(a)
        b_np = np.array(b)
        norm_a = np.linalg.norm(a_np)
        norm_b = np.linalg.norm(b_np)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a_np, b_np) / (norm_a * norm_b))

    async def _phase_3_quality_audit(self) -> Dict[str, Any]:
        """
        Phase 3: Audit knowledge base quality.
        """
        logger.info("=" * 60)
        logger.info("PHASE 3: QUALITY AUDIT")
        logger.info("=" * 60)

        async with self.db_pool.acquire() as conn:
            # Count low quality atoms
            low_quality = await conn.fetchval(
                """
                SELECT COUNT(*) FROM knowledge_atoms
                WHERE quality_score IS NOT NULL AND quality_score < $1
                """,
                LOW_QUALITY_THRESHOLD
            )

            # Count by atom type
            type_counts = await conn.fetch(
                """
                SELECT atom_type, COUNT(*) as count
                FROM knowledge_atoms
                WHERE atom_type IS NOT NULL
                GROUP BY atom_type
                ORDER BY count DESC
                """
            )

            # Count by equipment type (from tags)
            equipment_counts = await conn.fetch(
                """
                SELECT
                    COALESCE(metadata->>'equipment_type', 'unknown') as equipment,
                    COUNT(*) as count
                FROM knowledge_atoms
                WHERE metadata IS NOT NULL
                GROUP BY equipment
                ORDER BY count DESC
                LIMIT 10
                """
            )

            # Count by vendor
            vendor_counts = await conn.fetch(
                """
                SELECT
                    COALESCE(metadata->>'vendor', 'unknown') as vendor,
                    COUNT(*) as count
                FROM knowledge_atoms
                WHERE metadata IS NOT NULL
                GROUP BY vendor
                ORDER BY count DESC
                LIMIT 10
                """
            )

        type_distribution = {row["atom_type"]: row["count"] for row in type_counts}
        equipment_distribution = {row["equipment"]: row["count"] for row in equipment_counts}
        vendor_distribution = {row["vendor"]: row["count"] for row in vendor_counts}

        stats = {
            "status": "complete",
            "low_quality_atoms": low_quality or 0,
            "type_distribution": type_distribution,
            "equipment_distribution": equipment_distribution,
            "vendor_distribution": vendor_distribution,
        }

        logger.info(f"Low quality atoms: {low_quality or 0}")
        logger.info(f"Type distribution: {type_distribution}")
        logger.info(f"\nPHASE 3 COMPLETE")

        return stats

    async def _phase_4_growth_report(self) -> Dict[str, Any]:
        """
        Phase 4: Generate growth report.
        """
        logger.info("=" * 60)
        logger.info("PHASE 4: GROWTH REPORT")
        logger.info("=" * 60)

        today = datetime.utcnow()
        week_start = today - timedelta(days=7)

        async with self.db_pool.acquire() as conn:
            # Atoms added this week
            atoms_this_week = await conn.fetchval(
                """
                SELECT COUNT(*) FROM knowledge_atoms
                WHERE created_at > $1
                """,
                week_start
            )

            # Total atoms
            total_atoms = await conn.fetchval(
                "SELECT COUNT(*) FROM knowledge_atoms"
            )

            # Gap requests processed
            gaps_processed = await conn.fetchval(
                """
                SELECT COUNT(*) FROM gap_requests
                WHERE ingestion_completed = TRUE
                AND processed_at > $1
                """,
                week_start
            )

            # Jobs processed this week
            jobs_processed = await conn.fetchval(
                """
                SELECT COUNT(*) FROM kb_ingest_jobs
                WHERE status = 'completed'
                AND completed_at > $1
                """,
                week_start
            )

        growth_rate = (atoms_this_week / total_atoms * 100) if total_atoms > 0 else 0

        stats = {
            "status": "complete",
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": today.strftime("%Y-%m-%d"),
            "atoms_added_this_week": atoms_this_week or 0,
            "total_atoms": total_atoms or 0,
            "growth_rate": f"{growth_rate:.2f}%",
            "gaps_processed": gaps_processed or 0,
            "jobs_processed": jobs_processed or 0,
        }

        logger.info(f"Atoms added this week: {atoms_this_week}")
        logger.info(f"Total atoms: {total_atoms}")
        logger.info(f"Growth rate: {growth_rate:.2f}%")
        logger.info(f"\nPHASE 4 COMPLETE")

        return stats

    def _generate_report(self) -> str:
        """Generate comprehensive weekly report."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        report = f"""Weekly KB Maintenance Report - Week {self.week_number}
{timestamp}

PHASE 1: Reindexing
- Status: {self.stats['reindex'].get('status', 'N/A')}
- Total Atoms: {self.stats['reindex'].get('total_atoms', 'N/A')}
- With Embeddings: {self.stats['reindex'].get('with_embeddings', 'N/A')}
- Index Coverage: {self.stats['reindex'].get('index_coverage', 'N/A')}
- Stuck Jobs Reset: {self.stats['reindex'].get('stuck_jobs_reset', 0)}

PHASE 2: Deduplication
- Status: {self.stats['deduplicate'].get('status', 'N/A')}
- Method: {self.stats['deduplicate'].get('atoms_checked', 'N/A')}
- Duplicates Found: {self.stats['deduplicate'].get('duplicates_found', 0)}

PHASE 3: Quality Audit
- Status: {self.stats['quality'].get('status', 'N/A')}
- Low Quality Atoms: {self.stats['quality'].get('low_quality_atoms', 0)}
- Type Distribution: {json.dumps(self.stats['quality'].get('type_distribution', {}), indent=2)}

PHASE 4: Growth Report
- Week: {self.stats['growth'].get('week_start', 'N/A')} to {self.stats['growth'].get('week_end', 'N/A')}
- Atoms Added: {self.stats['growth'].get('atoms_added_this_week', 0)}
- Total Atoms: {self.stats['growth'].get('total_atoms', 0)}
- Growth Rate: {self.stats['growth'].get('growth_rate', 'N/A')}
- Gaps Processed: {self.stats['growth'].get('gaps_processed', 0)}
- Jobs Completed: {self.stats['growth'].get('jobs_processed', 0)}

Weekly maintenance complete!"""

        return report

    async def _send_slack(self, message: str):
        """Send message to Slack."""
        if not self.slack_webhook_url:
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    self.slack_webhook_url,
                    json={"text": f"*RIVET Pro KB Maintenance*\n{message}"}
                )
        except Exception as e:
            logger.warning(f"Failed to send Slack message: {e}")


async def main():
    """Main entry point."""
    maintenance = WeeklyKBMaintenance()
    return await maintenance.run()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
