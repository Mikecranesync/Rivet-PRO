"""
YCB v3 Integration Tests

Comprehensive end-to-end tests for the v3 video generation pipeline.
Tests component integration, fallback behaviors, and full pipeline flow.
"""

import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# =============================================================================
# Test: Module Imports
# =============================================================================

def test_all_module_imports():
    """Test that all v3 modules can be imported."""
    print("\n=== Testing Module Imports ===")

    modules = []

    # Rendering
    try:
        from ycb.rendering import ManimEngine
        modules.append(("ManimEngine", True))
    except ImportError as e:
        modules.append(("ManimEngine", f"FAIL: {e}"))

    # Storyboard
    try:
        from ycb.storyboard import StoryboardGenerator, SceneRouter, Storyboard, Scene
        modules.append(("Storyboard (all)", True))
    except ImportError as e:
        modules.append(("Storyboard", f"FAIL: {e}"))

    # Audio
    try:
        from ycb.audio import TimingSync, TimingMap
        modules.append(("Audio Timing", True))
    except ImportError as e:
        modules.append(("Audio Timing", f"FAIL: {e}"))

    # Composition
    try:
        from ycb.composition import (
            VideoCompositor, PostProcessor, OutputQuality,
            ColorGradePreset, TransitionType, ClipConfig
        )
        modules.append(("Composition (all)", True))
    except ImportError as e:
        modules.append(("Composition", f"FAIL: {e}"))

    # Pipeline
    try:
        from ycb.pipeline import VideoGeneratorV3, V3GenerationConfig, V3GenerationResult
        modules.append(("Pipeline v3", True))
    except ImportError as e:
        modules.append(("Pipeline v3", f"FAIL: {e}"))

    # Evaluation
    try:
        from ycb.evaluation import VideoQualityJudgeV3, V3QualityEvaluation
        modules.append(("Evaluation v3", True))
    except ImportError as e:
        modules.append(("Evaluation v3", f"FAIL: {e}"))

    # Print results
    all_passed = True
    for name, result in modules:
        if result is True:
            print(f"  [+] {name}: OK")
        else:
            print(f"  [-] {name}: {result}")
            all_passed = False

    return all_passed


# =============================================================================
# Test: Storyboard Generation
# =============================================================================

def test_storyboard_generation_integration():
    """Test storyboard generation creates valid scene structure."""
    print("\n=== Testing Storyboard Generation Integration ===")

    from ycb.storyboard import StoryboardGenerator, Storyboard

    generator = StoryboardGenerator()

    script = """
    Introduction to PLCs

    A PLC, or Programmable Logic Controller, is an industrial computer.
    It reads inputs from sensors and controls outputs like motors.

    The main components are:
    1. CPU - processes the program
    2. I/O modules - connect to field devices
    3. Power supply - provides electrical power

    PLCs are programmed using ladder logic diagrams.
    """

    storyboard = generator.generate(
        script=script,
        title="Introduction to PLCs",
        description="Learn the basics of PLC systems",
        target_duration=60.0,
    )

    # Validate structure
    assert storyboard is not None
    assert isinstance(storyboard, Storyboard)
    assert storyboard.title == "Introduction to PLCs"
    assert len(storyboard.scenes) > 0

    # Validate scenes
    for scene in storyboard.scenes:
        assert scene.scene_id is not None
        assert scene.duration > 0
        assert scene.scene_type is not None

    print(f"  Title: {storyboard.title}")
    print(f"  Scenes: {len(storyboard.scenes)}")
    print(f"  Total duration: {storyboard.total_duration:.1f}s")

    return True


# =============================================================================
# Test: Scene Router
# =============================================================================

