"""Test script for scene-to-renderer routing system."""

import sys
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ycb.storyboard import (
    SceneRouter,
    RenderResult,
    RouteStatus,
    SceneType,
    RenderEngine,
    Scene,
    Storyboard,
    VisualDescription,
    TemplateParameters,
)


def create_test_scene(
    scene_id: str,
    scene_type: SceneType,
    title: str = "Test Scene",
    duration: float = 5.0,
) -> Scene:
    """Create a test scene with given parameters."""
    return Scene(
        scene_id=scene_id,
        scene_type=scene_type,
        duration=duration,
        narration_text=f"Narration for {title}",
        visual_description=VisualDescription(main_subject=title),
        template_params=TemplateParameters(
            template_name=f"{scene_type.value.title()}Template",
            title=title,
            duration=duration,
        ),
        render_engine=RenderEngine.MANIM,
    )


def test_router_initialization():
    """Test that router initializes correctly."""
    print("\n=== Testing Router Initialization ===")

    router = SceneRouter(
        output_dir="./test_output/clips",
        manim_quality="low_quality",
        enable_blender=False,
    )

    assert router.output_dir.exists(), "Output directory should be created"
    assert router.manim_quality == "low_quality"
    assert router.enable_blender is False

    # Check routing table
    assert SceneType.TITLE in router.routing_table
    assert SceneType.DIAGRAM in router.routing_table
    assert SceneType.THREE_D in router.routing_table

    print("  Router initialized successfully")
    print(f"  Output dir: {router.output_dir}")
    print(f"  Routing table entries: {len(router.routing_table)}")

    return True


def test_routing_table():
    """Test routing table mappings."""
    print("\n=== Testing Routing Table ===")

    router = SceneRouter()

    # Test Manim routes
    manim_types = [
        SceneType.TITLE,
        SceneType.TEXT,
        SceneType.DIAGRAM,
        SceneType.FLOWCHART,
        SceneType.COMPARISON,
        SceneType.LADDER_LOGIC,
        SceneType.TIMELINE,
    ]

    for scene_type in manim_types:
        primary, fallback = router.routing_table[scene_type]
        assert primary == RenderEngine.MANIM, f"{scene_type} should route to Manim"
        print(f"  {scene_type.value}: {primary.value} (fallback: {fallback})")

    # Test 3D route (Blender with Manim fallback)
    primary, fallback = router.routing_table[SceneType.THREE_D]
    assert primary == RenderEngine.BLENDER, "THREE_D should route to Blender"
    assert fallback == RenderEngine.MANIM, "THREE_D should fallback to Manim"
    print(f"  {SceneType.THREE_D.value}: {primary.value} (fallback: {fallback.value})")

    # Test external route
    primary, fallback = router.routing_table[SceneType.B_ROLL]
    assert primary == RenderEngine.EXTERNAL, "B_ROLL should route to External"
    print(f"  {SceneType.B_ROLL.value}: {primary.value}")

    # Test transition route (none)
    primary, fallback = router.routing_table[SceneType.TRANSITION]
    assert primary == RenderEngine.NONE, "TRANSITION should route to None"
    print(f"  {SceneType.TRANSITION.value}: {primary.value}")

    return True


def test_engine_availability():
    """Test engine availability checking."""
    print("\n=== Testing Engine Availability ===")

    router = SceneRouter(enable_blender=False)

    engines = router.get_available_engines()
    print(f"  Available engines: {engines}")

    # Manim should be available (installed in this project)
    # Note: This test may fail if Manim is not installed
    manim_available = engines.get("manim", False)
    print(f"  Manim available: {manim_available}")

    # Blender should not be available (disabled)
    blender_available = engines.get("blender", False)
    assert blender_available is False, "Blender should be disabled"
    print(f"  Blender available: {blender_available}")

    return True


def test_route_skipped_scene():
    """Test routing a scene that should be skipped."""
    print("\n=== Testing Skipped Scene Routing ===")

    router = SceneRouter()

    scene = create_test_scene(
        scene_id="transition_001",
        scene_type=SceneType.TRANSITION,
        title="Fade Transition",
    )

    result = router.route(scene)

    assert result.status == RouteStatus.SKIPPED, "Transition should be skipped"
    assert result.engine_used == RenderEngine.NONE
    assert result.clip_path is None
    print(f"  Status: {result.status.value}")
    print(f"  Engine: {result.engine_used.value}")

    return True


def test_route_external_scene():
    """Test routing an external/B-roll scene."""
    print("\n=== Testing External Scene Routing ===")

    router = SceneRouter()

    scene = create_test_scene(
        scene_id="broll_001",
        scene_type=SceneType.B_ROLL,
        title="Factory Floor Footage",
        duration=10.0,
    )

    result = router.route(scene)

    assert result.status == RouteStatus.SUCCESS, "B-roll should succeed (placeholder)"
    assert result.engine_used == RenderEngine.EXTERNAL
    assert result.clip_path is None  # No clip generated for external
    assert result.duration == 10.0
    print(f"  Status: {result.status.value}")
    print(f"  Engine: {result.engine_used.value}")
    print(f"  Duration: {result.duration}s")

    return True


def test_render_result_serialization():
    """Test that RenderResult can be serialized to dict."""
    print("\n=== Testing RenderResult Serialization ===")

    result = RenderResult(
        scene_id="test_001",
        status=RouteStatus.SUCCESS,
        clip_path="/path/to/clip.mp4",
        engine_used=RenderEngine.MANIM,
        duration=5.0,
    )

    data = result.to_dict()

    assert data["scene_id"] == "test_001"
    assert data["status"] == "success"
    assert data["clip_path"] == "/path/to/clip.mp4"
    assert data["engine_used"] == "manim"
    assert data["duration"] == 5.0
    assert data["error"] is None

    print(f"  Serialized: {data}")

    return True


def test_route_storyboard():
    """Test routing a complete storyboard."""
    print("\n=== Testing Storyboard Routing ===")

    router = SceneRouter(enable_blender=False)

    # Create a mini storyboard
    storyboard = Storyboard(
        title="Test Storyboard",
        description="Testing router",
        target_duration=30.0,
    )

    storyboard.add_scene(
        create_test_scene("scene_001", SceneType.TRANSITION, "Intro Fade")
    )
    storyboard.add_scene(
        create_test_scene("scene_002", SceneType.B_ROLL, "Factory Footage")
    )
    storyboard.add_scene(
        create_test_scene("scene_003", SceneType.TRANSITION, "Outro Fade")
    )

    results = router.route_storyboard(storyboard)

    assert len(results) == 3, "Should have 3 results"

    # First and last should be skipped (transitions)
    assert results[0].status == RouteStatus.SKIPPED
    assert results[2].status == RouteStatus.SKIPPED

    # Middle should be success (external)
    assert results[1].status == RouteStatus.SUCCESS
    assert results[1].engine_used == RenderEngine.EXTERNAL

    print(f"  Routed {len(results)} scenes")
    for r in results:
        print(f"    {r.scene_id}: {r.status.value}")

    return True


if __name__ == "__main__":
    print("=" * 50)
    print("YCB v3 - Scene Router Tests")
    print("=" * 50)

    tests = [
        ("Router initialization", test_router_initialization),
        ("Routing table", test_routing_table),
        ("Engine availability", test_engine_availability),
        ("Skipped scene routing", test_route_skipped_scene),
        ("External scene routing", test_route_external_scene),
        ("RenderResult serialization", test_render_result_serialization),
        ("Storyboard routing", test_route_storyboard),
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
