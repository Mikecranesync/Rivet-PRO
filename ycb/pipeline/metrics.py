"""
YCB Pipeline Metrics & Logging

Tracks video generation metrics, costs, and iteration history.
Persists to JSON file for analysis and monitoring.

Usage:
    from ycb.pipeline.metrics import PipelineMetrics

    metrics = PipelineMetrics()
    metrics.log_video_result(result)
    stats = metrics.get_stats()
"""

import json
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class VideoMetric:
    """Single video generation metric."""
    topic: str
    timestamp: str
    final_score: float
    passed: bool
    iterations_used: int
    cost_estimate: float
    iteration_scores: List[float] = field(default_factory=list)
    rejections_count: int = 0
    output_dir: Optional[str] = None
    video_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DailyStats:
    """Daily aggregated statistics."""
    date: str
    videos_attempted: int = 0
    videos_passed: int = 0
    videos_failed: int = 0
    total_iterations: int = 0
    total_cost: float = 0.0
    avg_score: float = 0.0
    avg_iterations: float = 0.0
    pass_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PipelineMetrics:
    """
    Metrics tracking and logging for video generation pipeline.

    Persists metrics to JSON files for analysis.
    """

    def __init__(self, metrics_dir: str = "./ycb_metrics"):
        """
        Initialize metrics tracker.

        Args:
            metrics_dir: Directory to store metrics files
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_file = self.metrics_dir / "video_metrics.json"
        self.daily_file = self.metrics_dir / "daily_stats.json"

        # Load existing metrics
        self.metrics: List[VideoMetric] = self._load_metrics()
        self.daily_stats: Dict[str, DailyStats] = self._load_daily_stats()

    def _load_metrics(self) -> List[VideoMetric]:
        """Load existing metrics from file."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file) as f:
                    data = json.load(f)
                    return [VideoMetric(**m) for m in data]
            except Exception:
                pass
        return []

    def _load_daily_stats(self) -> Dict[str, DailyStats]:
        """Load existing daily stats from file."""
        if self.daily_file.exists():
            try:
                with open(self.daily_file) as f:
                    data = json.load(f)
                    return {k: DailyStats(**v) for k, v in data.items()}
            except Exception:
                pass
        return {}

    def _save_metrics(self):
        """Save metrics to file."""
        with open(self.metrics_file, "w") as f:
            json.dump([m.to_dict() for m in self.metrics], f, indent=2)

    def _save_daily_stats(self):
        """Save daily stats to file."""
        with open(self.daily_file, "w") as f:
            json.dump({k: v.to_dict() for k, v in self.daily_stats.items()}, f, indent=2)

    def log_video_result(self, result: Any) -> VideoMetric:
        """
        Log a video generation result.

        Args:
            result: QualityIterationResult from the pipeline

        Returns:
            VideoMetric that was logged
        """
        # Extract iteration scores
        iteration_scores = [r.score for r in result.iteration_history]
        rejections_count = sum(len(r.rejections) for r in result.iteration_history)

        metric = VideoMetric(
            topic=result.topic,
            timestamp=datetime.now().isoformat(),
            final_score=result.final_score,
            passed=result.passed,
            iterations_used=result.iterations_used,
            cost_estimate=result.total_cost_estimate,
            iteration_scores=iteration_scores,
            rejections_count=rejections_count,
            output_dir=result.video.get("output_dir") if result.video else None,
            video_file=result.video.get("video_file") if result.video else None
        )

        self.metrics.append(metric)
        self._save_metrics()

        # Update daily stats
        self._update_daily_stats(metric)

        return metric

    def _update_daily_stats(self, metric: VideoMetric):
        """Update daily aggregated stats."""
        today = date.today().isoformat()

        if today not in self.daily_stats:
            self.daily_stats[today] = DailyStats(date=today)

        stats = self.daily_stats[today]
        stats.videos_attempted += 1
        stats.total_iterations += metric.iterations_used
        stats.total_cost += metric.cost_estimate

        if metric.passed:
            stats.videos_passed += 1
        else:
            stats.videos_failed += 1

        # Recalculate averages
        stats.pass_rate = stats.videos_passed / stats.videos_attempted * 100
        stats.avg_iterations = stats.total_iterations / stats.videos_attempted

        # Calculate average score from today's metrics
        today_metrics = [m for m in self.metrics if m.timestamp.startswith(today)]
        if today_metrics:
            stats.avg_score = sum(m.final_score for m in today_metrics) / len(today_metrics)

        self._save_daily_stats()

    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get aggregated statistics.

        Args:
            days: Number of days to include (default 7)

        Returns:
            Dictionary with stats
        """
        # Get recent metrics
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        recent = [m for m in self.metrics
                  if datetime.fromisoformat(m.timestamp).timestamp() > cutoff]

        if not recent:
            return {
                "period_days": days,
                "videos_total": 0,
                "videos_passed": 0,
                "videos_failed": 0,
                "pass_rate": 0.0,
                "avg_score": 0.0,
                "avg_iterations": 0.0,
                "total_cost": 0.0,
            }

        passed = sum(1 for m in recent if m.passed)
        total_iterations = sum(m.iterations_used for m in recent)
        total_cost = sum(m.cost_estimate for m in recent)

        return {
            "period_days": days,
            "videos_total": len(recent),
            "videos_passed": passed,
            "videos_failed": len(recent) - passed,
            "pass_rate": passed / len(recent) * 100,
            "avg_score": sum(m.final_score for m in recent) / len(recent),
            "avg_iterations": total_iterations / len(recent),
            "total_cost": total_cost,
            "cost_per_video": total_cost / len(recent),
        }

    def get_today_stats(self) -> Optional[DailyStats]:
        """Get today's stats."""
        today = date.today().isoformat()
        return self.daily_stats.get(today)

    def print_summary(self, days: int = 7):
        """Print a summary of recent metrics."""
        stats = self.get_stats(days)

        print(f"\n{'='*50}")
        print(f"YCB PIPELINE METRICS (Last {days} days)")
        print(f"{'='*50}")
        print(f"Videos Generated: {stats['videos_total']}")
        print(f"  - Passed: {stats['videos_passed']}")
        print(f"  - Failed: {stats['videos_failed']}")
        print(f"Pass Rate: {stats['pass_rate']:.1f}%")
        print(f"Average Score: {stats['avg_score']:.1f}/10")
        print(f"Average Iterations: {stats['avg_iterations']:.1f}")
        print(f"Total Cost: ${stats['total_cost']:.3f}")
        if stats['videos_total'] > 0:
            print(f"Cost per Video: ${stats['cost_per_video']:.3f}")
        print(f"{'='*50}")
