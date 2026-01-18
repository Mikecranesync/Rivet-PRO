#!/usr/bin/env python3
"""
URL Scheduler - Seeds Redis Queue with Maintenance Documentation URLs

Loads curated manufacturer manual URLs and pushes them to Redis queue
for the 24/7 KB ingestion worker to process.

Based on Agent Factory's simple_url_scheduler.py, adapted for:
- Upstash Redis (serverless)
- Maintenance-focused OEM sources (Rockwell, Siemens, Trane, etc.)
- Slack notifications

Usage:
    # Run once
    python -m rivet_pro.workers.url_scheduler --once

    # Run continuously (hourly batches)
    python -m rivet_pro.workers.url_scheduler

Environment Variables:
    REDIS_URL - Upstash Redis connection string
    SLACK_WEBHOOK_URL - Slack webhook for notifications
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Optional

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed")


# =============================================================================
# Seed URLs - Maintenance Equipment Manuals
# =============================================================================

SEED_URLS: Dict[str, List[str]] = {
    "rockwell_automation": [
        # PowerFlex Drives
        "https://literature.rockwellautomation.com/idc/groups/literature/documents/um/520-um001_-en-e.pdf",
        "https://literature.rockwellautomation.com/idc/groups/literature/documents/um/750-um001_-en-p.pdf",
        # ControlLogix PLCs
        "https://literature.rockwellautomation.com/idc/groups/literature/documents/um/1756-um001_-en-p.pdf",
        "https://literature.rockwellautomation.com/idc/groups/literature/documents/rm/1756-rm003_-en-p.pdf",
        # CompactLogix
        "https://literature.rockwellautomation.com/idc/groups/literature/documents/um/1769-um011_-en-p.pdf",
    ],
    "siemens": [
        # SINAMICS Drives
        "https://support.industry.siemens.com/cs/document/109761276/sinamics-g120c-operating-instructions",
        "https://support.industry.siemens.com/cs/document/109478922/sinamics-g120-parameter-manual",
        # S7-1200 PLCs
        "https://support.industry.siemens.com/cs/document/109759862/s7-1200-system-manual",
        "https://support.industry.siemens.com/cs/document/109478882/s7-1500-system-manual",
    ],
    "abb": [
        # ACS580 Drives
        "https://search.abb.com/library/Download.aspx?DocumentID=3AUA0000081917&LanguageCode=en&DocumentPartId=1",
        # ACS880 Drives
        "https://search.abb.com/library/Download.aspx?DocumentID=3AUA0000098111&LanguageCode=en&DocumentPartId=1",
    ],
    "danfoss": [
        # VLT Drives
        "https://www.danfoss.com/en/service-and-support/downloads/dds/vlt-automation-drive-fc-301-fc-302/",
    ],
    "trane": [
        # HVAC Equipment
        "https://www.trane.com/commercial/north-america/us/en/products-systems/equipment/unitary/rooftop-units.html",
    ],
    "carrier": [
        # HVAC Equipment
        "https://www.carrier.com/commercial/en/us/products/hvac/",
    ],
    "grundfos": [
        # Pumps
        "https://www.grundfos.com/products",
    ],
}


def get_all_urls() -> List[str]:
    """Get flattened list of all seed URLs."""
    all_urls = []
    for manufacturer, urls in SEED_URLS.items():
        all_urls.extend(urls)
    return all_urls


def get_url_metadata() -> Dict[str, int]:
    """Get count of URLs per manufacturer."""
    metadata = {}
    total = 0
    for manufacturer, urls in SEED_URLS.items():
        metadata[manufacturer] = len(urls)
        total += len(urls)
    metadata["total"] = total
    return metadata


# =============================================================================
# URL Scheduler
# =============================================================================

class URLScheduler:
    """
    Seeds Redis queue with documentation URLs for KB ingestion.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        slack_webhook_url: Optional[str] = None,
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self) -> bool:
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            logger.error("redis package not installed")
            return False

        if not self.redis_url:
            logger.error("REDIS_URL not configured")
            return False

        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10
            )
            self.redis_client.ping()
            logger.info("Connected to Redis")
            return True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            await self._send_slack(f"❌ URL Scheduler FAILED\n\nRedis connection error: {e}")
            return False

    async def push_urls(self, urls: Optional[List[str]] = None) -> int:
        """
        Push URLs to Redis queue.

        Args:
            urls: Optional list of URLs. If None, uses SEED_URLS.

        Returns:
            Number of URLs pushed
        """
        if not self.redis_client:
            if not await self.connect():
                return 0

        urls = urls or get_all_urls()
        queue_before = self.redis_client.llen("kb_ingest_jobs")

        logger.info(f"Pushing {len(urls)} URLs to queue...")

        pushed = 0
        for url in urls:
            try:
                self.redis_client.rpush("kb_ingest_jobs", url)
                pushed += 1
            except Exception as e:
                logger.error(f"Failed to push {url}: {e}")

        queue_after = self.redis_client.llen("kb_ingest_jobs")

        logger.info(f"Pushed {pushed}/{len(urls)} URLs (queue: {queue_before} → {queue_after})")

        return pushed

    async def run_once(self) -> int:
        """Run scheduler once (push all seed URLs)."""
        start_time = datetime.utcnow()

        logger.info("=" * 60)
        logger.info("URL SCHEDULER - ONE-TIME RUN")
        logger.info("=" * 60)

        pushed = await self.push_urls()

        if pushed > 0:
            metadata = get_url_metadata()
            summary = self._build_summary(pushed, metadata, start_time)
            await self._send_slack(summary)
            logger.info(summary)

        return pushed

    async def run_continuous(self, interval_hours: int = 1):
        """
        Run scheduler continuously, pushing URLs at specified interval.

        Args:
            interval_hours: Hours between URL batches
        """
        logger.info("=" * 60)
        logger.info(f"URL SCHEDULER - CONTINUOUS (every {interval_hours}h)")
        logger.info("=" * 60)

        while True:
            await self.run_once()
            logger.info(f"Sleeping {interval_hours} hours until next batch...")
            await asyncio.sleep(interval_hours * 3600)

    def _build_summary(
        self,
        pushed: int,
        metadata: Dict[str, int],
        start_time: datetime
    ) -> str:
        """Build summary message."""
        duration = (datetime.utcnow() - start_time).total_seconds()

        lines = [
            "📋 *URL Scheduler Report*",
            f"🕐 {start_time.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "*URLs Pushed by Manufacturer:*",
        ]

        for manufacturer, count in metadata.items():
            if manufacturer != "total":
                name = manufacturer.replace("_", " ").title()
                lines.append(f"• {name}: {count}")

        lines.extend([
            "",
            f"*Total:* {pushed} URLs",
            f"*Duration:* {duration:.1f}s",
            "",
            "✅ Worker will process these automatically",
        ])

        return "\n".join(lines)

    async def _send_slack(self, message: str):
        """Send message to Slack."""
        if not self.slack_webhook_url:
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    self.slack_webhook_url,
                    json={"text": message}
                )
        except Exception as e:
            logger.warning(f"Failed to send Slack message: {e}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="KB URL Scheduler")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1,
        help="Hours between batches (continuous mode)"
    )

    args = parser.parse_args()

    scheduler = URLScheduler()

    if args.once:
        pushed = await scheduler.run_once()
        return 0 if pushed > 0 else 1
    else:
        await scheduler.run_continuous(args.interval)
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
