"""
YCB Pipeline Module

Video generation pipeline with free/cheap provider fallbacks.

Full pipeline:
1. Generate script (Groq -> Anthropic -> OpenAI)
2. Generate voice (ElevenLabs -> Edge TTS -> Piper)
3. Generate thumbnail (Pollinations -> Stability -> Placeholder)
4. Assemble MP4 video (MoviePy)
5. Upload to YouTube (optional)

Cost: $0/month with free providers.
"""

from .video_generator import VideoGenerator, GeneratedVideo
from .video_assembler import VideoAssembler, assemble_from_package

__all__ = [
    "VideoGenerator",
    "GeneratedVideo",
    "VideoAssembler",
    "assemble_from_package",
]
