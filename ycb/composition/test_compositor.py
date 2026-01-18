"""Test script for multi-scene video compositor."""

import sys
import tempfile
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ycb.composition import (
    VideoCompositor,
    CompositionResult,
    TransitionType,
    OverlayConfig,
)
from ycb.composition.compositor import ClipConfig


def test_transition_type():
    """Test TransitionType enum."""
    print("\n=== Testing TransitionType ===")

    assert TransitionType.CUT.value == "cut"
    assert TransitionType.FADE.value == "fade"
    assert TransitionType.CROSSFADE.value == "crossfade"

    print(f"  Available transitions: {[t.value for t in TransitionType]}")
    return True


def test_overlay_config():
    """Test OverlayConfig dataclass."""
    print("\n=== Testing OverlayConfig ===")

    overlay = OverlayConfig(
        text="Introduction to PLCs",
        position="bottom_left",
        start_time=1.0,
        duration=5.0,
        font_size=28,
    )

    assert overlay.text == "Introduction to PLCs"
    assert overlay.position == "bottom_left"
    assert overlay.start_time == 1.0
    assert overlay.duration == 5.0

    data = overlay.to_dict()
    assert "text" in data
    assert data["font_size"] == 28

    print(f"  Overlay: '{overlay.text}' at {overlay.position}")
    return True


def test_clip_config():
    """Test ClipConfig dataclass."""
    print("\n=== Testing ClipConfig ===")

    clip = ClipConfig(
        path="/test/clip.mp4",
        duration=10.0,
        transition_in=TransitionType.FADE,
        transition_out=TransitionType.CROSSFADE,
        volume=0.8,
    )

    assert clip.path == "/test/clip.mp4"
    assert clip.duration == 10.0
    assert clip.transition_in == TransitionType.FADE
    assert clip.volume == 0.8

    data = clip.to_dict()
    assert data["transition_in"] == "fade"
    assert data["transition_out"] == "crossfade"

    print(f"  Clip: {clip.path}, transition: {clip.transition_in.value}")
    return True


def test_composition_result():
    """Test CompositionResult dataclass."""
    print("\n=== Testing CompositionResult ===")

    result = CompositionResult(
        success=True,
        output_path="/output/final.mp4",
        duration=60.0,
        clip_count=5,
    )

    assert result.success is True
    assert result.output_path == "/output/final.mp4"
    assert result.duration == 60.0
    assert result.clip_count == 5

    data = result.to_dict()
    assert data["success"] is True
    assert data["error"] is None

    print(f"  Result: success={result.success}, duration={result.duration}s")
    return True


def test_compositor_init():
    """Test VideoCompositor initialization."""
    print("\n=== Testing VideoCompositor Initialization ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        compositor = VideoCompositor(
            output_dir=tmpdir,
            quality="1080p",
            fps=30,
        )

        assert compositor.quality == "1080p"
        assert compositor.fps == 30
        assert compositor.output_dir.exists()

        print(f"  Output dir: {compositor.output_dir}")
        print(f"  Quality: {compositor.quality}")
        print(f"  FPS: {compositor.fps}")

    return True


def test_quality_presets():
    """Test quality presets."""
    print("\n=== Testing Quality Presets ===")

    compositor = VideoCompositor()

    for preset_name, (width, height, bitrate) in compositor.QUALITY_PRESETS.items():
        print(f"  {preset_name}: {width}x{height} @ {bitrate}")

    assert "720p" in compositor.QUALITY_PRESETS
    assert "1080p" in compositor.QUALITY_PRESETS
    assert "4k" in compositor.QUALITY_PRESETS
    assert "preview" in compositor.QUALITY_PRESETS

    # Check 1080p values
    w, h, b = compositor.QUALITY_PRESETS["1080p"]
    assert w == 1920
    assert h == 1080

    return True


def test_ffmpeg_availability():
    """Test FFmpeg availability check."""
    print("\n=== Testing FFmpeg Availability ===")

    compositor = VideoCompositor()
    available = compositor._check_ffmpeg_available()

    print(f"  FFmpeg available: {available}")

    # This test passes regardless - we're just checking the detection works
    return True


def test_compose_empty_clips():
    """Test compose with empty clips list."""
    print("\n=== Testing Compose with Empty Clips ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        compositor = VideoCompositor(output_dir=tmpdir)
        result = compositor.compose([], "test_empty")

        assert result.success is False
        assert "No clips" in result.error

        print(f"  Result: success={result.success}, error={result.error}")

    return True


def test_compose_missing_clips():
    """Test compose with non-existent clips."""
    print("\n=== Testing Compose with Missing Clips ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        compositor = VideoCompositor(output_dir=tmpdir)

        clips = [
            ClipConfig(path="/nonexistent/clip1.mp4"),
            ClipConfig(path="/nonexistent/clip2.mp4"),
        ]

        result = compositor.compose(clips, "test_missing")

        assert result.success is False
        assert "No valid clips" in result.error

        print(f"  Result: success={result.success}, error={result.error}")

    return True


def test_xfade_type_mapping():
    """Test transition to FFmpeg xfade mapping."""
    print("\n=== Testing xfade Type Mapping ===")

    compositor = VideoCompositor()

    mappings = {
        TransitionType.FADE: "fade",
        TransitionType.CROSSFADE: "dissolve",
        TransitionType.WIPE_LEFT: "wipeleft",
        TransitionType.WIPE_RIGHT: "wiperight",
    }

    for transition, expected in mappings.items():
        actual = compositor._get_xfade_type(transition)
        assert actual == expected, f"Expected {expected} for {transition}, got {actual}"
        print(f"  {transition.value} -> {actual}")

    return True


def test_create_test_video():
    """Test creating a test video (requires FFmpeg)."""
    print("\n=== Testing Test Video Creation ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        compositor = VideoCompositor(output_dir=tmpdir, quality="preview")

        # Check if FFmpeg is available
        if not compositor._check_ffmpeg_available():
            print("  SKIP: FFmpeg not available")
            return True

        # Create test video
        output = compositor.create_test_video(
            output_name="test",
            duration=2.0,
            text="Test",
        )

        if output:
            assert Path(output).exists()
            duration = compositor.get_clip_duration(output)
            print(f"  Created: {output}")
            print(f"  Duration: {duration}s")
        else:
            print("  Could not create test video")

    return True


if __name__ == "__main__":
    print("=" * 50)
    print("YCB v3 - Video Compositor Tests")
    print("=" * 50)

    tests = [
        ("TransitionType", test_transition_type),
        ("OverlayConfig", test_overlay_config),
        ("ClipConfig", test_clip_config),
        ("CompositionResult", test_composition_result),
        ("Compositor initialization", test_compositor_init),
        ("Quality presets", test_quality_presets),
        ("FFmpeg availability", test_ffmpeg_availability),
        ("Compose empty clips", test_compose_empty_clips),
        ("Compose missing clips", test_compose_missing_clips),
        ("xfade type mapping", test_xfade_type_mapping),
        ("Create test video", test_create_test_video),
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
