# YCB v3: Professional Video Generation with Manim + Blender

## Resume Prompt for WhatsApp/New Session

**Context:** We built YCB v1.0 and v2.0 video generator with LLM-as-Judge quality system. Videos improved from 5-6/10 to 8.3-8.5/10 with feedback loops. Now we're planning v3 with Manim + Blender for 8.5-9/10 quality.

**To Resume:** "Continue implementing YCB v3 from the plan in YCB_V3_IMPLEMENTATION_PLAN.md. Start with Story 1.1: Manim Integration Module."

---

## Executive Summary

Build a professional-grade video generation system that produces 8.5-9/10 quality industrial automation training videos using open-source tools (Manim + Blender + FFmpeg).

**Current State (v2):** PIL slides + Edge TTS → 5-6/10 quality
**Target State (v3):** Manim diagrams + Blender 3D + Edge TTS → 8.5-9/10 quality

**Cost:** $0.50-$5 per video (vs $90-$150 for Sora 2)

---

## Architecture Overview

```
Script (Claude/Groq)
    ↓
Storyboard Generator (new)
    ↓
┌─────────────────────────────────────────────────────┐
│  Visual Generation (parallel)                        │
│  ├─ Manim Engine (60%): Technical diagrams, flows   │
│  ├─ Blender Engine (30%): 3D component animations   │
│  └─ B-Roll Provider (10%): Stock/AI fallback        │
└─────────────────────────────────────────────────────┘
    ↓
Scene Compositor (FFmpeg + MoviePy)
    ↓
Audio Layer (Edge TTS + timing sync)
    ↓
Final Video (8.5-9/10 quality)
```

---

## Ralph Stories (18 Stories, ~4 weeks)

### Epic 1: Foundation & Asset Library (Week 1)

#### Story 1.1: Manim Integration Module
**ID:** YCB3-MANIM-001
**Title:** Create Manim rendering engine integration
**Priority:** High
**Estimate:** 8 hours

**Description:**
Create a Python module that generates Manim scenes from structured scene descriptions.

**Acceptance Criteria:**
- [ ] `ycb/rendering/manim_engine.py` exists with `ManimEngine` class
- [ ] Can render basic scenes: text, shapes, arrows, diagrams
- [ ] Outputs MP4 clips to specified directory
- [ ] Includes error handling and logging
- [ ] Test: Generate a simple PLC diagram animation

**Files to Create:**
- `ycb/rendering/__init__.py`
- `ycb/rendering/manim_engine.py`
- `ycb/rendering/scene_types.py` (Pydantic models)

---

#### Story 1.2: Industrial Asset Library - Electrical Symbols
**ID:** YCB3-ASSETS-001
**Title:** Create SVG asset library for electrical symbols
**Priority:** High
**Estimate:** 6 hours

**Description:**
Create reusable SVG assets for common industrial electrical symbols.

**Acceptance Criteria:**
- [ ] `ycb/assets/electrical/` directory with SVG files
- [ ] Symbols: motor, relay, contactor, overload, transformer, fuse, switch
- [ ] PLC I/O symbols: digital input, digital output, analog input
- [ ] Each symbol has consistent sizing and anchor points
- [ ] Manim can import and animate these symbols

**Files to Create:**
- `ycb/assets/electrical/*.svg` (15-20 symbols)
- `ycb/assets/electrical/manifest.json` (metadata)

---

#### Story 1.3: Industrial Asset Library - PLC Components
**ID:** YCB3-ASSETS-002
**Title:** Create SVG/PNG assets for PLC components
**Priority:** High
**Estimate:** 6 hours

**Description:**
Create visual assets for PLC hardware and software components.

**Acceptance Criteria:**
- [ ] `ycb/assets/plc/` directory with assets
- [ ] Hardware: PLC rack, CPU, I/O cards, power supply
- [ ] Software: ladder logic symbols (XIC, XIO, OTE, TON, CTU)
- [ ] Communication: Ethernet, serial, Modbus icons
- [ ] Consistent visual style across all assets

**Files to Create:**
- `ycb/assets/plc/*.svg` (20-25 assets)
- `ycb/assets/plc/manifest.json`

---

