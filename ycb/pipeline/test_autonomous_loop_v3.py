"""Test script for YCB v3 autonomous loop updates."""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ycb.pipeline.autonomous_loop import (
    TopicQueue,
    TopicQueueItem,
    AutonomousLoop,
    V3IterationResult,
    DEFAULT_TOPICS,
)


def test_topic_queue_item_v1():
    """Test TopicQueueItem with v1 pipeline (default)."""
    print("\n=== Testing TopicQueueItem (v1) ===")

    item = TopicQueueItem(topic="PLC Basics")

    assert item.topic == "PLC Basics"
    assert item.pipeline_version == "v1"  # Default
    assert item.status == "pending"

    data = item.to_dict()
    assert data["pipeline_version"] == "v1"

    print(f"  Topic: {item.topic}")
    print(f"  Pipeline: {item.pipeline_version}")

    return True


def test_topic_queue_item_v3():
    """Test TopicQueueItem with v3 pipeline."""
    print("\n=== Testing TopicQueueItem (v3) ===")

    item = TopicQueueItem(topic="Motor Control", pipeline_version="v3")

    assert item.topic == "Motor Control"
    assert item.pipeline_version == "v3"

    print(f"  Topic: {item.topic}")
    print(f"  Pipeline: {item.pipeline_version}")

    return True


