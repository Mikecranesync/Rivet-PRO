"""
YCB v3 Video Quality Judge

LLM-as-Judge for evaluating v3 video outputs with visual quality assessment.
Evaluates Manim/Blender rendered videos on professional animation standards.

Target quality threshold: 8.5/10 for v3 videos.
"""

import os
import json
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from pathlib import Path


@dataclass
class V3QualityEvaluation:
    """Result of a v3 video quality evaluation."""

    score: float  # 0-10 overall score
    passed: bool  # True if score >= target (default 8.5 for v3)

    # Component scores
    visual_quality: float = 0.0  # Animation smoothness, clarity
    diagram_quality: float = 0.0  # Technical diagram accuracy
    transition_quality: float = 0.0  # Scene transitions
    script_quality: float = 0.0  # Content quality
    audio_sync: float = 0.0  # Audio-visual synchronization
    metadata_quality: float = 0.0  # SEO and discoverability

    # Feedback for improvement
    rejections: List[str] = field(default_factory=list)
    improvement_suggestions: Dict[str, str] = field(default_factory=dict)

    # Raw response for debugging
    raw_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "component_scores": {
                "visual_quality": self.visual_quality,
                "diagram_quality": self.diagram_quality,
                "transition_quality": self.transition_quality,
                "script_quality": self.script_quality,
                "audio_sync": self.audio_sync,
                "metadata_quality": self.metadata_quality,
            },
            "rejections": self.rejections,
            "improvement_suggestions": self.improvement_suggestions,
        }


# V3 Quality rubric with visual quality focus
V3_QUALITY_RUBRIC = """You are an expert video quality evaluator for professional industrial automation educational videos.

These videos are generated using Manim (2D animations) and optionally Blender (3D animations).
Score this video output on these criteria (0-10 each):

## 1. Visual Quality (0-10) - CRITICAL
- Are animations smooth and professional-looking (30fps, no stuttering)?
- Are colors, fonts, and styles consistent throughout?
- Is the visual resolution appropriate (at least 1080p)?
- Do animated elements appear at appropriate timing?
- Is the overall aesthetic professional (not amateurish)?
- **Pass threshold: >= 8.0** (v3 standard)

## 2. Diagram Quality (0-10) - CRITICAL
- Are technical diagrams clear and readable?
- Do flowcharts have proper flow and arrow directions?
- Are PLC ladder logic diagrams technically accurate?
- Are component relationships clear?
- Is text legible and appropriately sized?
- **Pass threshold: >= 8.0** (v3 standard)

## 3. Transition Quality (0-10)
- Are scene transitions smooth (fades, crossfades)?
- Is pacing appropriate (not too fast or slow)?
- Do transitions enhance understanding rather than distract?
- Is there appropriate visual continuity between scenes?
- **Pass threshold: >= 7.0**

## 4. Script/Content Quality (0-10)
- Is the content technically accurate for industrial automation?
- Does it follow a clear structure: introduction -> content -> conclusion?
- Is it appropriate for the target audience (technicians/engineers)?
- Is terminology explained when necessary?
- **Pass threshold: >= 7.5**

## 5. Audio Synchronization (0-10)
- Does narration align with visual content?
- Are pauses placed at appropriate moments?
- Is the pacing comfortable for learning?
- Do animations sync with narration points?
- **Pass threshold: >= 7.5**

## 6. Metadata Quality (0-10)
- Is the title clear and SEO-friendly?
- Does the description accurately summarize the content?
- Are tags relevant and comprehensive?
- **Pass threshold: >= 7.0**

---

## V3 Scoring Rules

1. Score each component 0-10
2. Calculate overall score as WEIGHTED average:
   - Visual Quality: 25%
   - Diagram Quality: 25%
   - Transition Quality: 10%
   - Script Quality: 20%
   - Audio Sync: 10%
   - Metadata: 10%
3. Video PASSES if:
   - Overall score >= 8.5 (v3 threshold)
   - Visual Quality >= 8.0
   - Diagram Quality >= 8.0
   - No other component below 6.5
4. If FAIL, provide specific rejections with visual improvement suggestions

## Response Format (JSON only)

```json
{
  "score": <overall 0-10>,
  "component_scores": {
    "visual_quality": <0-10>,
    "diagram_quality": <0-10>,
    "transition_quality": <0-10>,
    "script_quality": <0-10>,
    "audio_sync": <0-10>,
    "metadata_quality": <0-10>
  },
  "passed": true/false,
  "rejections": [
    "Specific visual/content issue 1",
    "Specific visual/content issue 2"
  ],
  "improvement_suggestions": {
    "issue_name": "Concrete fix - include Manim/Blender specific suggestions if applicable"
  }
}
```

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation text.
"""


