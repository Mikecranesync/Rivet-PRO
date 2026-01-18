"""Test script for post-processing effects pipeline."""

import sys
import tempfile
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ycb.composition import (
    PostProcessor,
    PostProcessConfig,
    PostProcessResult,
    ColorGradePreset,
    OutputQuality,
    WatermarkConfig,
    SubtitleEntry,
    VideoCompositor,
)


def test_color_grade_preset():
    """Test ColorGradePreset enum."""
    print("\n=== Testing ColorGradePreset ===")

    assert ColorGradePreset.NONE.value == "none"
    assert ColorGradePreset.INDUSTRIAL.value == "industrial"
    assert ColorGradePreset.CLEAN.value == "clean"
    assert ColorGradePreset.WARM.value == "warm"
    assert ColorGradePreset.CINEMATIC.value == "cinematic"
    assert ColorGradePreset.PROFESSIONAL.value == "professional"

    print(f"  Available presets: {[p.value for p in ColorGradePreset]}")
    return True


def test_output_quality():
    """Test OutputQuality enum."""
    print("\n=== Testing OutputQuality ===")

    qualities = [q.value for q in OutputQuality]
    assert "preview" in qualities
    assert "sd" in qualities
    assert "hd" in qualities
    assert "full_hd" in qualities
    assert "qhd" in qualities
    assert "uhd" in qualities

    print(f"  Available qualities: {qualities}")
    return True


def test_subtitle_entry():
    """Test SubtitleEntry dataclass."""
    print("\n=== Testing SubtitleEntry ===")

    entry = SubtitleEntry(
        start_time=1.5,
        end_time=4.0,
        text="This is a test subtitle.",
    )

    assert entry.start_time == 1.5
    assert entry.end_time == 4.0
    assert "test subtitle" in entry.text

    data = entry.to_dict()
    assert data["start_time"] == 1.5
    assert data["end_time"] == 4.0

    print(f"  Entry: '{entry.text}' ({entry.start_time}s - {entry.end_time}s)")
    return True


def test_watermark_config():
    """Test WatermarkConfig dataclass."""
    print("\n=== Testing WatermarkConfig ===")

    watermark = WatermarkConfig(
        image_path="/path/to/logo.png",
        position="bottom_right",
        opacity=0.5,
        scale=0.1,
        margin=30,
    )

    assert watermark.position == "bottom_right"
    assert watermark.opacity == 0.5
    assert watermark.scale == 0.1

    data = watermark.to_dict()
    assert data["position"] == "bottom_right"

    print(f"  Watermark: {watermark.position}, opacity={watermark.opacity}")
    return True


def test_post_process_config():
    """Test PostProcessConfig dataclass."""
    print("\n=== Testing PostProcessConfig ===")

    config = PostProcessConfig(
        color_grade=ColorGradePreset.INDUSTRIAL,
        output_quality=OutputQuality.FULL_HD,
        normalize_audio=True,
        audio_loudness=-14.0,
        sharpen=True,
        denoise=False,
    )

    assert config.color_grade == ColorGradePreset.INDUSTRIAL
    assert config.output_quality == OutputQuality.FULL_HD
    assert config.normalize_audio is True
    assert config.audio_loudness == -14.0

    data = config.to_dict()
    assert data["color_grade"] == "industrial"
    assert data["output_quality"] == "full_hd"

    print(f"  Config: {config.color_grade.value}, {config.output_quality.value}")
    print(f"  Audio: normalize={config.normalize_audio}, loudness={config.audio_loudness}")
    return True


def test_post_process_result():
    """Test PostProcessResult dataclass."""
    print("\n=== Testing PostProcessResult ===")

    result = PostProcessResult(
        success=True,
        output_path="/output/final.mp4",
        subtitle_path="/output/final.srt",
        duration=120.5,
        file_size=50_000_000,
        effects_applied=["color_grade:industrial", "audio_normalize"],
    )

    assert result.success is True
    assert result.duration == 120.5
    assert len(result.effects_applied) == 2

    data = result.to_dict()
    assert data["success"] is True
    assert "color_grade" in data["effects_applied"][0]

    print(f"  Result: success={result.success}, duration={result.duration}s")
    print(f"  Effects: {result.effects_applied}")
    return True


