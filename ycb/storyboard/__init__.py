"""
YCB Storyboard Generation

Converts scripts into structured storyboards with scene definitions
using LLM intelligence for smart scene planning.
"""

from .generator import StoryboardGenerator
from .models import (
    Scene,
    SceneType,
    Storyboard,
    VisualDescription,
)

__all__ = [
    "StoryboardGenerator",
    "Scene",
    "SceneType",
    "Storyboard",
    "VisualDescription",
]
