"""
Scene Type Definitions for Manim Rendering

Pydantic models for structured scene descriptions that can be rendered by ManimEngine.
"""

from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field


class SceneType(str, Enum):
    """Types of scenes that can be rendered."""
    TITLE = "title"
    TEXT = "text"
    DIAGRAM = "diagram"
    FLOWCHART = "flowchart"
    COMPARISON = "comparison"
    LADDER_LOGIC = "ladder_logic"
    TIMELINE = "timeline"
    CUSTOM = "custom"


@dataclass
class TextConfig:
    """Configuration for text elements."""
    text: str
    font_size: int = 48
    color: str = "#FFFFFF"
    position: Tuple[float, float, float] = (0, 0, 0)
    alignment: str = "center"  # left, center, right
    weight: str = "normal"  # normal, bold


@dataclass
class ShapeConfig:
    """Configuration for shape elements."""
    shape_type: str  # rectangle, circle, arrow, line
    position: Tuple[float, float, float] = (0, 0, 0)
    width: float = 2.0
    height: float = 1.0
    color: str = "#3B82F6"  # Fill color
    stroke_color: str = "#FFFFFF"
    stroke_width: float = 2.0
    label: Optional[str] = None
    label_color: str = "#FFFFFF"


@dataclass
class ArrowConfig:
    """Configuration for arrow/connection elements."""
    start: Tuple[float, float, float]
    end: Tuple[float, float, float]
    color: str = "#10B981"
    stroke_width: float = 4.0
    tip_length: float = 0.25
    label: Optional[str] = None


@dataclass
class DiagramConfig:
    """Configuration for a complete diagram scene."""
    title: str
    elements: List[Dict[str, Any]] = field(default_factory=list)
    arrows: List[ArrowConfig] = field(default_factory=list)
    background_color: str = "#1E1E1E"
    duration: float = 5.0

    def add_box(self, label: str, x: float, y: float,
                width: float = 2.5, height: float = 1.0,
                color: str = "#3B82F6") -> "DiagramConfig":
        """Add a labeled box to the diagram."""
        self.elements.append({
            "type": "box",
            "label": label,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "color": color
        })
        return self

    def add_arrow(self, from_pos: Tuple[float, float],
                  to_pos: Tuple[float, float],
                  label: Optional[str] = None,
                  color: str = "#10B981") -> "DiagramConfig":
        """Add an arrow between positions."""
        self.arrows.append(ArrowConfig(
            start=(from_pos[0], from_pos[1], 0),
            end=(to_pos[0], to_pos[1], 0),
            color=color,
            label=label
        ))
        return self


@dataclass
class SceneConfig:
    """Complete scene configuration for rendering."""
    scene_type: SceneType
    title: Optional[str] = None
    subtitle: Optional[str] = None
    texts: List[TextConfig] = field(default_factory=list)
    shapes: List[ShapeConfig] = field(default_factory=list)
    arrows: List[ArrowConfig] = field(default_factory=list)
    diagram: Optional[DiagramConfig] = None
    duration: float = 5.0
    background_color: str = "#1E1E1E"
    animation_style: str = "fade"  # fade, write, grow

    @classmethod
    def title_scene(cls, title: str, subtitle: Optional[str] = None,
                    duration: float = 3.0) -> "SceneConfig":
        """Create a title card scene."""
        return cls(
            scene_type=SceneType.TITLE,
            title=title,
            subtitle=subtitle,
            duration=duration,
            animation_style="write"
        )

    @classmethod
    def text_scene(cls, main_text: str, bullet_points: Optional[List[str]] = None,
                   duration: float = 5.0) -> "SceneConfig":
        """Create a text-based scene with optional bullet points."""
        texts = [TextConfig(text=main_text, font_size=36, position=(0, 2, 0))]
        if bullet_points:
            for i, point in enumerate(bullet_points):
                texts.append(TextConfig(
                    text=f"• {point}",
                    font_size=28,
                    position=(-3, 1 - i * 0.8, 0),
                    alignment="left"
                ))
        return cls(
            scene_type=SceneType.TEXT,
            texts=texts,
            duration=duration
        )

    @classmethod
    def diagram_scene(cls, diagram: DiagramConfig) -> "SceneConfig":
        """Create a diagram scene."""
        return cls(
            scene_type=SceneType.DIAGRAM,
            title=diagram.title,
            diagram=diagram,
            duration=diagram.duration,
            background_color=diagram.background_color
        )


# Preset color palettes for industrial themes
INDUSTRIAL_COLORS = {
    "primary": "#3B82F6",      # Blue
    "secondary": "#10B981",    # Green
    "accent": "#F59E0B",       # Amber
    "danger": "#EF4444",       # Red
    "neutral": "#6B7280",      # Gray
    "background": "#1a1a2e",   # Dark (Manim default dark)
    "text": "#FFFFFF",         # White
    "arrow": "#10B981",        # Green - for flow arrows
    "success": "#22C55E",      # Bright green - success/highlight
}

PLC_COLORS = {
    "input": "#22C55E",        # Green - inputs
    "output": "#EF4444",       # Red - outputs
    "internal": "#3B82F6",     # Blue - internal
    "timer": "#F59E0B",        # Amber - timers
    "counter": "#8B5CF6",      # Purple - counters
    "rung": "#9CA3AF",         # Gray - rungs
    "rail": "#4A5568",         # Dark gray - power rails
    "contact": "#3B82F6",      # Blue - contacts
    "coil": "#22C55E",         # Green - output coils
    "active": "#10B981",       # Bright green - active/energized
}
