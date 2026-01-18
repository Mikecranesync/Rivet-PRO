"""
Narration-to-Scene Timing Synchronization

Analyzes narration audio to extract word-level timestamps and
synchronizes them with visual scene boundaries.
"""

import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


@dataclass
class WordTiming:
    """Timing information for a single word."""
    word: str
    start_time: float  # seconds
    end_time: float  # seconds
    confidence: float = 1.0

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "word": self.word,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "confidence": self.confidence,
        }


@dataclass
class SceneTiming:
    """Timing information for a scene."""
    scene_id: str
    start_time: float  # seconds
    end_time: float  # seconds
    original_duration: float  # original planned duration
    narration_text: str = ""
    word_timings: List[WordTiming] = field(default_factory=list)
    adjusted: bool = False  # True if timing was adjusted

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "original_duration": self.original_duration,
            "narration_text": self.narration_text,
            "word_count": len(self.word_timings),
            "adjusted": self.adjusted,
        }


@dataclass
class TimingMap:
    """Complete timing map for a video."""
    total_duration: float
    scene_timings: List[SceneTiming] = field(default_factory=list)
    word_timings: List[WordTiming] = field(default_factory=list)
    audio_path: Optional[str] = None
    gaps: List[Tuple[float, float]] = field(default_factory=list)  # silence gaps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_duration": self.total_duration,
            "scene_count": len(self.scene_timings),
            "word_count": len(self.word_timings),
            "audio_path": self.audio_path,
            "gaps": self.gaps,
            "scenes": [s.to_dict() for s in self.scene_timings],
        }

    def to_json(self, path: str):
        """Save timing map to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_json(cls, path: str) -> "TimingMap":
        """Load timing map from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)

        timing_map = cls(
            total_duration=data["total_duration"],
            audio_path=data.get("audio_path"),
            gaps=data.get("gaps", []),
        )

        for scene_data in data.get("scenes", []):
            timing = SceneTiming(
                scene_id=scene_data["scene_id"],
                start_time=scene_data["start_time"],
                end_time=scene_data["end_time"],
                original_duration=scene_data["original_duration"],
                narration_text=scene_data.get("narration_text", ""),
                adjusted=scene_data.get("adjusted", False),
            )
            timing_map.scene_timings.append(timing)

        return timing_map


