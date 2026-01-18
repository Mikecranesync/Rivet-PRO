"""
YCB Rendering Engines

Provides rendering engines for generating video clips:
- ManimEngine: 2D technical diagrams and animations
- BlenderEngine: 3D equipment animations (future)

Templates for common scene types:
- TitleTemplate, DiagramTemplate, FlowchartTemplate
- ComparisonTemplate, LadderLogicTemplate, TimelineTemplate
"""

from .manim_engine import ManimEngine
from .scene_types import (
    SceneType,
    SceneConfig,
    TextConfig,
    ShapeConfig,
    ArrowConfig,
    DiagramConfig,
    INDUSTRIAL_COLORS,
    PLC_COLORS,
)
from .templates import (
    TitleTemplate,
    DiagramTemplate,
    DiagramElement,
    DiagramCallout,
    FlowchartTemplate,
    FlowchartStep,
    ComparisonTemplate,
    ComparisonItem,
    LadderLogicTemplate,
    LadderRung,
    TimelineTemplate,
    TimelineEvent,
    TemplateFactory,
    TransitionType,
)

__all__ = [
    # Engine
    "ManimEngine",
    # Scene types
    "SceneType",
    "SceneConfig",
    "TextConfig",
    "ShapeConfig",
    "ArrowConfig",
    "DiagramConfig",
    # Color palettes
    "INDUSTRIAL_COLORS",
    "PLC_COLORS",
    # Templates
    "TitleTemplate",
    "DiagramTemplate",
    "DiagramElement",
    "DiagramCallout",
    "FlowchartTemplate",
    "FlowchartStep",
    "ComparisonTemplate",
    "ComparisonItem",
    "LadderLogicTemplate",
    "LadderRung",
    "TimelineTemplate",
    "TimelineEvent",
    "TemplateFactory",
    "TransitionType",
]
