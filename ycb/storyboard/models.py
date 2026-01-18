"""
Storyboard Data Models

Defines the structures for scenes, storyboards, and visual descriptions.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class SceneType(Enum):
    """Types of scenes that can be rendered."""
    TITLE = "title"
    TEXT = "text"
    DIAGRAM = "diagram"
    FLOWCHART = "flowchart"
    COMPARISON = "comparison"
    LADDER_LOGIC = "ladder_logic"
    TIMELINE = "timeline"
    THREE_D = "3d"  # Blender scenes
    B_ROLL = "b_roll"  # Stock footage / external
    TRANSITION = "transition"


class RenderEngine(Enum):
    """Rendering engines available for scenes."""
    MANIM = "manim"
    BLENDER = "blender"
    EXTERNAL = "external"  # Stock footage, pre-rendered
    NONE = "none"  # Transition/placeholder


@dataclass
class VisualDescription:
    """
    Structured description of visual elements in a scene.

    Used to guide the rendering engine on what to create.
    """
    main_subject: str  # Primary visual element
    elements: List[str] = field(default_factory=list)  # Additional elements
    layout: str = "centered"  # centered, left, right, split
    color_scheme: str = "industrial"  # industrial, clean, warm
    annotations: List[str] = field(default_factory=list)  # Callouts/labels
    animation_style: str = "professional"  # professional, dynamic, minimal

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "main_subject": self.main_subject,
            "elements": self.elements,
            "layout": self.layout,
            "color_scheme": self.color_scheme,
            "annotations": self.annotations,
            "animation_style": self.animation_style,
        }


@dataclass
class TemplateParameters:
    """
    Parameters for a specific template.

    These are passed to the template class during rendering.
    """
    template_name: str  # e.g., "DiagramTemplate", "FlowchartTemplate"
    title: Optional[str] = None
    elements: List[Dict[str, Any]] = field(default_factory=list)
    arrows: List[Dict[str, Any]] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    items: List[Dict[str, Any]] = field(default_factory=list)
    rungs: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    orientation: str = "horizontal"
    duration: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)  # Additional params

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "template_name": self.template_name,
            "title": self.title,
            "duration": self.duration,
            "orientation": self.orientation,
        }
        if self.elements:
            result["elements"] = self.elements
        if self.arrows:
            result["arrows"] = self.arrows
        if self.steps:
            result["steps"] = self.steps
        if self.columns:
            result["columns"] = self.columns
        if self.items:
            result["items"] = self.items
        if self.rungs:
            result["rungs"] = self.rungs
        if self.events:
            result["events"] = self.events
        if self.extra:
            result.update(self.extra)
        return result


@dataclass
class Scene:
    """
    A single scene in a storyboard.

    Contains all information needed to render one segment of the video.
    """
    scene_id: str
    scene_type: SceneType
    duration: float  # Duration in seconds
    narration_text: str  # Text to be narrated during this scene
    visual_description: VisualDescription
    template_params: Optional[TemplateParameters] = None
    render_engine: RenderEngine = RenderEngine.MANIM
    start_time: float = 0.0  # Start time in the video (filled during composition)
    notes: str = ""  # Additional notes for editors/reviewers

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "scene_id": self.scene_id,
            "scene_type": self.scene_type.value,
            "duration": self.duration,
            "narration_text": self.narration_text,
            "visual_description": self.visual_description.to_dict(),
            "template_params": self.template_params.to_dict() if self.template_params else None,
            "render_engine": self.render_engine.value,
            "start_time": self.start_time,
            "notes": self.notes,
        }


@dataclass
class Storyboard:
    """
    A complete storyboard for a video.

    Contains all scenes in order, plus metadata about the video.
    """
    title: str
    description: str
    target_duration: float  # Target total duration in seconds
    scenes: List[Scene] = field(default_factory=list)
    total_duration: float = 0.0  # Actual total duration (sum of scenes)
    word_count: int = 0  # Total narration word count
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_scene(self, scene: Scene) -> None:
        """Add a scene to the storyboard."""
        scene.start_time = self.total_duration
        self.scenes.append(scene)
        self.total_duration += scene.duration
        self.word_count += len(scene.narration_text.split())

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        """Get a scene by ID."""
        for scene in self.scenes:
            if scene.scene_id == scene_id:
                return scene
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "target_duration": self.target_duration,
            "total_duration": self.total_duration,
            "word_count": self.word_count,
            "scene_count": len(self.scenes),
            "scenes": [s.to_dict() for s in self.scenes],
            "metadata": self.metadata,
        }

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            f"Storyboard: {self.title}",
            f"Description: {self.description}",
            f"Target Duration: {self.target_duration}s | Actual: {self.total_duration:.1f}s",
            f"Scenes: {len(self.scenes)} | Words: {self.word_count}",
            "",
            "Scene Breakdown:",
        ]

        for i, scene in enumerate(self.scenes, 1):
            lines.append(
                f"  {i}. [{scene.scene_type.value}] {scene.duration:.1f}s - "
                f"{scene.visual_description.main_subject[:40]}..."
            )

        return "\n".join(lines)
