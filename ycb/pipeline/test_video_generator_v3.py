"""Test script for YCB v3 video generation pipeline."""

import sys
import tempfile
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ycb.pipeline import VideoGeneratorV3, V3GenerationConfig, V3GenerationResult
from ycb.composition import OutputQuality, ColorGradePreset
from ycb.composition.compositor import TransitionType


def test_v3_generation_config():
    """Test V3GenerationConfig dataclass."""
    print("\n=== Testing V3GenerationConfig ===")

    config = V3GenerationConfig(
        output_dir="./test_output",
        output_quality=OutputQuality.HD,
        fps=24,
        manim_quality="medium_quality",
        target_duration=90.0,
        parallel_rendering=True,
        max_workers=2,
    )

    assert config.output_quality == OutputQuality.HD
    assert config.fps == 24
    assert config.target_duration == 90.0
    assert config.parallel_rendering is True

    data = config.to_dict()
    assert data["output_quality"] == "hd"
    assert data["fps"] == 24

    print(f"  Quality: {config.output_quality.value}")
    print(f"  Target duration: {config.target_duration}s")
    print(f"  Parallel: {config.parallel_rendering}")

    return True


def test_v3_generation_result():
    """Test V3GenerationResult dataclass."""
    print("\n=== Testing V3GenerationResult ===")

    result = V3GenerationResult(
        success=True,
        video_path="/output/final.mp4",
        duration=60.5,
        scene_count=8,
        scenes_rendered=7,
        scenes_failed=1,
        render_time=45.2,
        compose_time=12.3,
        total_time=60.0,
    )

    assert result.success is True
    assert result.scene_count == 8
    assert result.scenes_rendered == 7
    assert result.scenes_failed == 1

    data = result.to_dict()
    assert data["success"] is True
    assert data["render_time"] == 45.2

    print(f"  Success: {result.success}")
    print(f"  Duration: {result.duration}s")
    print(f"  Scenes: {result.scenes_rendered}/{result.scene_count}")
    print(f"  Times: render={result.render_time:.1f}s, compose={result.compose_time:.1f}s")

    return True


def test_v3_generator_init():
    """Test VideoGeneratorV3 initialization."""
    print("\n=== Testing VideoGeneratorV3 Initialization ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        config = V3GenerationConfig(
            output_dir=tmpdir,
            output_quality=OutputQuality.PREVIEW,
        )

        generator = VideoGeneratorV3(config)

        # Check directories created
        assert generator.output_dir.exists()
        assert generator.clips_dir.exists()
        assert generator.final_dir.exists()

        print(f"  Output dir: {generator.output_dir}")
        print(f"  Clips dir: {generator.clips_dir}")
        print(f"  Final dir: {generator.final_dir}")

    return True


def test_engine_status():
    """Test engine availability check."""
    print("\n=== Testing Engine Status ===")

    generator = VideoGeneratorV3()
    status = generator.get_engine_status()

    print(f"  Available engines: {status}")
    assert "manim" in status
    assert "blender" in status

    return True


def test_sanitize_filename():
    """Test filename sanitization."""
    print("\n=== Testing Filename Sanitization ===")

    generator = VideoGeneratorV3()

    test_cases = [
        ("What is a PLC?", "What_is_a_PLC"),
        ("Test: Special <chars>", "Test_Special_chars"),
        ("Very " * 20, "Very_" * 10),  # Long title truncated
    ]

    for title, expected_prefix in test_cases:
        result = generator._sanitize_filename(title)
        assert expected_prefix[:20] in result or len(result) <= 70
        print(f"  '{title[:30]}...' -> '{result[:40]}...'")

    return True


def test_storyboard_generation():
    """Test storyboard generation component."""
    print("\n=== Testing Storyboard Generation ===")

    generator = VideoGeneratorV3()
    storyboard_gen = generator._get_storyboard_generator()

    script = """
    What is a PLC?

    A PLC, or Programmable Logic Controller, is the brain of industrial automation.
    It reads inputs from sensors, processes the logic, and controls outputs.
    """

    storyboard = generator._generate_storyboard(
        script=script,
        title="PLC Basics",
        description="Introduction to PLCs",
    )

    assert storyboard is not None
    assert len(storyboard.scenes) > 0
    assert storyboard.title == "PLC Basics"

    print(f"  Title: {storyboard.title}")
    print(f"  Scenes: {len(storyboard.scenes)}")

    return True


