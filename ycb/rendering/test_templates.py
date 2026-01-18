"""Test script for Manim scene templates."""

import subprocess
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ycb.rendering.templates import (
    TitleTemplate,
    DiagramTemplate,
    FlowchartTemplate,
    ComparisonTemplate,
    LadderLogicTemplate,
    TimelineTemplate,
    TemplateFactory,
)


def _run_template_test(template, scene_class: str, output_name: str) -> bool:
    """Run a template test by generating code and rendering with Manim."""

    code = template.generate_code()

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name

    try:
        output_dir = Path(__file__).parent.parent.parent / "ycb_output" / "template_tests"
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable, "-m", "manim",
            "-ql",
            "--fps", "30",
            "--media_dir", str(output_dir),
            "--output_file", output_name,
            temp_path,
            scene_class
        ]

        print(f"  Rendering {output_name}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print(f"  FAILED: {result.stderr[:500]}")
            return False

        # Find output
        for mp4 in output_dir.rglob("*.mp4"):
            if output_name in mp4.name.lower():
                print(f"  SUCCESS: {mp4.stat().st_size} bytes")
                return True

        print(f"  SUCCESS (output location may vary)")
        return True

    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_title_template():
    """Test TitleTemplate."""
    print("\n1. Testing TitleTemplate...")
    template = TitleTemplate(
        title="Introduction to PLCs",
        subtitle="Industrial Automation Fundamentals",
        duration=4.0,
        show_underline=True
    )
    return _run_template_test(template, "TitleScene", "title_test")


def test_diagram_template():
    """Test DiagramTemplate."""
    print("\n2. Testing DiagramTemplate...")
    template = DiagramTemplate(title="PLC System Architecture", duration=6.0)
    template.add_element("CPU", 0, 1.5, color="#3B82F6")
    template.add_element("Input Module", -3, -0.5, color="#22C55E")
    template.add_element("Output Module", 3, -0.5, color="#EF4444")
    template.add_element("Power Supply", 0, -0.5, color="#F59E0B")
    template.add_arrow((-2, 0), (-0.5, 1))
    template.add_arrow((0.5, 1), (2, 0))
    template.add_callout("Processes logic", 0, 1.5, "right")
    return _run_template_test(template, "DiagramScene", "diagram_test")


def test_flowchart_template():
    """Test FlowchartTemplate."""
    print("\n3. Testing FlowchartTemplate...")
    template = FlowchartTemplate(
        title="Motor Start Sequence",
        orientation="horizontal",
        duration=8.0,
        animate_sequentially=True
    )
    template.add_step("Start", color="#3B82F6", shape="oval")
    template.add_step("Check Safety", color="#F59E0B", shape="diamond")
    template.add_step("Enable VFD", color="#22C55E")
    template.add_step("Ramp Up", color="#22C55E")
    template.add_step("Running", color="#3B82F6", shape="oval")
    return _run_template_test(template, "FlowchartScene", "flowchart_test")


def test_comparison_template():
    """Test ComparisonTemplate."""
    print("\n4. Testing ComparisonTemplate...")
    template = ComparisonTemplate(
        title="PLC vs DCS Comparison",
        columns=["Feature", "PLC", "DCS"],
        duration=8.0
    )
    template.add_item("Cost", "Lower", "Higher", highlight=1)
    template.add_item("Scalability", "Limited", "High", highlight=2)
    template.add_item("Speed", "Fast", "Moderate", highlight=1)
    template.add_item("Complexity", "Simple", "Complex")
    return _run_template_test(template, "ComparisonScene", "comparison_test")


def test_ladder_logic_template():
    """Test LadderLogicTemplate."""
    print("\n5. Testing LadderLogicTemplate...")
    template = LadderLogicTemplate(
        title="Motor Control Circuit",
        duration=10.0
    )
    # Rung 1: Start/Stop circuit
    template.add_rung(
        inputs=[("xic", "Start_PB"), ("xio", "Stop_PB")],
        output=("ote", "Motor_Run")
    )
    # Rung 2: Seal-in circuit
    template.add_rung(
        inputs=[("xic", "Motor_Run"), ("xio", "Overload")],
        output=("ote", "Motor_Run")
    )
    # Rung 3: Motor output
    template.add_rung(
        inputs=[("xic", "Motor_Run")],
        output=("ote", "Motor_Out")
    )
    return _run_template_test(template, "LadderLogicScene", "ladder_test")


def test_timeline_template():
    """Test TimelineTemplate."""
    print("\n6. Testing TimelineTemplate...")
    template = TimelineTemplate(
        title="PLC Scan Cycle",
        orientation="horizontal",
        duration=10.0
    )
    template.add_event("Read Inputs", color="#22C55E")
    template.add_event("Execute Logic", color="#3B82F6")
    template.add_event("Update Outputs", color="#EF4444")
    template.add_event("Housekeeping", color="#F59E0B")
    template.add_event("Communication", color="#8B5CF6")
    return _run_template_test(template, "TimelineScene", "timeline_test")


def test_template_factory():
    """Test TemplateFactory convenience methods."""
    print("\n7. Testing TemplateFactory...")

    # Quick test using factory
    template = TemplateFactory.title("Factory Test", "Created via factory")
    return _run_template_test(template, "TitleScene", "factory_test")


if __name__ == "__main__":
    print("=" * 50)
    print("YCB v3 - Manim Template Tests")
    print("=" * 50)

    results = {
        "TitleTemplate": test_title_template(),
        "DiagramTemplate": test_diagram_template(),
        "FlowchartTemplate": test_flowchart_template(),
        "ComparisonTemplate": test_comparison_template(),
        "LadderLogicTemplate": test_ladder_logic_template(),
        "TimelineTemplate": test_timeline_template(),
        "TemplateFactory": test_template_factory(),
    }

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
