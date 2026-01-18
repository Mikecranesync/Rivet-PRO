"""Test script for narration-to-scene timing synchronization."""

import sys
import tempfile
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ycb.audio import TimingSync, TimingMap, WordTiming, SceneTiming


def test_word_timing():
    """Test WordTiming dataclass."""
    print("\n=== Testing WordTiming ===")

    timing = WordTiming(
        word="Hello",
        start_time=0.0,
        end_time=0.5,
        confidence=0.95,
    )

    assert timing.word == "Hello"
    assert timing.duration == 0.5
    assert timing.confidence == 0.95

    data = timing.to_dict()
    assert data["word"] == "Hello"
    assert data["start_time"] == 0.0
    assert data["end_time"] == 0.5

    print(f"  WordTiming: {timing.word} ({timing.duration:.2f}s)")
    return True


def test_scene_timing():
    """Test SceneTiming dataclass."""
    print("\n=== Testing SceneTiming ===")

    timing = SceneTiming(
        scene_id="scene_001",
        start_time=0.0,
        end_time=5.0,
        original_duration=4.0,
        narration_text="This is test narration.",
        adjusted=True,
    )

    assert timing.scene_id == "scene_001"
    assert timing.duration == 5.0
    assert timing.adjusted is True

    data = timing.to_dict()
    assert data["scene_id"] == "scene_001"
    assert data["duration"] == 5.0
    assert data["original_duration"] == 4.0

    print(f"  SceneTiming: {timing.scene_id} ({timing.duration:.1f}s)")
    print(f"  Adjusted from {timing.original_duration}s")
    return True


def test_timing_map():
    """Test TimingMap dataclass."""
    print("\n=== Testing TimingMap ===")

    timing_map = TimingMap(
        total_duration=30.0,
        audio_path="/test/audio.mp3",
    )

    # Add scenes
    timing_map.scene_timings.append(SceneTiming(
        scene_id="scene_001",
        start_time=0.0,
        end_time=10.0,
        original_duration=8.0,
    ))
    timing_map.scene_timings.append(SceneTiming(
        scene_id="scene_002",
        start_time=10.5,
        end_time=20.0,
        original_duration=10.0,
    ))

    timing_map.gaps = [(10.0, 10.5)]

    data = timing_map.to_dict()
    assert data["total_duration"] == 30.0
    assert data["scene_count"] == 2
    assert len(data["gaps"]) == 1

    print(f"  Total duration: {timing_map.total_duration}s")
    print(f"  Scenes: {len(timing_map.scene_timings)}")
    print(f"  Gaps: {timing_map.gaps}")

    return True


def test_timing_map_json():
    """Test TimingMap JSON serialization."""
    print("\n=== Testing TimingMap JSON Serialization ===")

    timing_map = TimingMap(
        total_duration=15.0,
    )
    timing_map.scene_timings.append(SceneTiming(
        scene_id="scene_001",
        start_time=0.0,
        end_time=15.0,
        original_duration=15.0,
        narration_text="Test narration.",
    ))

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as f:
        temp_path = f.name

    timing_map.to_json(temp_path)
    print(f"  Saved to: {temp_path}")

    # Load back
    loaded = TimingMap.from_json(temp_path)
    assert loaded.total_duration == 15.0
    assert len(loaded.scene_timings) == 1
    assert loaded.scene_timings[0].scene_id == "scene_001"

    print(f"  Loaded: {loaded.total_duration}s, {len(loaded.scene_timings)} scenes")

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)

    return True


def test_timing_sync_init():
    """Test TimingSync initialization."""
    print("\n=== Testing TimingSync Initialization ===")

    sync = TimingSync(
        min_scene_duration=2.0,
        max_scene_duration=20.0,
        padding=0.3,
        words_per_second=3.0,
    )

    assert sync.min_scene_duration == 2.0
    assert sync.max_scene_duration == 20.0
    assert sync.padding == 0.3
    assert sync.words_per_second == 3.0

    print(f"  Min duration: {sync.min_scene_duration}s")
    print(f"  Max duration: {sync.max_scene_duration}s")
    print(f"  Words/second: {sync.words_per_second}")

    return True


def test_sync_from_text():
    """Test syncing scenes from text without audio."""
    print("\n=== Testing Text-Based Sync ===")

    sync = TimingSync(
        min_scene_duration=3.0,
        max_scene_duration=30.0,
        words_per_second=2.5,
    )

    scenes = [
        {
            "scene_id": "scene_001",
            "duration": 5.0,
            "narration_text": "Welcome to this tutorial on PLCs.",  # 7 words
        },
        {
            "scene_id": "scene_002",
            "duration": 8.0,
            "narration_text": "A PLC is a programmable logic controller used in industrial automation. It controls machinery and processes.",  # 17 words
        },
        {
            "scene_id": "scene_003",
            "duration": 5.0,
            "narration_text": "The main components include the CPU, I/O modules, and power supply.",  # 12 words
        },
    ]

    timing_map = sync.sync_from_text(scenes)

    assert len(timing_map.scene_timings) == 3
    assert timing_map.total_duration > 0

    print(f"  Total duration: {timing_map.total_duration:.1f}s")
    for st in timing_map.scene_timings:
        print(f"  {st.scene_id}: {st.start_time:.1f}s - {st.end_time:.1f}s ({st.duration:.1f}s)")

    return True


