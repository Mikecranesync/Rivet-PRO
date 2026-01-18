"""
AI-Powered Storyboard Generator

Converts scripts into structured storyboards using LLM intelligence
for smart scene planning and template selection.
"""

import json
import logging
import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from .models import (
    Scene,
    SceneType,
    Storyboard,
    VisualDescription,
    TemplateParameters,
    RenderEngine,
)

logger = logging.getLogger(__name__)


# Mapping of scene types to render engines
SCENE_TO_ENGINE = {
    SceneType.TITLE: RenderEngine.MANIM,
    SceneType.TEXT: RenderEngine.MANIM,
    SceneType.DIAGRAM: RenderEngine.MANIM,
    SceneType.FLOWCHART: RenderEngine.MANIM,
    SceneType.COMPARISON: RenderEngine.MANIM,
    SceneType.LADDER_LOGIC: RenderEngine.MANIM,
    SceneType.TIMELINE: RenderEngine.MANIM,
    SceneType.THREE_D: RenderEngine.BLENDER,
    SceneType.B_ROLL: RenderEngine.EXTERNAL,
    SceneType.TRANSITION: RenderEngine.NONE,
}

# Scene type to template name mapping
SCENE_TO_TEMPLATE = {
    SceneType.TITLE: "TitleTemplate",
    SceneType.TEXT: "TitleTemplate",  # Can use title for text
    SceneType.DIAGRAM: "DiagramTemplate",
    SceneType.FLOWCHART: "FlowchartTemplate",
    SceneType.COMPARISON: "ComparisonTemplate",
    SceneType.LADDER_LOGIC: "LadderLogicTemplate",
    SceneType.TIMELINE: "TimelineTemplate",
}


# LLM prompt for storyboard generation
STORYBOARD_SYSTEM_PROMPT = """You are an expert video storyboard creator for industrial automation educational content.

Given a script, you create structured storyboards that:
1. Break the script into logical scenes
2. Choose appropriate visual types for each concept
3. Suggest specific visual elements and animations
4. Estimate appropriate durations based on narration length

Scene types available:
- title: Animated title cards (use for intros, section headers)
- diagram: Technical diagrams showing component relationships
- flowchart: Process flows with steps and arrows
- comparison: Side-by-side comparisons (features, specs)
- ladder_logic: PLC ladder diagrams (for PLC-specific content)
- timeline: Sequential steps in a process
- text: Key points with bullet points

For industrial automation content:
- Use diagrams for showing PLC architecture, I/O connections
- Use flowcharts for processes, startup sequences, troubleshooting
- Use ladder_logic when explaining PLC programming
- Use comparisons for vendor comparisons, technology choices
- Use timelines for scan cycles, communication timing

Output your response as valid JSON with this structure:
{
  "scenes": [
    {
      "scene_type": "title|diagram|flowchart|comparison|ladder_logic|timeline|text",
      "duration": <seconds as number>,
      "narration": "<narration text for this scene>",
      "visual": {
        "main_subject": "<primary visual element>",
        "elements": ["<element1>", "<element2>"],
        "layout": "centered|left|right|split",
        "annotations": ["<callout1>", "<callout2>"]
      },
      "template_params": {
        // Specific parameters for the template type
        // For diagram: elements, arrows
        // For flowchart: steps
        // For comparison: columns, items
        // For ladder_logic: rungs
        // For timeline: events
      }
    }
  ]
}

Be specific with template_params - include actual labels, positions, and colors."""


STORYBOARD_USER_PROMPT = """Create a storyboard for this video script. Target duration: {target_duration} seconds.

Script:
{script}

Requirements:
- Break into {min_scenes}-{max_scenes} scenes
- Each scene should be 5-15 seconds
- Match visual types to content
- Include specific visual elements for each scene
- Ensure narration flows naturally

Return valid JSON only, no explanations."""


