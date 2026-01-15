"""
Autonomous Enrichment Worker - AUTO-KB-003

24/7 background worker that processes enrichment queue continuously.
Runs as a systemd service, processing jobs in priority order.
"""

import asyncio
import json
import signal
import socket
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

import asyncpg

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from rivet_pro.core.services.enrichment_queue_service import EnrichmentQueueService


class AutonomousEnrichmentWorker:
    """
    Background worker that processes enrichment queue continuously.

    Features:
    - Polls queue every 30 seconds
    - Processes jobs in priority order (highest first)
    - Runs 3-5 concurrent jobs via asyncio.gather
    - Graceful shutdown on SIGTERM
    - Heartbeat every 5 minutes
    - Exponential backoff on failures
    """

    POLL_INTERVAL = 30  # seconds
    HEARTBEAT_INTERVAL = 300  # 5 minutes
    MAX_CONCURRENT_JOBS = 3
    MAX_RETRIES = 3
    BASE_BACKOFF = 5  # seconds

    def __init__(self, db_url: str):
        """
        Initialize worker with database URL.

        Args:
            db_url: PostgreSQL connection string
        """
        self.db_url = db_url
        self.db_pool: Optional[asyncpg.Pool] = None
        self.queue_service: Optional[EnrichmentQueueService] = None
        self.worker_id = f"worker-{socket.gethostname()}-{uuid4().hex[:8]}"
        self.running = False
        self.shutdown_event = asyncio.Event()
        self.jobs_processed = 0
        self.jobs_failed = 0
        self.started_at: Optional[datetime] = None

    async def start(self):
        """Start the worker and begin processing."""
        print(f"[{self.worker_id}] Starting Autonomous Enrichment Worker...")

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._handle_shutdown)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                signal.signal(sig, lambda s, f: self._handle_shutdown())

        # Connect to database
        try:
            self.db_pool = await asyncpg.create_pool(
                self.db_url,
                min_size=2,
                max_size=self.MAX_CONCURRENT_JOBS + 2
            )
            self.queue_service = EnrichmentQueueService(self.db_pool)
            print(f"[{self.worker_id}] Connected to database")
        except Exception as e:
            print(f"[{self.worker_id}] Failed to connect to database: {e}")
            return

        self.running = True
        self.started_at = datetime.now()

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Main processing loop
        try:
            await self._process_loop()
        finally:
            self.running = False
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

            if self.db_pool:
                await self.db_pool.close()

            print(f"[{self.worker_id}] Worker stopped. "
                  f"Processed: {self.jobs_processed}, Failed: {self.jobs_failed}")

    def _handle_shutdown(self):
        """Handle shutdown signal gracefully."""
        print(f"\n[{self.worker_id}] Received shutdown signal, finishing current jobs...")
        self.running = False
        self.shutdown_event.set()

    async def _process_loop(self):
        """Main processing loop - poll queue and process jobs."""
        consecutive_errors = 0

        while self.running:
            try:
                # Get pending jobs (up to MAX_CONCURRENT_JOBS)
                jobs = await self._get_pending_jobs(self.MAX_CONCURRENT_JOBS)

                if jobs:
                    print(f"[{self.worker_id}] Found {len(jobs)} jobs to process")

                    # Process jobs concurrently
                    tasks = [self._process_job(job) for job in jobs]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Count results
                    for result in results:
                        if isinstance(result, Exception):
                            self.jobs_failed += 1
                            print(f"[{self.worker_id}] Job failed with exception: {result}")
                        elif result:
                            self.jobs_processed += 1
                        else:
                            self.jobs_failed += 1

                    consecutive_errors = 0
                else:
                    # No jobs, wait before polling again
                    pass

                # Wait for next poll (or shutdown)
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(),
                        timeout=self.POLL_INTERVAL
                    )
                    # If we get here, shutdown was requested
                    break
                except asyncio.TimeoutError:
                    # Normal timeout, continue polling
                    pass

            except Exception as e:
                consecutive_errors += 1
                backoff = min(self.BASE_BACKOFF * (2 ** consecutive_errors), 300)
                print(f"[{self.worker_id}] Error in process loop (attempt {consecutive_errors}): {e}")
                print(f"[{self.worker_id}] Backing off for {backoff} seconds...")

                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(),
                        timeout=backoff
                    )
                    break
                except asyncio.TimeoutError:
                    pass

    async def _get_pending_jobs(self, limit: int) -> list:
        """Get pending jobs from queue."""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        id,
                        manufacturer,
                        model_pattern,
                        priority,
                        user_query_count,
                        metadata,
                        created_at
                    FROM enrichment_queue
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT $1
                    """,
                    limit
                )
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[{self.worker_id}] Error getting pending jobs: {e}")
            return []

    async def _process_job(self, job: Dict[str, Any]) -> bool:
        """
        Process a single enrichment job.

        Steps:
        1. Mark job as processing
        2. Discover product family
        3. Search for manuals
        4. Download manuals
        5. Create knowledge atoms
        6. Mark job as completed

        Args:
            job: Job dict from queue

        Returns:
            True if successful, False otherwise
        """
        job_id = job['id']
        manufacturer = job['manufacturer']
        model_pattern = job['model_pattern']

        print(f"[{self.worker_id}] Processing job {job_id}: {manufacturer} {model_pattern}")

        try:
            # Mark as processing
            await self.queue_service.update_job_status(
                job_id=job_id,
                status='processing',
                worker_id=self.worker_id
            )

            # TODO: Implement actual enrichment logic
            # For now, simulate processing
            family_size = 0
            manuals_indexed = 0

            # Step 1: Discover product family (stub)
            # family = await self._discover_family(manufacturer, model_pattern)
            # family_size = len(family)

            # Step 2: Search for manuals (stub)
            # manuals = await self._search_manuals(manufacturer, model_pattern)

            # Step 3: Download and index manuals (stub)
            # manuals_indexed = await self._index_manuals(manuals)

            # Step 4: Create knowledge atoms (stub)
            # await self._create_atoms(manufacturer, model_pattern, manuals)

            # Simulate some work
            await asyncio.sleep(2)

            # Mark as completed
            await self.queue_service.update_job_status(
                job_id=job_id,
                status='completed',
                family_size=family_size,
                manuals_indexed=manuals_indexed
            )

            print(f"[{self.worker_id}] Completed job {job_id}: "
                  f"family_size={family_size}, manuals={manuals_indexed}")
            return True

        except Exception as e:
            print(f"[{self.worker_id}] Job {job_id} failed: {e}")

            await self.queue_service.update_job_status(
                job_id=job_id,
                status='failed',
                error_message=str(e)
            )
            return False

    async def _heartbeat_loop(self):
        """Send heartbeat every 5 minutes."""
        while self.running:
            try:
                await self._send_heartbeat()
            except Exception as e:
                print(f"[{self.worker_id}] Heartbeat error: {e}")

            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=self.HEARTBEAT_INTERVAL
                )
                break
            except asyncio.TimeoutError:
                pass

    async def _send_heartbeat(self):
        """Record heartbeat in enrichment_stats table."""
        try:
            async with self.db_pool.acquire() as conn:
                metrics = json.dumps({
                    'jobs_processed': self.jobs_processed,
                    'jobs_failed': self.jobs_failed,
                    'uptime_seconds': (datetime.now() - self.started_at).total_seconds() if self.started_at else 0
                })
                await conn.execute(
                    """
                    INSERT INTO enrichment_stats (
                        stat_type,
                        worker_id,
                        timestamp,
                        metrics
                    ) VALUES (
                        'worker_heartbeat',
                        $1,
                        NOW(),
                        $2::jsonb
                    )
                    """,
                    self.worker_id,
                    metrics
                )
                print(f"[{self.worker_id}] Heartbeat sent | "
                      f"processed={self.jobs_processed}, failed={self.jobs_failed}")
        except Exception as e:
            print(f"[{self.worker_id}] Failed to send heartbeat: {e}")


async def main():
    """Entry point for the worker."""
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description='Autonomous Enrichment Worker')
    parser.add_argument('--db-url', type=str, help='Database URL (or use DATABASE_URL env)')
    args = parser.parse_args()

    # Get database URL
    db_url = args.db_url or os.getenv('DATABASE_URL')

    if not db_url:
        # Try to load from .env file
        env_file = Path(__file__).parent.parent.parent / '.env'
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        db_url = line.split('=', 1)[1].strip()
                        break

    if not db_url:
        print("ERROR: DATABASE_URL not found")
        print("Set DATABASE_URL environment variable or use --db-url")
        sys.exit(1)

    worker = AutonomousEnrichmentWorker(db_url)
    await worker.start()


if __name__ == '__main__':
    asyncio.run(main())
