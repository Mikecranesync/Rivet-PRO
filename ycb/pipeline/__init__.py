"""
YCB Pipeline Module

Video generation pipeline with free/cheap provider fallbacks.

Full pipeline:
1. Generate script (Groq -> Anthropic -> OpenAI)
2. Generate voice (ElevenLabs -> Edge TTS -> Piper)
3. Generate thumbnail (Pollinations -> Stability -> Placeholder)
4. Assemble MP4 video (MoviePy)
5. Upload to YouTube (optional)

V3 Pipeline (Manim + Blender):
1. Script -> Storyboard (LLM)
2. Storyboard -> Scene rendering (Manim/Blender)
3. Scene clips -> Video composition (FFmpeg)
4. Post-processing -> Final video

Cost: $0/month with free providers.
"""

from .video_generator import VideoGenerator, GeneratedVideo
from .video_assembler import VideoAssembler, assemble_from_package
from .quality_iteration import QualityIterativeGenerator, QualityIterationResult
from .metrics import PipelineMetrics, VideoMetric, DailyStats
from .autonomous_loop import AutonomousLoop, TopicQueue
from .video_generator_v3 import VideoGeneratorV3, V3GenerationConfig, V3GenerationResult

__all__ = [
    "VideoGenerator",
    "GeneratedVideo",
    "VideoAssembler",
    "assemble_from_package",
    "QualityIterativeGenerator",
    "QualityIterationResult",
    "PipelineMetrics",
    "VideoMetric",
    "DailyStats",
    "AutonomousLoop",
    "TopicQueue",
    # V3 Pipeline
    "VideoGeneratorV3",
    "V3GenerationConfig",
    "V3GenerationResult",
]