class TimingSync:
    """
    Synchronizes narration audio with visual scenes.

    Analyzes audio to extract word-level timestamps and adjusts
    scene boundaries to match natural speech patterns.
    """

    def __init__(
        self,
        min_scene_duration: float = 3.0,
        max_scene_duration: float = 30.0,
        padding: float = 0.5,  # padding between scenes
        words_per_second: float = 2.5,
    ):
        """
        Initialize timing synchronizer.

        Args:
            min_scene_duration: Minimum scene duration in seconds
            max_scene_duration: Maximum scene duration in seconds
            padding: Padding between scenes in seconds
            words_per_second: Estimated speaking rate for fallback
        """
        self.min_scene_duration = min_scene_duration
        self.max_scene_duration = max_scene_duration
        self.padding = padding
        self.words_per_second = words_per_second

        # Check available backends
        self._whisper_available = None
        self._ffmpeg_available = None

        logger.info(f"TimingSync initialized: min={min_scene_duration}s, max={max_scene_duration}s")

    def _check_whisper_available(self) -> bool:
        """Check if Whisper is available for transcription."""
        if self._whisper_available is not None:
            return self._whisper_available

        try:
            import whisper  # noqa: F401
            self._whisper_available = True
        except ImportError:
            self._whisper_available = False

        logger.info(f"Whisper available: {self._whisper_available}")
        return self._whisper_available

    def _check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available for audio processing."""
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

    def get_audio_duration(self, audio_path: str) -> Optional[float]:
        """Get duration of audio file using FFprobe."""
        if not self._check_ffmpeg_available():
            return None

        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    audio_path
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")

        return None

    def transcribe_audio(self, audio_path: str) -> List[WordTiming]:
        """
        Transcribe audio and extract word-level timestamps.

        Args:
            audio_path: Path to audio file

        Returns:
            List of WordTiming objects
        """
        if not Path(audio_path).exists():
            logger.error(f"Audio file not found: {audio_path}")
            return []

        # Try Whisper first
        if self._check_whisper_available():
            return self._transcribe_with_whisper(audio_path)

        logger.warning("No transcription backend available")
        return []

    def _transcribe_with_whisper(self, audio_path: str) -> List[WordTiming]:
        """Transcribe using OpenAI Whisper."""
        try:
            import whisper

            logger.info(f"Transcribing with Whisper: {audio_path}")
            model = whisper.load_model("base")

            result = model.transcribe(
                audio_path,
                word_timestamps=True,
                language="en",
            )

            word_timings = []
            for segment in result.get("segments", []):
                for word_info in segment.get("words", []):
                    timing = WordTiming(
                        word=word_info["word"].strip(),
                        start_time=word_info["start"],
                        end_time=word_info["end"],
                        confidence=word_info.get("probability", 1.0),
                    )
                    word_timings.append(timing)

            logger.info(f"Transcribed {len(word_timings)} words")
            return word_timings

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return []

    def sync_scenes_to_audio(
        self,
        scenes: List[Dict[str, Any]],
        audio_path: str,
    ) -> TimingMap:
        """
        Synchronize scenes to audio timing.

        Args:
            scenes: List of scene dictionaries with 'scene_id', 'duration', 'narration_text'
            audio_path: Path to narration audio file

        Returns:
            TimingMap with adjusted scene timings
        """
        logger.info(f"Syncing {len(scenes)} scenes to audio: {audio_path}")

        # Get audio duration
        audio_duration = self.get_audio_duration(audio_path)
        if audio_duration is None:
            # Estimate from scene durations
            audio_duration = sum(s.get("duration", 5.0) for s in scenes)
            logger.warning(f"Could not get audio duration, estimating: {audio_duration}s")

        # Transcribe audio for word timings
        word_timings = self.transcribe_audio(audio_path)

        # Create timing map
        timing_map = TimingMap(
            total_duration=audio_duration,
            word_timings=word_timings,
            audio_path=audio_path,
        )

        # If we have word timings, sync scenes to words
        if word_timings:
            self._sync_with_word_timings(scenes, word_timings, timing_map)
        else:
            # Fall back to proportional timing
            self._sync_proportional(scenes, audio_duration, timing_map)

        # Find gaps (silences)
        timing_map.gaps = self._find_gaps(timing_map)

        logger.info(f"Timing sync complete: {timing_map.total_duration:.1f}s total")
        return timing_map

    def _sync_with_word_timings(
        self,
        scenes: List[Dict[str, Any]],
        word_timings: List[WordTiming],
        timing_map: TimingMap,
    ):
        """Sync scenes using word-level timestamps."""
        logger.info("Syncing scenes using word-level timestamps")

        # Build word lookup by normalized text
        word_index = 0
        current_time = 0.0

        for scene in scenes:
            scene_id = scene.get("scene_id", f"scene_{len(timing_map.scene_timings):03d}")
            narration = scene.get("narration_text", "")
            original_duration = scene.get("duration", 5.0)

            # Find words that belong to this scene's narration
            scene_words = []
            narration_words = narration.lower().split()

            for narration_word in narration_words:
                # Look for matching word in timings
                while word_index < len(word_timings):
                    word_timing = word_timings[word_index]
                    word_lower = word_timing.word.lower().strip(".,!?;:\"'")

                    if narration_word.strip(".,!?;:\"'") == word_lower:
                        scene_words.append(word_timing)
                        word_index += 1
                        break
                    elif word_lower in narration_word or narration_word in word_lower:
                        # Partial match
                        scene_words.append(word_timing)
                        word_index += 1
                        break
                    else:
                        word_index += 1

            # Calculate scene timing from word timings
            if scene_words:
                start_time = scene_words[0].start_time - self.padding / 2
                end_time = scene_words[-1].end_time + self.padding / 2
            else:
                # No word matches, use original duration
                start_time = current_time
                end_time = current_time + original_duration

            # Enforce min/max duration
            duration = end_time - start_time
            if duration < self.min_scene_duration:
                end_time = start_time + self.min_scene_duration
            elif duration > self.max_scene_duration:
                end_time = start_time + self.max_scene_duration

            # Create scene timing
            scene_timing = SceneTiming(
                scene_id=scene_id,
                start_time=max(0, start_time),
                end_time=end_time,
                original_duration=original_duration,
                narration_text=narration,
                word_timings=scene_words,
                adjusted=abs(end_time - start_time - original_duration) > 0.5,
            )
            timing_map.scene_timings.append(scene_timing)
            current_time = end_time

    def _sync_proportional(
        self,
        scenes: List[Dict[str, Any]],
        total_duration: float,
        timing_map: TimingMap,
    ):
        """Sync scenes proportionally based on original durations."""
        logger.info("Syncing scenes proportionally (no word timings)")

        # Calculate total original duration
        total_original = sum(s.get("duration", 5.0) for s in scenes)
        if total_original == 0:
            total_original = len(scenes) * 5.0

        # Scale factor
        scale = total_duration / total_original

        current_time = 0.0
        for scene in scenes:
            scene_id = scene.get("scene_id", f"scene_{len(timing_map.scene_timings):03d}")
            original_duration = scene.get("duration", 5.0)
            narration = scene.get("narration_text", "")

            # Scale duration
            scaled_duration = original_duration * scale

            # Enforce min/max
            scaled_duration = max(self.min_scene_duration, min(self.max_scene_duration, scaled_duration))

            scene_timing = SceneTiming(
                scene_id=scene_id,
                start_time=current_time,
                end_time=current_time + scaled_duration,
                original_duration=original_duration,
                narration_text=narration,
                adjusted=abs(scaled_duration - original_duration) > 0.5,
            )
            timing_map.scene_timings.append(scene_timing)
            current_time += scaled_duration

        # Update total duration
        timing_map.total_duration = current_time

    def _find_gaps(self, timing_map: TimingMap) -> List[Tuple[float, float]]:
        """Find gaps (silences) in the timing map."""
        gaps = []

        if not timing_map.scene_timings:
            return gaps

        # Check gap at start
        if timing_map.scene_timings[0].start_time > 0.5:
            gaps.append((0.0, timing_map.scene_timings[0].start_time))

        # Check gaps between scenes
        for i in range(len(timing_map.scene_timings) - 1):
            current_end = timing_map.scene_timings[i].end_time
            next_start = timing_map.scene_timings[i + 1].start_time

            if next_start - current_end > 0.5:
                gaps.append((current_end, next_start))

        # Check gap at end
        if timing_map.scene_timings:
            last_end = timing_map.scene_timings[-1].end_time
            if timing_map.total_duration - last_end > 0.5:
                gaps.append((last_end, timing_map.total_duration))

        return gaps

    def sync_from_text(
        self,
        scenes: List[Dict[str, Any]],
        total_duration: Optional[float] = None,
    ) -> TimingMap:
        """
        Sync scenes based on text narration without audio.

        Estimates timing based on word count and speaking rate.

        Args:
            scenes: List of scene dictionaries with narration_text
            total_duration: Optional target total duration

        Returns:
            TimingMap based on text analysis
        """
        logger.info(f"Syncing {len(scenes)} scenes from text")

        # Estimate duration for each scene based on word count
        scene_durations = []
        for scene in scenes:
            narration = scene.get("narration_text", "")
            word_count = len(narration.split()) if narration else 0

            if word_count > 0:
                estimated = word_count / self.words_per_second
            else:
                estimated = scene.get("duration", 5.0)

            # Enforce min/max
            estimated = max(self.min_scene_duration, min(self.max_scene_duration, estimated))
            scene_durations.append(estimated)

        # Scale to target duration if provided
        actual_total = sum(scene_durations)
        if total_duration and actual_total > 0:
            scale = total_duration / actual_total
            scene_durations = [d * scale for d in scene_durations]

        # Build timing map
        timing_map = TimingMap(
            total_duration=sum(scene_durations),
        )

        current_time = 0.0
        for scene, duration in zip(scenes, scene_durations):
            scene_id = scene.get("scene_id", f"scene_{len(timing_map.scene_timings):03d}")
            original_duration = scene.get("duration", 5.0)
            narration = scene.get("narration_text", "")

            scene_timing = SceneTiming(
                scene_id=scene_id,
                start_time=current_time,
                end_time=current_time + duration,
                original_duration=original_duration,
                narration_text=narration,
                adjusted=abs(duration - original_duration) > 0.5,
            )
            timing_map.scene_timings.append(scene_timing)
            current_time += duration

        logger.info(f"Text sync complete: {timing_map.total_duration:.1f}s total")
        return timing_map

    def adjust_for_pauses(
        self,
        timing_map: TimingMap,
        min_pause: float = 0.3,
        max_pause: float = 1.5,
    ) -> TimingMap:
        """
        Adjust timing map to add natural pauses between scenes.

        Args:
            timing_map: Original timing map
            min_pause: Minimum pause between scenes
            max_pause: Maximum pause between scenes

        Returns:
            Adjusted TimingMap
        """
        if len(timing_map.scene_timings) < 2:
            return timing_map

        # Calculate shift needed
        total_shift = 0.0

        for i in range(1, len(timing_map.scene_timings)):
            prev = timing_map.scene_timings[i - 1]
            curr = timing_map.scene_timings[i]

            current_gap = curr.start_time - prev.end_time
            if current_gap < min_pause:
                shift = min_pause - current_gap
                curr.start_time += total_shift + shift
                curr.end_time += total_shift + shift
                total_shift += shift
                curr.adjusted = True
            elif current_gap > max_pause:
                shift = current_gap - max_pause
                curr.start_time -= shift
                curr.end_time -= shift
                curr.adjusted = True
            else:
                curr.start_time += total_shift
                curr.end_time += total_shift

        # Update total duration
        if timing_map.scene_timings:
            timing_map.total_duration = timing_map.scene_timings[-1].end_time

        # Recalculate gaps
        timing_map.gaps = self._find_gaps(timing_map)

        return timing_map
