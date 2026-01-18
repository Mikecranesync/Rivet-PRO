"""
YCB Video Quality Judge

LLM-as-Judge for evaluating video outputs before publishing.
Uses Claude to score videos on a rubric and provide improvement feedback.

Cost: ~$0.003 per evaluation (Claude 3.5 Sonnet)

Usage:
    from ycb.evaluation.video_judge import VideoQualityJudge

    judge = VideoQualityJudge()
    result = await judge.evaluate(video_data)

    if result.passed:
        publish_video(video_data)
    else:
        regenerate_with_feedback(result.improvement_suggestions)
"""

import os
import json
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from pathlib import Path


@dataclass
class QualityEvaluation:
    """Result of a video quality evaluation."""

    score: float  # 0-10 overall score
    passed: bool  # True if score >= target (default 8.0)

    # Component scores
    script_quality: float = 0.0
    visual_assets: float = 0.0
    audio_narration: float = 0.0
    metadata_quality: float = 0.0

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
                "script_quality": self.script_quality,
                "visual_assets": self.visual_assets,
                "audio_narration": self.audio_narration,
                "metadata_quality": self.metadata_quality,
            },
            "rejections": self.rejections,
            "improvement_suggestions": self.improvement_suggestions,
        }


# Quality rubric for industrial automation videos
QUALITY_RUBRIC = """You are an expert video quality evaluator for industrial automation educational content.

Score this video output on these criteria (0-10 each):

## 1. Script Quality (0-10)
- Is the content technically accurate for industrial automation/PLC/maintenance topics?
- Does it follow a clear structure: hook (first 15 sec) -> problem -> solution -> call-to-action?
- Is it engaging without excessive jargon? Does it explain terms when needed?
- Is the length appropriate (aim for 3-8 minutes of spoken content)?
- **Pass threshold: >= 7**

## 2. Visual Assets (0-10)
- Does the thumbnail description suggest a professional, clickable image?
- Would the visual concept grab attention on YouTube?
- Is it relevant to the topic and not misleading?
- **Pass threshold: >= 7**

## 3. Audio/Narration (0-10)
- Is the script written for natural speech (not robotic)?
- Are there appropriate [PAUSE] markers for pacing?
- Is the estimated duration reasonable (not rushed or too slow)?
- **Pass threshold: >= 7**

## 4. Metadata Quality (0-10)
- Title: Is it under 60 chars, SEO-friendly, and attention-grabbing?
- Description: Does it clearly explain what viewers will learn (150-200 words)?
- Tags: Are they relevant, searchable, and comprehensive (8-15 tags)?
- **Pass threshold: >= 7**

---

## Scoring Instructions

1. Score each component 0-10
2. Calculate overall score as average of all components
3. Video PASSES if overall score >= 8.0 AND no component is below 6.0
4. If FAIL, provide specific rejections and actionable improvement suggestions

## Response Format (JSON only)

```json
{
  "score": <overall 0-10>,
  "component_scores": {
    "script_quality": <0-10>,
    "visual_assets": <0-10>,
    "audio_narration": <0-10>,
    "metadata_quality": <0-10>
  },
  "passed": true/false,
  "rejections": [
    "Specific issue 1",
    "Specific issue 2"
  ],
  "improvement_suggestions": {
    "issue_name": "Concrete fix with example if possible"
  }
}
```

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation text.
"""


