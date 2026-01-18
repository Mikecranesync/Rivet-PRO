# YCB v3 Architecture

## Overview

YCB (YouTube Content Bot) v3 is a professional-grade video generation pipeline that creates educational industrial automation videos. The system uses Manim for 2D animations and technical diagrams, with an extensible architecture supporting future Blender integration for 3D content.

## System Components

```
Script Text
    │
    ▼
┌──────────────────┐
│ StoryboardGenerator │  ← LLM-powered scene planning
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    SceneRouter   │  ← Routes scenes to rendering engines
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌────────┐
│ Manim │ │Blender │  ← Rendering engines
└───┬───┘ └────┬───┘
    │         │
    └────┬────┘
         ▼
┌──────────────────┐
│    TimingSync    │  ← Narration-to-scene synchronization
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ VideoCompositor  │  ← Scene composition with transitions
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  PostProcessor   │  ← Color grading, audio normalization
└────────┬─────────┘
         │
         ▼
    Final MP4
```

## Module Structure

```
ycb/
├── storyboard/           # Scene planning
│   ├── generator.py      # StoryboardGenerator - LLM scene planning
│   ├── router.py         # SceneRouter - Engine dispatch
│   └── models.py         # Scene, Storyboard dataclasses
│
├── rendering/            # Video rendering
│   ├── manim_engine.py   # ManimEngine - 2D animations
│   ├── templates.py      # Reusable scene templates
│   └── scene_types.py    # Color schemes, constants
│
├── assets/               # Visual assets
│   ├── electrical/       # IEC electrical symbols (11 SVGs)
│   └── plc/              # PLC components (17 SVGs)
│
├── audio/                # Audio processing
│   └── timing.py         # TimingSync - Whisper integration
│
├── composition/          # Video composition
│   ├── compositor.py     # VideoCompositor - FFmpeg concat
│   └── post_processor.py # PostProcessor - Color/audio
│
├── pipeline/             # Orchestration
│   ├── video_generator_v3.py  # VideoGeneratorV3 main class
│   └── autonomous_loop.py     # AutonomousLoop for batch processing
│
├── evaluation/           # Quality assessment
│   └── video_judge_v3.py # VideoQualityJudgeV3 - LLM judge
│
├── cli/                  # Command line tools
│   └── assets.py         # Asset management CLI
│
└── tests/                # Test suite
    ├── test_integration_v3.py  # E2E integration tests
    └── run_all_tests.py        # Test runner
```

## Key Classes

### StoryboardGenerator

Converts script text into structured scene definitions using LLM intelligence.

```python
from ycb.storyboard import StoryboardGenerator

generator = StoryboardGenerator()
storyboard = generator.generate(
    script="Introduction to PLCs...",
    title="PLC Basics",
    description="Learn PLC fundamentals",
    target_duration=120.0,
)
```

**Features:**
- LLM-powered scene planning (Groq/Claude)
- Rule-based fallback when LLM unavailable
- Automatic scene type classification
- Duration distribution

### SceneRouter

Routes scenes to appropriate rendering engines based on scene type.

```python
from ycb.storyboard import SceneRouter

router = SceneRouter(output_dir="./clips")
for scene in storyboard.scenes:
    result = router.route(scene)
    print(f"{scene.scene_type} -> {result.engine_used}")
```

**Routing Table:**
| Scene Type | Primary Engine | Fallback |
|------------|----------------|----------|
| TITLE | Manim | - |
| DIAGRAM | Manim | - |
| FLOWCHART | Manim | - |
| LADDER_LOGIC | Manim | - |
| THREE_D | Blender | Manim |
| B_ROLL | External | - |

### ManimEngine

Renders 2D animations using the Manim library.

```python
from ycb.rendering import ManimEngine

engine = ManimEngine(output_dir="./clips", quality="medium_quality")
clip_path = engine.render(scene_config)
```

**Supported Scene Types:**
- Title cards with animations
- Technical diagrams with callouts
- Process flowcharts
- Ladder logic diagrams
- Timelines
- Comparison tables

### VideoCompositor

Combines rendered clips with transitions and overlays.

```python
from ycb.composition import VideoCompositor, ClipConfig, TransitionType

compositor = VideoCompositor(output_dir="./final", quality="1080p")
result = compositor.compose(
    clips=[
        ClipConfig(path="clip1.mp4", transition_out=TransitionType.CROSSFADE),
        ClipConfig(path="clip2.mp4", transition_in=TransitionType.CROSSFADE),
    ],
    output_name="final_video.mp4",
)
```

**Features:**
- FFmpeg-based composition
- Transition types: cut, fade, crossfade, wipe
- Lower-third text overlays
- Audio mixing with volume control

### PostProcessor

Applies final polish to videos.

```python
from ycb.composition import PostProcessor, PostProcessConfig, ColorGradePreset

processor = PostProcessor()
result = processor.process(
    input_path="raw_video.mp4",
    config=PostProcessConfig(
        color_grade=ColorGradePreset.PROFESSIONAL,
        output_quality=OutputQuality.FULL_HD,
        normalize_audio=True,
    ),
)
```

