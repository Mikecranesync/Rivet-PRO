"""
Reusable Manim Scene Templates for YCB v3

Parameterized template classes for common video scene types.
Each template generates Manim code that can be rendered to MP4.

Templates:
- TitleTemplate: Animated title cards
- DiagramTemplate: Technical diagrams with callouts
- FlowchartTemplate: Process flows with animated arrows
- ComparisonTemplate: Side-by-side comparisons
- LadderLogicTemplate: PLC ladder diagram animations
- TimelineTemplate: Sequential process steps
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

from .scene_types import INDUSTRIAL_COLORS, PLC_COLORS


class TransitionType(Enum):
    """Animation transition types for scenes."""
    FADE = "fade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    ZOOM = "zoom"
    WRITE = "write"


@dataclass
class TitleTemplate:
    """
    Animated title card template.

    Creates professional title screens with main title, subtitle,
    and optional decorative elements.
    """
    title: str
    subtitle: Optional[str] = None
    duration: float = 4.0
    background_color: str = INDUSTRIAL_COLORS["background"]
    title_color: str = "#FFFFFF"
    subtitle_color: str = "#A0AEC0"
    title_font_size: int = 72
    subtitle_font_size: int = 36
    transition_in: TransitionType = TransitionType.WRITE
    transition_out: TransitionType = TransitionType.FADE
    show_underline: bool = True
    underline_color: str = INDUSTRIAL_COLORS["primary"]

    def generate_code(self) -> str:
        """Generate Manim Python code for this title scene."""
        subtitle_create = ""
        subtitle_anim = ""
        subtitle_fadeout = ""

        if self.subtitle:
            subtitle_create = f'''
        subtitle = Text("{self.subtitle}", font_size={self.subtitle_font_size}, color="{self.subtitle_color}")
        subtitle.next_to(title, DOWN, buff=0.5)'''
            subtitle_anim = "        self.play(FadeIn(subtitle), run_time=0.8)"
            subtitle_fadeout = ", FadeOut(subtitle)"

        underline_create = ""
        underline_anim = ""
        underline_fadeout = ""

        if self.show_underline:
            underline_create = f'''
        underline = Line(LEFT * 3, RIGHT * 3, color="{self.underline_color}", stroke_width=4)
        underline.next_to(title, DOWN, buff=0.2)'''
            underline_anim = "        self.play(Create(underline), run_time=0.5)"
            underline_fadeout = ", FadeOut(underline)"

        return f'''from manim import *

class TitleScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"

        # Title
        title = Text("{self.title}", font_size={self.title_font_size}, color="{self.title_color}")
        title.move_to(UP * 0.5)
{subtitle_create}
{underline_create}

        # Animate in
        self.play(Write(title), run_time=1.5)
{underline_anim}
{subtitle_anim}

        # Hold
        self.wait({max(0.5, self.duration - 3.5)})

        # Fade out
        self.play(FadeOut(title){underline_fadeout}{subtitle_fadeout}, run_time=0.8)
'''


@dataclass
class DiagramElement:
    """A single element in a diagram."""
    label: str
    x: float
    y: float
    width: float = 2.5
    height: float = 1.0
    color: str = INDUSTRIAL_COLORS["primary"]
    text_color: str = "#FFFFFF"
    shape: str = "rectangle"  # rectangle, circle, hexagon


@dataclass
class DiagramCallout:
    """A callout annotation pointing to a diagram element."""
    text: str
    target_x: float
    target_y: float
    position: str = "right"  # right, left, above, below
    color: str = INDUSTRIAL_COLORS["secondary"]


@dataclass
class DiagramTemplate:
    """
    Technical diagram template with labeled elements and callouts.

    Creates diagrams showing relationships between components
    with arrows, labels, and optional callout annotations.
    """
    title: str
    elements: List[DiagramElement] = field(default_factory=list)
    arrows: List[Tuple[Tuple[float, float], Tuple[float, float], str]] = field(default_factory=list)
    callouts: List[DiagramCallout] = field(default_factory=list)
    duration: float = 6.0
    background_color: str = INDUSTRIAL_COLORS["background"]
    animate_sequentially: bool = False

    def add_element(self, label: str, x: float, y: float,
                    color: str = None, width: float = 2.5, height: float = 1.0) -> None:
        """Add an element to the diagram."""
        self.elements.append(DiagramElement(
            label=label, x=x, y=y,
            color=color or INDUSTRIAL_COLORS["primary"],
            width=width, height=height
        ))

    def add_arrow(self, start: Tuple[float, float], end: Tuple[float, float],
                  color: str = None) -> None:
        """Add an arrow connecting two points."""
        self.arrows.append((start, end, color or INDUSTRIAL_COLORS["arrow"]))

    def add_callout(self, text: str, target_x: float, target_y: float,
                    position: str = "right") -> None:
        """Add a callout annotation."""
        self.callouts.append(DiagramCallout(
            text=text, target_x=target_x, target_y=target_y, position=position
        ))

    def generate_code(self) -> str:
        """Generate Manim Python code for this diagram scene."""

        # Generate element creation code
        element_code_lines = []
        element_names = []

        for i, elem in enumerate(self.elements):
            name = f"elem_{i}"
            element_names.append(name)
            label = elem.label.replace("\n", " ").replace('"', '\\"')

            element_code_lines.append(f'''
        # Element: {label}
        {name}_rect = RoundedRectangle(
            width={elem.width}, height={elem.height},
            corner_radius=0.1,
            fill_color="{elem.color}", fill_opacity=0.8,
            stroke_color=WHITE, stroke_width=2
        ).move_to(RIGHT * {elem.x} + UP * {elem.y})
        {name}_text = Text("{label}", font_size=24, color="{elem.text_color}").move_to({name}_rect.get_center())
        {name} = VGroup({name}_rect, {name}_text)''')

        element_code = "\n".join(element_code_lines)

        # Generate arrow creation code
        arrow_code_lines = []
        arrow_names = []

        for i, (start, end, color) in enumerate(self.arrows):
            name = f"arrow_{i}"
            arrow_names.append(name)
            arrow_code_lines.append(f'''
        {name} = Arrow(
            start=RIGHT * {start[0]} + UP * {start[1]},
            end=RIGHT * {end[0]} + UP * {end[1]},
            color="{color}", stroke_width=4, buff=0.1
        )''')

        arrow_code = "\n".join(arrow_code_lines) if arrow_code_lines else "        pass"

        # Generate callout creation code
        callout_code_lines = []
        callout_names = []

        for i, callout in enumerate(self.callouts):
            name = f"callout_{i}"
            callout_names.append(name)

            # Position offset based on direction
            offsets = {
                "right": (2.5, 0),
                "left": (-2.5, 0),
                "above": (0, 1.5),
                "below": (0, -1.5)
            }
            offset = offsets.get(callout.position, (2.5, 0))

            callout_code_lines.append(f'''
        # Callout: {callout.text}
        {name}_text = Text("{callout.text}", font_size=20, color="{callout.color}")
        {name}_text.move_to(RIGHT * {callout.target_x + offset[0]} + UP * {callout.target_y + offset[1]})
        {name}_line = Line(
            start=RIGHT * {callout.target_x} + UP * {callout.target_y},
            end={name}_text.get_edge_center({'LEFT' if callout.position == 'right' else 'RIGHT' if callout.position == 'left' else 'DOWN' if callout.position == 'above' else 'UP'}),
            color="{callout.color}", stroke_width=2
        )
        {name} = VGroup({name}_line, {name}_text)''')

        callout_code = "\n".join(callout_code_lines) if callout_code_lines else ""

        # Build animation code
        elem_list = ", ".join(element_names)
        arrow_list = ", ".join(arrow_names)
        callout_list = ", ".join(callout_names)

        if self.animate_sequentially:
            elem_anim = f'''
        for elem in [{elem_list}]:
            self.play(FadeIn(elem), run_time=0.5)'''
            arrow_anim = f'''
        for arr in [{arrow_list}]:
            self.play(GrowArrow(arr), run_time=0.3)''' if arrow_names else ""
        else:
            elem_anim = f"        self.play(*[FadeIn(e) for e in [{elem_list}]], run_time=1.5)" if element_names else ""
            arrow_anim = f"        self.play(*[GrowArrow(a) for a in [{arrow_list}]], run_time=1.0)" if arrow_names else ""

        callout_anim = f"        self.play(*[FadeIn(c) for c in [{callout_list}]], run_time=0.8)" if callout_names else ""

        # Build fadeout
        all_objects = []
        if element_names:
            all_objects.extend(element_names)
        if arrow_names:
            all_objects.extend(arrow_names)
        if callout_names:
            all_objects.extend(callout_names)
        all_objects.append("title")
        fadeout_list = ", ".join(all_objects)

        return f'''from manim import *

class DiagramScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"

        # Title
        title = Text("{self.title}", font_size=48, color=WHITE).to_edge(UP, buff=0.5)
{element_code}
{arrow_code}
{callout_code}

        # Animations
        self.play(Write(title), run_time=1.0)
{elem_anim}
{arrow_anim}
{callout_anim}

        # Hold
        self.wait({max(0.5, self.duration - 4.0)})

        # Fade out
        all_obj = [{fadeout_list}]
        self.play(*[FadeOut(o) for o in all_obj], run_time=0.8)
'''


@dataclass
class FlowchartStep:
    """A step in a flowchart."""
    label: str
    description: Optional[str] = None
    color: str = INDUSTRIAL_COLORS["primary"]
    shape: str = "rectangle"  # rectangle, diamond, oval


@dataclass
class FlowchartTemplate:
    """
    Process flow template with animated arrows.

    Creates horizontal or vertical flowcharts showing
    process steps with animated connections.
    """
    title: str
    steps: List[FlowchartStep] = field(default_factory=list)
    orientation: str = "horizontal"  # horizontal, vertical
    duration: float = 8.0
    background_color: str = INDUSTRIAL_COLORS["background"]
    arrow_color: str = INDUSTRIAL_COLORS["arrow"]
    animate_sequentially: bool = True

    def add_step(self, label: str, description: str = None,
                 color: str = None, shape: str = "rectangle") -> None:
        """Add a step to the flowchart."""
        self.steps.append(FlowchartStep(
            label=label,
            description=description,
            color=color or INDUSTRIAL_COLORS["primary"],
            shape=shape
        ))

    def generate_code(self) -> str:
        """Generate Manim Python code for this flowchart scene."""

        n_steps = len(self.steps)
        if n_steps == 0:
            return self._generate_empty_code()

        # Calculate positions
        if self.orientation == "horizontal":
            spacing = 10 / max(n_steps, 1)
            positions = [(i * spacing - (n_steps - 1) * spacing / 2, 0) for i in range(n_steps)]
        else:
            spacing = 6 / max(n_steps, 1)
            positions = [(0, (n_steps - 1 - i) * spacing - (n_steps - 1) * spacing / 2) for i in range(n_steps)]

        # Generate step creation code
        step_code_lines = []
        step_names = []

        for i, (step, pos) in enumerate(zip(self.steps, positions)):
            name = f"step_{i}"
            step_names.append(name)
            label = step.label.replace("\n", " ").replace('"', '\\"')

            if step.shape == "diamond":
                shape_code = f'''
        {name}_shape = Polygon(
            UP * 0.7, RIGHT * 1.2, DOWN * 0.7, LEFT * 1.2,
            fill_color="{step.color}", fill_opacity=0.8,
            stroke_color=WHITE, stroke_width=2
        ).move_to(RIGHT * {pos[0]} + UP * {pos[1]})'''
            elif step.shape == "oval":
                shape_code = f'''
        {name}_shape = Ellipse(
            width=2.2, height=1.0,
            fill_color="{step.color}", fill_opacity=0.8,
            stroke_color=WHITE, stroke_width=2
        ).move_to(RIGHT * {pos[0]} + UP * {pos[1]})'''
            else:  # rectangle
                shape_code = f'''
        {name}_shape = RoundedRectangle(
            width=2.0, height=0.8, corner_radius=0.1,
            fill_color="{step.color}", fill_opacity=0.8,
            stroke_color=WHITE, stroke_width=2
        ).move_to(RIGHT * {pos[0]} + UP * {pos[1]})'''

            step_code_lines.append(f'''
        # Step {i + 1}: {label}{shape_code}
        {name}_text = Text("{label}", font_size=18, color=WHITE).move_to({name}_shape.get_center())
        {name} = VGroup({name}_shape, {name}_text)''')

        step_code = "\n".join(step_code_lines)

        # Generate arrow code
        arrow_code_lines = []
        arrow_names = []

        for i in range(n_steps - 1):
            name = f"flow_arrow_{i}"
            arrow_names.append(name)
            start_pos = positions[i]
            end_pos = positions[i + 1]

            if self.orientation == "horizontal":
                start = (start_pos[0] + 1.1, start_pos[1])
                end = (end_pos[0] - 1.1, end_pos[1])
            else:
                start = (start_pos[0], start_pos[1] - 0.5)
                end = (end_pos[0], end_pos[1] + 0.5)

            arrow_code_lines.append(f'''
        {name} = Arrow(
            start=RIGHT * {start[0]} + UP * {start[1]},
            end=RIGHT * {end[0]} + UP * {end[1]},
            color="{self.arrow_color}", stroke_width=3, buff=0
        )''')

        arrow_code = "\n".join(arrow_code_lines) if arrow_code_lines else ""

        # Build animations
        if self.animate_sequentially:
            anim_lines = []
            for i, (step_name, arrow_name) in enumerate(zip(step_names, arrow_names + [None])):
                anim_lines.append(f"        self.play(FadeIn({step_name}), run_time=0.5)")
                if arrow_name:
                    anim_lines.append(f"        self.play(GrowArrow({arrow_name}), run_time=0.3)")
            anim_code = "\n".join(anim_lines)
        else:
            step_list = ", ".join(step_names)
            arrow_list = ", ".join(arrow_names)
            anim_code = f'''        self.play(*[FadeIn(s) for s in [{step_list}]], run_time=1.5)
        self.play(*[GrowArrow(a) for a in [{arrow_list}]], run_time=1.0)''' if arrow_names else f"        self.play(*[FadeIn(s) for s in [{step_list}]], run_time=1.5)"

        # Fadeout
        all_obj = step_names + arrow_names + ["title"]
        fadeout_list = ", ".join(all_obj)

        return f'''from manim import *

class FlowchartScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"

        # Title
        title = Text("{self.title}", font_size=42, color=WHITE).to_edge(UP, buff=0.5)
{step_code}
{arrow_code}

        # Animations
        self.play(Write(title), run_time=1.0)
{anim_code}

        # Hold
        self.wait({max(0.5, self.duration - n_steps * 0.8 - 2.0)})

        # Fade out
        all_obj = [{fadeout_list}]
        self.play(*[FadeOut(o) for o in all_obj], run_time=0.8)
'''

    def _generate_empty_code(self) -> str:
        """Generate code for empty flowchart."""
        return f'''from manim import *

class FlowchartScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"
        title = Text("{self.title}", font_size=42, color=WHITE)
        self.play(Write(title), run_time=1.0)
        self.wait({self.duration - 1.8})
        self.play(FadeOut(title), run_time=0.8)
'''


@dataclass
class ComparisonItem:
    """An item in a comparison."""
    label: str
    values: List[str]  # One value per column
    highlight_column: Optional[int] = None


@dataclass
class ComparisonTemplate:
    """
    Side-by-side comparison template.

    Creates comparison tables or cards showing differences
    between two or more options.
    """
    title: str
    columns: List[str]  # Column headers (e.g., ["Feature", "Option A", "Option B"])
    items: List[ComparisonItem] = field(default_factory=list)
    duration: float = 8.0
    background_color: str = INDUSTRIAL_COLORS["background"]
    header_color: str = INDUSTRIAL_COLORS["primary"]
    highlight_color: str = INDUSTRIAL_COLORS["success"]

    def add_item(self, label: str, *values: str, highlight: int = None) -> None:
        """Add a comparison item."""
        self.items.append(ComparisonItem(
            label=label,
            values=list(values),
            highlight_column=highlight
        ))

    def generate_code(self) -> str:
        """Generate Manim Python code for this comparison scene."""

        n_cols = len(self.columns)
        n_items = len(self.items)

        if n_cols == 0:
            return self._generate_empty_code()

        col_width = 3.5
        row_height = 0.8
        start_x = -(n_cols - 1) * col_width / 2
        start_y = 1.5

        # Generate header code
        header_lines = []
        header_names = []

        for i, col in enumerate(self.columns):
            name = f"header_{i}"
            header_names.append(name)
            x = start_x + i * col_width

            header_lines.append(f'''
        {name}_bg = Rectangle(width={col_width - 0.1}, height={row_height}, fill_color="{self.header_color}", fill_opacity=0.9, stroke_width=0).move_to(RIGHT * {x} + UP * {start_y})
        {name}_text = Text("{col}", font_size=22, color=WHITE, weight=BOLD).move_to({name}_bg.get_center())
        {name} = VGroup({name}_bg, {name}_text)''')

        header_code = "\n".join(header_lines)

        # Generate item code
        item_lines = []
        item_names = []

        for row, item in enumerate(self.items):
            row_y = start_y - (row + 1) * row_height

            # Build full row values: label + values
            row_values = [item.label] + item.values
            # Pad with empty strings if needed
            while len(row_values) < n_cols:
                row_values.append("")

            for col in range(n_cols):
                name = f"cell_{row}_{col}"
                item_names.append(name)
                x = start_x + col * col_width
                value = row_values[col]

                # Determine if highlighted (1-indexed for values columns)
                is_highlight = item.highlight_column == col
                bg_color = self.highlight_color if is_highlight else "#2D3748"
                opacity = 0.8 if is_highlight else 0.6

                # First column is label
                if col == 0:
                    font_weight = ", weight=BOLD"
                else:
                    font_weight = ""

                item_lines.append(f'''
        {name}_bg = Rectangle(width={col_width - 0.1}, height={row_height}, fill_color="{bg_color}", fill_opacity={opacity}, stroke_width=0).move_to(RIGHT * {x} + UP * {row_y})
        {name}_text = Text("{value}", font_size=18, color=WHITE{font_weight}).move_to({name}_bg.get_center())
        {name} = VGroup({name}_bg, {name}_text)''')

        item_code = "\n".join(item_lines)

        # Build animations
        header_list = ", ".join(header_names)

        # Animate rows sequentially
        anim_lines = []
        for row in range(n_items):
            row_cells = [f"cell_{row}_{col}" for col in range(n_cols)]
            row_list = ", ".join(row_cells)
            anim_lines.append(f"        self.play(*[FadeIn(c) for c in [{row_list}]], run_time=0.4)")

        anim_code = "\n".join(anim_lines)

        # Fadeout
        all_obj = header_names + item_names + ["title"]
        fadeout_list = ", ".join(all_obj)

        return f'''from manim import *

class ComparisonScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"

        # Title
        title = Text("{self.title}", font_size=42, color=WHITE).to_edge(UP, buff=0.3)
{header_code}
{item_code}

        # Animations
        self.play(Write(title), run_time=0.8)
        self.play(*[FadeIn(h) for h in [{header_list}]], run_time=0.5)
{anim_code}

        # Hold
        self.wait({max(0.5, self.duration - n_items * 0.4 - 2.0)})

        # Fade out
        all_obj = [{fadeout_list}]
        self.play(*[FadeOut(o) for o in all_obj], run_time=0.8)
'''

    def _generate_empty_code(self) -> str:
        """Generate code for empty comparison."""
        return f'''from manim import *

class ComparisonScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"
        title = Text("{self.title}", font_size=42, color=WHITE)
        self.play(Write(title), run_time=1.0)
        self.wait({self.duration - 1.8})
        self.play(FadeOut(title), run_time=0.8)
'''


@dataclass
class LadderRung:
    """A rung in a ladder logic diagram."""
    inputs: List[Tuple[str, str]]  # List of (type, label) - type: "xic", "xio", "ote", etc.
    output: Tuple[str, str]  # (type, label) for output coil


@dataclass
class LadderLogicTemplate:
    """
    PLC ladder diagram animation template.

    Creates animated ladder logic diagrams showing
    input conditions and output coils with power flow.
    """
    title: str
    rungs: List[LadderRung] = field(default_factory=list)
    duration: float = 10.0
    background_color: str = INDUSTRIAL_COLORS["background"]
    rail_color: str = PLC_COLORS["rail"]
    active_color: str = PLC_COLORS["active"]
    show_power_flow: bool = True

    def add_rung(self, inputs: List[Tuple[str, str]], output: Tuple[str, str]) -> None:
        """Add a rung to the ladder diagram."""
        self.rungs.append(LadderRung(inputs=inputs, output=output))

    def generate_code(self) -> str:
        """Generate Manim Python code for this ladder logic scene."""

        n_rungs = len(self.rungs)
        if n_rungs == 0:
            return self._generate_empty_code()

        # Layout constants
        rung_height = 1.5
        rail_x = 5.5
        start_y = 2.0

        # Generate rail code
        rail_code = f'''
        # Power rails
        left_rail = Line(
            start=LEFT * {rail_x} + UP * {start_y + 0.5},
            end=LEFT * {rail_x} + DOWN * {n_rungs * rung_height - start_y},
            color="{self.rail_color}", stroke_width=6
        )
        right_rail = Line(
            start=RIGHT * {rail_x} + UP * {start_y + 0.5},
            end=RIGHT * {rail_x} + DOWN * {n_rungs * rung_height - start_y},
            color="{self.rail_color}", stroke_width=6
        )
        l1_label = Text("L1", font_size=18, color="{self.rail_color}").next_to(left_rail, UP)
        l2_label = Text("L2", font_size=18, color="{self.rail_color}").next_to(right_rail, UP)
'''

        # Generate rung code
        rung_code_lines = []
        rung_names = []

        for r, rung in enumerate(self.rungs):
            rung_y = start_y - r * rung_height
            n_inputs = len(rung.inputs)

            # Horizontal wire
            rung_code_lines.append(f'''
        # Rung {r + 1}
        rung_{r}_wire = Line(
            start=LEFT * {rail_x} + UP * {rung_y},
            end=RIGHT * {rail_x} + UP * {rung_y},
            color="{self.rail_color}", stroke_width=3
        )''')
            rung_names.append(f"rung_{r}_wire")

            # Input contacts
            for i, (contact_type, label) in enumerate(rung.inputs):
                contact_x = -rail_x + 2.5 + i * 2.5
                contact_name = f"rung_{r}_input_{i}"
                rung_names.append(contact_name)

                clean_label = label.replace('"', '\\"')

                # XIC (normally open) or XIO (normally closed)
                if contact_type.lower() == "xio":
                    # Normally closed - add diagonal
                    rung_code_lines.append(f'''
        {contact_name}_l = Line(UP * 0.3, DOWN * 0.3, color="{PLC_COLORS['contact']}", stroke_width=3).move_to(RIGHT * {contact_x - 0.3} + UP * {rung_y})
        {contact_name}_r = Line(UP * 0.3, DOWN * 0.3, color="{PLC_COLORS['contact']}", stroke_width=3).move_to(RIGHT * {contact_x + 0.3} + UP * {rung_y})
        {contact_name}_slash = Line(DOWN * 0.3 + LEFT * 0.2, UP * 0.3 + RIGHT * 0.2, color="{PLC_COLORS['contact']}", stroke_width=2).move_to(RIGHT * {contact_x} + UP * {rung_y})
        {contact_name}_label = Text("{clean_label}", font_size=14, color=WHITE).next_to(VGroup({contact_name}_l, {contact_name}_r), UP, buff=0.15)
        {contact_name} = VGroup({contact_name}_l, {contact_name}_r, {contact_name}_slash, {contact_name}_label)''')
                else:
                    # XIC - normally open
                    rung_code_lines.append(f'''
        {contact_name}_l = Line(UP * 0.3, DOWN * 0.3, color="{PLC_COLORS['contact']}", stroke_width=3).move_to(RIGHT * {contact_x - 0.3} + UP * {rung_y})
        {contact_name}_r = Line(UP * 0.3, DOWN * 0.3, color="{PLC_COLORS['contact']}", stroke_width=3).move_to(RIGHT * {contact_x + 0.3} + UP * {rung_y})
        {contact_name}_label = Text("{clean_label}", font_size=14, color=WHITE).next_to(VGroup({contact_name}_l, {contact_name}_r), UP, buff=0.15)
        {contact_name} = VGroup({contact_name}_l, {contact_name}_r, {contact_name}_label)''')

            # Output coil
            output_type, output_label = rung.output
            output_x = rail_x - 1.5
            output_name = f"rung_{r}_output"
            rung_names.append(output_name)
            clean_output = output_label.replace('"', '\\"')

            rung_code_lines.append(f'''
        {output_name}_l = Arc(angle=PI, start_angle=PI/2, radius=0.35, color="{PLC_COLORS['coil']}", stroke_width=3).move_to(RIGHT * {output_x - 0.15} + UP * {rung_y})
        {output_name}_r = Arc(angle=PI, start_angle=-PI/2, radius=0.35, color="{PLC_COLORS['coil']}", stroke_width=3).move_to(RIGHT * {output_x + 0.15} + UP * {rung_y})
        {output_name}_label = Text("{clean_output}", font_size=14, color=WHITE).next_to(VGroup({output_name}_l, {output_name}_r), UP, buff=0.15)
        {output_name} = VGroup({output_name}_l, {output_name}_r, {output_name}_label)''')

        rung_code = "\n".join(rung_code_lines)

        # Animation code
        rung_list = ", ".join(rung_names)

        all_obj = ["left_rail", "right_rail", "l1_label", "l2_label", "title"] + rung_names
        fadeout_list = ", ".join(all_obj)

        return f'''from manim import *

class LadderLogicScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"

        # Title
        title = Text("{self.title}", font_size=36, color=WHITE).to_edge(UP, buff=0.3)
{rail_code}
{rung_code}

        # Animations
        self.play(Write(title), run_time=0.8)
        self.play(Create(left_rail), Create(right_rail), FadeIn(l1_label), FadeIn(l2_label), run_time=1.0)

        # Animate rungs sequentially
        for obj in [{rung_list}]:
            self.play(FadeIn(obj), run_time=0.3)

        # Hold
        self.wait({max(0.5, self.duration - n_rungs * 0.3 - 2.5)})

        # Fade out
        all_obj = [{fadeout_list}]
        self.play(*[FadeOut(o) for o in all_obj], run_time=0.8)
'''

    def _generate_empty_code(self) -> str:
        """Generate code for empty ladder diagram."""
        return f'''from manim import *

class LadderLogicScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"
        title = Text("{self.title}", font_size=36, color=WHITE)
        self.play(Write(title), run_time=1.0)
        self.wait({self.duration - 1.8})
        self.play(FadeOut(title), run_time=0.8)
'''


@dataclass
class TimelineEvent:
    """An event on a timeline."""
    label: str
    description: Optional[str] = None
    color: str = INDUSTRIAL_COLORS["primary"]
    icon: Optional[str] = None  # Optional icon name


@dataclass
class TimelineTemplate:
    """
    Sequential process timeline template.

    Creates animated timelines showing a sequence of
    events or process steps in order.
    """
    title: str
    events: List[TimelineEvent] = field(default_factory=list)
    orientation: str = "horizontal"  # horizontal, vertical
    duration: float = 10.0
    background_color: str = INDUSTRIAL_COLORS["background"]
    line_color: str = INDUSTRIAL_COLORS["secondary"]

    def add_event(self, label: str, description: str = None,
                  color: str = None) -> None:
        """Add an event to the timeline."""
        self.events.append(TimelineEvent(
            label=label,
            description=description,
            color=color or INDUSTRIAL_COLORS["primary"]
        ))

    def generate_code(self) -> str:
        """Generate Manim Python code for this timeline scene."""

        n_events = len(self.events)
        if n_events == 0:
            return self._generate_empty_code()

        # Layout
        if self.orientation == "horizontal":
            line_start = (-5.5, 0)
            line_end = (5.5, 0)
            spacing = 11 / max(n_events - 1, 1) if n_events > 1 else 0
            positions = [(-5.5 + i * spacing, 0) for i in range(n_events)]
        else:
            line_start = (0, 2.5)
            line_end = (0, -2.5)
            spacing = 5 / max(n_events - 1, 1) if n_events > 1 else 0
            positions = [(0, 2.5 - i * spacing) for i in range(n_events)]

        # Timeline line code
        timeline_code = f'''
        # Timeline line
        timeline_line = Line(
            start=RIGHT * {line_start[0]} + UP * {line_start[1]},
            end=RIGHT * {line_end[0]} + UP * {line_end[1]},
            color="{self.line_color}", stroke_width=4
        )'''

        # Event code
        event_code_lines = []
        event_names = []

        for i, (event, pos) in enumerate(zip(self.events, positions)):
            name = f"event_{i}"
            event_names.append(name)
            label = event.label.replace('"', '\\"')

            if self.orientation == "horizontal":
                label_direction = "UP" if i % 2 == 0 else "DOWN"
                label_offset = 0.8 if i % 2 == 0 else -0.8
            else:
                label_direction = "RIGHT"
                label_offset = 0

            event_code_lines.append(f'''
        # Event {i + 1}: {label}
        {name}_dot = Dot(point=RIGHT * {pos[0]} + UP * {pos[1]}, radius=0.15, color="{event.color}")
        {name}_label = Text("{label}", font_size=18, color=WHITE)
        {name}_label.next_to({name}_dot, {label_direction}, buff=0.3)
        {name} = VGroup({name}_dot, {name}_label)''')

            # Add description if provided
            if event.description:
                desc = event.description.replace('"', '\\"')[:50]  # Truncate long descriptions
                event_code_lines.append(f'''
        {name}_desc = Text("{desc}", font_size=14, color=GRAY_B)
        {name}_desc.next_to({name}_label, {label_direction}, buff=0.15)
        {name}.add({name}_desc)''')

        event_code = "\n".join(event_code_lines)

        # Animation
        event_list = ", ".join(event_names)

        all_obj = ["timeline_line", "title"] + event_names
        fadeout_list = ", ".join(all_obj)

        return f'''from manim import *

class TimelineScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"

        # Title
        title = Text("{self.title}", font_size=42, color=WHITE).to_edge(UP, buff=0.3)
{timeline_code}
{event_code}

        # Animations
        self.play(Write(title), run_time=0.8)
        self.play(Create(timeline_line), run_time=1.0)

        # Animate events sequentially
        for ev in [{event_list}]:
            self.play(FadeIn(ev, scale=1.2), run_time=0.5)

        # Hold
        self.wait({max(0.5, self.duration - n_events * 0.5 - 2.5)})

        # Fade out
        all_obj = [{fadeout_list}]
        self.play(*[FadeOut(o) for o in all_obj], run_time=0.8)
'''

    def _generate_empty_code(self) -> str:
        """Generate code for empty timeline."""
        return f'''from manim import *

class TimelineScene(Scene):
    def construct(self):
        self.camera.background_color = "{self.background_color}"
        title = Text("{self.title}", font_size=42, color=WHITE)
        self.play(Write(title), run_time=1.0)
        self.wait({self.duration - 1.8})
        self.play(FadeOut(title), run_time=0.8)
'''


# Template factory for easy instantiation
class TemplateFactory:
    """Factory for creating scene templates."""

    @staticmethod
    def title(title: str, subtitle: str = None, **kwargs) -> TitleTemplate:
        """Create a title template."""
        return TitleTemplate(title=title, subtitle=subtitle, **kwargs)

    @staticmethod
    def diagram(title: str, **kwargs) -> DiagramTemplate:
        """Create a diagram template."""
        return DiagramTemplate(title=title, **kwargs)

    @staticmethod
    def flowchart(title: str, **kwargs) -> FlowchartTemplate:
        """Create a flowchart template."""
        return FlowchartTemplate(title=title, **kwargs)

    @staticmethod
    def comparison(title: str, columns: List[str], **kwargs) -> ComparisonTemplate:
        """Create a comparison template."""
        return ComparisonTemplate(title=title, columns=columns, **kwargs)

    @staticmethod
    def ladder_logic(title: str, **kwargs) -> LadderLogicTemplate:
        """Create a ladder logic template."""
        return LadderLogicTemplate(title=title, **kwargs)

    @staticmethod
    def timeline(title: str, **kwargs) -> TimelineTemplate:
        """Create a timeline template."""
        return TimelineTemplate(title=title, **kwargs)
