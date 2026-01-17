"""
YCB Autonomous Video Production Loop

Automated daily video generation with quality gates.
Processes topics from queue, generates quality-gated videos,
and tracks metrics.

Usage:
    # Run once (process all topics in queue)
    python -m ycb.pipeline.autonomous_loop

    # Run as daemon (continuous with schedule)
    python -m ycb.pipeline.autonomous_loop --daemon --interval 3600

    # Add topics to queue
    python -m ycb.pipeline.autonomous_loop --add-topic "PLC Basics"
"""

import os
import json
import asyncio
import signal
import sys
from pathlib import Path
from datetime import datetime, time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict, field

from ycb.pipeline.quality_iteration import QualityIterativeGenerator, QualityIterationResult
from ycb.pipeline.metrics import PipelineMetrics


@dataclass
class TopicQueueItem:
    """Item in the topic queue."""
    topic: str
    style: str = "educational"
    priority: int = 0  # Higher = more urgent
    added_at: str = ""
    status: str = "pending"  # pending, processing, completed, failed
    attempts: int = 0
    last_attempt: Optional[str] = None
    result_score: Optional[float] = None

    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TopicQueue:
    """
    Persistent topic queue for video generation.

    Topics are stored in a JSON file and processed in priority order.
    """

    def __init__(self, queue_file: str = "./ycb_metrics/topic_queue.json"):
        self.queue_file = Path(queue_file)
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self.items: List[TopicQueueItem] = self._load()

    def _load(self) -> List[TopicQueueItem]:
        """Load queue from file."""
        if self.queue_file.exists():
            try:
                with open(self.queue_file) as f:
                    data = json.load(f)
                    return [TopicQueueItem(**item) for item in data]
            except Exception:
                pass
        return []

    def _save(self):
        """Save queue to file."""
        with open(self.queue_file, "w") as f:
            json.dump([item.to_dict() for item in self.items], f, indent=2)

    def add(self, topic: str, style: str = "educational", priority: int = 0) -> TopicQueueItem:
        """Add a topic to the queue."""
        item = TopicQueueItem(topic=topic, style=style, priority=priority)
        self.items.append(item)
        self._save()
        return item

    def add_batch(self, topics: List[str], style: str = "educational"):
        """Add multiple topics at once."""
        for topic in topics:
            self.add(topic, style)

    def get_pending(self) -> List[TopicQueueItem]:
        """Get all pending topics, sorted by priority."""
        pending = [item for item in self.items if item.status == "pending"]
        return sorted(pending, key=lambda x: -x.priority)

    def get_next(self) -> Optional[TopicQueueItem]:
        """Get next topic to process."""
        pending = self.get_pending()
        return pending[0] if pending else None

    def mark_processing(self, topic: str):
        """Mark a topic as currently processing."""
        for item in self.items:
            if item.topic == topic and item.status == "pending":
                item.status = "processing"
                item.last_attempt = datetime.now().isoformat()
                item.attempts += 1
                break
        self._save()

    def mark_completed(self, topic: str, score: float):
        """Mark a topic as completed."""
        for item in self.items:
            if item.topic == topic and item.status == "processing":
                item.status = "completed"
                item.result_score = score
                break
        self._save()

    def mark_failed(self, topic: str, score: float = 0.0):
        """Mark a topic as failed."""
        for item in self.items:
            if item.topic == topic and item.status == "processing":
                item.status = "failed"
                item.result_score = score
                break
        self._save()

    def retry_failed(self):
        """Reset failed items to pending for retry."""
        for item in self.items:
            if item.status == "failed":
                item.status = "pending"
        self._save()

    def clear_completed(self):
        """Remove completed items from queue."""
        self.items = [item for item in self.items if item.status != "completed"]
        self._save()

    def stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        return {
            "total": len(self.items),
            "pending": sum(1 for i in self.items if i.status == "pending"),
            "processing": sum(1 for i in self.items if i.status == "processing"),
            "completed": sum(1 for i in self.items if i.status == "completed"),
            "failed": sum(1 for i in self.items if i.status == "failed"),
        }


