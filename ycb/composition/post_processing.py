"""
Post-Processing Effects Pipeline

Applies polish effects to final video output for professional quality.
Includes color grading, audio normalization, watermarks, and subtitles.
"""

import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class ColorGradePreset(Enum):
    """Color grading presets."""
    NONE = "none"
    INDUSTRIAL = "industrial"  # Cool, technical look
    CLEAN = "clean"  # Bright, crisp colors
    WARM = "warm"  # Warm tones
    CINEMATIC = "cinematic"  # High contrast, desaturated
    PROFESSIONAL = "professional"  # Balanced, polished


class OutputQuality(Enum):
    """Output quality presets."""
    PREVIEW = "preview"  # 360p, low bitrate
    SD = "sd"  # 480p
    HD = "hd"  # 720p
    FULL_HD = "full_hd"  # 1080p
    QHD = "qhd"  # 1440p
    UHD = "uhd"  # 4K


@dataclass
class SubtitleEntry:
    """Single subtitle entry."""
    start_time: float  # seconds
    end_time: float  # seconds
    text: str

    def to_srt_entry(self, index: int) -> str:
        """Convert to SRT format entry."""
        start = self._format_timestamp(self.start_time)
        end = self._format_timestamp(self.end_time)
        return f"{index}\n{start} --> {end}\n{text}\n"

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
        }


@dataclass
class WatermarkConfig:
    """Watermark/logo overlay configuration."""
    image_path: str
    position: str = "bottom_right"  # top_left, top_right, bottom_left, bottom_right
    opacity: float = 0.7  # 0.0 to 1.0
    scale: float = 0.15  # Scale relative to video width
    margin: int = 20  # Margin from edge in pixels

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_path": self.image_path,
            "position": self.position,
            "opacity": self.opacity,
            "scale": self.scale,
            "margin": self.margin,
        }


@dataclass
class PostProcessConfig:
    """Configuration for post-processing."""
    color_grade: ColorGradePreset = ColorGradePreset.PROFESSIONAL
    output_quality: OutputQuality = OutputQuality.FULL_HD
    normalize_audio: bool = True
    audio_loudness: float = -16.0  # Target loudness in LUFS
    watermark: Optional[WatermarkConfig] = None
    subtitles: List[SubtitleEntry] = field(default_factory=list)
    add_fade_in: float = 0.0  # Fade in duration (0 = none)
    add_fade_out: float = 0.0  # Fade out duration
    sharpen: bool = False
    denoise: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "color_grade": self.color_grade.value,
            "output_quality": self.output_quality.value,
            "normalize_audio": self.normalize_audio,
            "audio_loudness": self.audio_loudness,
            "watermark": self.watermark.to_dict() if self.watermark else None,
            "subtitle_count": len(self.subtitles),
            "add_fade_in": self.add_fade_in,
            "add_fade_out": self.add_fade_out,
            "sharpen": self.sharpen,
            "denoise": self.denoise,
        }


@dataclass
class PostProcessResult:
    """Result of post-processing."""
    success: bool
    output_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    duration: float = 0.0
    file_size: int = 0
    error: Optional[str] = None
    effects_applied: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output_path": self.output_path,
            "subtitle_path": self.subtitle_path,
            "duration": self.duration,
            "file_size": self.file_size,
            "error": self.error,
            "effects_applied": self.effects_applied,
        }