class VideoQualityJudge:
    """
    LLM-as-Judge for video quality evaluation.

    Uses Claude 3.5 Sonnet for cost-effective evaluation (~$0.003/eval).
    Falls back to Groq if Anthropic API unavailable.
    """

    def __init__(
        self,
        target_score: float = 8.0,
        min_component_score: float = 6.0,
        api_key: Optional[str] = None
    ):
        """
        Initialize the video quality judge.

        Args:
            target_score: Minimum overall score to pass (default 8.0)
            min_component_score: Minimum score for any component (default 6.0)
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
        """
        self.target_score = target_score
        self.min_component_score = min_component_score
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

        metadata = video_data.get("metadata", {})
        if not metadata:
            # Handle flat structure from video_generator
            metadata = {
                "title": video_data.get("title", "N/A"),
                "description": video_data.get("description", "N/A"),
                "tags": video_data.get("tags", []),
            }

        script = video_data.get("script", "No script provided")
        thumbnail_prompt = video_data.get("thumbnail_prompt", "No thumbnail description")
        audio_duration = video_data.get("audio_duration", "unknown")

        # Estimate duration from script if not provided
        if audio_duration == "unknown" and script:
            # Rough estimate: 150 words per minute
            word_count = len(script.split())
            audio_duration = f"~{word_count // 150} minutes (estimated from {word_count} words)"

        return f"""
VIDEO TO EVALUATE:

=== METADATA ===
Title: {metadata.get('title', 'N/A')}
Description: {metadata.get('description', 'N/A')}
Tags: {', '.join(metadata.get('tags', [])) if metadata.get('tags') else 'None'}

=== SCRIPT ===
{script[:5000]}{'... [truncated]' if len(script) > 5000 else ''}

=== VISUAL ASSETS ===
Thumbnail Concept: {thumbnail_prompt}

=== AUDIO ===
Duration: {audio_duration}

Now evaluate this video output:
"""

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks."""

        # Try direct JSON parse first
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding JSON object in text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Return empty result if parsing fails
        return {}

    async def evaluate(self, video_data: Dict[str, Any]) -> QualityEvaluation:
        """
        Evaluate a video output and return quality assessment.

        Args:
            video_data: Dictionary containing:
                - script: The video script text
                - title/metadata.title: Video title
                - description/metadata.description: Video description
                - tags/metadata.tags: List of tags
                - thumbnail_prompt: Thumbnail image concept
                - audio_duration: Optional duration info

        Returns:
            QualityEvaluation with scores, pass/fail, and improvement suggestions
        """

        video_prompt = self._format_video_for_evaluation(video_data)
        full_prompt = f"{QUALITY_RUBRIC}\n\n---\n\n{video_prompt}"

        raw_response = ""

        # Try Anthropic first (preferred for quality)
        if self.anthropic_client:
            try:
                response = self.anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": full_prompt}]
                )
                raw_response = response.content[0].text
            except Exception as e:
                print(f"    [!] Anthropic eval failed: {e}")

        # Fallback to Groq
        if not raw_response and self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a video quality evaluator. Respond only with valid JSON."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=1500,
                    temperature=0.3
                )
                raw_response = response.choices[0].message.content
            except Exception as e:
                print(f"    [!] Groq eval failed: {e}")

        # Parse response
        if not raw_response:
            # No evaluation possible - return conservative fail
            return QualityEvaluation(
                score=0.0,
                passed=False,
                rejections=["Evaluation failed - no LLM provider available"],
                raw_response="",
            )

        parsed = self._parse_json_response(raw_response)

        if not parsed:
            # Parsing failed - return with raw response for debugging
            return QualityEvaluation(
                score=5.0,  # Conservative middle score
                passed=False,
                rejections=["Could not parse evaluation response"],
                raw_response=raw_response,
            )

        # Extract component scores
        component_scores = parsed.get("component_scores", {})
        script_quality = component_scores.get("script_quality", 0)
        visual_assets = component_scores.get("visual_assets", 0)
        audio_narration = component_scores.get("audio_narration", 0)
        metadata_quality = component_scores.get("metadata_quality", 0)

        # Calculate overall score if not provided
        overall_score = parsed.get("score", 0)
        if not overall_score and component_scores:
            scores = [script_quality, visual_assets, audio_narration, metadata_quality]
            scores = [s for s in scores if s > 0]
            overall_score = sum(scores) / len(scores) if scores else 0

        # Determine pass/fail
        all_components_pass = all(
            s >= self.min_component_score
            for s in [script_quality, visual_assets, audio_narration, metadata_quality]
            if s > 0
        )
        passed = overall_score >= self.target_score and all_components_pass

        # Override with LLM's pass decision if available
        if "passed" in parsed:
            passed = parsed["passed"]

        return QualityEvaluation(
            score=overall_score,
            passed=passed,
            script_quality=script_quality,
            visual_assets=visual_assets,
            audio_narration=audio_narration,
            metadata_quality=metadata_quality,
            rejections=parsed.get("rejections", []),
            improvement_suggestions=parsed.get("improvement_suggestions", {}),
            raw_response=raw_response,
        )

    def evaluate_sync(self, video_data: Dict[str, Any]) -> QualityEvaluation:
        """Synchronous wrapper for evaluate()."""
        import asyncio
        return asyncio.run(self.evaluate(video_data))


async def evaluate_video_file(metadata_path: Path) -> QualityEvaluation:
    """
    Convenience function to evaluate a video from its metadata.json file.

    Args:
        metadata_path: Path to metadata.json from video generator

    Returns:
        QualityEvaluation result
    """
    with open(metadata_path) as f:
        video_data = json.load(f)

    judge = VideoQualityJudge()
    return await judge.evaluate(video_data)


# CLI entry point
async def main():
    """CLI for testing video evaluation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m ycb.evaluation.video_judge <metadata.json>")
        print("\nExample:")
        print("  python -m ycb.evaluation.video_judge ycb_output/My_Video/metadata.json")
        sys.exit(1)

    metadata_path = Path(sys.argv[1])

    if not metadata_path.exists():
        print(f"[!] File not found: {metadata_path}")
        sys.exit(1)

    print(f"\n[*] Evaluating video: {metadata_path.parent.name}")

    result = await evaluate_video_file(metadata_path)

    print(f"\n{'='*60}")
    print("QUALITY EVALUATION RESULT")
    print(f"{'='*60}")
    print(f"Overall Score: {result.score}/10")
    print(f"Status: {'PASSED' if result.passed else 'FAILED'}")
    print(f"\nComponent Scores:")
    print(f"  - Script Quality:   {result.script_quality}/10")
    print(f"  - Visual Assets:    {result.visual_assets}/10")
    print(f"  - Audio/Narration:  {result.audio_narration}/10")
    print(f"  - Metadata Quality: {result.metadata_quality}/10")

    if result.rejections:
        print(f"\nRejections:")
        for r in result.rejections:
            print(f"  - {r}")

    if result.improvement_suggestions:
        print(f"\nImprovement Suggestions:")
        for issue, fix in result.improvement_suggestions.items():
            print(f"  [{issue}]: {fix}")

    print(f"{'='*60}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