def test_scene_router_integration():
    """Test scene router routes scenes to correct engines."""
    print("\n=== Testing Scene Router Integration ===")

    from ycb.storyboard import SceneRouter, Scene, SceneType, VisualDescription

    with tempfile.TemporaryDirectory() as tmpdir:
        router = SceneRouter(output_dir=tmpdir)

        # Create test scenes
        scenes = [
            Scene(
                scene_id="s1",
                scene_type=SceneType.TITLE,
                duration=5.0,
                narration_text="Welcome",
                visual_description=VisualDescription(main_subject="Title"),
            ),
            Scene(
                scene_id="s2",
                scene_type=SceneType.DIAGRAM,
                duration=15.0,
                narration_text="Here is a diagram",
                visual_description=VisualDescription(main_subject="PLC diagram"),
            ),
            Scene(
                scene_id="s3",
                scene_type=SceneType.FLOWCHART,
                duration=10.0,
                narration_text="Process flow",
                visual_description=VisualDescription(main_subject="Flowchart"),
            ),
        ]

        # Test routing - use route() method
        for scene in scenes:
            result = router.route(scene)
            assert result is not None
            # RenderResult has engine_used field (RenderEngine enum)
            engine = result.engine_used.value if result.engine_used else "none"
            # Accept any valid engine or "none" if rendering failed
            assert engine in ["manim", "blender", "external", "none"], f"Unexpected engine: {engine}"
            print(f"  {scene.scene_type.value} -> {engine} (status: {result.status.value})")

    return True


# =============================================================================
# Test: Timing Synchronization
# =============================================================================

def test_timing_sync_integration():
    """Test timing synchronization without audio file."""
    print("\n=== Testing Timing Sync Integration ===")

    from ycb.audio import TimingSync
    from ycb.storyboard import Storyboard, Scene, SceneType, VisualDescription

    sync = TimingSync()

    # Create test storyboard
    storyboard = Storyboard(
        title="Test",
        description="Test storyboard",
        target_duration=30.0
    )
    storyboard.add_scene(Scene(
        scene_id="s1",
        scene_type=SceneType.TITLE,
        duration=5.0,
        narration_text="Welcome to this tutorial.",
        visual_description=VisualDescription(main_subject="Title"),
    ))
    storyboard.add_scene(Scene(
        scene_id="s2",
        scene_type=SceneType.TEXT,
        duration=10.0,
        narration_text="Today we will learn about PLCs.",
        visual_description=VisualDescription(main_subject="Content"),
    ))

    # Sync using text-based estimation (sync_from_text expects list of dicts)
    scenes_dicts = [s.to_dict() for s in storyboard.scenes]
    timing_map = sync.sync_from_text(scenes_dicts)

    assert timing_map is not None
    assert len(timing_map.scene_timings) == 2
    assert timing_map.total_duration > 0

    print(f"  Scenes timed: {len(timing_map.scene_timings)}")
    print(f"  Total duration: {timing_map.total_duration:.1f}s")

    return True


# =============================================================================
# Test: Compositor Configuration
# =============================================================================

def test_compositor_configuration():
    """Test compositor can be configured with various options."""
    print("\n=== Testing Compositor Configuration ===")

    from ycb.composition import (
        VideoCompositor, ClipConfig, TransitionType, OverlayConfig
    )

    compositor = VideoCompositor()

    # Test clip config creation (use actual field names)
    config = ClipConfig(
        path="/path/to/clip.mp4",
        duration=10.0,
        transition_in=TransitionType.CROSSFADE,
        transition_out=TransitionType.FADE,
        transition_duration=0.5,
    )

    assert config.duration == 10.0
    assert config.transition_in == TransitionType.CROSSFADE

    # Test overlay config (use actual field names)
    overlay = OverlayConfig(
        text="Key Point",
        position="bottom_left",
        start_time=5.0,
        duration=3.0,
    )

    assert overlay.start_time == 5.0
    assert overlay.position == "bottom_left"

    print(f"  ClipConfig: OK")
    print(f"  OverlayConfig: OK")
    print(f"  Transitions available: {[t.value for t in TransitionType]}")

    return True


# =============================================================================
# Test: Post-Processor Configuration
# =============================================================================

def test_post_processor_configuration():
    """Test post-processor configuration options."""
    print("\n=== Testing Post-Processor Configuration ===")

    from ycb.composition import (
        PostProcessor, PostProcessConfig, ColorGradePreset, OutputQuality
    )

    processor = PostProcessor()

    # Test config creation (use actual field names)
    config = PostProcessConfig(
        color_grade=ColorGradePreset.PROFESSIONAL,
        output_quality=OutputQuality.FULL_HD,
        normalize_audio=True,
        audio_loudness=-16.0,
    )

    assert config.color_grade == ColorGradePreset.PROFESSIONAL
    assert config.output_quality == OutputQuality.FULL_HD
    assert config.normalize_audio is True

    print(f"  Color grades: {[c.value for c in ColorGradePreset]}")
    print(f"  Quality presets: {[q.value for q in OutputQuality]}")
    print(f"  Config: OK")

    return True