@dataclass
class StoryboardConfig:
    """Configuration for storyboard generation."""
    target_duration: float = 60.0  # Target video duration in seconds
    min_scenes: int = 4
    max_scenes: int = 12
    words_per_second: float = 2.5  # Average speaking rate
    default_scene_duration: float = 8.0
    title_duration: float = 4.0
    model_provider: str = "groq"  # groq, claude, openai
    model_name: str = "llama-3.3-70b-versatile"  # Default model


class StoryboardGenerator:
    """
    AI-powered storyboard generator.

    Converts scripts into structured storyboards using LLM intelligence.
    """

    def __init__(self, config: Optional[StoryboardConfig] = None):
        """
        Initialize the storyboard generator.

        Args:
            config: Configuration options
        """
        self.config = config or StoryboardConfig()
        self._llm_client = None
        logger.info(f"StoryboardGenerator initialized with {self.config.model_provider}")

    def _get_llm_client(self):
        """Get or create LLM client."""
        if self._llm_client is not None:
            return self._llm_client

        # Try to use the project's LLM service if available
        try:
            if self.config.model_provider == "groq":
                from groq import Groq
                import os
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    self._llm_client = Groq(api_key=api_key)
                    return self._llm_client
        except ImportError:
            pass

        # Fallback: return None, will use rule-based generation
        logger.warning("No LLM client available, using rule-based generation")
        return None

    def generate(self, script: str, title: str = "Untitled",
                 description: str = "", **kwargs) -> Storyboard:
        """
        Generate a storyboard from a script.

        Args:
            script: The video script text
            title: Video title
            description: Video description
            **kwargs: Additional configuration overrides

        Returns:
            A structured Storyboard object
        """
        # Apply any config overrides
        config = self.config
        if kwargs:
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        logger.info(f"Generating storyboard for: {title}")
        logger.info(f"Script length: {len(script)} chars, ~{len(script.split())} words")

        # Try LLM-based generation first
        llm_client = self._get_llm_client()
        if llm_client:
            try:
                return self._generate_with_llm(script, title, description, llm_client)
            except Exception as e:
                logger.warning(f"LLM generation failed: {e}, falling back to rules")

        # Fallback to rule-based generation
        return self._generate_with_rules(script, title, description)

    def _generate_with_llm(self, script: str, title: str, description: str,
                           llm_client) -> Storyboard:
        """Generate storyboard using LLM."""

        # Calculate scene constraints
        word_count = len(script.split())
        estimated_duration = word_count / self.config.words_per_second
        target_duration = self.config.target_duration or estimated_duration

        # Prepare prompts
        user_prompt = STORYBOARD_USER_PROMPT.format(
            target_duration=int(target_duration),
            script=script,
            min_scenes=self.config.min_scenes,
            max_scenes=self.config.max_scenes,
        )

        # Call LLM
        logger.info(f"Calling LLM ({self.config.model_name}) for storyboard generation")

        response = llm_client.chat.completions.create(
            model=self.config.model_name,
            messages=[
                {"role": "system", "content": STORYBOARD_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=4000,
        )

        # Parse response
        content = response.choices[0].message.content
        logger.debug(f"LLM response: {content[:500]}...")

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            raise ValueError("No valid JSON found in LLM response")

        data = json.loads(json_match.group())
        scenes_data = data.get("scenes", [])

        # Build storyboard
        storyboard = Storyboard(
            title=title,
            description=description,
            target_duration=target_duration,
        )

        for i, scene_data in enumerate(scenes_data):
            scene = self._parse_scene_data(scene_data, i + 1)
            storyboard.add_scene(scene)

        logger.info(f"Generated storyboard: {len(storyboard.scenes)} scenes, "
                    f"{storyboard.total_duration:.1f}s total")

        return storyboard

    def _parse_scene_data(self, data: Dict[str, Any], index: int) -> Scene:
        """Parse scene data from LLM response into Scene object."""

        # Get scene type
        scene_type_str = data.get("scene_type", "text").lower()
        try:
            scene_type = SceneType(scene_type_str)
        except ValueError:
            scene_type = SceneType.TEXT

        # Get visual description
        visual_data = data.get("visual", {})
        visual = VisualDescription(
            main_subject=visual_data.get("main_subject", "Scene content"),
            elements=visual_data.get("elements", []),
            layout=visual_data.get("layout", "centered"),
            annotations=visual_data.get("annotations", []),
        )

        # Get template parameters
        template_data = data.get("template_params", {})
        template_name = SCENE_TO_TEMPLATE.get(scene_type, "TitleTemplate")

        template_params = TemplateParameters(
            template_name=template_name,
            title=template_data.get("title", visual.main_subject),
            elements=template_data.get("elements", []),
            arrows=template_data.get("arrows", []),
            steps=template_data.get("steps", []),
            columns=template_data.get("columns", []),
            items=template_data.get("items", []),
            rungs=template_data.get("rungs", []),
            events=template_data.get("events", []),
            duration=data.get("duration", self.config.default_scene_duration),
        )

        return Scene(
            scene_id=f"scene_{index:03d}",
            scene_type=scene_type,
            duration=data.get("duration", self.config.default_scene_duration),
            narration_text=data.get("narration", ""),
            visual_description=visual,
            template_params=template_params,
            render_engine=SCENE_TO_ENGINE.get(scene_type, RenderEngine.MANIM),
        )

    def _generate_with_rules(self, script: str, title: str,
                              description: str) -> Storyboard:
        """
        Generate storyboard using rule-based heuristics.

        Falls back to this when LLM is not available.
        """
        logger.info("Using rule-based storyboard generation")

        # Split script into paragraphs
        paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]

        # Calculate timing
        word_count = len(script.split())
        target_duration = self.config.target_duration or (word_count / self.config.words_per_second)

        storyboard = Storyboard(
            title=title,
            description=description,
            target_duration=target_duration,
        )

        # Always start with a title scene
        title_scene = Scene(
            scene_id="scene_001",
            scene_type=SceneType.TITLE,
            duration=self.config.title_duration,
            narration_text="",  # Title scenes usually don't have narration
            visual_description=VisualDescription(main_subject=title),
            template_params=TemplateParameters(
                template_name="TitleTemplate",
                title=title,
                duration=self.config.title_duration,
                extra={"subtitle": description[:50] if description else None}
            ),
            render_engine=RenderEngine.MANIM,
        )
        storyboard.add_scene(title_scene)

        # Process each paragraph as a scene
        for i, paragraph in enumerate(paragraphs, 2):
            scene_type, template_name = self._infer_scene_type(paragraph)

            # Estimate duration based on word count
            words = len(paragraph.split())
            duration = max(5.0, min(15.0, words / self.config.words_per_second))

            # Extract key terms for visual description
            visual = self._extract_visual_description(paragraph, scene_type)

            # Create template params based on scene type
            template_params = self._create_template_params(
                scene_type, template_name, paragraph, visual, duration
            )

            scene = Scene(
                scene_id=f"scene_{i:03d}",
                scene_type=scene_type,
                duration=duration,
                narration_text=paragraph,
                visual_description=visual,
                template_params=template_params,
                render_engine=SCENE_TO_ENGINE.get(scene_type, RenderEngine.MANIM),
            )
            storyboard.add_scene(scene)

        logger.info(f"Generated {len(storyboard.scenes)} scenes via rules")
        return storyboard

    def _infer_scene_type(self, text: str) -> Tuple[SceneType, str]:
        """Infer the best scene type based on text content."""
        text_lower = text.lower()

        # Check for specific content patterns
        if any(word in text_lower for word in ["compared to", "vs", "versus", "difference between"]):
            return SceneType.COMPARISON, "ComparisonTemplate"

        if any(word in text_lower for word in ["step", "first", "then", "next", "finally", "process"]):
            if any(word in text_lower for word in ["flowchart", "sequence", "order"]):
                return SceneType.FLOWCHART, "FlowchartTemplate"
            return SceneType.TIMELINE, "TimelineTemplate"

        if any(word in text_lower for word in ["ladder", "rung", "xic", "xio", "ote", "plc program"]):
            return SceneType.LADDER_LOGIC, "LadderLogicTemplate"

        if any(word in text_lower for word in ["architecture", "component", "module", "connection", "diagram"]):
            return SceneType.DIAGRAM, "DiagramTemplate"

        # Default to text/title for general content
        return SceneType.TEXT, "TitleTemplate"

    def _extract_visual_description(self, text: str, scene_type: SceneType) -> VisualDescription:
        """Extract visual description from text."""

        # Extract first sentence or phrase as main subject
        first_sentence = text.split(".")[0].strip()
        main_subject = first_sentence[:60] if len(first_sentence) > 60 else first_sentence

        # Extract key terms as elements
        elements = []
        keywords = ["PLC", "CPU", "I/O", "input", "output", "motor", "sensor",
                    "controller", "module", "network", "communication"]
        for word in keywords:
            if word.lower() in text.lower():
                elements.append(word)

        return VisualDescription(
            main_subject=main_subject,
            elements=elements[:5],  # Limit to 5 elements
            layout="centered",
            annotations=[],
        )

    def _create_template_params(self, scene_type: SceneType, template_name: str,
                                 text: str, visual: VisualDescription,
                                 duration: float) -> TemplateParameters:
        """Create template parameters based on scene type."""

        params = TemplateParameters(
            template_name=template_name,
            title=visual.main_subject,
            duration=duration,
        )

        # Add type-specific parameters
        if scene_type == SceneType.DIAGRAM and visual.elements:
            # Create simple diagram elements from extracted keywords
            for i, elem in enumerate(visual.elements[:4]):
                x = (i % 2) * 4 - 2
                y = (i // 2) * -2 + 1
                params.elements.append({
                    "label": elem,
                    "x": x, "y": y,
                    "color": "#3B82F6"
                })

        elif scene_type == SceneType.FLOWCHART:
            # Extract steps from text
            steps = self._extract_steps(text)
            for step in steps[:5]:
                params.steps.append({"label": step, "color": "#3B82F6"})

        elif scene_type == SceneType.TIMELINE:
            # Extract events from text
            events = self._extract_steps(text)
            for event in events[:5]:
                params.events.append({"label": event, "color": "#3B82F6"})

        elif scene_type == SceneType.COMPARISON:
            # Simple two-column comparison
            params.columns = ["Feature", "Value"]
            for elem in visual.elements[:3]:
                params.items.append({"label": elem, "values": ["Details"]})

        return params

    def _extract_steps(self, text: str) -> List[str]:
        """Extract numbered or sequential steps from text."""
        steps = []

        # Look for numbered lists
        numbered = re.findall(r'\d+[.)]\s*([^.]+)', text)
        if numbered:
            return [s.strip()[:30] for s in numbered[:5]]

        # Look for bullet-like patterns
        bullets = re.findall(r'[-*]\s*([^.]+)', text)
        if bullets:
            return [s.strip()[:30] for s in bullets[:5]]

        # Fall back to sentences
        sentences = text.split(".")
        for sentence in sentences[:5]:
            sentence = sentence.strip()
            if len(sentence) > 10:
                steps.append(sentence[:30])

        return steps


# Factory function for easy instantiation
def create_storyboard_generator(
    target_duration: float = 60.0,
    model_provider: str = "groq",
    **kwargs
) -> StoryboardGenerator:
    """
    Create a storyboard generator with custom configuration.

    Args:
        target_duration: Target video duration in seconds
        model_provider: LLM provider (groq, claude, openai)
        **kwargs: Additional configuration options

    Returns:
        Configured StoryboardGenerator instance
    """
    config = StoryboardConfig(
        target_duration=target_duration,
        model_provider=model_provider,
        **kwargs
    )
    return StoryboardGenerator(config)
