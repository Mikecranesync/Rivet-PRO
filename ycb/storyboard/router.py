"""
Scene-to-Renderer Routing System

Dispatches scenes to the appropriate rendering engine based on scene type.
Handles fallbacks when engines are unavailable.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from .models import Scene, SceneType, RenderEngine, Storyboard, TemplateParameters

logger = logging.getLogger(__name__)


class RouteStatus(Enum):
    """Status of a routing attempt."""
    SUCCESS = "success"
    FALLBACK = "fallback"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RenderResult:
    """Result of rendering a scene."""
    scene_id: str
    status: RouteStatus
    clip_path: Optional[str] = None
    engine_used: Optional[RenderEngine] = None
    duration: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "status": self.status.value,
            "clip_path": self.clip_path,
            "engine_used": self.engine_used.value if self.engine_used else None,
            "duration": self.duration,
            "error": self.error,
        }


class SceneRouter:
    """
    Routes scenes to appropriate rendering engines.

    Handles:
    - Dispatching to Manim for 2D scenes
    - Dispatching to Blender for 3D scenes (when available)
    - Fallback to Manim when Blender unavailable
    - Placeholder handling for external/stock footage
    """

    def __init__(self, output_dir: str = "./ycb_output/clips",
                 manim_quality: str = "medium_quality",
                 enable_blender: bool = False):
        """
        Initialize the scene router.

        Args:
            output_dir: Directory to save rendered clips
            manim_quality: Quality preset for Manim rendering
            enable_blender: Whether to attempt Blender rendering
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manim_quality = manim_quality
        self.enable_blender = enable_blender

        # Engine availability
        self._manim_available = None
        self._blender_available = None

        # Engine instances (lazy loaded)
        self._manim_engine = None

        # Routing table: scene_type -> (primary_engine, fallback_engine)
        self.routing_table: Dict[SceneType, tuple] = {
            SceneType.TITLE: (RenderEngine.MANIM, None),
            SceneType.TEXT: (RenderEngine.MANIM, None),
            SceneType.DIAGRAM: (RenderEngine.MANIM, None),
            SceneType.FLOWCHART: (RenderEngine.MANIM, None),
            SceneType.COMPARISON: (RenderEngine.MANIM, None),
            SceneType.LADDER_LOGIC: (RenderEngine.MANIM, None),
            SceneType.TIMELINE: (RenderEngine.MANIM, None),
            SceneType.THREE_D: (RenderEngine.BLENDER, RenderEngine.MANIM),  # Fallback to Manim
            SceneType.B_ROLL: (RenderEngine.EXTERNAL, None),
            SceneType.TRANSITION: (RenderEngine.NONE, None),
        }

        logger.info(f"SceneRouter initialized: output_dir={output_dir}")

    def _check_manim_available(self) -> bool:
        """Check if Manim is available."""
        if self._manim_available is not None:
            return self._manim_available

        try:
            import subprocess
            import sys
            result = subprocess.run(
                [sys.executable, "-m", "manim", "--version"],
                capture_output=True, timeout=10
            )
            self._manim_available = result.returncode == 0
        except Exception:
            self._manim_available = False

        logger.info(f"Manim available: {self._manim_available}")
        return self._manim_available

    def _check_blender_available(self) -> bool:
        """Check if Blender is available."""
        if not self.enable_blender:
            return False

        if self._blender_available is not None:
            return self._blender_available

        try:
            import subprocess
            result = subprocess.run(
                ["blender", "--version"],
                capture_output=True, timeout=10
            )
            self._blender_available = result.returncode == 0
        except Exception:
            self._blender_available = False

        logger.info(f"Blender available: {self._blender_available}")
        return self._blender_available

    def _get_manim_engine(self):
        """Get or create Manim engine instance."""
        if self._manim_engine is None:
            from ycb.rendering import ManimEngine
            self._manim_engine = ManimEngine(
                output_dir=str(self.output_dir),
                quality=self.manim_quality
            )
        return self._manim_engine

    def route(self, scene: Scene) -> RenderResult:
        """
        Route a scene to the appropriate renderer.

        Args:
            scene: Scene to render

        Returns:
            RenderResult with clip path or error
        """
        logger.info(f"Routing scene {scene.scene_id} ({scene.scene_type.value})")

        # Get routing info
        primary, fallback = self.routing_table.get(
            scene.scene_type,
            (RenderEngine.MANIM, None)
        )

        # Handle special cases
        if primary == RenderEngine.NONE:
            return RenderResult(
                scene_id=scene.scene_id,
                status=RouteStatus.SKIPPED,
                engine_used=RenderEngine.NONE,
                duration=scene.duration,
            )

        if primary == RenderEngine.EXTERNAL:
            return self._handle_external(scene)

        # Try primary engine
        result = self._render_with_engine(scene, primary)

        # If failed and fallback available, try fallback
        if result.status == RouteStatus.FAILED and fallback:
            logger.warning(f"Primary engine failed, trying fallback: {fallback.value}")
            result = self._render_with_engine(scene, fallback)
            if result.status == RouteStatus.SUCCESS:
                result.status = RouteStatus.FALLBACK

        return result

    def _render_with_engine(self, scene: Scene, engine: RenderEngine) -> RenderResult:
        """Render a scene with a specific engine."""

        if engine == RenderEngine.MANIM:
            return self._render_manim(scene)
        elif engine == RenderEngine.BLENDER:
            return self._render_blender(scene)
        else:
            return RenderResult(
                scene_id=scene.scene_id,
                status=RouteStatus.FAILED,
                error=f"Unknown engine: {engine.value}"
            )

    def _render_manim(self, scene: Scene) -> RenderResult:
        """Render a scene with Manim."""

        if not self._check_manim_available():
            return RenderResult(
                scene_id=scene.scene_id,
                status=RouteStatus.FAILED,
                error="Manim not available"
            )

        try:
            engine = self._get_manim_engine()
            clip_path = self._render_manim_scene(engine, scene)

            if clip_path:
                return RenderResult(
                    scene_id=scene.scene_id,
                    status=RouteStatus.SUCCESS,
                    clip_path=clip_path,
                    engine_used=RenderEngine.MANIM,
                    duration=scene.duration,
                )
            else:
                return RenderResult(
                    scene_id=scene.scene_id,
                    status=RouteStatus.FAILED,
                    engine_used=RenderEngine.MANIM,
                    error="Manim rendering returned no output"
                )

        except Exception as e:
            logger.error(f"Manim rendering failed: {e}")
            return RenderResult(
                scene_id=scene.scene_id,
                status=RouteStatus.FAILED,
                engine_used=RenderEngine.MANIM,
                error=str(e)
            )

    def _render_manim_scene(self, engine, scene: Scene) -> Optional[str]:
        """Render a specific scene type with Manim."""

        params = scene.template_params
        if not params:
            # Create default params from visual description
            params = TemplateParameters(
                template_name="TitleTemplate",
                title=scene.visual_description.main_subject,
                duration=scene.duration,
            )

        # Route to appropriate render method based on template
        template_name = params.template_name

        if template_name == "TitleTemplate":
            return engine.render_title(
                title=params.title or scene.visual_description.main_subject,
                subtitle=params.extra.get("subtitle") if params.extra else None,
                duration=params.duration or scene.duration,
            )

        elif template_name == "DiagramTemplate":
            from ycb.rendering import DiagramConfig
            diagram = DiagramConfig(
                title=params.title or scene.visual_description.main_subject,
                duration=params.duration or scene.duration,
            )
            # Add elements from params
            for elem in params.elements:
                diagram.add_box(
                    label=elem.get("label", ""),
                    x=elem.get("x", 0),
                    y=elem.get("y", 0),
                    color=elem.get("color", "#3B82F6"),
                )
            # Add arrows
            for arrow in params.arrows:
                start = arrow.get("start", (0, 0))
                end = arrow.get("end", (1, 1))
                diagram.add_arrow(start, end)

            return engine.render_diagram(diagram)

        elif template_name == "FlowchartTemplate":
            from ycb.rendering.templates import FlowchartTemplate
            template = FlowchartTemplate(
                title=params.title or scene.visual_description.main_subject,
                duration=params.duration or scene.duration,
            )
            for step in params.steps:
                template.add_step(
                    label=step.get("label", ""),
                    color=step.get("color"),
                    shape=step.get("shape", "rectangle"),
                )
            return self._render_template(template, "FlowchartScene", scene.scene_id)

        elif template_name == "ComparisonTemplate":
            from ycb.rendering.templates import ComparisonTemplate
            template = ComparisonTemplate(
                title=params.title or scene.visual_description.main_subject,
                columns=params.columns or ["Feature", "Value"],
                duration=params.duration or scene.duration,
            )
            for item in params.items:
                template.add_item(
                    item.get("label", ""),
                    *item.get("values", []),
                )
            return self._render_template(template, "ComparisonScene", scene.scene_id)

        elif template_name == "LadderLogicTemplate":
            from ycb.rendering.templates import LadderLogicTemplate
            template = LadderLogicTemplate(
                title=params.title or scene.visual_description.main_subject,
                duration=params.duration or scene.duration,
            )
            for rung in params.rungs:
                inputs = [(i.get("type", "xic"), i.get("label", "")) for i in rung.get("inputs", [])]
                output = (rung.get("output", {}).get("type", "ote"), rung.get("output", {}).get("label", ""))
                template.add_rung(inputs, output)
            return self._render_template(template, "LadderLogicScene", scene.scene_id)

        elif template_name == "TimelineTemplate":
            from ycb.rendering.templates import TimelineTemplate
            template = TimelineTemplate(
                title=params.title or scene.visual_description.main_subject,
                duration=params.duration or scene.duration,
            )
            for event in params.events:
                template.add_event(
                    label=event.get("label", ""),
                    color=event.get("color"),
                )
            return self._render_template(template, "TimelineScene", scene.scene_id)

        else:
            # Default to title
            return engine.render_title(
                title=params.title or scene.visual_description.main_subject,
                duration=params.duration or scene.duration,
            )

    def _render_template(self, template, scene_class: str, scene_id: str) -> Optional[str]:
        """Render a template by generating code and running Manim."""
        import subprocess
        import sys
        import tempfile

        code = template.generate_code()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            output_name = f"clip_{scene_id}"

            cmd = [
                sys.executable, "-m", "manim",
                self._get_quality_flag(),
                "--fps", "30",
                "--media_dir", str(self.output_dir),
                "--output_file", output_name,
                temp_path,
                scene_class
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.error(f"Manim failed: {result.stderr[:500]}")
                return None

            # Find output
            for mp4 in self.output_dir.rglob("*.mp4"):
                if output_name in mp4.name.lower() or scene_id in mp4.name.lower():
                    final_path = self.output_dir / f"{output_name}.mp4"
                    if final_path.exists():
                        final_path.unlink()
                    mp4.rename(final_path)
                    return str(final_path)

            return None

        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return None
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def _get_quality_flag(self) -> str:
        """Get Manim quality flag."""
        flags = {
            "low_quality": "-ql",
            "medium_quality": "-qm",
            "high_quality": "-qh",
            "production_quality": "-qp",
        }
        return flags.get(self.manim_quality, "-qm")

    def _render_blender(self, scene: Scene) -> RenderResult:
        """Render a scene with Blender."""

        if not self._check_blender_available():
            return RenderResult(
                scene_id=scene.scene_id,
                status=RouteStatus.FAILED,
                error="Blender not available"
            )

        # Blender rendering would go here
        # For now, return failed since Blender isn't implemented
        return RenderResult(
            scene_id=scene.scene_id,
            status=RouteStatus.FAILED,
            error="Blender rendering not implemented"
        )

    def _handle_external(self, scene: Scene) -> RenderResult:
        """Handle external/stock footage placeholder."""

        # For external content, we just create a placeholder result
        # The actual footage would be sourced externally
        return RenderResult(
            scene_id=scene.scene_id,
            status=RouteStatus.SUCCESS,
            clip_path=None,  # No clip generated - external source
            engine_used=RenderEngine.EXTERNAL,
            duration=scene.duration,
        )

    def route_storyboard(self, storyboard: Storyboard,
                          parallel: bool = False) -> List[RenderResult]:
        """
        Route all scenes in a storyboard.

        Args:
            storyboard: Storyboard to render
            parallel: Whether to render scenes in parallel (not yet implemented)

        Returns:
            List of RenderResults for all scenes
        """
        logger.info(f"Routing storyboard: {storyboard.title} ({len(storyboard.scenes)} scenes)")

        results = []
        for scene in storyboard.scenes:
            result = self.route(scene)
            results.append(result)

            # Log progress
            status_emoji = {
                RouteStatus.SUCCESS: "[OK]",
                RouteStatus.FALLBACK: "[FALLBACK]",
                RouteStatus.FAILED: "[FAIL]",
                RouteStatus.SKIPPED: "[SKIP]",
            }
            logger.info(f"  {status_emoji.get(result.status, '?')} {scene.scene_id}: {result.status.value}")

        # Summary
        success_count = sum(1 for r in results if r.status in [RouteStatus.SUCCESS, RouteStatus.FALLBACK])
        logger.info(f"Routing complete: {success_count}/{len(results)} scenes rendered")

        return results

    def get_available_engines(self) -> Dict[str, bool]:
        """Get availability status of all engines."""
        return {
            "manim": self._check_manim_available(),
            "blender": self._check_blender_available(),
        }
