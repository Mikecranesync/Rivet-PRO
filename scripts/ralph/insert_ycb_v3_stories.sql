-- YCB v3: Professional Video Generation with Manim + Blender
-- 18 Ralph Stories for Autonomous Development
-- Run: psql $DATABASE_URL -f scripts/ralph/insert_ycb_v3_stories.sql

-- Clear any existing YCB v3 stories (idempotent)
DELETE FROM ralph_stories WHERE story_id LIKE 'YCB3-%';

-- Insert all 18 stories
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status) VALUES

-- =============================================================================
-- EPIC 1: Foundation & Asset Library (Week 1)
-- =============================================================================

(1, 'YCB3-MANIM-001', 'Create Manim rendering engine integration',
'Create a Python module that generates Manim scenes from structured scene descriptions. This is the core rendering engine for technical diagrams and animations.',
'["ycb/rendering/manim_engine.py exists with ManimEngine class", "Can render basic scenes: text, shapes, arrows, diagrams", "Outputs MP4 clips to specified directory", "Includes error handling and logging", "Test: Generate a simple PLC diagram animation", "Files: ycb/rendering/__init__.py, ycb/rendering/manim_engine.py, ycb/rendering/scene_types.py"]'::jsonb,
1, 'todo'),

(1, 'YCB3-ASSETS-001', 'Create SVG asset library for electrical symbols',
'Create reusable SVG assets for common industrial electrical symbols that can be animated in Manim.',
'["ycb/assets/electrical/ directory with SVG files", "Symbols: motor, relay, contactor, overload, transformer, fuse, switch", "PLC I/O symbols: digital input, digital output, analog input", "Each symbol has consistent sizing and anchor points", "Manim can import and animate these symbols", "Files: ycb/assets/electrical/*.svg (15-20 symbols), ycb/assets/electrical/manifest.json"]'::jsonb,
2, 'todo'),

(1, 'YCB3-ASSETS-002', 'Create SVG/PNG assets for PLC components',
'Create visual assets for PLC hardware and software components.',
'["ycb/assets/plc/ directory with assets", "Hardware: PLC rack, CPU, I/O cards, power supply", "Software: ladder logic symbols (XIC, XIO, OTE, TON, CTU)", "Communication: Ethernet, serial, Modbus icons", "Consistent visual style across all assets", "Files: ycb/assets/plc/*.svg (20-25 assets), ycb/assets/plc/manifest.json"]'::jsonb,
3, 'todo'),

(1, 'YCB3-MANIM-002', 'Create reusable Manim scene templates',
'Create template classes for common video scene types that can be parameterized and reused.',
'["TitleScene - Animated title cards with topic name", "DiagramScene - Technical diagram with callouts", "FlowchartScene - Process flow with animated arrows", "ComparisonScene - Side-by-side comparison", "LadderLogicScene - PLC ladder diagram animation", "TimelineScene - Sequential process steps", "Each template is parameterized and reusable", "Files: ycb/rendering/templates/title.py, diagram.py, flowchart.py, comparison.py, ladder_logic.py, timeline.py"]'::jsonb,
4, 'todo'),

-- =============================================================================
-- EPIC 2: Blender Integration (Week 2)
-- =============================================================================

(1, 'YCB3-BLENDER-001', 'Create Blender headless rendering engine',
'Create a module that generates 3D animations using Blender Python API in headless mode for professional 3D equipment animations.',
'["ycb/rendering/blender_engine.py with BlenderEngine class", "Can run Blender in background (no GUI)", "Renders to MP4 with configurable resolution/fps", "Includes basic scene setup (camera, lighting)", "Error handling for Blender subprocess failures", "Test: Render a spinning motor animation", "Files: ycb/rendering/blender_engine.py, ycb/rendering/blender_scripts/"]'::jsonb,
5, 'todo'),

(1, 'YCB3-ASSETS-003', 'Create/source 3D models for industrial equipment',
'Build a library of 3D models (.blend files) for common industrial equipment.',
'["ycb/assets/3d/ directory with .blend files", "Models: motor, VFD, PLC cabinet, conveyor section, pump", "Each model has proper materials and textures", "Models are optimized for rendering (low poly where appropriate)", "Include animation rigs where relevant (motor rotation)", "Files: ycb/assets/3d/*.blend (8-10 models), ycb/assets/3d/manifest.json"]'::jsonb,
6, 'todo'),

(1, 'YCB3-BLENDER-002', 'Create reusable Blender scene templates',
'Create parameterized Blender scene templates for common industrial animations.',
'["MotorRotationScene - Motor spinning with speed control", "SignalFlowScene - Animated signal path through components", "ExplodedViewScene - Component assembly/disassembly", "ControlPanelScene - Panel with animated indicators", "Each template accepts parameters (speed, colors, labels)", "Templates render in <60 seconds each", "Files: ycb/rendering/blender_templates/motor.py, signal_flow.py, exploded_view.py, control_panel.py"]'::jsonb,
7, 'todo'),

-- =============================================================================
-- EPIC 3: Storyboard & Scene Planning (Week 2-3)
-- =============================================================================

(1, 'YCB3-STORY-001', 'Create AI-powered storyboard generator',
'Create a module that converts scripts into structured storyboards with scene definitions using LLM intelligence.',
'["ycb/storyboard/generator.py with StoryboardGenerator class", "Takes script text as input", "Outputs list of Scene objects with: scene type, duration, visual description, narration text, suggested template + parameters", "Uses LLM (Groq/Claude) for intelligent scene planning", "Respects timing constraints (total video duration)", "Files: ycb/storyboard/__init__.py, generator.py, models.py"]'::jsonb,
8, 'todo'),

