"""Test script for YCB v3 Video Quality Judge."""

import sys
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ycb.evaluation import VideoQualityJudgeV3, V3QualityEvaluation


def test_v3_quality_evaluation_dataclass():
    """Test V3QualityEvaluation dataclass."""
    print("\n=== Testing V3QualityEvaluation ===")

    eval_result = V3QualityEvaluation(
        score=8.7,
        passed=True,
        visual_quality=8.5,
        diagram_quality=9.0,
        transition_quality=8.0,
        script_quality=8.5,
        audio_sync=8.2,
        metadata_quality=8.0,
        rejections=[],
        improvement_suggestions={},
    )

    assert eval_result.score == 8.7
    assert eval_result.passed is True
    assert eval_result.visual_quality == 8.5
    assert eval_result.diagram_quality == 9.0

    data = eval_result.to_dict()
    assert data["score"] == 8.7
    assert data["passed"] is True
    assert data["component_scores"]["visual_quality"] == 8.5
    assert data["component_scores"]["diagram_quality"] == 9.0

    print(f"  Score: {eval_result.score}")
    print(f"  Passed: {eval_result.passed}")
    print(f"  Visual: {eval_result.visual_quality}")
    print(f"  Diagram: {eval_result.diagram_quality}")

    return True


def test_v3_quality_evaluation_failed():
    """Test V3QualityEvaluation with failing scores."""
    print("\n=== Testing V3QualityEvaluation (Failed) ===")

    eval_result = V3QualityEvaluation(
        score=7.2,
        passed=False,
        visual_quality=7.0,
        diagram_quality=7.5,
        transition_quality=7.0,
        script_quality=7.5,
        audio_sync=7.0,
        metadata_quality=7.0,
        rejections=[
            "Visual quality below 8.0 threshold",
            "Overall score below 8.5 threshold",
        ],
        improvement_suggestions={
            "visual_quality": "Increase animation framerate to 30fps",
            "diagram_quality": "Use larger font sizes for labels",
        },
    )

    assert eval_result.passed is False
    assert len(eval_result.rejections) == 2
    assert "visual_quality" in eval_result.improvement_suggestions

    print(f"  Score: {eval_result.score}")
    print(f"  Passed: {eval_result.passed}")
    print(f"  Rejections: {eval_result.rejections}")

    return True


def test_judge_initialization():
    """Test VideoQualityJudgeV3 initialization."""
    print("\n=== Testing VideoQualityJudgeV3 Initialization ===")

    judge = VideoQualityJudgeV3()

    assert judge.target_score == 8.5
    assert judge.min_visual_score == 8.0
    assert judge.min_diagram_score == 8.0
    assert judge.min_other_score == 6.5

    print(f"  Target score: {judge.target_score}")
    print(f"  Min visual: {judge.min_visual_score}")
    print(f"  Min diagram: {judge.min_diagram_score}")
    print(f"  Min other: {judge.min_other_score}")

    return True


def test_judge_custom_thresholds():
    """Test VideoQualityJudgeV3 with custom thresholds."""
    print("\n=== Testing Custom Thresholds ===")

    judge = VideoQualityJudgeV3(
        target_score=9.0,
        min_visual_score=8.5,
        min_diagram_score=8.5,
        min_other_score=7.0,
    )

    assert judge.target_score == 9.0
    assert judge.min_visual_score == 8.5
    assert judge.min_diagram_score == 8.5
    assert judge.min_other_score == 7.0

    print(f"  Custom target: {judge.target_score}")
    print(f"  Custom min visual: {judge.min_visual_score}")

    return True


def test_component_weights():
    """Test component weights sum to 1.0."""
    print("\n=== Testing Component Weights ===")

    total_weight = sum(VideoQualityJudgeV3.COMPONENT_WEIGHTS.values())

    assert abs(total_weight - 1.0) < 0.001, f"Weights sum to {total_weight}, expected 1.0"

    print("  Weights:")
    for component, weight in VideoQualityJudgeV3.COMPONENT_WEIGHTS.items():
        print(f"    {component}: {weight * 100:.0f}%")
    print(f"  Total: {total_weight * 100:.0f}%")

    return True


def test_weighted_score_calculation():
    """Test weighted score calculation."""
    print("\n=== Testing Weighted Score Calculation ===")

    judge = VideoQualityJudgeV3()

    component_scores = {
        "visual_quality": 9.0,      # 25%
        "diagram_quality": 8.5,     # 25%
        "transition_quality": 8.0,  # 10%
        "script_quality": 8.5,      # 20%
        "audio_sync": 8.0,          # 10%
        "metadata_quality": 7.5,    # 10%
    }

    expected = (
        9.0 * 0.25 +   # visual
        8.5 * 0.25 +   # diagram
        8.0 * 0.10 +   # transition
        8.5 * 0.20 +   # script
        8.0 * 0.10 +   # audio
        7.5 * 0.10     # metadata
    )

    result = judge._calculate_weighted_score(component_scores)

    assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"

    print(f"  Calculated score: {result:.2f}")
    print(f"  Expected: {expected:.2f}")

    return True