**Color Grades:**
- `none` - No color adjustment
- `industrial` - Cool, technical look
- `clean` - Bright, clear presentation
- `warm` - Approachable, friendly
- `cinematic` - Film-like quality
- `professional` - Balanced, broadcast-ready

### VideoGeneratorV3

Main pipeline orchestrator.

```python
from ycb.pipeline import VideoGeneratorV3, V3GenerationConfig

config = V3GenerationConfig(
    output_dir="./output",
    output_quality=OutputQuality.FULL_HD,
    target_duration=120.0,
    color_grade=ColorGradePreset.PROFESSIONAL,
)

generator = VideoGeneratorV3(config)
result = generator.generate(
    script="Learn about PLCs...",
    title="PLC Fundamentals",
    description="Industrial automation basics",
)

print(f"Video: {result.video_path}")
print(f"Duration: {result.duration}s")
```

### VideoQualityJudgeV3

LLM-based quality evaluation with weighted scoring.

```python
from ycb.evaluation import VideoQualityJudgeV3

judge = VideoQualityJudgeV3(target_score=8.5)
evaluation = judge.evaluate(video_data)

print(f"Score: {evaluation.score}/10")
print(f"Passed: {evaluation.passed}")
print(f"Feedback: {evaluation.feedback}")
```

**Scoring Weights:**
- Visual Quality: 25%
- Diagram Quality: 25%
- Script Quality: 20%
- Transition Quality: 10%
- Audio Sync: 10%
- Metadata Quality: 10%

## Configuration

### V3GenerationConfig

```python
@dataclass
class V3GenerationConfig:
    output_dir: str = "./ycb_output"
    output_quality: OutputQuality = OutputQuality.FULL_HD
    fps: int = 30
    target_duration: float = 120.0
    manim_quality: str = "medium_quality"
    enable_blender: bool = False
    default_transition: TransitionType = TransitionType.FADE
    transition_duration: float = 0.5
    color_grade: ColorGradePreset = ColorGradePreset.PROFESSIONAL
    normalize_audio: bool = True
    audio_loudness: float = -16.0
```

### Quality Presets

| Preset | Resolution | Bitrate |
|--------|------------|---------|
| preview | 640x360 | 1M |
| sd | 854x480 | 2M |
| hd | 1280x720 | 4M |
| full_hd | 1920x1080 | 8M |
| qhd | 2560x1440 | 12M |
| uhd | 3840x2160 | 20M |

## CLI Tools

### Asset Management

```bash
# List all assets
python -m ycb.cli.assets list

# List with templates
python -m ycb.cli.assets list --templates

# Preview an asset
python -m ycb.cli.assets preview motor

# Test render a template
python -m ycb.cli.assets render title

# Validate asset library
python -m ycb.cli.assets validate
```

### Autonomous Loop

```bash
# Run v3 pipeline
python -m ycb.pipeline.autonomous_loop --v3

# Check engine status
python -m ycb.pipeline.autonomous_loop --check-engines

# Run specific topic
python -m ycb.pipeline.autonomous_loop --v3 --topic "PLC Programming"
```

## Dependencies

### Required

- Python 3.11+
- FFmpeg (for composition)
- Whisper (for audio timing, optional)

### Optional

- Manim (for 2D rendering)
- Blender (for 3D rendering, future)

### Python Packages

```
manim>=0.18.0
openai-whisper>=20231117
groq>=0.4.0
anthropic>=0.15.0
```

## Data Flow

1. **Script Input** → Plain text description of video content
2. **Storyboard Generation** → Structured scene list with types and durations
3. **Scene Routing** → Each scene dispatched to appropriate engine
4. **Rendering** → Engine-specific clip generation
5. **Timing Sync** → Match clips to narration timestamps
6. **Composition** → Concatenate clips with transitions
7. **Post-Processing** → Color grading, audio normalization
8. **Quality Check** → LLM evaluation with improvement feedback
9. **Final Output** → MP4 video file

## Error Handling

The pipeline implements graceful degradation:

- **LLM Unavailable** → Falls back to rule-based storyboard generation
- **Blender Unavailable** → Routes 3D scenes to Manim placeholder
- **Whisper Unavailable** → Uses text-based timing estimation
- **FFmpeg Missing** → Returns unprocessed clips with warning

## Testing

```bash
# Run all tests
python -m ycb.tests.run_all_tests

# Run integration tests only
python -m ycb.tests.test_integration_v3

# Run specific component tests
python -m ycb.storyboard.test_storyboard_generator
```

## Future Roadmap

1. **Blender Integration** - Full 3D rendering support
2. **Voice Generation** - TTS for narration
3. **Stock Footage** - B-roll integration
4. **Multi-language** - Subtitles and localization
5. **Template Marketplace** - Custom template sharing
