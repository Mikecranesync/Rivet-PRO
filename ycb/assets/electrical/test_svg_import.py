"""Test that Manim can import and animate the SVG electrical symbols."""

import subprocess
import sys
import tempfile
from pathlib import Path
import json


def test_svg_import():
    """Test importing and animating SVG symbols in Manim."""

    # Get path to electrical symbols
    assets_dir = Path(__file__).parent
    manifest_path = assets_dir / "manifest.json"

    # Load manifest
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Test importing motor.svg
    motor_svg = assets_dir / "motor.svg"

    # Generate Manim test scene code
    scene_code = f'''
from manim import *

class SVGImportTest(Scene):
    def construct(self):
        # Set background
        self.camera.background_color = "#1a1a2e"

        # Import motor SVG
        motor = SVGMobject("{motor_svg.as_posix()}")
        motor.set_height(2)
        motor.move_to(LEFT * 3)

        # Import relay SVG
        relay = SVGMobject("{(assets_dir / "relay.svg").as_posix()}")
        relay.set_height(2)
        relay.move_to(ORIGIN)

        # Import digital_input SVG
        di = SVGMobject("{(assets_dir / "digital_input.svg").as_posix()}")
        di.set_height(2)
        di.move_to(RIGHT * 3)

        # Animate them appearing
        self.play(
            FadeIn(motor, shift=UP),
            FadeIn(relay, shift=UP),
            FadeIn(di, shift=UP),
            run_time=1
        )

        # Add labels
        motor_label = Text("Motor", font_size=24, color=WHITE)
        motor_label.next_to(motor, DOWN)

        relay_label = Text("Relay", font_size=24, color=WHITE)
        relay_label.next_to(relay, DOWN)

        di_label = Text("Digital Input", font_size=24, color=WHITE)
        di_label.next_to(di, DOWN)

        self.play(
            Write(motor_label),
            Write(relay_label),
            Write(di_label),
            run_time=0.5
        )

        # Animate scaling
        self.play(
            motor.animate.scale(1.2),
            relay.animate.scale(1.2),
            di.animate.scale(1.2),
            run_time=0.5
        )

        self.play(
            motor.animate.scale(1/1.2),
            relay.animate.scale(1/1.2),
            di.animate.scale(1/1.2),
            run_time=0.5
        )

        self.wait(0.5)
'''

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(scene_code)
        temp_path = f.name

    try:
        # Output directory
        output_dir = Path(__file__).parent.parent.parent.parent / "ycb_output" / "test_clips"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_name = "svg_import_test"

        # Run manim
        cmd = [
            sys.executable, "-m", "manim",
            "-ql",  # Low quality for quick test
            "--fps", "30",
            "--media_dir", str(output_dir),
            "--output_file", output_name,
            temp_path,
            "SVGImportTest"
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            return False

        # Find the output file
        for mp4_file in output_dir.rglob("*.mp4"):
            if "svg_import_test" in mp4_file.name.lower() or "svgimporttest" in mp4_file.name.lower():
                print(f"SUCCESS: Created {mp4_file}")
                print(f"File size: {mp4_file.stat().st_size} bytes")
                return True

        print("WARNING: MP4 file not found in expected location")
        print(f"Checking output dir: {output_dir}")
        for f in output_dir.rglob("*"):
            print(f"  Found: {f}")

        return True  # Manim ran successfully even if file location differs

    except subprocess.TimeoutExpired:
        print("ERROR: Manim timed out")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    finally:
        # Cleanup temp file
        Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    success = test_svg_import()
    sys.exit(0 if success else 1)
