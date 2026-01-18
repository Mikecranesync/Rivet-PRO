"""
YCB Video Composition

Multi-scene video composition with transitions and effects.
"""

from .compositor import (
    VideoCompositor,
    CompositionResult,
    TransitionType,
    OverlayConfig,
)

__all__ = [
    "VideoCompositor",
    "CompositionResult",
    "TransitionType",
    "OverlayConfig",
]
