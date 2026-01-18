"""
YCB Rendering Engines

Provides rendering engines for generating video clips:
- ManimEngine: 2D technical diagrams and animations
- BlenderEngine: 3D equipment animations (future)
"""

from .manim_engine import ManimEngine
from .scene_types import (
    SceneType,
    SceneConfig,
    TextConfig,
    ShapeConfig,
    ArrowConfig,
    DiagramConfig,
)

__all__ = [
    "ManimEngine",
    "SceneType",
    "SceneConfig",
    "TextConfig",
    "ShapeConfig",
    "ArrowConfig",
    "DiagramConfig",
]