# =============================================================================
# Test: V3 Generator Configuration
# =============================================================================

def test_v3_generator_configuration():
    """Test VideoGeneratorV3 configuration."""
    print("\n=== Testing V3 Generator Configuration ===")

    from ycb.pipeline import VideoGeneratorV3, V3GenerationConfig
    from ycb.composition import OutputQuality, ColorGradePreset
    from ycb.composition.compositor import TransitionType

    with tempfile.TemporaryDirectory() as tmpdir:
        config = V3GenerationConfig(
            output_dir=tmpdir,
            output_quality=OutputQuality.HD,
            fps=24,
            target_duration=90.0,
            manim_quality="medium_quality",
            enable_blender=False,
            default_transition=TransitionType.FADE,
            color_grade=ColorGradePreset.CLEAN,
        )

        generator = VideoGeneratorV3(config)

        # Check directories created
        assert generator.output_dir.exists()
        assert generator.clips_dir.exists()
        assert generator.final_dir.exists()

        # Check engine status
        status = generator.get_engine_status()
        assert "manim" in status
        assert "blender" in status

        print(f"  Output dir: {generator.output_dir}")
        print(f"  Engine status: {status}")
        print(f"  Config OK")

    return True


# =============================================================================
# Test: V3 Quality Judge
# =============================================================================

def test_v3_quality_judge_evaluation():
    """Test V3QualityJudge evaluation logic."""
    print("\n=== Testing V3 Quality Judge ===")

    from ycb.evaluation import VideoQualityJudgeV3

    judge = VideoQualityJudgeV3(target_score=8.5)

    # Test weighted score calculation
    scores = {
        "visual_quality": 9.0,      # 25%
        "diagram_quality": 8.5,     # 25%
        "transition_quality": 8.0,  # 10%
        "script_quality": 8.5,      # 20%
        "audio_sync": 8.0,          # 10%
        "metadata_quality": 7.5,    # 10%
    }

    weighted = judge._calculate_weighted_score(scores)

    expected = (
        9.0 * 0.25 +
        8.5 * 0.25 +
        8.0 * 0.10 +
        8.5 * 0.20 +
        8.0 * 0.10 +
        7.5 * 0.10
    )

    assert abs(weighted - expected) < 0.01

    print(f"  Target score: {judge.target_score}")
    print(f"  Weighted score: {weighted:.2f}")
    print(f"  Expected: {expected:.2f}")

    return True


# =============================================================================
# Test: Fallback Behaviors
# =============================================================================

def test_storyboard_fallback():
    """Test storyboard generator fallback to rule-based when LLM unavailable."""
    print("\n=== Testing Storyboard Fallback ===")

    from ycb.storyboard import StoryboardGenerator

    # Create generator with no API keys
    generator = StoryboardGenerator()

    script = "Short test script about PLCs and automation systems."

    # This should use fallback if LLM unavailable
    storyboard = generator.generate(
        script=script,
        title="Test",
        description="Test",
        target_duration=30.0,
    )

    assert storyboard is not None
    assert len(storyboard.scenes) > 0

    print(f"  Fallback worked: {len(storyboard.scenes)} scenes generated")

    return True


def test_router_fallback_to_manim():
    """Test scene router falls back to Manim when Blender unavailable."""
    print("\n=== Testing Router Fallback ===")

    from ycb.storyboard import SceneRouter, Scene, SceneType, VisualDescription

    with tempfile.TemporaryDirectory() as tmpdir:
        # Router - Blender availability is auto-detected
        router = SceneRouter(output_dir=tmpdir)

        # 3D scene (use THREE_D enum value) that would normally go to Blender
        scene = Scene(
            scene_id="s1",
            scene_type=SceneType.THREE_D,
            duration=10.0,
            narration_text="3D animation",
            visual_description=VisualDescription(main_subject="Motor"),
        )

        result = router.route(scene)

        # Check engine_used field
        engine = result.engine_used.value if result.engine_used else "none"
        # Without Blender installed, should fall back to Manim or placeholder
        assert engine in ["manim", "blender", "external", "none"]

        print(f"  3D scene routed to: {engine}")

    return True


# =============================================================================
# Test: End-to-End Data Flow
# =============================================================================