def test_format_video_for_evaluation():
    """Test video data formatting for evaluation."""
    print("\n=== Testing Video Data Formatting ===")

    judge = VideoQualityJudgeV3()

    video_data = {
        "script": "This is a test script about PLC programming.",
        "title": "PLC Programming Basics",
        "description": "Learn the fundamentals of PLC programming.",
        "tags": ["PLC", "automation", "programming"],
        "duration": 120.0,
        "storyboard": {
            "scene_count": 5,
            "scenes": [
                {
                    "scene_type": "title",
                    "duration": 5.0,
                    "narration_text": "Welcome to PLC Programming Basics",
                },
                {
                    "scene_type": "diagram",
                    "duration": 30.0,
                    "narration_text": "Let's start with the basic structure.",
                },
            ],
            "total_duration": 120.0,
        },
        "render_info": {
            "scenes_rendered": 5,
            "scenes_failed": 0,
            "primary_engine": "Manim",
        },
    }

    formatted = judge._format_video_for_evaluation(video_data)

    assert "PLC Programming Basics" in formatted
    assert "Manim" in formatted
    assert "120.0s" in formatted
    assert "5" in formatted  # scene count

    print(f"  Formatted length: {len(formatted)} chars")
    print(f"  Contains title: {'PLC Programming Basics' in formatted}")
    print(f"  Contains engine: {'Manim' in formatted}")

    return True


def test_json_response_parsing():
    """Test JSON response parsing."""
    print("\n=== Testing JSON Response Parsing ===")

    judge = VideoQualityJudgeV3()

    # Test direct JSON
    json_str = '{"score": 8.5, "passed": true}'
    result = judge._parse_json_response(json_str)
    assert result["score"] == 8.5
    assert result["passed"] is True

    # Test with markdown code block
    markdown_json = '''```json
{"score": 9.0, "component_scores": {"visual_quality": 8.5}}
```'''
    result = judge._parse_json_response(markdown_json)
    assert result["score"] == 9.0
    assert result["component_scores"]["visual_quality"] == 8.5

    # Test embedded JSON
    embedded = 'Here is the evaluation: {"score": 7.5, "passed": false} end.'
    result = judge._parse_json_response(embedded)
    assert result["score"] == 7.5
    assert result["passed"] is False

    print("  Direct JSON: PASS")
    print("  Markdown JSON: PASS")
    print("  Embedded JSON: PASS")

    return True


def test_v3_rubric_content():
    """Test V3 quality rubric contains expected content."""
    print("\n=== Testing V3 Quality Rubric ===")

    from ycb.evaluation.video_judge_v3 import V3_QUALITY_RUBRIC

    # Check for v3-specific requirements
    assert "8.5" in V3_QUALITY_RUBRIC  # v3 threshold
    assert "Visual Quality" in V3_QUALITY_RUBRIC
    assert "Diagram Quality" in V3_QUALITY_RUBRIC
    assert "Manim" in V3_QUALITY_RUBRIC
    assert "Blender" in V3_QUALITY_RUBRIC
    assert "25%" in V3_QUALITY_RUBRIC  # visual weight
    assert "industrial automation" in V3_QUALITY_RUBRIC.lower()

    print("  Contains 8.5 threshold: YES")
    print("  Contains Visual Quality: YES")
    print("  Contains Diagram Quality: YES")
    print("  Contains Manim/Blender: YES")
    print("  Contains weights: YES")

    return True


def test_lazy_client_loading():
    """Test lazy loading of API clients."""
    print("\n=== Testing Lazy Client Loading ===")

    judge = VideoQualityJudgeV3()

    # Clients should not be loaded yet
    assert judge._anthropic_client is None
    assert judge._groq_client is None

    print("  Anthropic client: not loaded (lazy)")
    print("  Groq client: not loaded (lazy)")

    return True


def test_to_dict_serialization():
    """Test V3QualityEvaluation serialization."""
    print("\n=== Testing to_dict Serialization ===")

    eval_result = V3QualityEvaluation(
        score=8.7,
        passed=True,
        visual_quality=8.5,
        diagram_quality=9.0,
        transition_quality=8.0,
        script_quality=8.5,
        audio_sync=8.2,
        metadata_quality=8.0,
        rejections=["Minor issue"],
        improvement_suggestions={"audio_sync": "Adjust timing"},
    )

    data = eval_result.to_dict()

    # Check structure
    assert "score" in data
    assert "passed" in data
    assert "component_scores" in data
    assert "rejections" in data
    assert "improvement_suggestions" in data

    # Check component_scores structure
    components = data["component_scores"]
    assert "visual_quality" in components
    assert "diagram_quality" in components
    assert "transition_quality" in components
    assert "script_quality" in components
    assert "audio_sync" in components
    assert "metadata_quality" in components

    print(f"  Keys: {list(data.keys())}")
    print(f"  Component keys: {list(components.keys())}")

    return True


if __name__ == "__main__":
    print("=" * 50)
    print("YCB v3 - Video Quality Judge Tests")
    print("=" * 50)

    tests = [
        ("V3QualityEvaluation dataclass", test_v3_quality_evaluation_dataclass),
        ("V3QualityEvaluation (failed)", test_v3_quality_evaluation_failed),
        ("Judge initialization", test_judge_initialization),
        ("Custom thresholds", test_judge_custom_thresholds),
        ("Component weights", test_component_weights),
        ("Weighted score calculation", test_weighted_score_calculation),
        ("Video data formatting", test_format_video_for_evaluation),
        ("JSON response parsing", test_json_response_parsing),
        ("V3 quality rubric", test_v3_rubric_content),
        ("Lazy client loading", test_lazy_client_loading),
        ("to_dict serialization", test_to_dict_serialization),
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
