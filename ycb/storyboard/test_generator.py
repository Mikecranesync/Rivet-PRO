"""Test script for storyboard generator."""

import sys
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ycb.storyboard import StoryboardGenerator, Storyboard, SceneType


# Sample script for testing
TEST_SCRIPT = """
What is a PLC?

A PLC, or Programmable Logic Controller, is the brain of modern industrial automation.
Unlike traditional relay-based systems, PLCs use digital logic to control machinery and processes.

The main components of a PLC include the CPU, which processes the program logic,
input modules that receive signals from sensors, and output modules that send commands to actuators.

How does a PLC work? The PLC operates in a continuous scan cycle. First, it reads all inputs.
Then, it executes the program logic. Finally, it updates all outputs. This cycle repeats
thousands of times per second.

Compared to traditional relay systems, PLCs offer several advantages: they're more flexible,
easier to troubleshoot, and can be reprogrammed without rewiring. However, they do require
programming knowledge and have higher initial costs.

Let's look at a simple ladder logic example. The first rung checks if a start button is pressed.
If true, it energizes the motor output. A stop button provides a way to de-energize the motor.
"""


def test_rule_based_generation():
    """Test rule-based storyboard generation (no LLM)."""
    print("\n=== Testing Rule-Based Generation ===")

    generator = StoryboardGenerator()
    storyboard = generator.generate(
        script=TEST_SCRIPT,
        title="Introduction to PLCs",
        description="Learn the basics of Programmable Logic Controllers"
    )

    print(storyboard.summary())
    print(f"\nTotal scenes: {len(storyboard.scenes)}")
    print(f"Total duration: {storyboard.total_duration:.1f}s")

    # Verify basic structure
    assert len(storyboard.scenes) > 0, "Should have at least one scene"
    assert storyboard.scenes[0].scene_type == SceneType.TITLE, "First scene should be title"
    assert storyboard.total_duration > 0, "Total duration should be positive"

    # Check scene types are appropriate
    scene_types = [s.scene_type for s in storyboard.scenes]
    print(f"\nScene types: {[st.value for st in scene_types]}")

    # Should have detected comparison scene
    has_comparison = any(st == SceneType.COMPARISON for st in scene_types)
    print(f"Has comparison scene: {has_comparison}")

    # Should have detected ladder_logic or flowchart
    has_process = any(st in [SceneType.FLOWCHART, SceneType.TIMELINE, SceneType.LADDER_LOGIC]
                      for st in scene_types)
    print(f"Has process/flowchart scene: {has_process}")

    return True


def test_storyboard_serialization():
    """Test that storyboard can be serialized to dict."""
    print("\n=== Testing Serialization ===")

    generator = StoryboardGenerator()
    storyboard = generator.generate(
        script=TEST_SCRIPT,
        title="PLC Basics",
    )

    # Convert to dict
    data = storyboard.to_dict()

    assert "title" in data
    assert "scenes" in data
    assert len(data["scenes"]) > 0
    assert "scene_type" in data["scenes"][0]
    assert "template_params" in data["scenes"][0]

    print(f"Serialized {len(data['scenes'])} scenes")
    print(f"Keys in scene: {list(data['scenes'][0].keys())}")

    return True


def test_scene_template_params():
    """Test that template parameters are generated correctly."""
    print("\n=== Testing Template Parameters ===")

    generator = StoryboardGenerator()
    storyboard = generator.generate(
        script=TEST_SCRIPT,
        title="PLC Test",
    )

    for scene in storyboard.scenes:
        assert scene.template_params is not None, f"Scene {scene.scene_id} missing template_params"
        assert scene.template_params.template_name, f"Scene {scene.scene_id} missing template_name"
        assert scene.template_params.duration > 0, f"Scene {scene.scene_id} has invalid duration"

        print(f"  {scene.scene_id}: {scene.template_params.template_name} ({scene.duration:.1f}s)")

    return True


def test_custom_config():
    """Test custom configuration."""
    print("\n=== Testing Custom Configuration ===")

    from ycb.storyboard.generator import StoryboardConfig

    config = StoryboardConfig(
        target_duration=30.0,
        min_scenes=2,
        max_scenes=5,
        default_scene_duration=6.0,
    )

    generator = StoryboardGenerator(config)
    storyboard = generator.generate(
        script="This is a short test script about PLCs.",
        title="Short Test",
    )

    print(f"Target duration: {storyboard.target_duration}s")
    print(f"Scenes: {len(storyboard.scenes)}")

    return True


if __name__ == "__main__":
    print("=" * 50)
    print("YCB v3 - Storyboard Generator Tests")
    print("=" * 50)

    tests = [
        ("Rule-based generation", test_rule_based_generation),
        ("Serialization", test_storyboard_serialization),
        ("Template parameters", test_scene_template_params),
        ("Custom configuration", test_custom_config),
    ]

    results = {}
    for name, test_func in tests:
        try:
            success = test_func()
            results[name] = success
        except Exception as e:
            print(f"\n!!! Test failed with error: {e}")
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