def test_topic_queue_add_with_version():
    """Test TopicQueue.add with pipeline version."""
    print("\n=== Testing TopicQueue.add with version ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_file = Path(tmpdir) / "queue.json"
        queue = TopicQueue(str(queue_file))

        # Add v1 topic
        item1 = queue.add("Topic A", pipeline_version="v1")
        assert item1.pipeline_version == "v1"

        # Add v3 topic
        item2 = queue.add("Topic B", pipeline_version="v3")
        assert item2.pipeline_version == "v3"

        # Verify persistence
        assert queue_file.exists()
        with open(queue_file) as f:
            data = json.load(f)
        assert len(data) == 2
        assert data[0]["pipeline_version"] == "v1"
        assert data[1]["pipeline_version"] == "v3"

        print(f"  Added 2 topics with different versions")
        print(f"  Queue file: {queue_file}")

    return True


def test_topic_queue_add_batch_v3():
    """Test TopicQueue.add_batch with v3 pipeline."""
    print("\n=== Testing TopicQueue.add_batch (v3) ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_file = Path(tmpdir) / "queue.json"
        queue = TopicQueue(str(queue_file))

        topics = ["Topic 1", "Topic 2", "Topic 3"]
        queue.add_batch(topics, pipeline_version="v3")

        assert len(queue.items) == 3
        for item in queue.items:
            assert item.pipeline_version == "v3"

        print(f"  Added {len(topics)} v3 topics")

    return True


def test_v3_iteration_result():
    """Test V3IterationResult dataclass."""
    print("\n=== Testing V3IterationResult ===")

    result = V3IterationResult(
        topic="PLC Basics",
        final_score=8.7,
        passed=True,
        iterations_used=2,
        max_iterations=4,
        render_time=45.2,
        scene_count=8,
        scenes_rendered=7,
        scenes_failed=1,
    )

    assert result.topic == "PLC Basics"
    assert result.passed is True
    assert result.render_time == 45.2
    assert result.scene_count == 8

    data = result.to_dict()
    assert "render_time" in data
    assert "scene_count" in data
    assert "scenes_rendered" in data

    print(f"  Topic: {result.topic}")
    print(f"  Score: {result.final_score}/10")
    print(f"  Render time: {result.render_time}s")
    print(f"  Scenes: {result.scenes_rendered}/{result.scene_count}")

    return True


def test_autonomous_loop_v3_init():
    """Test AutonomousLoop initialization with v3 flag."""
    print("\n=== Testing AutonomousLoop (v3 init) ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        loop = AutonomousLoop(
            output_dir=tmpdir,
            use_v3=True,
            target_score=7.0  # Will be adjusted to 8.5
        )

        assert loop.use_v3 is True
        assert loop.target_score == 8.5  # Auto-adjusted for v3

        print(f"  use_v3: {loop.use_v3}")
        print(f"  target_score: {loop.target_score} (auto-adjusted)")

    return True


def test_autonomous_loop_v1_init():
    """Test AutonomousLoop initialization with v1 (default)."""
    print("\n=== Testing AutonomousLoop (v1 init) ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        loop = AutonomousLoop(
            output_dir=tmpdir,
            use_v3=False,
            target_score=8.0
        )

        assert loop.use_v3 is False
        assert loop.target_score == 8.0  # Not adjusted

        print(f"  use_v3: {loop.use_v3}")
        print(f"  target_score: {loop.target_score}")

    return True


def test_get_engine_status():
    """Test engine status reporting."""
    print("\n=== Testing Engine Status ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        loop = AutonomousLoop(output_dir=tmpdir, use_v3=False)
        status = loop.get_engine_status()

        assert "v1" in status
        assert status["v1"] is True  # v1 always available

        print(f"  Engine status: {status}")

    return True


def test_default_topics_count():
    """Test default topics list."""
    print("\n=== Testing Default Topics ===")

    assert len(DEFAULT_TOPICS) == 10

    for topic in DEFAULT_TOPICS:
        assert isinstance(topic, str)
        assert len(topic) > 0

    print(f"  Default topics: {len(DEFAULT_TOPICS)}")
    print(f"  First: {DEFAULT_TOPICS[0]}")
    print(f"  Last: {DEFAULT_TOPICS[-1]}")

    return True


def test_v3_iteration_result_serialization():
    """Test V3IterationResult JSON serialization."""
    print("\n=== Testing V3IterationResult Serialization ===")

    result = V3IterationResult(
        topic="Test Topic",
        final_score=8.5,
        passed=True,
        iterations_used=1,
        max_iterations=4,
        video={"path": "/output/video.mp4"},
        iteration_history=[
            {"iteration": 1, "score": 8.5, "passed": True}
        ],
        render_time=30.0,
        scene_count=5,
        scenes_rendered=5,
        scenes_failed=0,
    )

    data = result.to_dict()

    # Test JSON serialization
    json_str = json.dumps(data)
    parsed = json.loads(json_str)

    assert parsed["topic"] == "Test Topic"
    assert parsed["render_time"] == 30.0
    assert parsed["scene_count"] == 5

    print(f"  Serializable: YES")
    print(f"  JSON length: {len(json_str)} chars")

    return True


def test_lazy_generator_loading():
    """Test lazy loading of generators."""
    print("\n=== Testing Lazy Generator Loading ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        loop = AutonomousLoop(output_dir=tmpdir, use_v3=False)

        # Generators should not be loaded yet
        assert loop._v1_generator is None
        assert loop._v3_generator is None
        assert loop._v3_judge is None

        print("  v1_generator: not loaded (lazy)")
        print("  v3_generator: not loaded (lazy)")
        print("  v3_judge: not loaded (lazy)")

    return True


def test_queue_stats_structure():
    """Test queue stats dictionary structure."""
    print("\n=== Testing Queue Stats Structure ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_file = Path(tmpdir) / "queue.json"
        queue = TopicQueue(str(queue_file))

        stats = queue.stats()

        required_keys = ["total", "pending", "processing", "completed", "failed"]
        for key in required_keys:
            assert key in stats

        print(f"  Stats keys: {list(stats.keys())}")

    return True


if __name__ == "__main__":
    print("=" * 50)
    print("YCB v3 - Autonomous Loop Tests")
    print("=" * 50)

    tests = [
        ("TopicQueueItem (v1)", test_topic_queue_item_v1),
        ("TopicQueueItem (v3)", test_topic_queue_item_v3),
        ("TopicQueue.add with version", test_topic_queue_add_with_version),
        ("TopicQueue.add_batch (v3)", test_topic_queue_add_batch_v3),
        ("V3IterationResult", test_v3_iteration_result),
        ("AutonomousLoop v3 init", test_autonomous_loop_v3_init),
        ("AutonomousLoop v1 init", test_autonomous_loop_v1_init),
        ("Engine status", test_get_engine_status),
        ("Default topics", test_default_topics_count),
        ("V3IterationResult serialization", test_v3_iteration_result_serialization),
        ("Lazy generator loading", test_lazy_generator_loading),
        ("Queue stats structure", test_queue_stats_structure),
    ]

    results = {}
    for name, test_func in tests:
        try:
            success = test_func()
            results[name] = success
        except Exception as e:
            print(f"\n!!! Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