class AutonomousLoop:
    """
    Autonomous video production loop.

    Processes topics from queue with quality gates and metrics tracking.
    """

    def __init__(
        self,
        max_iterations: int = 4,
        target_score: float = 8.0,
        max_videos_per_run: int = 10,
        assemble_video: bool = True,
        output_dir: str = "./ycb_output"
    ):
        """
        Initialize autonomous loop.

        Args:
            max_iterations: Max quality iterations per video
            target_score: Minimum score to pass
            max_videos_per_run: Maximum videos per run cycle
            assemble_video: Whether to assemble final MP4
            output_dir: Output directory for videos
        """
        self.max_iterations = max_iterations
        self.target_score = target_score
        self.max_videos_per_run = max_videos_per_run
        self.assemble_video = assemble_video
        self.output_dir = output_dir

        self.queue = TopicQueue()
        self.metrics = PipelineMetrics()
        self.generator = QualityIterativeGenerator(
            max_iterations=max_iterations,
            target_score=target_score,
            output_dir=output_dir
        )

        self._running = False
        self._stop_requested = False

    async def process_topic(self, item: TopicQueueItem) -> QualityIterationResult:
        """Process a single topic from the queue."""
        print(f"\n[*] Processing: {item.topic}")
        print(f"    Style: {item.style}")
        print(f"    Attempt: {item.attempts}")

        self.queue.mark_processing(item.topic)

        try:
            result = await self.generator.generate_with_quality_gate(
                topic=item.topic,
                style=item.style,
                assemble_video=self.assemble_video
            )

            # Log metrics
            self.metrics.log_video_result(result)

            if result.passed:
                self.queue.mark_completed(item.topic, result.final_score)
                print(f"\n[+] PASSED: {item.topic} ({result.final_score}/10)")
            else:
                self.queue.mark_failed(item.topic, result.final_score)
                print(f"\n[-] FAILED: {item.topic} ({result.final_score}/10)")

            return result

        except Exception as e:
            print(f"\n[!] ERROR processing {item.topic}: {e}")
            self.queue.mark_failed(item.topic)
            raise

    async def run_once(self) -> Dict[str, Any]:
        """
        Run one cycle - process all pending topics up to max.

        Returns:
            Summary of processed videos
        """
        print(f"\n{'='*60}")
        print(f"YCB AUTONOMOUS LOOP - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        queue_stats = self.queue.stats()
        print(f"Queue: {queue_stats['pending']} pending, {queue_stats['completed']} completed, {queue_stats['failed']} failed")

        results = {
            "started_at": datetime.now().isoformat(),
            "processed": 0,
            "passed": 0,
            "failed": 0,
            "videos": []
        }

        processed = 0
        while processed < self.max_videos_per_run:
            if self._stop_requested:
                print("\n[!] Stop requested, finishing current cycle...")
                break

            item = self.queue.get_next()
            if not item:
                print("\n[*] No more pending topics in queue")
                break

            try:
                result = await self.process_topic(item)
                results["processed"] += 1
                results["videos"].append({
                    "topic": item.topic,
                    "passed": result.passed,
                    "score": result.final_score,
                    "iterations": result.iterations_used
                })

                if result.passed:
                    results["passed"] += 1
                else:
                    results["failed"] += 1

            except Exception as e:
                results["failed"] += 1
                print(f"[!] Error: {e}")

            processed += 1

        results["finished_at"] = datetime.now().isoformat()

        # Print summary
        print(f"\n{'='*60}")
        print(f"CYCLE COMPLETE")
        print(f"{'='*60}")
        print(f"Processed: {results['processed']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")

        # Print metrics
        self.metrics.print_summary(days=1)

        return results

    async def run_daemon(self, interval_seconds: int = 3600):
        """
        Run as daemon - continuous loop with interval.

        Args:
            interval_seconds: Seconds between cycles (default 1 hour)
        """
        print(f"\n[*] Starting YCB daemon (interval: {interval_seconds}s)")
        print(f"    Press Ctrl+C to stop\n")

        self._running = True
        self._stop_requested = False

        # Setup signal handlers
        def signal_handler(sig, frame):
            print("\n[!] Shutdown signal received...")
            self._stop_requested = True

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        while not self._stop_requested:
            try:
                await self.run_once()

                if self._stop_requested:
                    break

                print(f"\n[*] Sleeping for {interval_seconds}s until next cycle...")
                print(f"    Next run: {datetime.now().timestamp() + interval_seconds}")

                # Sleep in chunks to allow interrupt
                for _ in range(interval_seconds):
                    if self._stop_requested:
                        break
                    await asyncio.sleep(1)

            except Exception as e:
                print(f"\n[!] Daemon error: {e}")
                if not self._stop_requested:
                    print(f"    Retrying in 60s...")
                    await asyncio.sleep(60)

        print("\n[*] Daemon stopped")
        self._running = False

    def stop(self):
        """Request daemon stop."""
        self._stop_requested = True


# Default topics for industrial automation channel
DEFAULT_TOPICS = [
    "What is a PLC and How Does It Work",
    "Introduction to Ladder Logic Programming",
    "Understanding VFD Fault Codes",
    "PLC vs DCS - Key Differences Explained",
    "How to Read Electrical Schematics",
    "Introduction to SCADA Systems",
    "Motor Control Circuits Explained",
    "PLC Input Output Wiring Basics",
    "What is Modbus Communication Protocol",
    "Industrial Sensor Types and Applications",
]


async def main():
    """CLI entry point."""
    from dotenv import load_dotenv
    load_dotenv()

    import argparse
    parser = argparse.ArgumentParser(description="YCB Autonomous Video Production")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--interval", type=int, default=3600, help="Daemon interval in seconds")
    parser.add_argument("--max-videos", type=int, default=10, help="Max videos per cycle")
    parser.add_argument("--max-iterations", type=int, default=4, help="Max quality iterations")
    parser.add_argument("--target-score", type=float, default=8.0, help="Target quality score")
    parser.add_argument("--add-topic", type=str, help="Add a topic to queue")
    parser.add_argument("--add-defaults", action="store_true", help="Add default industrial topics")
    parser.add_argument("--show-queue", action="store_true", help="Show queue status")
    parser.add_argument("--show-metrics", action="store_true", help="Show metrics summary")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed topics")
    parser.add_argument("--clear-completed", action="store_true", help="Clear completed topics")
    parser.add_argument("--no-assemble", action="store_true", help="Skip video assembly")

    args = parser.parse_args()

    loop = AutonomousLoop(
        max_iterations=args.max_iterations,
        target_score=args.target_score,
        max_videos_per_run=args.max_videos,
        assemble_video=not args.no_assemble
    )

    # Handle queue operations
    if args.add_topic:
        item = loop.queue.add(args.add_topic)
        print(f"[+] Added to queue: {args.add_topic}")
        return

    if args.add_defaults:
        loop.queue.add_batch(DEFAULT_TOPICS)
        print(f"[+] Added {len(DEFAULT_TOPICS)} default topics to queue")
        return

    if args.show_queue:
        stats = loop.queue.stats()
        print(f"\nQueue Status:")
        print(f"  Total: {stats['total']}")
        print(f"  Pending: {stats['pending']}")
        print(f"  Processing: {stats['processing']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"\nPending Topics:")
        for item in loop.queue.get_pending()[:10]:
            print(f"  - {item.topic} (priority: {item.priority})")
        return

    if args.show_metrics:
        loop.metrics.print_summary(days=7)
        return

    if args.retry_failed:
        loop.queue.retry_failed()
        print("[+] Failed topics reset to pending")
        return

    if args.clear_completed:
        loop.queue.clear_completed()
        print("[+] Completed topics cleared from queue")
        return

    # Run the loop
    if args.daemon:
        await loop.run_daemon(interval_seconds=args.interval)
    else:
        await loop.run_once()


if __name__ == "__main__":
    asyncio.run(main())
