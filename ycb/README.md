# YCB v3 - Professional Video Generation

YCB (YouTube Content Bot) v3 is a professional-grade video generation pipeline for creating educational industrial automation content.

## Features

- **Manim Rendering** - 2D technical animations and diagrams
- **LLM Storyboarding** - AI-powered scene planning
- **28 SVG Assets** - IEC electrical and PLC symbols
- **6 Scene Templates** - Reusable animation templates
- **Quality Evaluation** - LLM-based video quality assessment
- **Autonomous Loop** - Batch video generation

## Quick Start

### Generate a Video

```python
from ycb.pipeline import VideoGeneratorV3, V3GenerationConfig
from ycb.composition import OutputQuality, ColorGradePreset

config = V3GenerationConfig(
    output_dir="./output",
    output_quality=OutputQuality.FULL_HD,
    color_grade=ColorGradePreset.PROFESSIONAL,
)

generator = VideoGeneratorV3(config)
result = generator.generate(
    script="Learn about PLCs and industrial automation...",
    title="PLC Fundamentals",
    description="Introduction to Programmable Logic Controllers",
)

print(f"Video: {result.video_path}")
```

### CLI Tools

```bash
# List all assets
python -m ycb.cli.assets list

# List with templates
python -m ycb.cli.assets list --templates

# Preview an asset
python -m ycb.cli.assets preview motor

# Test render a template
python -m ycb.cli.assets render title

# Validate assets
python -m ycb.cli.assets validate
```

### Autonomous Loop

```bash
# Run v3 pipeline
python -m ycb.pipeline.autonomous_loop --v3

# Check engine availability
python -m ycb.pipeline.autonomous_loop --check-engines
```

## Module Structure

```
ycb/
├── storyboard/     # Scene planning (generator, router, models)
├── rendering/      # Manim engine and templates
├── assets/         # SVG symbols (electrical, plc)
├── audio/          # Timing synchronization
├── composition/    # Video compositor and post-processor
├── pipeline/       # Main generator and autonomous loop
├── evaluation/     # Quality judge
├── cli/            # Command line tools
└── tests/          # Integration tests
```

## Requirements

- Python 3.11+
- FFmpeg (for video composition)
- Manim (optional, for rendering)
- Whisper (optional, for audio timing)

```bash
pip install manim openai-whisper groq anthropic
```

## Documentation

- [Architecture Overview](../docs/YCB_V3_ARCHITECTURE.md)
- [Asset Creation Guide](../docs/ASSET_CREATION_GUIDE.md)
- [Template Development](../docs/TEMPLATE_DEVELOPMENT.md)

## Available Assets

### Electrical Symbols (11)

motor, relay, contactor, overload, transformer, fuse, switch,
digital_input, digital_output, analog_input, analog_output

### PLC Symbols (17)

plc_rack, cpu_module, io_module, power_supply,
ladder_xic, ladder_xio, ladder_ote, ladder_otl, ladder_otu,
ladder_ton, ladder_tof, ladder_ctu, ladder_ctd,
comm_ethernet, comm_serial, comm_modbus, comm_profinet

### Templates (6)

title, diagram, flowchart, comparison, ladderlogic, timeline

## Testing

```bash
# Run all tests
python -m ycb.tests.run_all_tests

# Run integration tests
python -m ycb.tests.test_integration_v3
```

## Quality Standards

Videos are evaluated on a 10-point scale with 8.5 minimum threshold:

| Dimension | Weight |
|-----------|--------|
| Visual Quality | 25% |
| Diagram Quality | 25% |
| Script Quality | 20% |
| Transition Quality | 10% |
| Audio Sync | 10% |
| Metadata Quality | 10% |