#### Story 1.4: Manim Scene Templates
**ID:** YCB3-MANIM-002
**Title:** Create reusable Manim scene templates
**Priority:** Medium
**Estimate:** 8 hours

**Description:**
Create template classes for common video scene types.

**Acceptance Criteria:**
- [ ] `TitleScene` - Animated title cards with topic name
- [ ] `DiagramScene` - Technical diagram with callouts
- [ ] `FlowchartScene` - Process flow with animated arrows
- [ ] `ComparisonScene` - Side-by-side comparison
- [ ] `LadderLogicScene` - PLC ladder diagram animation
- [ ] `TimelineScene` - Sequential process steps
- [ ] Each template is parameterized and reusable

**Files to Create:**
- `ycb/rendering/templates/title.py`
- `ycb/rendering/templates/diagram.py`
- `ycb/rendering/templates/flowchart.py`
- `ycb/rendering/templates/comparison.py`
- `ycb/rendering/templates/ladder_logic.py`
- `ycb/rendering/templates/timeline.py`

---

### Epic 2: Blender Integration (Week 2)

#### Story 2.1: Blender Python Engine
**ID:** YCB3-BLENDER-001
**Title:** Create Blender headless rendering engine
**Priority:** High
**Estimate:** 10 hours

**Description:**
Create a module that generates 3D animations using Blender's Python API in headless mode.

**Acceptance Criteria:**
- [ ] `ycb/rendering/blender_engine.py` with `BlenderEngine` class
- [ ] Can run Blender in background (no GUI)
- [ ] Renders to MP4 with configurable resolution/fps
- [ ] Includes basic scene setup (camera, lighting)
- [ ] Error handling for Blender subprocess failures
- [ ] Test: Render a spinning motor animation

**Dependencies:**
- Blender installed and accessible via CLI

**Files to Create:**
- `ycb/rendering/blender_engine.py`
- `ycb/rendering/blender_scripts/` (Python scripts for Blender)

---

#### Story 2.2: 3D Asset Library - Industrial Equipment
**ID:** YCB3-ASSETS-003
**Title:** Create/source 3D models for industrial equipment
**Priority:** High
**Estimate:** 8 hours

**Description:**
Build a library of 3D models (.blend files) for common industrial equipment.

**Acceptance Criteria:**
- [ ] `ycb/assets/3d/` directory with .blend files
- [ ] Models: motor, VFD, PLC cabinet, conveyor section, pump
- [ ] Each model has proper materials and textures
- [ ] Models are optimized for rendering (low poly where appropriate)
- [ ] Include animation rigs where relevant (motor rotation, etc.)

**Sources:** GrabCAD, Sketchfab (CC0), or custom creation

**Files to Create:**
- `ycb/assets/3d/*.blend` (8-10 models)
- `ycb/assets/3d/manifest.json`

---

#### Story 2.3: Blender Scene Templates
**ID:** YCB3-BLENDER-002
**Title:** Create reusable Blender scene templates
**Priority:** Medium
**Estimate:** 8 hours

**Description:**
Create parameterized Blender scene templates for common animations.

**Acceptance Criteria:**
- [ ] `MotorRotationScene` - Motor spinning with speed control
- [ ] `SignalFlowScene` - Animated signal path through components
- [ ] `ExplodedViewScene` - Component assembly/disassembly
- [ ] `ControlPanelScene` - Panel with animated indicators
- [ ] Each template accepts parameters (speed, colors, labels)
- [ ] Templates render in <60 seconds each

**Files to Create:**
- `ycb/rendering/blender_templates/motor.py`
- `ycb/rendering/blender_templates/signal_flow.py`
- `ycb/rendering/blender_templates/exploded_view.py`
- `ycb/rendering/blender_templates/control_panel.py`

---

### Epic 3: Storyboard & Scene Planning (Week 2-3)

#### Story 3.1: Storyboard Generator
**ID:** YCB3-STORY-001
**Title:** Create AI-powered storyboard generator
**Priority:** High
**Estimate:** 10 hours

**Description:**
Create a module that converts scripts into structured storyboards with scene definitions.

