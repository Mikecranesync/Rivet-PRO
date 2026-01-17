"""
YCB Evaluation Module

LLM-as-Judge quality evaluation for video outputs.
Enables automated quality gates with feedback loops.
"""

from .video_judge import VideoQualityJudge, QualityEvaluation

__all__ = [
    "VideoQualityJudge",
    "QualityEvaluation",
]
