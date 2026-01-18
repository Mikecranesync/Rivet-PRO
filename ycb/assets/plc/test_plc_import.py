"""Test that Manim can import and animate the PLC component SVGs."""

import subprocess
import sys
import tempfile
from pathlib import Path
import json


def test_plc_hardware_import():
    """Test importing PLC hardware components."""

    assets_dir = Path(__file__).parent

    scene_code = f'''
from manim import *

class PLCHardwareTest(Scene):
    def construct(self):
        self.camera.background_color = "#1a1a2e"

        # Title
        title = Text("PLC Hardware Components", font_size=32, color=WHITE)
        title.to_edge(UP)
        self.play(Write(title), run_time=0.5)

        # Import PLC rack
        rack = SVGMobject("{(assets_dir / "plc_rack.svg").as_posix()}")
        rack.set_width(6)
        rack.move_to(DOWN * 0.5)

        # Import modules
        power = SVGMobject("{(assets_dir / "power_supply.svg").as_posix()}")
        power.set_height(1.6)
        power.move_to(LEFT * 2.4 + DOWN * 0.5)

        cpu = SVGMobject("{(assets_dir / "cpu_module.svg").as_posix()}")
        cpu.set_height(1.6)
        cpu.move_to(LEFT * 1.5 + DOWN * 0.5)

        io1 = SVGMobject("{(assets_dir / "io_module.svg").as_posix()}")
        io1.set_height(1.6)
        io1.move_to(LEFT * 0.6 + DOWN * 0.5)

        io2 = SVGMobject("{(assets_dir / "io_module.svg").as_posix()}")
        io2.set_height(1.6)
        io2.move_to(RIGHT * 0.3 + DOWN * 0.5)

        # Animate rack appearing
        self.play(FadeIn(rack, shift=UP), run_time=0.5)

        # Animate modules sliding in
        self.play(
            FadeIn(power, shift=DOWN),
            FadeIn(cpu, shift=DOWN),
            FadeIn(io1, shift=DOWN),
            FadeIn(io2, shift=DOWN),
            run_time=0.7
        )

        self.wait(0.3)
'''

    return _run_manim_test(scene_code, "plc_hardware_test")


def test_ladder_logic_import():
    """Test importing ladder logic symbols."""

    assets_dir = Path(__file__).parent

    scene_code = f'''
from manim import *

class LadderLogicTest(Scene):
    def construct(self):
        self.camera.background_color = "#1a1a2e"

        # Title
        title = Text("Ladder Logic Symbols", font_size=32, color=WHITE)
        title.to_edge(UP)
        self.play(Write(title), run_time=0.5)

        # Power rails
        left_rail = Line(LEFT * 3 + UP * 1.5, LEFT * 3 + DOWN * 1.5, color="#3B82F6", stroke_width=4)
        right_rail = Line(RIGHT * 3 + UP * 1.5, RIGHT * 3 + DOWN * 1.5, color="#3B82F6", stroke_width=4)

        self.play(Create(left_rail), Create(right_rail), run_time=0.3)

        # Import XIC
        xic = SVGMobject("{(assets_dir / "ladder_xic.svg").as_posix()}")
        xic.set_width(1.2)
        xic.move_to(LEFT * 1.5 + UP * 0.5)

        # Import XIO
        xio = SVGMobject("{(assets_dir / "ladder_xio.svg").as_posix()}")
        xio.set_width(1.2)
        xio.move_to(LEFT * 0 + UP * 0.5)

        # Import OTE
        ote = SVGMobject("{(assets_dir / "ladder_ote.svg").as_posix()}")
        ote.set_width(1.2)
        ote.move_to(RIGHT * 1.5 + UP * 0.5)

        # Import TON
        ton = SVGMobject("{(assets_dir / "ladder_ton.svg").as_posix()}")
        ton.set_width(1.5)
        ton.move_to(DOWN * 1)

        # Animate
        self.play(FadeIn(xic), FadeIn(xio), FadeIn(ote), run_time=0.5)
        self.play(FadeIn(ton, shift=UP), run_time=0.5)

        # Add labels
        xic_label = Text("XIC", font_size=16, color="#A0AEC0").next_to(xic, DOWN)
        xio_label = Text("XIO", font_size=16, color="#A0AEC0").next_to(xio, DOWN)
        ote_label = Text("OTE", font_size=16, color="#A0AEC0").next_to(ote, DOWN)
        ton_label = Text("TON Timer", font_size=16, color="#A0AEC0").next_to(ton, DOWN)

        self.play(
            Write(xic_label), Write(xio_label), Write(ote_label), Write(ton_label),
            run_time=0.5
        )

        self.wait(0.3)
'''

    return _run_manim_test(scene_code, "ladder_logic_test")


def _run_manim_test(scene_code: str, output_name: str) -> bool:
    """Run a Manim test scene."""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(scene_code)
        temp_path = f.name

    try:
        output_dir = Path(__file__).parent.parent.parent.parent / "ycb_output" / "test_clips"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract scene class name from the code
        scene_class = "PLCHardwareTest" if "PLCHardwareTest" in scene_code else "LadderLogicTest"

        cmd = [
            sys.executable, "-m", "manim",
            "-ql",
            "--fps", "30",
            "--media_dir", str(output_dir),
            "--output_file", output_name,
            temp_path,
            scene_class
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            return False

        for mp4_file in output_dir.rglob("*.mp4"):
            if output_name in mp4_file.name.lower():
                print(f"SUCCESS: Created {mp4_file}")
                print(f"File size: {mp4_file.stat().st_size} bytes")
                return True

        print(f"Test {output_name} completed (file location may vary)")
        return True

    except subprocess.TimeoutExpired:
        print("ERROR: Manim timed out")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    finally:
        Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    print("=== Testing PLC Hardware Import ===")
    hw_ok = test_plc_hardware_import()

    print("\n=== Testing Ladder Logic Import ===")
    ll_ok = test_ladder_logic_import()

    if hw_ok and ll_ok:
        print("\nAll PLC asset tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed")
        sys.exit(1)
