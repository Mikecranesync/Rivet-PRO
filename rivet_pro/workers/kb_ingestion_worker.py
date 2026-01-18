#!/usr/bin/env python3
"""
24/7 KB Ingestion Worker - RIVET Pro

Continuously polls Redis queue 'kb_ingest_jobs' for URLs to ingest.
Processes PDFs, web pages, and YouTube transcripts into knowledge atoms.
Sends hourly status updates to Slack.

Based on Agent Factory's rivet_worker.py, adapted for:
- Upstash Redis (serverless)
- Neon PostgreSQL
- Slack notifications

Usage:
    python -m rivet_pro.workers.kb_ingestion_worker

Environment Variables:
    REDIS_URL - Upstash Redis connection string
    DATABASE_URL - Neon PostgreSQL connection string
    SLACK_WEBHOOK_URL - Slack webhook for status updates

Deployment:
    Fly.io: Add as second process in fly.toml
"""

import os
import sys
import asyncio
import signal
import logging
import hashlib
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Try to import redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed - queue functionality disabled")


class KBIngestionWorker:
    """
    24/7 Knowledge Base Ingestion Worker.

    Polls Redis queue for URLs, processes them through ingestion pipeline,
    stores atoms in Neon PostgreSQL, and reports status to Slack.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        database_url: Optional[str] = None,
        slack_webhook_url: Optional[str] = None,
        poll_interval: int = 5,
        heartbeat_interval: int = 300,  # 5 minutes
        status_interval: int = 3600,  # 1 hour
    ):
        """
        Initialize the worker.

        Args:
            redis_url: Upstash Redis connection URL
            database_url: Neon PostgreSQL connection URL
            slack_webhook_url: Slack webhook for notifications
            poll_interval: Seconds between queue polls (for blpop timeout)
            heartbeat_interval: Seconds between heartbeat updates
            status_interval: Seconds between Slack status reports
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")

        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        self.status_interval = status_interval

        # Worker state
        self.worker_id = f"worker-{os.getpid()}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        self.shutdown_requested = False
        self.started_at = datetime.utcnow()

        # Metrics
        self.jobs_processed = 0
        self.jobs_failed = 0
        self.atoms_created = 0
        self.last_status_sent = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()

        # Connections
        self.redis_client: Optional[redis.Redis] = None
        self.db_pool = None

    async def start(self):
        """Start the worker loop."""
        logger.info("=" * 70)
        logger.info("RIVET PRO KB INGESTION WORKER")
        logger.info(f"Worker ID: {self.worker_id}")
        logger.info("=" * 70)

        # Validate configuration
        if not self.redis_url:
            logger.error("REDIS_URL not configured")
            return 1

        if not REDIS_AVAILABLE:
            logger.error("redis package not installed")
            return 1

        # Connect to Redis
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=60
            )
            self.redis_client.ping()
            logger.info(f"Connected to Redis")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            await self._send_slack_alert(f"❌ KB Worker Failed to Start\n\nRedis connection error: {e}")
            return 1

        # Connect to database
        try:
            import asyncpg
            self.db_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5
            )
            logger.info("Connected to Neon PostgreSQL")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            await self._send_slack_alert(f"❌ KB Worker Failed to Start\n\nDatabase error: {e}")
            return 1

        # Send startup notification
        await self._send_slack_status("🟢 KB Ingestion Worker Started", is_startup=True)

        # Register heartbeat
        await self._update_heartbeat("running")

        # Main loop
        logger.info("Starting polling loop (Ctrl+C to stop)")

        while not self.shutdown_requested:
            try:
                # Check if we need to send hourly status
                if (datetime.utcnow() - self.last_status_sent).total_seconds() >= self.status_interval:
                    await self._send_hourly_status()

                # Check if we need to update heartbeat
                if (datetime.utcnow() - self.last_heartbeat).total_seconds() >= self.heartbeat_interval:
                    await self._update_heartbeat("running")

                # Poll queue (blocking with timeout)
                result = self.redis_client.blpop("kb_ingest_jobs", timeout=self.poll_interval)

                if result:
                    queue_name, url = result
                    logger.info(f"Processing URL: {url}")

                    try:
                        success, atoms = await self._process_url(url)

                        if success:
                            self.jobs_processed += 1
                            self.atoms_created += atoms
                            logger.info(f"[SUCCESS] {url} - {atoms} atoms created")
                        else:
                            self.jobs_failed += 1
                            logger.warning(f"[FAILED] {url}")

                    except Exception as e:
                        self.jobs_failed += 1
                        logger.error(f"[ERROR] {url}: {e}")

                else:
                    # Queue empty, idle
                    pass

            except redis.ConnectionError as e:
                logger.error(f"Redis connection lost: {e}")
                await self._send_slack_alert(f"⚠️ Redis Connection Lost\n\nWaiting 60s before retry...")
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                await asyncio.sleep(10)

        # Graceful shutdown
        logger.info("Shutting down...")
        await self._update_heartbeat("shutdown")
        await self._send_slack_status("🔴 KB Ingestion Worker Stopped", is_shutdown=True)

        if self.db_pool:
            await self.db_pool.close()

        logger.info("Worker shutdown complete")
        return 0

    async def _process_url(self, url: str) -> tuple[bool, int]:
        """
        Process a single URL through ingestion pipeline.

        Args:
            url: URL to process

        Returns:
            Tuple of (success, atoms_created)
        """
        # Check for duplicate
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]

        async with self.db_pool.acquire() as conn:
            existing = await conn.fetchval(
                "SELECT id FROM source_fingerprints WHERE fingerprint = $1",
                url_hash
            )
            if existing:
                logger.info(f"Skipping duplicate: {url}")
                return True, 0

        # Determine source type
        if url.endswith('.pdf') or 'pdf' in url.lower():
            source_type = 'pdf'
        elif 'youtube.com' in url or 'youtu.be' in url:
            source_type = 'youtube'
        else:
            source_type = 'web'

        # TODO: Implement full ingestion pipeline
        # For now, just mark as processed
        logger.info(f"Would ingest {source_type}: {url}")

        # Record fingerprint
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO source_fingerprints (fingerprint, url, source_type)
                VALUES ($1, $2, $3)
                ON CONFLICT (fingerprint) DO NOTHING
                """,
                url_hash, url, source_type
            )

        # Placeholder: Return 0 atoms until pipeline is fully implemented
        return True, 0

    async def _update_heartbeat(self, status: str):
        """Update worker heartbeat in database."""
        self.last_heartbeat = datetime.utcnow()

        try:
            queue_depth = self.redis_client.llen("kb_ingest_jobs") if self.redis_client else 0

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO kb_worker_heartbeats
                        (worker_id, worker_type, status, jobs_processed, jobs_failed, queue_depth, started_at, last_heartbeat)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    ON CONFLICT (worker_id, worker_type)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        jobs_processed = EXCLUDED.jobs_processed,
                        jobs_failed = EXCLUDED.jobs_failed,
                        queue_depth = EXCLUDED.queue_depth,
                        last_heartbeat = NOW()
                    """,
                    self.worker_id, "ingestion", status,
                    self.jobs_processed, self.jobs_failed, queue_depth,
                    self.started_at
                )
                logger.debug(f"Heartbeat updated: {status}")

        except Exception as e:
            logger.warning(f"Failed to update heartbeat: {e}")

    async def _send_hourly_status(self):
        """Send hourly status to Slack."""
        self.last_status_sent = datetime.utcnow()
        await self._send_slack_status("📊 Hourly Status Report")

    async def _send_slack_status(self, title: str, is_startup: bool = False, is_shutdown: bool = False):
        """Send status message to Slack."""
        if not self.slack_webhook_url:
            return

        uptime = datetime.utcnow() - self.started_at
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds

        queue_depth = 0
        if self.redis_client:
            try:
                queue_depth = self.redis_client.llen("kb_ingest_jobs")
            except Exception:
                pass

        message = f"""🤖 *RIVET Pro KB Worker*
━━━━━━━━━━━━━━━━━━━━━━

{title}

📈 *Metrics:*
• Jobs Processed: {self.jobs_processed}
• Jobs Failed: {self.jobs_failed}
• Atoms Created: {self.atoms_created}
• Queue Depth: {queue_depth}

⏱️ *Uptime:* {uptime_str}
🆔 *Worker:* {self.worker_id[:20]}...

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"""

        await self._send_slack_message(message)

    async def _send_slack_alert(self, message: str):
        """Send alert message to Slack."""
        if not self.slack_webhook_url:
            return
        await self._send_slack_message(message)

    async def _send_slack_message(self, text: str):
        """Send message to Slack webhook."""
        if not self.slack_webhook_url:
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.slack_webhook_url,
                    json={"text": text}
                )
                if response.status_code != 200:
                    logger.warning(f"Slack webhook returned {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to send Slack message: {e}")

    def request_shutdown(self, signum=None, frame=None):
        """Handle shutdown signal."""
        logger.info(f"Received shutdown signal")
        self.shutdown_requested = True


async def main():
    """Main entry point."""
    worker = KBIngestionWorker()

    # Register signal handlers
    signal.signal(signal.SIGTERM, worker.request_shutdown)
    signal.signal(signal.SIGINT, worker.request_shutdown)

    return await worker.start()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
