# YCB Template Development Guide

This guide explains how to create new Manim scene templates for the YCB v3 video generation system.

## Template Architecture

Templates are Python dataclasses that generate Manim animation code. Each template:

1. Accepts parameters for customization
2. Has a `generate_code()` method that returns Manim Python code
3. Can be rendered by the ManimEngine

**Location:** `ycb/rendering/templates.py`

---

## Existing Templates

| Template | Purpose |
|----------|---------|
| TitleTemplate | Animated title cards with subtitles |
| DiagramTemplate | Technical diagrams with callouts |
| FlowchartTemplate | Process flows with animated arrows |
| ComparisonTemplate | Side-by-side comparisons |
| LadderLogicTemplate | PLC ladder diagram animations |
| TimelineTemplate | Sequential process timelines |

---

## Creating a New Template

### Step 1: Define the Dataclass

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class MyCustomTemplate:
    """
    Description of what this template does.

    Creates animated scenes for [specific purpose].
    """
    # Required parameters
    title: str

    # Optional parameters with defaults
    duration: float = 5.0
    background_color: str = "#1A1A2E"
    title_color: str = "#FFFFFF"
    font_size: int = 48

    # Complex parameters
    items: List[str] = field(default_factory=list)

    def generate_code(self) -> str:
        """Generate Manim Python code for this scene."""
        # Build the Manim code as a string
        code = f'''from manim import *

class MyCustomScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"

        # Title
        title = Text("{self.title}", font_size={self.font_size}, color="{self.title_color}")
        self.play(Write(title), run_time=1.5)
        self.wait({self.duration - 1.5})
'''
        return code
```

### Step 2: Add Supporting Dataclasses (if needed)

For complex templates, define helper dataclasses:

```python
@dataclass
class MyItem:
    """An item to display in the template."""
    text: str
    color: str = "#FFFFFF"
    position: int = 0
```

### Step 3: Implement generate_code()

The `generate_code()` method must return valid Manim Python code:

```python
def generate_code(self) -> str:
    # Build item creation code
    items_code = ""
    for i, item in enumerate(self.items):
        items_code += f'''
        item_{i} = Text("{item.text}", color="{item.color}")
        item_{i}.move_to(DOWN * {i * 0.8})
'''

    # Build animation code
    animations = ""
    for i in range(len(self.items)):
        animations += f"        self.play(FadeIn(item_{i}), run_time=0.5)\n"

    return f'''from manim import *

class MyCustomScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"
{items_code}
{animations}
        self.wait({self.duration})
'''
```

---

## Template Patterns

### 1. String Formatting

Use f-strings for simple substitution:

```python
code = f'''
title = Text("{self.title}", font_size={self.font_size})
'''
```

### 2. Conditional Elements

Handle optional elements with conditionals:

```python
subtitle_code = ""
if self.subtitle:
    subtitle_code = f'''
        subtitle = Text("{self.subtitle}", font_size=24)
        subtitle.next_to(title, DOWN)
        self.play(FadeIn(subtitle))
'''
```

### 3. Loops for Lists

Generate code for multiple items:

```python
for i, item in enumerate(self.items):
    code += f"        item_{i} = Text('{item}')\n"
```

### 4. Complex Positioning

Use Manim's positioning methods:

```python
# Relative positioning
element.next_to(other, DOWN, buff=0.5)
element.move_to(LEFT * 2 + UP * 1)

# Grid layout
for i, item in enumerate(items):
    row = i // 3
    col = i % 3
    item.move_to(LEFT * (2 - col * 2) + UP * (1 - row * 1.5))
```

---

## Example: Creating a Stats Template

This template displays animated statistics:

```python
@dataclass
class StatItem:
    """A statistic to display."""
    value: str
    label: str
    color: str = "#3B82F6"


@dataclass
class StatsTemplate:
    """
    Animated statistics display template.

    Shows key metrics with animated counter effects.
    """
    title: str
    stats: List[StatItem] = field(default_factory=list)
    duration: float = 8.0
    background_color: str = "#1A1A2E"
    title_color: str = "#FFFFFF"
    columns: int = 3

    def generate_code(self) -> str:
        # Build stat elements
        stat_elements = ""
        stat_positions = ""
        stat_animations = ""

        for i, stat in enumerate(self.stats):
            col = i % self.columns
            row = i // self.columns
            x_pos = -3 + col * 3
            y_pos = -row * 2

            stat_elements += f'''
        stat_{i}_value = Text("{stat.value}", font_size=48, color="{stat.color}")
        stat_{i}_label = Text("{stat.label}", font_size=24, color=WHITE)
        stat_{i}_group = VGroup(stat_{i}_value, stat_{i}_label).arrange(DOWN, buff=0.2)
'''
            stat_positions += f"        stat_{i}_group.move_to(RIGHT * {x_pos} + DOWN * {y_pos})\n"
            stat_animations += f"        self.play(FadeIn(stat_{i}_group, scale=0.5), run_time=0.5)\n"

        return f'''from manim import *

class StatsScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"

        # Title
        title = Text("{self.title}", font_size=56, color="{self.title_color}")
        title.to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=1.0)

        # Stats
{stat_elements}
{stat_positions}
{stat_animations}

        self.wait({max(0.5, self.duration - 1.0 - len(self.stats) * 0.5)})
'''
```

### Using the Template

```python
from ycb.rendering.templates import StatsTemplate, StatItem

