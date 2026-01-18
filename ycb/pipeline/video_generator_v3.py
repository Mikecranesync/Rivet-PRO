"""
YCB v3 Video Generator Pipeline

Professional-grade video generation using Manim + Blender rendering.
Orchestrates all components from script to final video.

Target quality: 8.5-9/10
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from ycb.storyboard import (
    StoryboardGenerator,
    SceneRouter,
    RenderResult,
    RouteStatus,
    Storyboard,
    Scene,
)
from ycb.audio import TimingSync, TimingMap
from ycb.composition import (
    VideoCompositor,
    PostProcessor,
    ClipConfig,
    CompositionResult,
    PostProcessConfig,
    PostProcessResult,
    ColorGradePreset,
    OutputQuality,
)
from ycb.composition.compositor import TransitionType

logger = logging.getLogger(__name__)


@dataclass
class V3GenerationConfig:
    """Configuration for v3 video generation."""
    # Output settings
    output_dir: str = "./ycb_output/v3"
    output_quality: OutputQuality = OutputQuality.FULL_HD
    fps: int = 30

    # Rendering settings
    manim_quality: str = "high_quality"
    enable_blender: bool = False  # Blender not available in current env

    # Storyboard settings
    target_duration: float = 60.0
    min_scenes: int = 4
    max_scenes: int = 12

    # Composition settings
    default_transition: TransitionType = TransitionType.CROSSFADE
    transition_duration: float = 0.5
    color_grade: ColorGradePreset = ColorGradePreset.PROFESSIONAL
    normalize_audio: bool = True

    # Performance settings
    parallel_rendering: bool = True
    max_workers: int = 4

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output_dir": self.output_dir,
            "output_quality": self.output_quality.value,
            "fps": self.fps,
            "manim_quality": self.manim_quality,
            "enable_blender": self.enable_blender,
            "target_duration": self.target_duration,
            "parallel_rendering": self.parallel_rendering,
        }


@dataclass
class V3GenerationResult:
    """Result of v3 video generation."""
    success: bool
    video_path: Optional[str] = None
    duration: float = 0.0
    scene_count: int = 0
    scenes_rendered: int = 0
    scenes_failed: int = 0
    render_time: float = 0.0
    compose_time: float = 0.0
    total_time: float = 0.0
    error: Optional[str] = None
    storyboard: Optional[Storyboard] = None
    timing_map: Optional[TimingMap] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "video_path": self.video_path,
            "duration": self.duration,
            "scene_count": self.scene_count,
            "scenes_rendered": self.scenes_rendered,
            "scenes_failed": self.scenes_failed,
            "render_time": self.render_time,
            "compose_time": self.compose_time,
            "total_time": self.total_time,
            "error": self.error,
            "metrics": self.metrics,
        }


class VideoGeneratorV3:
    """
    YCB v3 Video Generation Pipeline.

    Orchestrates the full pipeline:
    1. Script -> Storyboard generation (LLM)
    2. Storyboard -> Scene rendering (Manim/Blender)
    3. Scene clips -> Video composition (FFmpeg)
    4. Post-processing -> Final video

    Features:
    - Parallel scene rendering
    - Graceful degradation (Blender -> Manim fallback)
    - Progress tracking and callbacks
    - Quality metrics output
    """

    def __init__(self, config: Optional[V3GenerationConfig] = None):
        """
        Initialize the v3 video generator.

        Args:
            config: Generation configuration
        """
        self.config = config or V3GenerationConfig()

        # Create output directories
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.clips_dir = self.output_dir / "clips"
        self.clips_dir.mkdir(exist_ok=True)

        self.final_dir = self.output_dir / "final"
        self.final_dir.mkdir(exist_ok=True)

        # Initialize components
        self._storyboard_generator = None
        self._scene_router = None
        self._timing_sync = None
        self._compositor = None
        self._post_processor = None

        # Progress callback
        self._progress_callback: Optional[Callable[[str, float], None]] = None

        logger.info(f"VideoGeneratorV3 initialized: output_dir={self.output_dir}")

    def _get_storyboard_generator(self) -> StoryboardGenerator:
        """Lazy load storyboard generator."""
        if self._storyboard_generator is None:
            from ycb.storyboard.generator import StoryboardConfig
            config = StoryboardConfig(
                target_duration=self.config.target_duration,
                min_scenes=self.config.min_scenes,
                max_scenes=self.config.max_scenes,
            )
            self._storyboard_generator = StoryboardGenerator(config)
        return self._storyboard_generator

    def _get_scene_router(self) -> SceneRouter:
        """Lazy load scene router."""
        if self._scene_router is None:
            self._scene_router = SceneRouter(
                output_dir=str(self.clips_dir),
                manim_quality=self.config.manim_quality,
                enable_blender=self.config.enable_blender,
            )
        return self._scene_router

    def _get_timing_sync(self) -> TimingSync:
        """Lazy load timing sync."""
        if self._timing_sync is None:
            self._timing_sync = TimingSync()
        return self._timing_sync

    def _get_compositor(self) -> VideoCompositor:
        """Lazy load compositor."""
        if self._compositor is None:
            self._compositor = VideoCompositor(
                output_dir=str(self.final_dir),
                quality=self._get_ffmpeg_quality(),
                fps=self.config.fps,
            )
        return self._compositor

    def _get_post_processor(self) -> PostProcessor:
        """Lazy load post processor."""
        if self._post_processor is None:
            self._post_processor = PostProcessor(
                output_dir=str(self.final_dir),
            )
        return self._post_processor

    def _get_ffmpeg_quality(self) -> str:
        """Convert OutputQuality to FFmpeg quality string."""
        mapping = {
            OutputQuality.PREVIEW: "preview",
            OutputQuality.SD: "preview",
            OutputQuality.HD: "720p",
            OutputQuality.FULL_HD: "1080p",
            OutputQuality.QHD: "1080p",
            OutputQuality.UHD: "4k",
        }
        return mapping.get(self.config.output_quality, "1080p")

    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """Set progress callback function."""
        self._progress_callback = callback

    def _report_progress(self, stage: str, progress: float):
        """Report progress to callback if set."""
        if self._progress_callback:
            self._progress_callback(stage, progress)
        logger.info(f"Progress: {stage} - {progress*100:.0f}%")

    def generate(
        self,
        script: str,
        title: str,
        output_name: Optional[str] = None,
        audio_path: Optional[str] = None,
        description: str = "",
    ) -> V3GenerationResult:
        """
        Generate a video from a script.

        Args:
            script: Video script text
            title: Video title
            output_name: Output filename (default: sanitized title)
            audio_path: Optional narration audio file
            description: Video description

        Returns:
            V3GenerationResult with video path or error
        """
        start_time = time.time()
        result = V3GenerationResult(success=False)

        if not output_name:
            output_name = self._sanitize_filename(title)

        logger.info(f"Starting v3 generation: {title}")
        self._report_progress("Starting", 0.0)

        try:
            # Stage 1: Generate storyboard
            self._report_progress("Generating storyboard", 0.1)
            storyboard = self._generate_storyboard(script, title, description)
            result.storyboard = storyboard
            result.scene_count = len(storyboard.scenes)

            logger.info(f"Storyboard: {len(storyboard.scenes)} scenes")

            # Stage 2: Sync timing (if audio provided)
            self._report_progress("Syncing timing", 0.2)
            timing_map = self._sync_timing(storyboard, audio_path)
            result.timing_map = timing_map

            # Stage 3: Render scenes
            self._report_progress("Rendering scenes", 0.3)
            render_start = time.time()
            render_results = self._render_scenes(storyboard)
            result.render_time = time.time() - render_start

            # Count results
            rendered = [r for r in render_results if r.status in [RouteStatus.SUCCESS, RouteStatus.FALLBACK]]
            failed = [r for r in render_results if r.status == RouteStatus.FAILED]
            result.scenes_rendered = len(rendered)
            result.scenes_failed = len(failed)

            logger.info(f"Rendered: {len(rendered)}/{len(storyboard.scenes)} scenes")

            # Stage 4: Compose video
            self._report_progress("Composing video", 0.7)
            compose_start = time.time()
            composition_result = self._compose_video(
                render_results,
                output_name,
                audio_path,
            )
            result.compose_time = time.time() - compose_start

            if not composition_result.success:
                result.error = f"Composition failed: {composition_result.error}"
                return result

            # Stage 5: Post-process
            self._report_progress("Post-processing", 0.9)
            final_result = self._post_process(
                composition_result.output_path,
                output_name,
            )

            if final_result.success:
                result.success = True
                result.video_path = final_result.output_path
                result.duration = final_result.duration
            else:
                # Fall back to unprocessed video
                result.success = True
                result.video_path = composition_result.output_path
                result.duration = composition_result.duration

            # Collect metrics
            result.total_time = time.time() - start_time
            result.metrics = {
                "storyboard_scenes": len(storyboard.scenes),
                "scenes_rendered": result.scenes_rendered,
                "scenes_failed": result.scenes_failed,
                "render_time_seconds": result.render_time,
                "compose_time_seconds": result.compose_time,
                "total_time_seconds": result.total_time,
                "output_quality": self.config.output_quality.value,
                "parallel_rendering": self.config.parallel_rendering,
            }

            self._report_progress("Complete", 1.0)
            logger.info(f"Generation complete: {result.video_path}")

            return result

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            result.error = str(e)
            result.total_time = time.time() - start_time
            return result

    def _generate_storyboard(
        self,
        script: str,
        title: str,
        description: str,
    ) -> Storyboard:
        """Generate storyboard from script."""
        generator = self._get_storyboard_generator()
        return generator.generate(
            script=script,
            title=title,
            description=description,
        )

    def _sync_timing(
        self,
        storyboard: Storyboard,
        audio_path: Optional[str],
    ) -> TimingMap:
        """Sync scenes to audio timing."""
        sync = self._get_timing_sync()

        # Convert scenes to dict format
        scenes = [
            {
                "scene_id": scene.scene_id,
                "duration": scene.duration,
                "narration_text": scene.narration_text,
            }
            for scene in storyboard.scenes
        ]

        if audio_path and Path(audio_path).exists():
            return sync.sync_scenes_to_audio(scenes, audio_path)
        else:
            return sync.sync_from_text(scenes, storyboard.target_duration)

    def _render_scenes(self, storyboard: Storyboard) -> List[RenderResult]:
        """Render all scenes, optionally in parallel."""
        router = self._get_scene_router()

        if self.config.parallel_rendering and len(storyboard.scenes) > 1:
            return self._render_parallel(router, storyboard)
        else:
            return self._render_sequential(router, storyboard)

    def _render_sequential(
        self,
        router: SceneRouter,
        storyboard: Storyboard,
    ) -> List[RenderResult]:
        """Render scenes sequentially."""
        results = []
        total = len(storyboard.scenes)

        for i, scene in enumerate(storyboard.scenes):
            progress = 0.3 + (0.4 * (i / total))
            self._report_progress(f"Rendering scene {i+1}/{total}", progress)

            result = router.route(scene)
            results.append(result)

            status = "OK" if result.status == RouteStatus.SUCCESS else result.status.value
            logger.info(f"  Scene {scene.scene_id}: {status}")

        return results

    def _render_parallel(
        self,
        router: SceneRouter,
        storyboard: Storyboard,
    ) -> List[RenderResult]:
        """Render scenes in parallel."""
        results = [None] * len(storyboard.scenes)
        completed = 0
        total = len(storyboard.scenes)

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all render tasks
            future_to_idx = {
                executor.submit(router.route, scene): i
                for i, scene in enumerate(storyboard.scenes)
            }

            # Collect results as they complete
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result()
                    results[idx] = result
                except Exception as e:
                    logger.error(f"Scene {idx} render failed: {e}")
                    results[idx] = RenderResult(
                        scene_id=storyboard.scenes[idx].scene_id,
                        status=RouteStatus.FAILED,
                        error=str(e),
                    )

                completed += 1
                progress = 0.3 + (0.4 * (completed / total))
                self._report_progress(f"Rendering ({completed}/{total})", progress)

        return results

    def _compose_video(
        self,
        render_results: List[RenderResult],
        output_name: str,
        audio_path: Optional[str],
    ) -> CompositionResult:
        """Compose rendered clips into final video."""
        compositor = self._get_compositor()

        # Filter successful renders with clip paths
        clips = []
        for result in render_results:
            if result.clip_path and Path(result.clip_path).exists():
                clip = ClipConfig(
                    path=result.clip_path,
                    duration=result.duration,
                    transition_in=self.config.default_transition,
                    transition_duration=self.config.transition_duration,
                )
                clips.append(clip)

        if not clips:
            return CompositionResult(
                success=False,
                error="No clips to compose",
            )

        logger.info(f"Composing {len(clips)} clips")

        # Try with transitions first
        if len(clips) >= 2:
            result = compositor.compose_with_transitions(
                clips,
                f"{output_name}_composed",
                self.config.default_transition,
                self.config.transition_duration,
            )
        else:
            result = compositor.compose(
                clips,
                f"{output_name}_composed",
                audio_path,
            )

        return result

    def _post_process(
        self,
        video_path: str,
        output_name: str,
    ) -> PostProcessResult:
        """Apply post-processing effects."""
        processor = self._get_post_processor()

        config = PostProcessConfig(
            color_grade=self.config.color_grade,
            output_quality=self.config.output_quality,
            normalize_audio=self.config.normalize_audio,
        )

        return processor.process(
            video_path,
            output_name,
            config,
        )

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename."""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        result = title
        for char in invalid_chars:
            result = result.replace(char, '')

        # Replace spaces with underscores
        result = result.replace(' ', '_')

        # Limit length
        result = result[:50]

        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{result}_{timestamp}"

    def get_engine_status(self) -> Dict[str, bool]:
        """Get availability status of rendering engines."""
        router = self._get_scene_router()
        return router.get_available_engines()

    def generate_from_storyboard(
        self,
        storyboard: Storyboard,
        output_name: str,
        audio_path: Optional[str] = None,
    ) -> V3GenerationResult:
        """
        Generate video from an existing storyboard.

        Useful for re-generating with a modified storyboard.

        Args:
            storyboard: Pre-generated storyboard
            output_name: Output filename
            audio_path: Optional narration audio

        Returns:
            V3GenerationResult
        """
        start_time = time.time()
        result = V3GenerationResult(success=False)
        result.storyboard = storyboard
        result.scene_count = len(storyboard.scenes)

        try:
            # Sync timing
            timing_map = self._sync_timing(storyboard, audio_path)
            result.timing_map = timing_map

            # Render
            render_start = time.time()
            render_results = self._render_scenes(storyboard)
            result.render_time = time.time() - render_start

            rendered = [r for r in render_results if r.status in [RouteStatus.SUCCESS, RouteStatus.FALLBACK]]
            result.scenes_rendered = len(rendered)
            result.scenes_failed = len(storyboard.scenes) - len(rendered)

            # Compose
            compose_start = time.time()
            composition_result = self._compose_video(render_results, output_name, audio_path)
            result.compose_time = time.time() - compose_start

            if composition_result.success:
                # Post-process
                final_result = self._post_process(composition_result.output_path, output_name)

                result.success = True
                result.video_path = final_result.output_path if final_result.success else composition_result.output_path
                result.duration = final_result.duration if final_result.success else composition_result.duration

            result.total_time = time.time() - start_time
            return result

        except Exception as e:
            logger.error(f"Generation from storyboard failed: {e}")
            result.error = str(e)
            result.total_time = time.time() - start_time
            return result