class VideoQualityJudgeV3:
    """
    LLM-as-Judge for v3 video quality evaluation.

    Evaluates videos with focus on visual quality (Manim/Blender rendering).
    Uses higher threshold (8.5/10) for v3 professional standard.
    """

    # Weights for component scores
    COMPONENT_WEIGHTS = {
        "visual_quality": 0.25,
        "diagram_quality": 0.25,
        "transition_quality": 0.10,
        "script_quality": 0.20,
        "audio_sync": 0.10,
        "metadata_quality": 0.10,
    }

    def __init__(
        self,
        target_score: float = 8.5,  # Higher threshold for v3
        min_visual_score: float = 8.0,  # Critical for v3
        min_diagram_score: float = 8.0,  # Critical for v3
        min_other_score: float = 6.5,
        api_key: Optional[str] = None
    ):
        """
        Initialize the v3 video quality judge.

        Args:
            target_score: Minimum overall score to pass (default 8.5 for v3)
            min_visual_score: Minimum visual quality score (default 8.0)
            min_diagram_score: Minimum diagram quality score (default 8.0)
            min_other_score: Minimum for other components (default 6.5)
            api_key: Anthropic API key
        """
        self.target_score = target_score
        self.min_visual_score = min_visual_score
        self.min_diagram_score = min_diagram_score
        self.min_other_score = min_other_score
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        # Lazy-load clients
        self._anthropic_client = None
        self._groq_client = None

    @property
    def anthropic_client(self):
        if self._anthropic_client is None and self.api_key:
            try:
                from anthropic import Anthropic
                self._anthropic_client = Anthropic(api_key=self.api_key)
            except ImportError:
                pass
        return self._anthropic_client

    @property
    def groq_client(self):
        if self._groq_client is None:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                try:
                    from groq import Groq
                    self._groq_client = Groq(api_key=groq_key)
                except ImportError:
                    pass
        return self._groq_client

    def _format_video_for_evaluation(self, video_data: Dict[str, Any]) -> str:
        """Format video data into evaluation prompt."""

        # Extract metadata
        metadata = video_data.get("metadata", {})
        if not metadata:
            metadata = {
                "title": video_data.get("title", "N/A"),
                "description": video_data.get("description", "N/A"),
                "tags": video_data.get("tags", []),
            }

        # V3-specific data
        storyboard = video_data.get("storyboard", {})
        scene_count = storyboard.get("scene_count", len(storyboard.get("scenes", [])))
        total_duration = storyboard.get("total_duration", video_data.get("duration", 0))

        # Render info
        render_info = video_data.get("render_info", {})
        scenes_rendered = render_info.get("scenes_rendered", "unknown")
        render_engine = render_info.get("primary_engine", "Manim")

        # Script
        script = video_data.get("script", "No script provided")

        # Scene breakdown
        scenes_summary = []
        for scene in storyboard.get("scenes", [])[:10]:  # First 10 scenes
            scene_type = scene.get("scene_type", "unknown")
            duration = scene.get("duration", 0)
            narration = scene.get("narration_text", "")[:100]
            scenes_summary.append(f"  - {scene_type}: {duration:.1f}s - {narration}...")

        return f"""
VIDEO TO EVALUATE (V3 - Manim/Blender Rendered):

=== METADATA ===
Title: {metadata.get('title', 'N/A')}
Description: {metadata.get('description', 'N/A')[:500]}
Tags: {', '.join(metadata.get('tags', [])) if metadata.get('tags') else 'None'}

=== TECHNICAL INFO ===
Render Engine: {render_engine}
Scene Count: {scene_count}
Scenes Rendered: {scenes_rendered}
Total Duration: {total_duration:.1f}s

=== STORYBOARD BREAKDOWN ===
{chr(10).join(scenes_summary) if scenes_summary else 'No scene breakdown available'}

=== SCRIPT ===
{script[:3000]}{'... [truncated]' if len(script) > 3000 else ''}

Now evaluate this v3 video output:
"""

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Try direct JSON parse
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try markdown code block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding JSON object
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return {}

    def _calculate_weighted_score(self, component_scores: Dict[str, float]) -> float:
        """Calculate weighted overall score."""
        total = 0.0
        total_weight = 0.0

        for component, weight in self.COMPONENT_WEIGHTS.items():
            score = component_scores.get(component, 0)
            if score > 0:
                total += score * weight
                total_weight += weight

        return total / total_weight if total_weight > 0 else 0.0

    async def evaluate(self, video_data: Dict[str, Any]) -> V3QualityEvaluation:
        """
        Evaluate a v3 video output and return quality assessment.

        Args:
            video_data: Dictionary containing:
                - script: The video script text
                - title/metadata.title: Video title
                - description/metadata.description: Video description
                - tags/metadata.tags: List of tags
                - storyboard: Storyboard data with scenes
                - render_info: Rendering information
                - duration: Total video duration

        Returns:
            V3QualityEvaluation with scores, pass/fail, and improvement suggestions
        """

        video_prompt = self._format_video_for_evaluation(video_data)
        full_prompt = f"{V3_QUALITY_RUBRIC}\n\n---\n\n{video_prompt}"

        raw_response = ""

        # Try Anthropic first
        if self.anthropic_client:
            try:
                response = self.anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": full_prompt}]
                )
                raw_response = response.content[0].text
            except Exception as e:
                print(f"    [!] Anthropic v3 eval failed: {e}")

        # Fallback to Groq
        if not raw_response and self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a professional video quality evaluator. Respond only with valid JSON."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )
                raw_response = response.choices[0].message.content
            except Exception as e:
                print(f"    [!] Groq v3 eval failed: {e}")

        # Parse response
        if not raw_response:
            return V3QualityEvaluation(
                score=0.0,
                passed=False,
                rejections=["Evaluation failed - no LLM provider available"],
                raw_response="",
            )

        parsed = self._parse_json_response(raw_response)

        if not parsed:
            return V3QualityEvaluation(
                score=5.0,
                passed=False,
                rejections=["Could not parse evaluation response"],
                raw_response=raw_response,
            )

        # Extract component scores
        component_scores = parsed.get("component_scores", {})
        visual_quality = component_scores.get("visual_quality", 0)
        diagram_quality = component_scores.get("diagram_quality", 0)
        transition_quality = component_scores.get("transition_quality", 0)
        script_quality = component_scores.get("script_quality", 0)
        audio_sync = component_scores.get("audio_sync", 0)
        metadata_quality = component_scores.get("metadata_quality", 0)

        # Calculate overall score
        overall_score = parsed.get("score", 0)
        if not overall_score and component_scores:
            overall_score = self._calculate_weighted_score(component_scores)

        # Determine pass/fail with v3 rules
        visual_passes = visual_quality >= self.min_visual_score
        diagram_passes = diagram_quality >= self.min_diagram_score
        others_pass = all(
            s >= self.min_other_score
            for s in [transition_quality, script_quality, audio_sync, metadata_quality]
            if s > 0
        )

        passed = (
            overall_score >= self.target_score and
            visual_passes and
            diagram_passes and
            others_pass
        )

        # Override with LLM's decision if available
        if "passed" in parsed:
            passed = parsed["passed"]

        return V3QualityEvaluation(
            score=overall_score,
            passed=passed,
            visual_quality=visual_quality,
            diagram_quality=diagram_quality,
            transition_quality=transition_quality,
            script_quality=script_quality,
            audio_sync=audio_sync,
            metadata_quality=metadata_quality,
            rejections=parsed.get("rejections", []),
            improvement_suggestions=parsed.get("improvement_suggestions", {}),
            raw_response=raw_response,
        )

    def evaluate_sync(self, video_data: Dict[str, Any]) -> V3QualityEvaluation:
        """Synchronous wrapper for evaluate()."""
        import asyncio
        return asyncio.run(self.evaluate(video_data))

    def evaluate_from_result(
        self,
        generation_result: Any,
        script: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> V3QualityEvaluation:
        """
        Evaluate from a V3GenerationResult object.

        Args:
            generation_result: V3GenerationResult from VideoGeneratorV3
            script: Original script
            title: Video title
            description: Video description
            tags: Optional tags

        Returns:
            V3QualityEvaluation
        """
        video_data = {
            "script": script,
            "title": title,
            "description": description,
            "tags": tags or [],
            "duration": generation_result.duration,
            "storyboard": {
                "scene_count": generation_result.scene_count,
                "scenes": generation_result.storyboard.to_dict()["scenes"] if generation_result.storyboard else [],
                "total_duration": generation_result.duration,
            },
            "render_info": {
                "scenes_rendered": generation_result.scenes_rendered,
                "scenes_failed": generation_result.scenes_failed,
                "render_time": generation_result.render_time,
                "primary_engine": "Manim",
            },
            "metadata": {
                "title": title,
                "description": description,
                "tags": tags or [],
            },
        }

        return self.evaluate_sync(video_data)