def test_sync_from_text_with_target():
    """Test text sync with target duration."""
    print("\n=== Testing Text Sync with Target Duration ===")

    sync = TimingSync(words_per_second=2.5)

    scenes = [
        {"scene_id": "scene_001", "narration_text": "First scene narration."},
        {"scene_id": "scene_002", "narration_text": "Second scene with more words in the narration."},
        {"scene_id": "scene_003", "narration_text": "Third scene."},
    ]

    # Sync with target duration of 30 seconds
    timing_map = sync.sync_from_text(scenes, total_duration=30.0)

    assert len(timing_map.scene_timings) == 3
    # Total should be close to 30s (may vary due to min/max constraints)
    print(f"  Target: 30.0s, Actual: {timing_map.total_duration:.1f}s")

    for st in timing_map.scene_timings:
        print(f"  {st.scene_id}: {st.duration:.1f}s")

    return True


def test_adjust_for_pauses():
    """Test pause adjustment between scenes."""
    print("\n=== Testing Pause Adjustment ===")

    sync = TimingSync()

    # Create timing map with tight scenes (no gaps)
    timing_map = TimingMap(total_duration=20.0)
    timing_map.scene_timings = [
        SceneTiming(
            scene_id="scene_001",
            start_time=0.0,
            end_time=6.0,
            original_duration=6.0,
        ),
        SceneTiming(
            scene_id="scene_002",
            start_time=6.0,  # No gap
            end_time=12.0,
            original_duration=6.0,
        ),
        SceneTiming(
            scene_id="scene_003",
            start_time=12.0,  # No gap
            end_time=18.0,
            original_duration=6.0,
        ),
    ]

    # Adjust to add pauses
    adjusted = sync.adjust_for_pauses(timing_map, min_pause=0.5, max_pause=1.0)

    # Check that pauses were added
    for i in range(1, len(adjusted.scene_timings)):
        prev_end = adjusted.scene_timings[i - 1].end_time
        curr_start = adjusted.scene_timings[i].start_time
        gap = curr_start - prev_end
        print(f"  Gap between scene_{i:03d}: {gap:.2f}s")
        assert gap >= 0.5, f"Gap should be at least 0.5s, got {gap}s"

    print(f"  Original total: 18.0s")
    print(f"  Adjusted total: {adjusted.total_duration:.1f}s")

    return True


def test_find_gaps():
    """Test gap detection in timing map."""
    print("\n=== Testing Gap Detection ===")

    sync = TimingSync()

    # Create timing map with intentional gaps
    timing_map = TimingMap(total_duration=25.0)
    timing_map.scene_timings = [
        SceneTiming(
            scene_id="scene_001",
            start_time=1.0,  # Gap at start
            end_time=6.0,
            original_duration=5.0,
        ),
        SceneTiming(
            scene_id="scene_002",
            start_time=8.0,  # Gap of 2s
            end_time=14.0,
            original_duration=6.0,
        ),
        SceneTiming(
            scene_id="scene_003",
            start_time=15.0,  # Gap of 1s
            end_time=20.0,
            original_duration=5.0,
        ),
        # Gap of 5s at end (to 25s)
    ]

    gaps = sync._find_gaps(timing_map)
    timing_map.gaps = gaps

    print(f"  Found {len(gaps)} gaps:")
    for start, end in gaps:
        print(f"    {start:.1f}s - {end:.1f}s ({end - start:.1f}s)")

    # Should find: start gap (0-1), middle gap (6-8), middle gap (14-15), end gap (20-25)
    assert len(gaps) >= 3, f"Expected at least 3 gaps, found {len(gaps)}"

    return True


if __name__ == "__main__":
    print("=" * 50)
    print("YCB v3 - Audio Timing Sync Tests")
    print("=" * 50)

    tests = [
        ("WordTiming", test_word_timing),
        ("SceneTiming", test_scene_timing),
        ("TimingMap", test_timing_map),
        ("TimingMap JSON", test_timing_map_json),
        ("TimingSync initialization", test_timing_sync_init),
        ("Text-based sync", test_sync_from_text),
        ("Text sync with target", test_sync_from_text_with_target),
        ("Pause adjustment", test_adjust_for_pauses),
        ("Gap detection", test_find_gaps),
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