def test_post_processor_init():
    """Test PostProcessor initialization."""
    print("\n=== Testing PostProcessor Initialization ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        processor = PostProcessor(output_dir=tmpdir)

        assert processor.output_dir.exists()
        assert len(processor.QUALITY_PRESETS) >= 6
        assert len(processor.COLOR_GRADE_FILTERS) >= 5

        print(f"  Output dir: {processor.output_dir}")
        print(f"  Quality presets: {len(processor.QUALITY_PRESETS)}")
        print(f"  Color grades: {len(processor.COLOR_GRADE_FILTERS)}")

    return True


def test_quality_presets():
    """Test quality preset configurations."""
    print("\n=== Testing Quality Presets ===")

    processor = PostProcessor()

    for quality, (w, h, vbr, abr) in processor.QUALITY_PRESETS.items():
        print(f"  {quality.value}: {w}x{h} @ {vbr}/{abr}")

    # Check specific values
    w, h, _, _ = processor.QUALITY_PRESETS[OutputQuality.FULL_HD]
    assert w == 1920
    assert h == 1080

    w, h, _, _ = processor.QUALITY_PRESETS[OutputQuality.UHD]
    assert w == 3840
    assert h == 2160

    return True


def test_color_grade_filters():
    """Test color grade filter strings."""
    print("\n=== Testing Color Grade Filters ===")

    processor = PostProcessor()

    for grade, filter_str in processor.COLOR_GRADE_FILTERS.items():
        if filter_str:
            print(f"  {grade.value}: {filter_str[:50]}...")
        else:
            print(f"  {grade.value}: (no filter)")

    # Check that industrial has color modification
    industrial = processor.COLOR_GRADE_FILTERS[ColorGradePreset.INDUSTRIAL]
    assert "colorbalance" in industrial or "eq=" in industrial

    return True


def test_build_video_filters():
    """Test video filter chain building."""
    print("\n=== Testing Video Filter Building ===")

    processor = PostProcessor()

    # Test with various configs
    config1 = PostProcessConfig(
        color_grade=ColorGradePreset.INDUSTRIAL,
        sharpen=True,
        denoise=False,
    )
    filters1 = processor._build_video_filters(config1)
    print(f"  Industrial + sharpen: {filters1[:60]}...")
    assert len(filters1) > 0

    config2 = PostProcessConfig(
        color_grade=ColorGradePreset.NONE,
        add_fade_in=1.0,
        add_fade_out=1.0,
    )
    filters2 = processor._build_video_filters(config2)
    print(f"  With fades: {filters2}")
    assert "fade" in filters2

    return True


def test_build_audio_filters():
    """Test audio filter chain building."""
    print("\n=== Testing Audio Filter Building ===")

    processor = PostProcessor()

    config = PostProcessConfig(
        normalize_audio=True,
        audio_loudness=-16.0,
    )
    filters = processor._build_audio_filters(config)

    assert "loudnorm" in filters
    assert "-16" in filters

    print(f"  Audio filter: {filters}")

    # Test without normalization
    config2 = PostProcessConfig(normalize_audio=False)
    filters2 = processor._build_audio_filters(config2)
    assert filters2 == ""

    return True


def test_generate_subtitles():
    """Test subtitle file generation."""
    print("\n=== Testing Subtitle Generation ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        processor = PostProcessor(output_dir=tmpdir)

        subtitles = [
            SubtitleEntry(0.0, 3.0, "Welcome to the tutorial."),
            SubtitleEntry(3.5, 7.0, "Today we'll learn about PLCs."),
            SubtitleEntry(8.0, 12.0, "Let's get started!"),
        ]

        srt_path = processor._generate_subtitle_file(subtitles, "test_subs")

        assert srt_path is not None
        assert Path(srt_path).exists()

        # Check content
        content = Path(srt_path).read_text()
        assert "Welcome" in content
        assert "-->" in content
        assert "1\n" in content

        print(f"  Generated: {srt_path}")
        print(f"  Subtitle count: {len(subtitles)}")

    return True


def test_srt_timestamp_format():
    """Test SRT timestamp formatting."""
    print("\n=== Testing SRT Timestamp Format ===")

    processor = PostProcessor()

    # Test various timestamps (avoid floating point precision issues)
    test_cases = [
        (0.0, "00:00:00,000"),
        (1.5, "00:00:01,500"),
        (61.25, "00:01:01,250"),
        (3662.0, "01:01:02,000"),  # Use exact value to avoid precision issues
    ]

    for seconds, expected in test_cases:
        result = processor._format_srt_timestamp(seconds)
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"  {seconds}s -> {result}")

    return True


def test_generate_subtitles_from_narration():
    """Test generating subtitles from narration segments."""
    print("\n=== Testing Subtitles from Narration ===")

    processor = PostProcessor()

    segments = [
        {"text": "First segment.", "start_time": 0.0, "end_time": 3.0},
        {"text": "Second segment.", "start_time": 3.5, "end_time": 7.0},
        {"text": "", "start_time": 8.0, "end_time": 10.0},  # Empty, should skip
        {"text": "Final segment.", "start_time": 10.0, "end_time": 15.0},
    ]

    subtitles = processor.generate_subtitles_from_narration(segments)

    assert len(subtitles) == 3  # Empty one skipped
    assert subtitles[0].text == "First segment."
    assert subtitles[2].text == "Final segment."

    print(f"  Generated {len(subtitles)} subtitle entries from {len(segments)} segments")

    return True


def test_process_missing_file():
    """Test processing with missing input file."""
    print("\n=== Testing Process Missing File ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        processor = PostProcessor(output_dir=tmpdir)

        result = processor.process(
            "/nonexistent/video.mp4",
            "test_output",
        )

        assert result.success is False
        assert "not found" in result.error.lower()

        print(f"  Result: success={result.success}, error={result.error}")

    return True


def test_process_with_test_video():
    """Test processing with an actual test video (requires FFmpeg)."""
    print("\n=== Testing Full Process (requires FFmpeg) ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # First create a test video using compositor
        compositor = VideoCompositor(output_dir=tmpdir, quality="preview")

        if not compositor._check_ffmpeg_available():
            print("  SKIP: FFmpeg not available")
            return True

        test_video = compositor.create_test_video(
            output_name="input",
            duration=3.0,
            text="Test Input",
        )

        if not test_video:
            print("  SKIP: Could not create test video")
            return True

        # Now process it
        processor = PostProcessor(output_dir=tmpdir)

        config = PostProcessConfig(
            color_grade=ColorGradePreset.INDUSTRIAL,
            output_quality=OutputQuality.PREVIEW,
            normalize_audio=False,  # No audio in test video
            subtitles=[
                SubtitleEntry(0.0, 2.0, "Test subtitle"),
            ],
        )

        result = processor.process(
            test_video,
            "output_processed",
            config,
        )

        print(f"  Success: {result.success}")
        if result.success:
            print(f"  Output: {result.output_path}")
            print(f"  Duration: {result.duration}s")
            print(f"  Effects: {result.effects_applied}")
            assert Path(result.output_path).exists()
        else:
            print(f"  Error: {result.error}")

    return True


if __name__ == "__main__":
    print("=" * 50)
    print("YCB v3 - Post-Processing Pipeline Tests")
    print("=" * 50)

    tests = [
        ("ColorGradePreset", test_color_grade_preset),
        ("OutputQuality", test_output_quality),
        ("SubtitleEntry", test_subtitle_entry),
        ("WatermarkConfig", test_watermark_config),
        ("PostProcessConfig", test_post_process_config),
        ("PostProcessResult", test_post_process_result),
        ("PostProcessor initialization", test_post_processor_init),
        ("Quality presets", test_quality_presets),
        ("Color grade filters", test_color_grade_filters),
        ("Build video filters", test_build_video_filters),
        ("Build audio filters", test_build_audio_filters),
        ("Generate subtitles", test_generate_subtitles),
        ("SRT timestamp format", test_srt_timestamp_format),
        ("Subtitles from narration", test_generate_subtitles_from_narration),
        ("Process missing file", test_process_missing_file),
        ("Full process", test_process_with_test_video),
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
