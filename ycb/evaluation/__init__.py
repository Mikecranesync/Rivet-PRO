"""
YCB Evaluation Module

LLM-as-Judge quality evaluation for video outputs.
Enables automated quality gates with feedback loops.

v1: Basic quality evaluation (7.0 threshold)
v3: Visual quality focus with Manim/Blender standards (8.5 threshold)
"""

from .video_judge import VideoQualityJudge, QualityEvaluation
from .video_judge_v3 import VideoQualityJudgeV3, V3QualityEvaluation

__all__ = [
    # v1 Judge
    "VideoQualityJudge",
    "QualityEvaluation",
    # v3 Judge (Manim/Blender)
    "VideoQualityJudgeV3",
    "V3QualityEvaluation",
]