**Acceptance Criteria:**
- [ ] `ycb/storyboard/generator.py` with `StoryboardGenerator` class
- [ ] Takes script text as input
- [ ] Outputs list of `Scene` objects with:
  - Scene type (title, diagram, 3d, comparison, etc.)
  - Duration (seconds)
  - Visual description
  - Narration text for that scene
  - Suggested template + parameters
- [ ] Uses LLM (Groq/Claude) for intelligent scene planning
- [ ] Respects timing constraints (total video duration)

**Files to Create:**
- `ycb/storyboard/__init__.py`
- `ycb/storyboard/generator.py`
- `ycb/storyboard/models.py` (Pydantic Scene models)

---

#### Story 3.2: Scene Router
**ID:** YCB3-STORY-002
**Title:** Create scene-to-renderer routing system
**Priority:** High
**Estimate:** 6 hours

**Description:**
Create a router that dispatches scenes to the appropriate rendering engine.

**Acceptance Criteria:**
- [ ] `ycb/storyboard/router.py` with `SceneRouter` class
- [ ] Routes scenes by type:
  - `diagram`, `flowchart`, `ladder_logic` → Manim
  - `3d_animation`, `exploded_view`, `motor` → Blender
  - `b_roll`, `stock` → Placeholder/external
- [ ] Supports fallback (if Blender unavailable → Manim)
- [ ] Returns rendered clip paths for composition

**Files to Create:**
- `ycb/storyboard/router.py`

---

#### Story 3.3: Narration Timing Sync
**ID:** YCB3-AUDIO-001
**Title:** Create narration-to-scene timing synchronization
**Priority:** Medium
**Estimate:** 6 hours

**Description:**
Ensure narration audio syncs properly with visual scenes.

**Acceptance Criteria:**
- [ ] `ycb/audio/timing.py` with `TimingSync` class
- [ ] Analyzes narration audio to get word-level timestamps
- [ ] Matches timestamps to scene boundaries
- [ ] Adjusts scene durations or adds pauses as needed
- [ ] Outputs timing map for final composition

**Files to Create:**
- `ycb/audio/__init__.py`
- `ycb/audio/timing.py`

---

### Epic 4: Video Composition (Week 3)

#### Story 4.1: Scene Compositor
**ID:** YCB3-COMPOSE-001
**Title:** Create multi-scene video compositor
**Priority:** High
**Estimate:** 8 hours

**Description:**
Create a compositor that combines rendered scenes into final video with transitions.

**Acceptance Criteria:**
- [ ] `ycb/composition/compositor.py` with `VideoCompositor` class
- [ ] Accepts list of rendered scene clips + audio
- [ ] Supports transitions (fade, dissolve, cut)
- [ ] Adds lower-third text overlays for key points
- [ ] Adds intro/outro bumpers
- [ ] Outputs final MP4 with proper encoding

**Files to Create:**
- `ycb/composition/__init__.py`
- `ycb/composition/compositor.py`
- `ycb/composition/transitions.py`
- `ycb/composition/overlays.py`

---

#### Story 4.2: Video Post-Processing
**ID:** YCB3-COMPOSE-002
**Title:** Add post-processing effects pipeline
**Priority:** Medium
**Estimate:** 4 hours

**Description:**
Add polish effects to final video output.

**Acceptance Criteria:**
- [ ] Color grading presets (industrial, clean, warm)
- [ ] Audio normalization
- [ ] Watermark/logo overlay option
- [ ] Subtitle track generation from script
- [ ] Configurable output quality presets (720p, 1080p, 4K)

**Files to Create:**
- `ycb/composition/post_processing.py`
- `ycb/composition/presets.py`

---

### Epic 5: Pipeline Integration (Week 3-4)

#### Story 5.1: V3 Video Generator
**ID:** YCB3-PIPE-001
**Title:** Create unified v3 video generation pipeline
**Priority:** High
**Estimate:** 10 hours

**Description:**
Create the main v3 pipeline that orchestrates all components.

**Acceptance Criteria:**
- [ ] `ycb/pipeline/video_generator_v3.py` with `VideoGeneratorV3` class
- [ ] Full pipeline: script → storyboard → render → compose → output
- [ ] Parallel rendering of independent scenes
- [ ] Progress tracking and logging
- [ ] Graceful degradation (Blender unavailable → Manim only)
- [ ] Quality metrics output