(1, 'YCB3-STORY-002', 'Create scene-to-renderer routing system',
'Create a router that dispatches scenes to the appropriate rendering engine based on scene type.',
'["ycb/storyboard/router.py with SceneRouter class", "Routes: diagram/flowchart/ladder_logic -> Manim", "Routes: 3d_animation/exploded_view/motor -> Blender", "Routes: b_roll/stock -> Placeholder/external", "Supports fallback (if Blender unavailable -> Manim)", "Returns rendered clip paths for composition", "Files: ycb/storyboard/router.py"]'::jsonb,
9, 'todo'),

(1, 'YCB3-AUDIO-001', 'Create narration-to-scene timing synchronization',
'Ensure narration audio syncs properly with visual scenes through word-level timing analysis.',
'["ycb/audio/timing.py with TimingSync class", "Analyzes narration audio to get word-level timestamps", "Matches timestamps to scene boundaries", "Adjusts scene durations or adds pauses as needed", "Outputs timing map for final composition", "Files: ycb/audio/__init__.py, timing.py"]'::jsonb,
10, 'todo'),

-- =============================================================================
-- EPIC 4: Video Composition (Week 3)
-- =============================================================================

(1, 'YCB3-COMPOSE-001', 'Create multi-scene video compositor',
'Create a compositor that combines rendered scenes into final video with professional transitions.',
'["ycb/composition/compositor.py with VideoCompositor class", "Accepts list of rendered scene clips + audio", "Supports transitions (fade, dissolve, cut)", "Adds lower-third text overlays for key points", "Adds intro/outro bumpers", "Outputs final MP4 with proper encoding", "Files: ycb/composition/__init__.py, compositor.py, transitions.py, overlays.py"]'::jsonb,
11, 'todo'),

(1, 'YCB3-COMPOSE-002', 'Add post-processing effects pipeline',
'Add polish effects to final video output for professional quality.',
'["Color grading presets (industrial, clean, warm)", "Audio normalization", "Watermark/logo overlay option", "Subtitle track generation from script", "Configurable output quality presets (720p, 1080p, 4K)", "Files: ycb/composition/post_processing.py, presets.py"]'::jsonb,
12, 'todo'),

-- =============================================================================
-- EPIC 5: Pipeline Integration (Week 3-4)
-- =============================================================================

(1, 'YCB3-PIPE-001', 'Create unified v3 video generation pipeline',
'Create the main v3 pipeline that orchestrates all components from script to final video.',
'["ycb/pipeline/video_generator_v3.py with VideoGeneratorV3 class", "Full pipeline: script -> storyboard -> render -> compose -> output", "Parallel rendering of independent scenes", "Progress tracking and logging", "Graceful degradation (Blender unavailable -> Manim only)", "Quality metrics output", "Files: ycb/pipeline/video_generator_v3.py"]'::jsonb,
13, 'todo'),

(1, 'YCB3-JUDGE-001', 'Update quality judge for v3 visual standards',
'Update the LLM judge rubric to evaluate v3 quality standards including visual quality.',
'["Updated rubric includes visual quality assessment", "Evaluates: animation smoothness, diagram clarity, 3D quality", "Higher pass threshold (8.5/10 for v3)", "Specific feedback for visual improvements", "Files to modify: ycb/evaluation/video_judge.py (add V3 rubric)"]'::jsonb,
14, 'todo'),

(1, 'YCB3-AUTO-001', 'Update autonomous loop for v3 pipeline',
'Update the autonomous loop to use the v3 pipeline with appropriate flags and metrics.',
'["--v3 flag to use new pipeline", "Tracks v3-specific metrics (render time, scene count)", "Fallback to v2 if v3 dependencies unavailable", "Files to modify: ycb/pipeline/autonomous_loop.py"]'::jsonb,
15, 'todo'),

-- =============================================================================
-- EPIC 6: Testing & Documentation (Week 4)
-- =============================================================================

(1, 'YCB3-TEST-001', 'Create comprehensive integration tests',
'Create tests for the full v3 pipeline and all rendering engines.',
'["Test Manim engine independently", "Test Blender engine independently", "Test storyboard generation", "Test full pipeline end-to-end", "Test fallback behaviors", "Files: tests/test_manim_engine.py, test_blender_engine.py, test_storyboard.py, test_video_generator_v3.py"]'::jsonb,
16, 'todo'),

(1, 'YCB3-CLI-001', 'Create CLI tools for asset management',
'Create CLI commands for managing and previewing assets.',
'["ycb assets list - List all assets", "ycb assets preview <asset> - Preview an asset", "ycb assets render <template> - Test render a template", "ycb assets validate - Validate asset library", "Files: ycb/cli/assets.py"]'::jsonb,
17, 'todo'),

(1, 'YCB3-DOCS-001', 'Create v3 documentation',
'Document the v3 system for future development and maintenance.',
'["docs/YCB_V3_ARCHITECTURE.md - System overview", "docs/ASSET_CREATION_GUIDE.md - How to add new assets", "docs/TEMPLATE_DEVELOPMENT.md - Creating new templates", "Updated README with v3 features"]'::jsonb,
18, 'todo');

-- Verify insertion
SELECT story_id, title, priority, status FROM ralph_stories
WHERE story_id LIKE 'YCB3-%'
ORDER BY priority;
