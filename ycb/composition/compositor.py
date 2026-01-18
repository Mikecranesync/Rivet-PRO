"""
Multi-Scene Video Compositor

Combines rendered scene clips into final video with professional
transitions, overlays, and audio mixing.
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


class TransitionType(Enum):
    """Video transition types."""
    CUT = "cut"  # Instant cut (no transition)
    FADE = "fade"  # Fade to/from black
    CROSSFADE = "crossfade"  # Dissolve between clips
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"


@dataclass
class OverlayConfig:
    """Configuration for text overlays (lower thirds, titles)."""
    text: str
    position: str = "bottom_left"  # bottom_left, bottom_right, top_left, top_right, center
    start_time: float = 0.0  # seconds from clip start
    duration: float = 5.0  # seconds
    font_size: int = 24
    font_color: str = "white"
    bg_color: str = "black@0.7"  # FFmpeg color with alpha
    padding: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "position": self.position,
            "start_time": self.start_time,
            "duration": self.duration,
            "font_size": self.font_size,
            "font_color": self.font_color,
        }


@dataclass
class ClipConfig:
    """Configuration for a single clip in the composition."""
    path: str
    duration: Optional[float] = None  # Override duration (None = use clip duration)
    start_offset: float = 0.0  # Start offset within the clip
    transition_in: TransitionType = TransitionType.CUT
    transition_out: TransitionType = TransitionType.CUT
    transition_duration: float = 0.5  # seconds
    overlays: List[OverlayConfig] = field(default_factory=list)
    volume: float = 1.0  # Audio volume multiplier

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "duration": self.duration,
            "start_offset": self.start_offset,
            "transition_in": self.transition_in.value,
            "transition_out": self.transition_out.value,
            "transition_duration": self.transition_duration,
            "overlays": [o.to_dict() for o in self.overlays],
            "volume": self.volume,
        }


@dataclass
class CompositionResult:
    """Result of video composition."""
    success: bool
    output_path: Optional[str] = None
    duration: float = 0.0
    clip_count: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output_path": self.output_path,
            "duration": self.duration,
            "clip_count": self.clip_count,
            "error": self.error,
            "metadata": self.metadata,
        }


class VideoCompositor:
    """
    Composes multiple video clips into a final video.

    Features:
    - Concatenates scene clips with transitions
    - Adds text overlays (lower thirds)
    - Mixes audio tracks
    - Applies intro/outro bumpers
    - Supports various output quality presets
    """

    # Quality presets (width, height, bitrate)
    QUALITY_PRESETS = {
        "720p": (1280, 720, "4M"),
        "1080p": (1920, 1080, "8M"),
        "4k": (3840, 2160, "20M"),
        "preview": (640, 360, "1M"),
    }

    def __init__(
        self,
        output_dir: str = "./ycb_output/final",
        quality: str = "1080p",
        fps: int = 30,
    ):
        """
        Initialize the video compositor.

        Args:
            output_dir: Directory for output videos
            quality: Quality preset (720p, 1080p, 4k, preview)
            fps: Frames per second
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.quality = quality
        self.fps = fps

        self._ffmpeg_available = None
        logger.info(f"VideoCompositor initialized: quality={quality}, fps={fps}")

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

    def get_clip_duration(self, clip_path: str) -> Optional[float]:
        """Get duration of a video clip using FFprobe."""
        if not Path(clip_path).exists():
            return None

        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    clip_path
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Error getting clip duration: {e}")

        return None

    def compose(
        self,
        clips: List[ClipConfig],
        output_name: str,
        audio_path: Optional[str] = None,
        intro_path: Optional[str] = None,
        outro_path: Optional[str] = None,
    ) -> CompositionResult:
        """
        Compose clips into final video.

        Args:
            clips: List of ClipConfig objects
            output_name: Output filename (without extension)
            audio_path: Optional narration audio to mix
            intro_path: Optional intro bumper video
            outro_path: Optional outro bumper video

        Returns:
            CompositionResult with output path or error
        """
        if not self._check_ffmpeg_available():
            return CompositionResult(
                success=False,
                error="FFmpeg not available",
            )

        if not clips:
            return CompositionResult(
                success=False,
                error="No clips provided",
            )

        logger.info(f"Composing {len(clips)} clips: {output_name}")

        # Validate clips exist
        valid_clips = []
        for clip in clips:
            if Path(clip.path).exists():
                valid_clips.append(clip)
            else:
                logger.warning(f"Clip not found, skipping: {clip.path}")

        if not valid_clips:
            return CompositionResult(
                success=False,
                error="No valid clips found",
            )

        try:
            # Add intro if provided
            all_clips = []
            if intro_path and Path(intro_path).exists():
                all_clips.append(ClipConfig(path=intro_path))

            all_clips.extend(valid_clips)

            # Add outro if provided
            if outro_path and Path(outro_path).exists():
                all_clips.append(ClipConfig(path=outro_path))

            # Build composition
            output_path = self.output_dir / f"{output_name}.mp4"

            # Use concat filter for smooth composition
            result = self._compose_with_concat(all_clips, str(output_path), audio_path)

            if result.success:
                result.clip_count = len(valid_clips)
                result.duration = self.get_clip_duration(str(output_path)) or 0.0

            return result

        except Exception as e:
            logger.error(f"Composition failed: {e}")
            return CompositionResult(
                success=False,
                error=str(e),
            )

    def _compose_with_concat(
        self,
        clips: List[ClipConfig],
        output_path: str,
        audio_path: Optional[str] = None,
    ) -> CompositionResult:
        """Compose using FFmpeg concat filter."""

        # Get quality settings
        width, height, bitrate = self.QUALITY_PRESETS.get(
            self.quality,
            self.QUALITY_PRESETS["1080p"]
        )

        # Create concat file for simple concatenation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = f.name
            for clip in clips:
                f.write(f"file '{clip.path}'\n")

        try:
            # Build FFmpeg command
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
            ]

            # Add audio if provided
            if audio_path and Path(audio_path).exists():
                cmd.extend(["-i", audio_path])

            # Video encoding settings
            cmd.extend([
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264",
                "-preset", "medium",
                "-b:v", bitrate,
                "-r", str(self.fps),
            ])

            # Audio settings
            if audio_path and Path(audio_path).exists():
                # Mix audio tracks
                cmd.extend([
                    "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest[aout]",
                    "-map", "0:v",
                    "-map", "[aout]",
                ])
            else:
                cmd.extend([
                    "-c:a", "aac",
                    "-b:a", "192k",
                ])

            cmd.append(output_path)

            logger.debug(f"FFmpeg command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr[:500]}")
                return CompositionResult(
                    success=False,
                    error=f"FFmpeg failed: {result.stderr[:200]}",
                )

            return CompositionResult(
                success=True,
                output_path=output_path,
            )

        finally:
            Path(concat_file).unlink(missing_ok=True)

    def compose_with_transitions(
        self,
        clips: List[ClipConfig],
        output_name: str,
        default_transition: TransitionType = TransitionType.CROSSFADE,
        transition_duration: float = 0.5,
    ) -> CompositionResult:
        """
        Compose clips with transitions between them.

        This is more complex and uses filter_complex for transitions.

        Args:
            clips: List of ClipConfig objects
            output_name: Output filename
            default_transition: Default transition type
            transition_duration: Default transition duration

        Returns:
            CompositionResult
        """
        if not self._check_ffmpeg_available():
            return CompositionResult(
                success=False,
                error="FFmpeg not available",
            )

        if len(clips) < 2:
            # Single clip - just copy/transcode
            return self.compose(clips, output_name)

        logger.info(f"Composing with transitions: {len(clips)} clips")

        # Get quality settings
        width, height, bitrate = self.QUALITY_PRESETS.get(
            self.quality,
            self.QUALITY_PRESETS["1080p"]
        )

        output_path = self.output_dir / f"{output_name}.mp4"

        try:
            # Build complex filter for transitions
            inputs = []
            filter_parts = []

            for i, clip in enumerate(clips):
                inputs.extend(["-i", clip.path])

            # Scale all inputs to same size
            for i in range(len(clips)):
                filter_parts.append(
                    f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setpts=PTS-STARTPTS[v{i}]"
                )

            # Apply transitions using xfade
            if len(clips) == 2:
                # Simple two-clip transition
                transition = clips[1].transition_in or default_transition
                duration = clips[1].transition_duration or transition_duration

                clip0_duration = self.get_clip_duration(clips[0].path) or 5.0

                filter_parts.append(
                    f"[v0][v1]xfade=transition={self._get_xfade_type(transition)}:"
                    f"duration={duration}:offset={clip0_duration - duration}[outv]"
                )
            else:
                # Multi-clip transitions (chain them)
                current_label = "v0"
                total_offset = 0.0

                for i in range(1, len(clips)):
                    clip_duration = self.get_clip_duration(clips[i-1].path) or 5.0
                    transition = clips[i].transition_in or default_transition
                    t_duration = clips[i].transition_duration or transition_duration

                    offset = total_offset + clip_duration - t_duration
                    next_label = f"tmp{i}" if i < len(clips) - 1 else "outv"

                    filter_parts.append(
                        f"[{current_label}][v{i}]xfade=transition={self._get_xfade_type(transition)}:"
                        f"duration={t_duration}:offset={offset}[{next_label}]"
                    )

                    total_offset = offset
                    current_label = next_label

            # Build command
            cmd = ["ffmpeg", "-y"]
            cmd.extend(inputs)

            filter_complex = ";".join(filter_parts)
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-c:v", "libx264",
                "-preset", "medium",
                "-b:v", bitrate,
                "-r", str(self.fps),
                "-an",  # No audio for now (would need separate audio handling)
                str(output_path)
            ])

            logger.debug(f"FFmpeg command: {' '.join(cmd[:20])}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg transition error: {result.stderr[:500]}")
                # Fall back to simple concat
                logger.info("Falling back to simple concatenation")
                return self.compose(clips, output_name)

            return CompositionResult(
                success=True,
                output_path=str(output_path),
                clip_count=len(clips),
                duration=self.get_clip_duration(str(output_path)) or 0.0,
            )

        except Exception as e:
            logger.error(f"Transition composition failed: {e}")
            # Fall back to simple concat
            return self.compose(clips, output_name)

    def _get_xfade_type(self, transition: TransitionType) -> str:
        """Convert TransitionType to FFmpeg xfade transition name."""
        mapping = {
            TransitionType.CUT: "fade",  # Instant cut not supported, use fade
            TransitionType.FADE: "fade",
            TransitionType.CROSSFADE: "dissolve",
            TransitionType.WIPE_LEFT: "wipeleft",
            TransitionType.WIPE_RIGHT: "wiperight",
            TransitionType.WIPE_UP: "wipeup",
            TransitionType.WIPE_DOWN: "wipedown",
        }
        return mapping.get(transition, "dissolve")

    def add_lower_third(
        self,
        video_path: str,
        output_path: str,
        text: str,
        start_time: float = 0.0,
        duration: float = 5.0,
        position: str = "bottom_left",
    ) -> bool:
        """
        Add a lower-third text overlay to a video.

        Args:
            video_path: Input video path
            output_path: Output video path
            text: Text to display
            start_time: When to show the overlay
            duration: How long to show it
            position: Position (bottom_left, bottom_right, etc.)

        Returns:
            True if successful
        """
        if not self._check_ffmpeg_available():
            return False

        if not Path(video_path).exists():
            return False

        # Calculate position
        if position == "bottom_left":
            x, y = "10", "H-h-50"
        elif position == "bottom_right":
            x, y = "W-w-10", "H-h-50"
        elif position == "top_left":
            x, y = "10", "50"
        elif position == "top_right":
            x, y = "W-w-10", "50"
        else:  # center
            x, y = "(W-w)/2", "(H-h)/2"

        # Build drawtext filter
        drawtext = (
            f"drawtext=text='{text}':"
            f"fontsize=24:fontcolor=white:"
            f"x={x}:y={y}:"
            f"enable='between(t,{start_time},{start_time + duration})':"
            f"box=1:boxcolor=black@0.7:boxborderw=5"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", drawtext,
            "-c:a", "copy",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Lower third failed: {e}")
            return False

    def add_audio_track(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        replace_audio: bool = False,
    ) -> bool:
        """
        Add or mix audio track with video.

        Args:
            video_path: Input video path
            audio_path: Audio file to add
            output_path: Output video path
            replace_audio: If True, replace video audio; if False, mix

        Returns:
            True if successful
        """
        if not self._check_ffmpeg_available():
            return False

        if not Path(video_path).exists() or not Path(audio_path).exists():
            return False

        if replace_audio:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path
            ]
        else:
            # Mix audio tracks
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                output_path
            ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Audio addition failed: {e}")
            return False

    def create_test_video(
        self,
        output_name: str = "test_video",
        duration: float = 5.0,
        text: str = "Test Video",
    ) -> str:
        """
        Create a simple test video for testing purposes.

        Args:
            output_name: Output filename
            duration: Video duration in seconds
            text: Text to display

        Returns:
            Path to created video
        """
        if not self._check_ffmpeg_available():
            return ""

        width, height, bitrate = self.QUALITY_PRESETS.get(
            self.quality,
            self.QUALITY_PRESETS["1080p"]
        )

        output_path = self.output_dir / f"{output_name}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=blue:s={width}x{height}:d={duration}",
            "-vf", f"drawtext=text='{text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264",
            "-t", str(duration),
            str(output_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode == 0:
                return str(output_path)
        except Exception as e:
            logger.error(f"Test video creation failed: {e}")

        return ""