**Files to Create:**
- `ycb/pipeline/video_generator_v3.py`

---

#### Story 5.2: Quality Judge V3
**ID:** YCB3-JUDGE-001
**Title:** Update quality judge for v3 visual standards
**Priority:** Medium
**Estimate:** 4 hours

**Description:**
Update the LLM judge rubric to evaluate v3 quality standards.

**Acceptance Criteria:**
- [ ] Updated rubric includes visual quality assessment
- [ ] Evaluates: animation smoothness, diagram clarity, 3D quality
- [ ] Higher pass threshold (8.5/10 for v3)
- [ ] Specific feedback for visual improvements

**Files to Modify:**
- `ycb/evaluation/video_judge.py` (add V3 rubric)

---

#### Story 5.3: V3 Autonomous Loop
**ID:** YCB3-AUTO-001
**Title:** Update autonomous loop for v3 pipeline
**Priority:** Medium
**Estimate:** 4 hours

**Description:**
Update the autonomous loop to use the v3 pipeline.

**Acceptance Criteria:**
- [ ] `--v3` flag to use new pipeline
- [ ] Tracks v3-specific metrics (render time, scene count)
- [ ] Fallback to v2 if v3 dependencies unavailable

**Files to Modify:**
- `ycb/pipeline/autonomous_loop.py`

---

### Epic 6: Testing & Documentation (Week 4)

#### Story 6.1: Integration Tests
**ID:** YCB3-TEST-001
**Title:** Create comprehensive integration tests
**Priority:** High
**Estimate:** 6 hours

**Description:**
Create tests for the full v3 pipeline.

**Acceptance Criteria:**
- [ ] Test Manim engine independently
- [ ] Test Blender engine independently
- [ ] Test storyboard generation
- [ ] Test full pipeline end-to-end
- [ ] Test fallback behaviors

**Files to Create:**
- `tests/test_manim_engine.py`
- `tests/test_blender_engine.py`
- `tests/test_storyboard.py`
- `tests/test_video_generator_v3.py`

---

#### Story 6.2: Asset Creation CLI
**ID:** YCB3-CLI-001
**Title:** Create CLI tools for asset management
**Priority:** Low
**Estimate:** 4 hours

**Description:**
Create CLI commands for managing and previewing assets.

**Acceptance Criteria:**
- [ ] `ycb assets list` - List all assets
- [ ] `ycb assets preview <asset>` - Preview an asset
- [ ] `ycb assets render <template>` - Test render a template
- [ ] `ycb assets validate` - Validate asset library

**Files to Create:**
- `ycb/cli/assets.py`

---

#### Story 6.3: Documentation
**ID:** YCB3-DOCS-001
**Title:** Create v3 documentation
**Priority:** Medium
**Estimate:** 4 hours

**Description:**
Document the v3 system for future development.

**Acceptance Criteria:**
- [ ] `docs/YCB_V3_ARCHITECTURE.md` - System overview
- [ ] `docs/ASSET_CREATION_GUIDE.md` - How to add new assets
- [ ] `docs/TEMPLATE_DEVELOPMENT.md` - Creating new templates
- [ ] Updated README with v3 features

**Files to Create:**
- `docs/YCB_V3_ARCHITECTURE.md`
- `docs/ASSET_CREATION_GUIDE.md`
- `docs/TEMPLATE_DEVELOPMENT.md`

---

## File Structure (Final)

```
ycb/
├── __init__.py
├── config.py
├── pipeline/
│   ├── __init__.py
│   ├── video_generator.py       # v2 (existing)
│   ├── video_generator_v3.py    # v3 (NEW)
│   ├── video_assembler.py       # v2 (existing)
│   ├── quality_iteration.py     # (existing)
│   ├── autonomous_loop.py       # (existing, updated)
│   └── metrics.py               # (existing)
├── rendering/                    # NEW
│   ├── __init__.py
│   ├── manim_engine.py
│   ├── blender_engine.py
│   ├── scene_types.py
│   ├── templates/
│   │   ├── __init__.py
│   │   ├── title.py
│   │   ├── diagram.py
│   │   ├── flowchart.py
│   │   ├── ladder_logic.py
│   │   └── ...
│   └── blender_templates/
│       ├── __init__.py
│       ├── motor.py
│       ├── signal_flow.py
│       └── ...
├── storyboard/                   # NEW
│   ├── __init__.py
│   ├── generator.py
│   ├── router.py
│   └── models.py
├── composition/                  # NEW
│   ├── __init__.py
│   ├── compositor.py
│   ├── transitions.py
│   ├── overlays.py
│   └── post_processing.py
├── audio/                        # NEW
│   ├── __init__.py
│   └── timing.py
├── assets/                       # NEW
│   ├── electrical/
│   │   ├── *.svg
│   │   └── manifest.json
│   ├── plc/
│   │   ├── *.svg
│   │   └── manifest.json
│   └── 3d/
│       ├── *.blend
│       └── manifest.json
├── evaluation/
│   ├── __init__.py
│   └── video_judge.py           # (updated for v3)
├── services/                     # (existing)
└── ...
```