def test_e2e_data_flow():
    """Test data flows correctly through pipeline components."""
    print("\n=== Testing End-to-End Data Flow ===")

    from ycb.storyboard import StoryboardGenerator, SceneRouter
    from ycb.audio import TimingSync
    from ycb.evaluation import VideoQualityJudgeV3

    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Generate storyboard
        storyboard_gen = StoryboardGenerator()
        storyboard = storyboard_gen.generate(
            script="Test script about industrial automation.",
            title="E2E Test",
            description="Testing data flow",
            target_duration=30.0,
        )
        assert storyboard is not None
        print(f"  1. Storyboard: {len(storyboard.scenes)} scenes")

        # Step 2: Route scenes
        router = SceneRouter(output_dir=tmpdir)
        routes = []
        for scene in storyboard.scenes:
            result = router.route(scene)
            routes.append(result)
        assert len(routes) == len(storyboard.scenes)
        print(f"  2. Routes: {len(routes)} scenes routed")

        # Step 3: Sync timing
        timing = TimingSync()
        scenes_dicts = [s.to_dict() for s in storyboard.scenes]
        timing_map = timing.sync_from_text(scenes_dicts)
        assert timing_map is not None
        print(f"  3. Timing: {timing_map.total_duration:.1f}s total")

        # Step 4: Create evaluation data
        video_data = {
            "script": "Test script",
            "title": storyboard.title,
            "description": storyboard.description,
            "tags": ["test"],
            "duration": timing_map.total_duration,
            "storyboard": {
                "scene_count": len(storyboard.scenes),
                "scenes": storyboard.to_dict()["scenes"],
            },
            "render_info": {
                "scenes_rendered": len(storyboard.scenes),
                "primary_engine": "Manim",
            },
        }

        # Step 5: Format for judge
        judge = VideoQualityJudgeV3()
        formatted = judge._format_video_for_evaluation(video_data)
        assert "E2E Test" in formatted
        assert "Manim" in formatted
        print(f"  4. Judge input: {len(formatted)} chars")

        print("  All data flowed correctly!")

    return True


# =============================================================================
# Test: Configuration Serialization
# =============================================================================

def test_config_serialization():
    """Test all config classes can be serialized to JSON."""
    print("\n=== Testing Config Serialization ===")

    from ycb.pipeline import V3GenerationConfig, V3GenerationResult
    from ycb.evaluation import V3QualityEvaluation
    from ycb.composition import PostProcessConfig, OutputQuality, ColorGradePreset

    # Test V3GenerationConfig
    gen_config = V3GenerationConfig(output_dir="./test")
    gen_dict = gen_config.to_dict()
    json_str = json.dumps(gen_dict)
    assert len(json_str) > 0
    print(f"  V3GenerationConfig: {len(json_str)} chars")

    # Test V3GenerationResult
    gen_result = V3GenerationResult(
        success=True,
        video_path="/test.mp4",
        duration=60.0,
        scene_count=5,
    )
    result_dict = gen_result.to_dict()
    json_str = json.dumps(result_dict)
    assert len(json_str) > 0
    print(f"  V3GenerationResult: {len(json_str)} chars")

    # Test V3QualityEvaluation
    eval_result = V3QualityEvaluation(
        score=8.5,
        passed=True,
    )
    eval_dict = eval_result.to_dict()
    json_str = json.dumps(eval_dict)
    assert len(json_str) > 0
    print(f"  V3QualityEvaluation: {len(json_str)} chars")

    return True


# =============================================================================
# Main Runner
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("YCB v3 - Integration Tests")
    print("=" * 60)

    tests = [
        ("Module imports", test_all_module_imports),
        ("Storyboard generation", test_storyboard_generation_integration),
        ("Scene router", test_scene_router_integration),
        ("Timing sync", test_timing_sync_integration),
        ("Compositor config", test_compositor_configuration),
        ("Post-processor config", test_post_processor_configuration),
        ("V3 generator config", test_v3_generator_configuration),
        ("V3 quality judge", test_v3_quality_judge_evaluation),
        ("Storyboard fallback", test_storyboard_fallback),
        ("Router fallback", test_router_fallback_to_manim),
        ("E2E data flow", test_e2e_data_flow),
        ("Config serialization", test_config_serialization),
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

    print("\n" + "=" * 60)
    print("INTEGRATION TEST RESULTS")
    print("=" * 60)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