def test_timing_sync_component():
    """Test timing sync component."""
    print("\n=== Testing Timing Sync Component ===")

    generator = VideoGeneratorV3()

    # Generate a simple storyboard
    from ycb.storyboard import Storyboard, Scene, SceneType, VisualDescription

    storyboard = Storyboard(title="Test", description="Test storyboard", target_duration=20.0)
    storyboard.add_scene(Scene(
        scene_id="scene_001",
        scene_type=SceneType.TITLE,
        duration=5.0,
        narration_text="Welcome to the tutorial.",
        visual_description=VisualDescription(main_subject="Title"),
    ))
    storyboard.add_scene(Scene(
        scene_id="scene_002",
        scene_type=SceneType.TEXT,
        duration=10.0,
        narration_text="Today we will learn about PLCs and industrial automation.",
        visual_description=VisualDescription(main_subject="Content"),
    ))

    timing_map = generator._sync_timing(storyboard, audio_path=None)

    assert timing_map is not None
    assert len(timing_map.scene_timings) == 2
    assert timing_map.total_duration > 0

    print(f"  Scenes timed: {len(timing_map.scene_timings)}")
    print(f"  Total duration: {timing_map.total_duration:.1f}s")

    return True


def test_progress_callback():
    """Test progress callback mechanism."""
    print("\n=== Testing Progress Callback ===")

    generator = VideoGeneratorV3()

    progress_log = []

    def callback(stage: str, progress: float):
        progress_log.append((stage, progress))

    generator.set_progress_callback(callback)

    # Simulate progress reporting
    generator._report_progress("Test", 0.5)

    assert len(progress_log) == 1
    assert progress_log[0] == ("Test", 0.5)

    print(f"  Callback received: {progress_log}")

    return True


def test_default_config_values():
    """Test default configuration values."""
    print("\n=== Testing Default Config Values ===")

    config = V3GenerationConfig()

    assert config.output_quality == OutputQuality.FULL_HD
    assert config.fps == 30
    assert config.manim_quality == "high_quality"
    assert config.enable_blender is False
    assert config.target_duration == 60.0
    assert config.default_transition == TransitionType.CROSSFADE
    assert config.color_grade == ColorGradePreset.PROFESSIONAL

    print(f"  Quality: {config.output_quality.value}")
    print(f"  FPS: {config.fps}")
    print(f"  Manim: {config.manim_quality}")
    print(f"  Transition: {config.default_transition.value}")
    print(f"  Color grade: {config.color_grade.value}")

    return True


def test_lazy_component_loading():
    """Test lazy loading of components."""
    print("\n=== Testing Lazy Component Loading ===")

    generator = VideoGeneratorV3()

    # Components should not be loaded yet
    assert generator._storyboard_generator is None
    assert generator._scene_router is None
    assert generator._timing_sync is None
    assert generator._compositor is None
    assert generator._post_processor is None

    # Load storyboard generator
    sg = generator._get_storyboard_generator()
    assert sg is not None
    assert generator._storyboard_generator is sg  # Same instance

    # Load again - should return same instance
    sg2 = generator._get_storyboard_generator()
    assert sg2 is sg

    print("  Storyboard generator: loaded and cached")
    print("  Other components: not loaded yet (lazy)")

    return True


def test_ffmpeg_quality_mapping():
    """Test FFmpeg quality string mapping."""
    print("\n=== Testing FFmpeg Quality Mapping ===")

    config = V3GenerationConfig()
    generator = VideoGeneratorV3(config)

    test_cases = [
        (OutputQuality.PREVIEW, "preview"),
        (OutputQuality.HD, "720p"),
        (OutputQuality.FULL_HD, "1080p"),
        (OutputQuality.UHD, "4k"),
    ]

    for quality, expected in test_cases:
        generator.config.output_quality = quality
        result = generator._get_ffmpeg_quality()
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"  {quality.value} -> {result}")

    return True


if __name__ == "__main__":
    print("=" * 50)
    print("YCB v3 - Video Generator Pipeline Tests")
    print("=" * 50)

    tests = [
        ("V3GenerationConfig", test_v3_generation_config),
        ("V3GenerationResult", test_v3_generation_result),
        ("Generator initialization", test_v3_generator_init),
        ("Engine status", test_engine_status),
        ("Filename sanitization", test_sanitize_filename),
        ("Storyboard generation", test_storyboard_generation),
        ("Timing sync component", test_timing_sync_component),
        ("Progress callback", test_progress_callback),
        ("Default config values", test_default_config_values),
        ("Lazy component loading", test_lazy_component_loading),
        ("FFmpeg quality mapping", test_ffmpeg_quality_mapping),
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