---

## Dependencies to Add

```toml
# pyproject.toml additions
manim = "^0.18"           # Math animation engine
moviepy = "^1.0"          # Video composition
Pillow = "^10.0"          # Image processing
pydub = "^0.25"           # Audio processing
numpy = "^1.26"           # Numerical operations

# External (system):
# - Blender 4.0+ (installed separately)
# - FFmpeg (already have)
```

---

## Quality Comparison

| Aspect | v2 (Current) | v3 (Target) |
|--------|--------------|-------------|
| Visual Quality | 5-6/10 (PIL slides) | 8.5-9/10 (Manim+Blender) |
| Technical Diagrams | Basic text boxes | Animated schematics |
| 3D Content | None | Motor, VFD, PLC animations |
| Transitions | Hard cuts | Fade, dissolve effects |
| Lower Thirds | None | Professional callouts |
| Render Time | ~30 sec | ~3-5 min |
| Cost per Video | $0.03 | $0.50-$5 |

---

## Verification Plan

### Per-Story Verification
Each story includes specific acceptance criteria that must pass.

### Integration Verification
```bash
# Test Manim rendering
python -c "from ycb.rendering import ManimEngine; e = ManimEngine(); e.render_test()"

# Test Blender rendering
python -c "from ycb.rendering import BlenderEngine; e = BlenderEngine(); e.render_test()"

# Test storyboard generation
python -c "from ycb.storyboard import StoryboardGenerator; s = StoryboardGenerator(); print(s.generate('Test topic'))"

# Full v3 pipeline test
python -m ycb.pipeline.video_generator_v3 "What is a Relay" --test

# Quality comparison
python -m ycb.evaluation.video_judge ycb_output/v3_test/metadata.json
```

---

## Timeline

| Week | Focus | Stories |
|------|-------|---------|
| 1 | Foundation | 1.1, 1.2, 1.3, 1.4 |
| 2 | Blender + Storyboard | 2.1, 2.2, 2.3, 3.1, 3.2 |
| 3 | Composition + Pipeline | 3.3, 4.1, 4.2, 5.1 |
| 4 | Integration + Polish | 5.2, 5.3, 6.1, 6.2, 6.3 |

**Total:** 18 stories, ~120 hours, 4 weeks

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Blender installation complex | Provide Docker container with Blender pre-installed |
| Render times too long | Implement parallel scene rendering |
| Asset creation time-consuming | Start with 10 core assets, expand later |
| Manim learning curve | Use simple templates first, iterate |
| Quality still not 8.5/10 | Iterative refinement with judge feedback |

---

## Success Metrics

- [ ] Generate 8.5/10+ quality video with v3 pipeline
- [ ] Render time <5 minutes for 3-minute video
- [ ] Cost per video <$5
- [ ] All 18 stories pass acceptance criteria
- [ ] 10 sample videos produced demonstrating quality

---

## Git Commits So Far (v1.0 and v2.0)

```
283f0b7 - feat(ycb): Add LLM-as-Judge VideoQualityJudge (Phase 1)
c6b5a93 - feat(ycb): Add QualityIterativeGenerator with feedback loop (Phase 2)
4b08bea - feat(ycb): Add PipelineMetrics and AutonomousLoop (Phases 3-4)
```

**Branch:** `feature/ycb-video-generator-v1.0`
**Tag:** `v1.0.0-ycb`