class PostProcessor:
    """
    Post-processing effects pipeline.

    Applies professional polish to final video output including:
    - Color grading with presets
    - Audio normalization
    - Watermark/logo overlay
    - Subtitle track generation
    - Output quality presets
    """

    # Quality preset configurations (width, height, video_bitrate, audio_bitrate)
    QUALITY_PRESETS = {
        OutputQuality.PREVIEW: (640, 360, "500k", "64k"),
        OutputQuality.SD: (854, 480, "1M", "96k"),
        OutputQuality.HD: (1280, 720, "4M", "128k"),
        OutputQuality.FULL_HD: (1920, 1080, "8M", "192k"),
        OutputQuality.QHD: (2560, 1440, "16M", "256k"),
        OutputQuality.UHD: (3840, 2160, "35M", "320k"),
    }

    # Color grading LUT filters (using FFmpeg eq and colorbalance)
    COLOR_GRADE_FILTERS = {
        ColorGradePreset.NONE: "",
        ColorGradePreset.INDUSTRIAL: "eq=saturation=0.85:contrast=1.1:brightness=-0.02,colorbalance=rs=-0.1:gs=-0.05:bs=0.15",
        ColorGradePreset.CLEAN: "eq=saturation=1.1:contrast=1.05:brightness=0.03",
        ColorGradePreset.WARM: "colorbalance=rs=0.15:gs=0.05:bs=-0.1,eq=saturation=1.05",
        ColorGradePreset.CINEMATIC: "eq=saturation=0.8:contrast=1.2:brightness=-0.05,curves=preset=cross_process",
        ColorGradePreset.PROFESSIONAL: "eq=saturation=0.95:contrast=1.05,unsharp=5:5:0.5:5:5:0",
    }

    def __init__(self, output_dir: str = "./ycb_output/final"):
        """
        Initialize the post-processor.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._ffmpeg_available = None
        logger.info(f"PostProcessor initialized: output_dir={output_dir}")

    def _check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available."""
        if self._ffmpeg_available is not None:
            return self._ffmpeg_available

        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=10,
            )
            self._ffmpeg_available = result.returncode == 0
        except Exception:
            self._ffmpeg_available = False

        logger.info(f"FFmpeg available: {self._ffmpeg_available}")
        return self._ffmpeg_available

    def process(
        self,
        input_path: str,
        output_name: str,
        config: Optional[PostProcessConfig] = None,
    ) -> PostProcessResult:
        """
        Apply post-processing effects to video.

        Args:
            input_path: Input video path
            output_name: Output filename (without extension)
            config: Post-processing configuration

        Returns:
            PostProcessResult with output path or error
        """
        if not self._check_ffmpeg_available():
            return PostProcessResult(
                success=False,
                error="FFmpeg not available",
            )

        if not Path(input_path).exists():
            return PostProcessResult(
                success=False,
                error=f"Input file not found: {input_path}",
            )

        config = config or PostProcessConfig()
        logger.info(f"Post-processing: {input_path} with {config.color_grade.value}")

        effects_applied = []

        try:
            # Build video filter chain
            video_filters = self._build_video_filters(config)
            if video_filters:
                effects_applied.append(f"color_grade:{config.color_grade.value}")

            # Build audio filter chain
            audio_filters = self._build_audio_filters(config)
            if audio_filters:
                effects_applied.append("audio_normalize")

            # Get quality settings
            width, height, video_br, audio_br = self.QUALITY_PRESETS.get(
                config.output_quality,
                self.QUALITY_PRESETS[OutputQuality.FULL_HD]
            )
            effects_applied.append(f"quality:{config.output_quality.value}")

            output_path = self.output_dir / f"{output_name}.mp4"

            # Build FFmpeg command
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
            ]

            # Add watermark if configured
            if config.watermark and Path(config.watermark.image_path).exists():
                cmd.extend(["-i", config.watermark.image_path])
                watermark_filter = self._build_watermark_filter(config.watermark, width, height)
                video_filters = f"{video_filters},{watermark_filter}" if video_filters else watermark_filter
                effects_applied.append("watermark")

            # Apply video filters
            if video_filters:
                # Add scaling
                scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
                full_video_filter = f"{scale_filter},{video_filters}" if video_filters else scale_filter
                cmd.extend(["-vf", full_video_filter])
            else:
                cmd.extend(["-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"])

            # Apply audio filters
            if audio_filters:
                cmd.extend(["-af", audio_filters])

            # Encoding settings
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "medium",
                "-b:v", video_br,
                "-c:a", "aac",
                "-b:a", audio_br,
                str(output_path)
            ])

            logger.debug(f"FFmpeg command: {' '.join(cmd[:30])}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900,  # 15 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr[:500]}")
                return PostProcessResult(
                    success=False,
                    error=f"FFmpeg failed: {result.stderr[:200]}",
                )

            # Generate subtitles if provided
            subtitle_path = None
            if config.subtitles:
                subtitle_path = self._generate_subtitle_file(
                    config.subtitles,
                    output_name,
                )
                if subtitle_path:
                    effects_applied.append("subtitles")

            # Get output file info
            duration = self._get_duration(str(output_path))
            file_size = output_path.stat().st_size if output_path.exists() else 0

            return PostProcessResult(
                success=True,
                output_path=str(output_path),
                subtitle_path=subtitle_path,
                duration=duration or 0.0,
                file_size=file_size,
                effects_applied=effects_applied,
            )

        except Exception as e:
            logger.error(f"Post-processing failed: {e}")
            return PostProcessResult(
                success=False,
                error=str(e),
            )

    def _build_video_filters(self, config: PostProcessConfig) -> str:
        """Build video filter chain."""
        filters = []

        # Color grading
        color_filter = self.COLOR_GRADE_FILTERS.get(config.color_grade, "")
        if color_filter:
            filters.append(color_filter)

        # Sharpening
        if config.sharpen:
            filters.append("unsharp=5:5:1.0:5:5:0.5")

        # Denoise
        if config.denoise:
            filters.append("hqdn3d=4:3:6:4.5")

        # Fade in/out
        if config.add_fade_in > 0:
            filters.append(f"fade=t=in:st=0:d={config.add_fade_in}")

        if config.add_fade_out > 0:
            # Note: fade_out needs video duration, would need to calculate
            filters.append(f"fade=t=out:st=-{config.add_fade_out}:d={config.add_fade_out}")

        return ",".join(filters)

    def _build_audio_filters(self, config: PostProcessConfig) -> str:
        """Build audio filter chain."""
        filters = []

        if config.normalize_audio:
            # Loudness normalization to target LUFS
            filters.append(f"loudnorm=I={config.audio_loudness}:TP=-1.5:LRA=11")

        return ",".join(filters)

    def _build_watermark_filter(
        self,
        watermark: WatermarkConfig,
        video_width: int,
        video_height: int,
    ) -> str:
        """Build watermark overlay filter."""
        # Calculate position
        scale_width = int(video_width * watermark.scale)

        if watermark.position == "top_left":
            x, y = watermark.margin, watermark.margin
        elif watermark.position == "top_right":
            x, y = f"W-w-{watermark.margin}", watermark.margin
        elif watermark.position == "bottom_left":
            x, y = watermark.margin, f"H-h-{watermark.margin}"
        else:  # bottom_right
            x, y = f"W-w-{watermark.margin}", f"H-h-{watermark.margin}"

        # Scale and apply watermark with overlay
        return f"[1:v]scale={scale_width}:-1,format=rgba,colorchannelmixer=aa={watermark.opacity}[wm];[0:v][wm]overlay={x}:{y}"

    def _generate_subtitle_file(
        self,
        subtitles: List[SubtitleEntry],
        output_name: str,
    ) -> Optional[str]:
        """Generate SRT subtitle file."""
        if not subtitles:
            return None

        srt_path = self.output_dir / f"{output_name}.srt"

        try:
            with open(srt_path, 'w', encoding='utf-8') as f:
                for i, entry in enumerate(subtitles, 1):
                    start = self._format_srt_timestamp(entry.start_time)
                    end = self._format_srt_timestamp(entry.end_time)
                    f.write(f"{i}\n{start} --> {end}\n{entry.text}\n\n")

            logger.info(f"Generated subtitles: {srt_path}")
            return str(srt_path)

        except Exception as e:
            logger.error(f"Subtitle generation failed: {e}")
            return None

    def _format_srt_timestamp(self, seconds: float) -> str:
        """Format seconds to SRT timestamp."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _get_duration(self, path: str) -> Optional[float]:
        """Get video duration using FFprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    path
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception:
            pass
        return None

    def generate_subtitles_from_narration(
        self,
        narration_segments: List[Dict[str, Any]],
    ) -> List[SubtitleEntry]:
        """
        Generate subtitle entries from narration segments.

        Args:
            narration_segments: List of dicts with 'text', 'start_time', 'end_time'

        Returns:
            List of SubtitleEntry objects
        """
        subtitles = []

        for segment in narration_segments:
            text = segment.get("text", "").strip()
            start = segment.get("start_time", 0.0)
            end = segment.get("end_time", start + 5.0)

            if text:
                subtitles.append(SubtitleEntry(
                    start_time=start,
                    end_time=end,
                    text=text,
                ))

        return subtitles

    def burn_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
    ) -> bool:
        """
        Burn subtitles directly into video.

        Args:
            video_path: Input video path
            subtitle_path: SRT subtitle file path
            output_path: Output video path

        Returns:
            True if successful
        """
        if not self._check_ffmpeg_available():
            return False

        if not Path(video_path).exists() or not Path(subtitle_path).exists():
            return False

        # Need to escape path for subtitles filter
        sub_path_escaped = str(subtitle_path).replace("\\", "/").replace(":", "\\:")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles='{sub_path_escaped}'",
            "-c:a", "copy",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=600)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Subtitle burn failed: {e}")
            return False

    def apply_quick_grade(
        self,
        input_path: str,
        output_path: str,
        grade: ColorGradePreset,
    ) -> bool:
        """
        Quick color grade application without full processing.

        Args:
            input_path: Input video
            output_path: Output video
            grade: Color grade preset

        Returns:
            True if successful
        """
        if not self._check_ffmpeg_available():
            return False

        if not Path(input_path).exists():
            return False

        filter_str = self.COLOR_GRADE_FILTERS.get(grade, "")
        if not filter_str:
            # Just copy if no filter
            filter_str = "copy"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", filter_str,
            "-c:a", "copy",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=600)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Quick grade failed: {e}")
            return False
