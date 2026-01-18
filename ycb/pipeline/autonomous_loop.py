"""
YCB Autonomous Video Production Loop

Automated daily video generation with quality gates.
Processes topics from queue, generates quality-gated videos,
and tracks metrics.

Supports both v1 (basic) and v3 (Manim/Blender) pipelines.

Usage:
    # Run once with v1 pipeline (default)
    python -m ycb.pipeline.autonomous_loop

    # Run once with v3 pipeline (Manim rendering)
    python -m ycb.pipeline.autonomous_loop --v3

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
from typing import List, Optional, Dict, Any, Union
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
    pipeline_version: str = "v1"  # v1 or v3

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

    def add(self, topic: str, style: str = "educational", priority: int = 0, pipeline_version: str = "v1") -> TopicQueueItem:
        """Add a topic to the queue."""
        item = TopicQueueItem(topic=topic, style=style, priority=priority, pipeline_version=pipeline_version)
        self.items.append(item)
        self._save()
        return item

    def add_batch(self, topics: List[str], style: str = "educational", pipeline_version: str = "v1"):
        """Add multiple topics at once."""
        for topic in topics:
            self.add(topic, style, pipeline_version=pipeline_version)

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


@dataclass
class V3IterationResult:
    """Result wrapper for v3 pipeline to match v1 interface."""
    topic: str
    final_score: float
    passed: bool
    iterations_used: int
    max_iterations: int
    video: Optional[Dict[str, Any]] = None
    iteration_history: List[Dict] = field(default_factory=list)
    total_cost_estimate: float = 0.0
    # v3-specific fields
    render_time: float = 0.0
    scene_count: int = 0
    scenes_rendered: int = 0
    scenes_failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutonomousLoop:
    """
    Autonomous video production loop.

    Processes topics from queue with quality gates and metrics tracking.
    Supports both v1 (basic) and v3 (Manim/Blender) pipelines.
    """

    def __init__(
        self,
        max_iterations: int = 4,
        target_score: float = 8.0,
        max_videos_per_run: int = 10,
        assemble_video: bool = True,
        output_dir: str = "./ycb_output",
        use_v3: bool = False
    ):
        """
        Initialize autonomous loop.

        Args:
            max_iterations: Max quality iterations per video
            target_score: Minimum score to pass
            max_videos_per_run: Maximum videos per run cycle
            assemble_video: Whether to assemble final MP4
            output_dir: Output directory for videos
            use_v3: Use v3 pipeline with Manim/Blender rendering
        """
        self.max_iterations = max_iterations
        self.target_score = target_score
        self.max_videos_per_run = max_videos_per_run
        self.assemble_video = assemble_video
        self.output_dir = output_dir
        self.use_v3 = use_v3

        # Adjust target score for v3 (higher threshold)
        if use_v3 and target_score < 8.5:
            self.target_score = 8.5
            print(f"[*] v3 mode: Target score adjusted to {self.target_score}")

        self.queue = TopicQueue()
        self.metrics = PipelineMetrics()

        # Lazy-load generators
        self._v1_generator = None
        self._v3_generator = None
        self._v3_judge = None
        self._v3_available = None

        self._running = False
        self._stop_requested = False

    def _check_v3_available(self) -> bool:
        """Check if v3 pipeline dependencies are available."""
        if self._v3_available is not None:
            return self._v3_available

        try:
            from ycb.pipeline import VideoGeneratorV3
            from ycb.evaluation import VideoQualityJudgeV3
            # Check if Manim is available
            import subprocess
            result = subprocess.run(
                ["manim", "--version"],
                capture_output=True,
                timeout=5
            )
            self._v3_available = result.returncode == 0
        except Exception as e:
            print(f"[!] v3 not available: {e}")
            self._v3_available = False

        return self._v3_available

    def _get_v1_generator(self) -> QualityIterativeGenerator:
        """Get or create v1 generator."""
        if self._v1_generator is None:
            self._v1_generator = QualityIterativeGenerator(
                max_iterations=self.max_iterations,
                target_score=self.target_score,
                output_dir=self.output_dir
            )
        return self._v1_generator

    def _get_v3_generator(self):
        """Get or create v3 generator and judge."""
        if self._v3_generator is None:
            from ycb.pipeline import VideoGeneratorV3, V3GenerationConfig
            from ycb.composition import OutputQuality

            config = V3GenerationConfig(
                output_dir=self.output_dir,
                output_quality=OutputQuality.FULL_HD,
                target_duration=90.0,  # 1.5 minutes default
            )
            self._v3_generator = VideoGeneratorV3(config)

        if self._v3_judge is None:
            from ycb.evaluation import VideoQualityJudgeV3
            self._v3_judge = VideoQualityJudgeV3(
                target_score=self.target_score
            )

        return self._v3_generator, self._v3_judge

    async def process_topic_v1(self, item: TopicQueueItem) -> QualityIterationResult:
        """Process a single topic using v1 pipeline."""
        generator = self._get_v1_generator()
        return await generator.generate_with_quality_gate(
            topic=item.topic,
            style=item.style,
            assemble_video=self.assemble_video
        )

    async def process_topic_v3(self, item: TopicQueueItem) -> V3IterationResult:
        """Process a single topic using v3 pipeline with quality iteration."""
        generator, judge = self._get_v3_generator()

        result = V3IterationResult(
            topic=item.topic,
            final_score=0.0,
            passed=False,
            iterations_used=0,
            max_iterations=self.max_iterations
        )

        for iteration in range(1, self.max_iterations + 1):
            result.iterations_used = iteration

            print(f"\n{'='*60}")
            print(f"[v3 Iteration {iteration}/{self.max_iterations}] Generating: {item.topic}")
            print(f"{'='*60}")

            # Step 1: Generate video with v3 pipeline
            try:
                gen_result = await generator.generate_async(
                    script=f"Generate an educational video about: {item.topic}",
                    title=item.topic,
                    description=f"Learn about {item.topic} in industrial automation.",
                )

                if not gen_result.success:
                    print(f"    [!] Generation failed")
                    result.iteration_history.append({
                        "iteration": iteration,
                        "score": 0.0,
                        "passed": False,
                        "rejections": ["Generation failed"]
                    })
                    continue

                result.render_time = gen_result.render_time
                result.scene_count = gen_result.scene_count
                result.scenes_rendered = gen_result.scenes_rendered
                result.scenes_failed = gen_result.scenes_failed

                print(f"    Duration: {gen_result.duration:.1f}s")
                print(f"    Scenes: {gen_result.scenes_rendered}/{gen_result.scene_count}")
                print(f"    Render time: {gen_result.render_time:.1f}s")

            except Exception as e:
                print(f"    [!] Generation error: {e}")
                result.iteration_history.append({
                    "iteration": iteration,
                    "score": 0.0,
                    "passed": False,
                    "rejections": [f"Error: {str(e)}"]
                })
                continue

            # Step 2: Evaluate with v3 judge
            print(f"\n[v3 Iteration {iteration}] Evaluating quality...")

            try:
                video_data = {
                    "script": f"Video about {item.topic}",
                    "title": item.topic,
                    "description": f"Educational video about {item.topic}",
                    "tags": ["industrial", "automation", item.topic.lower()],
                    "duration": gen_result.duration,
                    "storyboard": {
                        "scene_count": gen_result.scene_count,
                        "scenes": gen_result.storyboard.to_dict()["scenes"] if gen_result.storyboard else [],
                        "total_duration": gen_result.duration,
                    },
                    "render_info": {
                        "scenes_rendered": gen_result.scenes_rendered,
                        "scenes_failed": gen_result.scenes_failed,
                        "render_time": gen_result.render_time,
                        "primary_engine": "Manim",
                    },
                }

                evaluation = judge.evaluate_sync(video_data)

                print(f"    Score: {evaluation.score:.1f}/10 (target: {self.target_score})")
                print(f"    Visual: {evaluation.visual_quality}/10 | Diagram: {evaluation.diagram_quality}/10")
                print(f"    Script: {evaluation.script_quality}/10 | Audio: {evaluation.audio_sync}/10")
                print(f"    Status: {'PASSED' if evaluation.passed else 'FAILED'}")

                result.final_score = evaluation.score

            except Exception as e:
                print(f"    [!] Evaluation error: {e}")
                evaluation = None
                result.iteration_history.append({
                    "iteration": iteration,
                    "score": 5.0,
                    "passed": False,
                    "rejections": [f"Evaluation error: {str(e)}"]
                })
                continue

            # Record iteration
            result.iteration_history.append({
                "iteration": iteration,
                "score": evaluation.score,
                "passed": evaluation.passed,
                "rejections": evaluation.rejections,
                "visual_quality": evaluation.visual_quality,
                "diagram_quality": evaluation.diagram_quality,
            })

            # Step 3: Check if passed
            if evaluation.passed:
                print(f"\n[+] v3 Video PASSED quality gate at iteration {iteration}!")
                result.passed = True
                result.video = {
                    "topic": item.topic,
                    "video_path": gen_result.video_path,
                    "duration": gen_result.duration,
                    "render_time": gen_result.render_time,
                    "scene_count": gen_result.scene_count,
                    "quality_evaluation": evaluation.to_dict(),
                }
                break

            # For v3, we don't have iterative script regeneration yet
            # Future improvement: use feedback to adjust storyboard
            if iteration < self.max_iterations:
                print(f"\n[*] Retrying with fresh generation...")

        if not result.passed:
            print(f"\n[!] Max iterations reached. Best score: {result.final_score:.1f}/10")

        return result

    async def process_topic(self, item: TopicQueueItem) -> Union[QualityIterationResult, V3IterationResult]:
        """Process a single topic from the queue."""
        print(f"\n[*] Processing: {item.topic}")
        print(f"    Style: {item.style}")
        print(f"    Attempt: {item.attempts}")
        print(f"    Pipeline: {'v3' if self.use_v3 else 'v1'}")

        self.queue.mark_processing(item.topic)

        try:
            if self.use_v3:
                # Check if v3 is available, fallback to v1 if not
                if not self._check_v3_available():
                    print(f"    [!] v3 not available, falling back to v1")
                    result = await self.process_topic_v1(item)
                else:
                    result = await self.process_topic_v3(item)
            else:
                result = await self.process_topic_v1(item)

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
        print(f"Pipeline: {'v3 (Manim/Blender)' if self.use_v3 else 'v1 (Basic)'}")
        print(f"Target Score: {self.target_score}/10")
        print(f"{'='*60}")

        queue_stats = self.queue.stats()
        print(f"Queue: {queue_stats['pending']} pending, {queue_stats['completed']} completed, {queue_stats['failed']} failed")

        results = {
            "started_at": datetime.now().isoformat(),
            "pipeline_version": "v3" if self.use_v3 else "v1",
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

                video_info = {
                    "topic": item.topic,
                    "passed": result.passed,
                    "score": result.final_score,
                    "iterations": result.iterations_used
                }

                # Add v3-specific info
                if isinstance(result, V3IterationResult):
                    video_info["render_time"] = result.render_time
                    video_info["scene_count"] = result.scene_count
                    video_info["scenes_rendered"] = result.scenes_rendered

                results["videos"].append(video_info)

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
        print(f"Pipeline: {results['pipeline_version']}")
        print(f"Processed: {results['processed']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")

        # Print v3-specific metrics
        if self.use_v3 and results["videos"]:
            total_render = sum(v.get("render_time", 0) for v in results["videos"])
            total_scenes = sum(v.get("scene_count", 0) for v in results["videos"])
            print(f"\nv3 Metrics:")
            print(f"  Total render time: {total_render:.1f}s")
            print(f"  Total scenes: {total_scenes}")

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
        print(f"    Pipeline: {'v3' if self.use_v3 else 'v1'}")
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

    def get_engine_status(self) -> Dict[str, bool]:
        """Get availability status of rendering engines."""
        status = {"v1": True}  # v1 always available

        if self._check_v3_available():
            status["v3"] = True
            try:
                gen, _ = self._get_v3_generator()
                status.update(gen.get_engine_status())
            except Exception:
                pass
        else:
            status["v3"] = False

        return status


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
    parser.add_argument("--target-score", type=float, default=8.0, help="Target quality score (v3 default: 8.5)")
    parser.add_argument("--add-topic", type=str, help="Add a topic to queue")
    parser.add_argument("--add-defaults", action="store_true", help="Add default industrial topics")
    parser.add_argument("--show-queue", action="store_true", help="Show queue status")
    parser.add_argument("--show-metrics", action="store_true", help="Show metrics summary")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed topics")
    parser.add_argument("--clear-completed", action="store_true", help="Clear completed topics")
    parser.add_argument("--no-assemble", action="store_true", help="Skip video assembly")
    # v3 options
    parser.add_argument("--v3", action="store_true", help="Use v3 pipeline (Manim/Blender rendering)")
    parser.add_argument("--check-engines", action="store_true", help="Check available rendering engines")

    args = parser.parse_args()

    # Determine target score based on pipeline version
    target_score = args.target_score
    if args.v3 and target_score < 8.5:
        target_score = 8.5

    loop = AutonomousLoop(
        max_iterations=args.max_iterations,
        target_score=target_score,
        max_videos_per_run=args.max_videos,
        assemble_video=not args.no_assemble,
        use_v3=args.v3
    )

    # Check engines
    if args.check_engines:
        print("\nRendering Engine Status:")
        status = loop.get_engine_status()
        for engine, available in status.items():
            icon = "[+]" if available else "[-]"
            print(f"  {icon} {engine}: {'available' if available else 'not available'}")
        return

    # Handle queue operations
    if args.add_topic:
        pipeline_version = "v3" if args.v3 else "v1"
        item = loop.queue.add(args.add_topic, pipeline_version=pipeline_version)
        print(f"[+] Added to queue: {args.add_topic} (pipeline: {pipeline_version})")
        return

    if args.add_defaults:
        pipeline_version = "v3" if args.v3 else "v1"
        loop.queue.add_batch(DEFAULT_TOPICS, pipeline_version=pipeline_version)
        print(f"[+] Added {len(DEFAULT_TOPICS)} default topics to queue (pipeline: {pipeline_version})")
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
            print(f"  - {item.topic} (priority: {item.priority}, pipeline: {item.pipeline_version})")
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