template = StatsTemplate(
    title="PLC Market Overview",
    stats=[
        StatItem(value="$15B", label="Market Size"),
        StatItem(value="5.2%", label="CAGR"),
        StatItem(value="2,500+", label="Manufacturers"),
    ],
)

manim_code = template.generate_code()
```

---

## Testing Templates

### 1. Generate and Inspect Code

```python
from ycb.rendering.templates import MyTemplate

template = MyTemplate(title="Test")
code = template.generate_code()
print(code)  # Inspect the generated code
```

### 2. Save and Render Manually

```python
with open("test_scene.py", "w") as f:
    f.write(code)

# Then run:
# manim -qm test_scene.py MyScene
```

### 3. Use the CLI

```bash
python -m ycb.cli.assets render my_template
```

### 4. Write Unit Tests

```python
def test_my_template():
    template = MyTemplate(title="Test", items=["A", "B", "C"])
    code = template.generate_code()

    assert "class MyScene(Scene):" in code
    assert '"Test"' in code
    assert '"A"' in code
    assert "self.play" in code
```

---

## Common Manim Elements

### Text

```python
text = Text("Hello", font_size=48, color=WHITE)
math = MathTex(r"\frac{x^2}{y}")
title = Title("My Title")
```

### Shapes

```python
circle = Circle(radius=1, color=BLUE)
rect = Rectangle(width=2, height=1, color=GREEN)
line = Line(LEFT, RIGHT, color=WHITE)
arrow = Arrow(LEFT, RIGHT, color=YELLOW)
```

### Groups

```python
group = VGroup(elem1, elem2, elem3)
group.arrange(DOWN, buff=0.5)
group.to_edge(LEFT)
```

### Animations

```python
self.play(Write(text))
self.play(FadeIn(shape))
self.play(Create(line))
self.play(elem.animate.move_to(RIGHT * 2))
self.play(Transform(old, new))
self.wait(2)
```

### Positioning

```python
elem.move_to(ORIGIN)
elem.to_edge(UP)
elem.next_to(other, DOWN, buff=0.5)
elem.shift(LEFT * 2)
```

---

## Best Practices

### 1. Validate Parameters

Check parameter validity in generate_code():

```python
def generate_code(self) -> str:
    if not self.items:
        raise ValueError("At least one item is required")
```

### 2. Escape Strings

Handle special characters in text:

```python
import html
safe_title = html.escape(self.title)
```

### 3. Calculate Durations

Ensure animations fit within the duration:

```python
anim_time = len(self.items) * 0.5  # Time per item
wait_time = max(0.5, self.duration - anim_time - 1.0)
```

### 4. Document Parameters

Use docstrings to explain each parameter:

```python
@dataclass
class MyTemplate:
    """
    My template description.

    Parameters:
        title: Main title text displayed at top
        items: List of items to animate
        duration: Total scene duration in seconds
    """
```

### 5. Use Color Constants

Reference the defined color schemes:

```python
from .scene_types import INDUSTRIAL_COLORS, PLC_COLORS

background_color: str = INDUSTRIAL_COLORS["background"]
```

---

## Integration with Pipeline

Templates are used by the SceneRouter and ManimEngine:

```python
# In router.py
if scene.template:
    template = create_template(scene.template, scene.parameters)
    code = template.generate_code()
    clip_path = self.manim_engine.render_from_code(code)
```

To add a new template to the router:

1. Add the template class to `templates.py`
2. Export it in `__init__.py`
3. Add scene type mapping in `router.py`

---

## Troubleshooting

### Syntax Errors in Generated Code

1. Print the generated code and check for issues
2. Ensure proper string escaping
3. Check for unbalanced quotes/braces

### Animation Timing Issues

1. Calculate total animation time
2. Ensure wait() calls have positive duration
3. Use max() to prevent negative waits

### Rendering Failures

1. Check Manim is installed correctly
2. Verify all imports are present in generated code
3. Test with simple scenes first

### Position/Layout Problems

1. Use VGroup for grouped elements
2. Check coordinate values are reasonable
3. Test with different screen sizes
