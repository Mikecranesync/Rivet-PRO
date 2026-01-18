"""
Manim Rendering Engine for YCB v3

Generates animated technical diagrams and scenes using the Manim library.
Outputs MP4 clips that can be composited into final videos.

Usage:
    from ycb.rendering import ManimEngine, SceneConfig, DiagramConfig

    engine = ManimEngine(output_dir="./ycb_output/clips")

    # Render a title scene
    clip_path = engine.render_title("What is a PLC?", "Industrial Automation Basics")

    # Render a diagram
    diagram = DiagramConfig(title="PLC Architecture")
    diagram.add_box("CPU", 0, 2)
    diagram.add_box("Input Module", -3, 0)
    diagram.add_box("Output Module", 3, 0)
    diagram.add_arrow((-3, 0.5), (0, 1.5))
    diagram.add_arrow((0, 1.5), (3, 0.5))
    clip_path = engine.render_diagram(diagram)
"""

import os
import sys
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

from .scene_types import (
    SceneType,
    SceneConfig,
    TextConfig,
    ShapeConfig,
    ArrowConfig,
    DiagramConfig,
    INDUSTRIAL_COLORS,
)

logger = logging.getLogger(__name__)


class ManimEngine:
    """
    Rendering engine that generates Manim animations as MP4 clips.

    Uses subprocess to run Manim in a clean environment, avoiding
    conflicts with the main application's event loop.
    """

    def __init__(self, output_dir: str = "./ycb_output/clips",
                 quality: str = "medium_quality",
                 fps: int = 30):
        """
        Initialize the Manim rendering engine.

        Args:
            output_dir: Directory to save rendered clips
            quality: Manim quality preset (low_quality, medium_quality, high_quality, production_quality)
            fps: Frames per second for output video
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.quality = quality
        self.fps = fps

        # Quality presets map to Manim flags
        self.quality_flags = {
            "low_quality": "-ql",
            "medium_quality": "-qm",
            "high_quality": "-qh",
            "production_quality": "-qp",
        }

        logger.info(f"ManimEngine initialized: output_dir={output_dir}, quality={quality}")

    def _generate_scene_code(self, config: SceneConfig) -> str:
        """Generate Manim Python code for a scene configuration."""

        # Map scene type to generation method
        if config.scene_type == SceneType.TITLE:
            return self._generate_title_code(config)
        elif config.scene_type == SceneType.DIAGRAM:
            return self._generate_diagram_code(config)
        elif config.scene_type == SceneType.TEXT:
            return self._generate_text_code(config)
        else:
            return self._generate_generic_code(config)

    def _generate_title_code(self, config: SceneConfig) -> str:
        """Generate Manim code for a title scene."""
        title = config.title or "Untitled"
        subtitle = config.subtitle or ""
        duration = config.duration
        bg_color = config.background_color

        code = f'''
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "{bg_color}"

        # Title text
        title = Text("{title}", font_size=72, color=WHITE)
        title.move_to(UP * 0.5)

        # Subtitle if provided
        {"subtitle = Text('" + subtitle + "', font_size=36, color=GRAY_B)" if subtitle else "subtitle = None"}
        {"subtitle.next_to(title, DOWN, buff=0.5)" if subtitle else ""}

        # Animations
        self.play(Write(title), run_time=1.5)
        {"self.play(FadeIn(subtitle), run_time=0.8)" if subtitle else ""}
        self.wait({duration - 2.3 if subtitle else duration - 1.5})
        self.play(FadeOut(title), {"FadeOut(subtitle)," if subtitle else ""} run_time=0.8)
'''
        return code

    def _generate_diagram_code(self, config: SceneConfig) -> str:
        """Generate Manim code for a diagram scene."""
        diagram = config.diagram
        if not diagram:
            return self._generate_title_code(config)

        bg_color = diagram.background_color
        title = diagram.title
        duration = diagram.duration

        # Build element creation code
        element_lines = []
        element_names = []

        for i, elem in enumerate(diagram.elements):
            name = f"elem_{i}"
            element_names.append(name)

            if elem.get("type") == "box":
                color = elem.get("color", INDUSTRIAL_COLORS["primary"])
                x, y = elem.get("x", 0), elem.get("y", 0)
                w, h = elem.get("width", 2.5), elem.get("height", 1.0)
                label = elem.get("label", "").replace("\n", " ")

                element_lines.append(f"        # Box: {label}")
                element_lines.append(f"        {name}_rect = RoundedRectangle(width={w}, height={h}, corner_radius=0.1, fill_color=\"{color}\", fill_opacity=0.8, stroke_color=WHITE, stroke_width=2).move_to(RIGHT * {x} + UP * {y})")
                element_lines.append(f"        {name}_text = Text(\"{label}\", font_size=24, color=WHITE).move_to({name}_rect.get_center())")
                element_lines.append(f"        {name} = VGroup({name}_rect, {name}_text)")
                element_lines.append("")

        # Build arrow creation code
        arrow_lines = []
        arrow_names = []

        for i, arrow in enumerate(diagram.arrows):
            name = f"arrow_{i}"
            arrow_names.append(name)
            start = arrow.start
            end = arrow.end
            color = arrow.color

            arrow_lines.append(f"        # Arrow {i}")
            arrow_lines.append(f"        {name} = Arrow(start=RIGHT * {start[0]} + UP * {start[1]}, end=RIGHT * {end[0]} + UP * {end[1]}, color=\"{color}\", stroke_width=4, buff=0.1)")
            arrow_lines.append("")

        # Combine into full scene
        all_elements = ", ".join(element_names) if element_names else ""
        all_arrows = ", ".join(arrow_names) if arrow_names else ""
        element_code = "\n".join(element_lines) if element_lines else "        pass  # No elements"
        arrow_code = "\n".join(arrow_lines) if arrow_lines else "        pass  # No arrows"

        # Build animation lines
        elem_anim = f"self.play(*[FadeIn(e) for e in [{all_elements}]], run_time=1.5)" if all_elements else "pass"
        arrow_anim = f"self.play(*[GrowArrow(a) for a in [{all_arrows}]], run_time=1.0)" if all_arrows else "pass"

        # Build fadeout list
        fadeout_items = ["title"]
        if all_elements:
            fadeout_items.append(all_elements)
        if all_arrows:
            fadeout_items.append(all_arrows)
        fadeout_list = ", ".join(fadeout_items)

        code = f'''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "{bg_color}"

        # Title
        title = Text("{title}", font_size=48, color=WHITE).to_edge(UP, buff=0.5)

        # Create elements
{element_code}

        # Create arrows
{arrow_code}

        # Animate title
        self.play(Write(title), run_time=1.0)

        # Animate elements appearing
        {elem_anim}

        # Animate arrows
        {arrow_anim}

        # Hold
        self.wait({max(0.5, duration - 3.5)})

        # Fade out
        all_objects = [{fadeout_list}]
        self.play(*[FadeOut(obj) for obj in all_objects if obj], run_time=0.8)
'''
        return code

    def _generate_text_code(self, config: SceneConfig) -> str:
        """Generate Manim code for a text scene."""
        bg_color = config.background_color
        duration = config.duration

        text_code = []
        text_names = []

        for i, text_cfg in enumerate(config.texts):
            name = f"text_{i}"
            text_names.append(name)
            pos = text_cfg.position

            text_code.append(f'''
        {name} = Text("{text_cfg.text}", font_size={text_cfg.font_size}, color="{text_cfg.color}")
        {name}.move_to(RIGHT * {pos[0]} + UP * {pos[1]})
''')

        all_texts = ", ".join(text_names)

        code = f'''
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "{bg_color}"

{"".join(text_code)}

        # Animate texts
        for t in [{all_texts}]:
            self.play(FadeIn(t), run_time=0.5)

        self.wait({max(0.5, duration - len(config.texts) * 0.5 - 0.8)})

        self.play(*[FadeOut(t) for t in [{all_texts}]], run_time=0.8)
'''
        return code

    def _generate_generic_code(self, config: SceneConfig) -> str:
        """Generate generic Manim code for unsupported scene types."""
        return self._generate_title_code(config)

    def render(self, config: SceneConfig, output_name: Optional[str] = None) -> Optional[str]:
        """
        Render a scene configuration to an MP4 file.

        Args:
            config: Scene configuration to render
            output_name: Optional custom name for output file

        Returns:
            Path to the rendered MP4 file, or None if rendering failed
        """
        try:
            # Generate unique output name if not provided
            if not output_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_name = f"scene_{config.scene_type.value}_{timestamp}"

            # Generate Manim Python code
            scene_code = self._generate_scene_code(config)

            # Write to temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(scene_code)
                temp_path = f.name

            logger.debug(f"Generated Manim code at: {temp_path}")

            # Run Manim as subprocess
            quality_flag = self.quality_flags.get(self.quality, "-qm")
            output_dir_str = str(self.output_dir.absolute())

            cmd = [
                sys.executable, "-m", "manim",
                quality_flag,
                "--fps", str(self.fps),
                "--media_dir", output_dir_str,
                "--output_file", output_name,
                temp_path,
                "GeneratedScene"
            ]

            logger.info(f"Running Manim: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

            if result.returncode != 0:
                logger.error(f"Manim failed: {result.stderr}")
                return None

            # Find the output file
            # Manim creates: media_dir/videos/<scene_name>/<quality>/GeneratedScene.mp4
            possible_paths = [
                self.output_dir / "videos" / Path(temp_path).stem / self.quality.replace("_", "") / f"{output_name}.mp4",
                self.output_dir / "videos" / Path(temp_path).stem / "1080p60" / f"{output_name}.mp4",
                self.output_dir / "videos" / Path(temp_path).stem / "720p30" / f"{output_name}.mp4",
                self.output_dir / "videos" / Path(temp_path).stem / "480p15" / f"{output_name}.mp4",
            ]

            # Also check for GeneratedScene.mp4 naming
            for base in [self.output_dir / "videos"]:
                if base.exists():
                    for mp4 in base.rglob("*.mp4"):
                        if output_name in mp4.name or "GeneratedScene" in mp4.name:
                            # Move to our output directory with proper name
                            final_path = self.output_dir / f"{output_name}.mp4"
                            if final_path.exists():
                                final_path.unlink()  # Remove existing file
                            mp4.rename(final_path)
                            logger.info(f"Rendered clip: {final_path}")
                            return str(final_path)

            # Check explicit paths
            for path in possible_paths:
                if path.exists():
                    final_path = self.output_dir / f"{output_name}.mp4"
                    if path != final_path:
                        if final_path.exists():
                            final_path.unlink()
                        path.rename(final_path)
                    logger.info(f"Rendered clip: {final_path}")
                    return str(final_path)

            logger.error("Could not find rendered output file")
            return None

        except subprocess.TimeoutExpired:
            logger.error("Manim rendering timed out")
            return None
        except Exception as e:
            logger.error(f"Rendering failed: {e}")
            return None

    def render_title(self, title: str, subtitle: Optional[str] = None,
                     duration: float = 3.0) -> Optional[str]:
        """
        Render a title card scene.

        Args:
            title: Main title text
            subtitle: Optional subtitle
            duration: Scene duration in seconds

        Returns:
            Path to rendered MP4 or None
        """
        config = SceneConfig.title_scene(title, subtitle, duration)
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in title[:30])
        return self.render(config, f"title_{safe_name}")

    def render_diagram(self, diagram: DiagramConfig) -> Optional[str]:
        """
        Render a diagram scene.

        Args:
            diagram: Diagram configuration

        Returns:
            Path to rendered MP4 or None
        """
        config = SceneConfig.diagram_scene(diagram)
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in diagram.title[:30])
        return self.render(config, f"diagram_{safe_name}")

    def render_text(self, main_text: str, bullet_points: Optional[List[str]] = None,
                    duration: float = 5.0) -> Optional[str]:
        """
        Render a text scene with optional bullet points.

        Args:
            main_text: Main heading text
            bullet_points: Optional list of bullet points
            duration: Scene duration

        Returns:
            Path to rendered MP4 or None
        """
        config = SceneConfig.text_scene(main_text, bullet_points, duration)
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in main_text[:30])
        return self.render(config, f"text_{safe_name}")

    def render_test(self) -> Optional[str]:
        """
        Render a test scene to verify Manim is working.

        Returns:
            Path to rendered MP4 or None
        """
        # Create a simple PLC diagram for testing
        diagram = DiagramConfig(title="PLC Architecture", duration=5.0)
        diagram.add_box("CPU", 0, 2, color="#3B82F6")
        diagram.add_box("Input\nModule", -3, 0, color="#22C55E")
        diagram.add_box("Output\nModule", 3, 0, color="#EF4444")
        diagram.add_arrow((-2, 0.5), (-0.5, 1.5), color="#10B981")
        diagram.add_arrow((0.5, 1.5), (2, 0.5), color="#10B981")

        return self.render_diagram(diagram)


# CLI for testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    print("Testing ManimEngine...")
    engine = ManimEngine(output_dir="./ycb_output/test_clips")

    # Test 1: Title scene
    print("\n1. Rendering title scene...")
    result = engine.render_title("What is a PLC?", "Industrial Automation 101")
    if result:
        print(f"   Success: {result}")
    else:
        print("   Failed!")
        sys.exit(1)

    # Test 2: Diagram scene
    print("\n2. Rendering PLC diagram...")
    result = engine.render_test()
    if result:
        print(f"   Success: {result}")
    else:
        print("   Failed!")
        sys.exit(1)

    # Test 3: Text scene
    print("\n3. Rendering text scene...")
    result = engine.render_text(
        "Key Components",
        ["CPU - The brain of the PLC", "I/O Modules - Interface with field devices", "Power Supply - Provides DC power"],
        duration=6.0
    )
    if result:
        print(f"   Success: {result}")
    else:
        print("   Failed!")
        sys.exit(1)

    print("\nAll tests passed!")
