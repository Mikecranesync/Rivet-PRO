"""
YCB Video Composition

Multi-scene video composition with transitions and effects.
"""

from .compositor import (
    VideoCompositor,
    CompositionResult,
    TransitionType,
    OverlayConfig,
    ClipConfig,
)
from .post_processing import (
    PostProcessor,
    PostProcessConfig,
    PostProcessResult,
    ColorGradePreset,
    OutputQuality,
    WatermarkConfig,
    SubtitleEntry,
)

__all__ = [
    "VideoCompositor",
    "CompositionResult",
    "TransitionType",
    "OverlayConfig",
    "ClipConfig",
    "PostProcessor",
    "PostProcessConfig",
    "PostProcessResult",
    "ColorGradePreset",
    "OutputQuality",
    "WatermarkConfig",
    "SubtitleEntry",
]
