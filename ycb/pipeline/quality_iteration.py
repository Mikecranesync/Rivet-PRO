"""
YCB Quality Iteration Pipeline

Wraps the video generator with an LLM-as-Judge feedback loop.
Regenerates videos until they pass quality threshold or max iterations.

Cost: ~$0.05-0.15 per video (including regeneration attempts)

Usage:
    from ycb.pipeline.quality_iteration import QualityIterativeGenerator

    gen = QualityIterativeGenerator(max_iterations=4, target_score=8.0)
    video = await gen.generate_with_quality_gate("PLC Programming Basics")

    if video["passed"]:
        upload_to_youtube(video)
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

from ycb.evaluation.video_judge import VideoQualityJudge, QualityEvaluation
from ycb.pipeline.video_generator import VideoGenerator, GeneratedVideo


@dataclass
class IterationRecord:
    """Record of a single iteration attempt."""
    iteration: int
    score: float
    passed: bool
    rejections: List[str] = field(default_factory=list)
    improvements_applied: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class QualityIterationResult:
    """Result of quality-gated video generation."""
    topic: str
    final_score: float
    passed: bool
    iterations_used: int
    max_iterations: int
    video: Optional[Dict[str, Any]] = None
    iteration_history: List[IterationRecord] = field(default_factory=list)
    total_cost_estimate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["iteration_history"] = [asdict(r) for r in self.iteration_history]
        return result


class QualityIterativeGenerator:
    """
    Video generator with automatic quality iteration.

    Generates videos, evaluates them with LLM judge, and regenerates
    with feedback until quality threshold is met or max iterations reached.
    """

    def __init__(
        self,
        max_iterations: int = 4,
        target_score: float = 8.0,
        min_component_score: float = 6.0,
        output_dir: str = "./ycb_output"
    ):
        """
        Initialize quality-gated generator.

        Args:
            max_iterations: Maximum regeneration attempts (default 4)
            target_score: Minimum overall score to pass (default 8.0)
            min_component_score: Minimum score for any component (default 6.0)
            output_dir: Output directory for generated videos
        """
        self.max_iterations = max_iterations
        self.target_score = target_score
        self.min_component_score = min_component_score

        self.generator = VideoGenerator(output_dir=output_dir)
        self.judge = VideoQualityJudge(
            target_score=target_score,
            min_component_score=min_component_score
        )

        # Cost tracking (estimates)
        self.cost_per_generation = 0.01  # LLM script generation
        self.cost_per_evaluation = 0.003  # Judge evaluation

    async def _regenerate_script_with_feedback(
        self,
        topic: str,
        style: str,
        improvement_prompt: str,
        previous_video: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Regenerate script content using judge feedback."""
        import os

        prompt = f"""You are a professional YouTube scriptwriter for industrial automation content.

ORIGINAL TOPIC: {topic}
STYLE: {style}

PREVIOUS ATTEMPT (needs improvement):
Title: {previous_video.get('title', 'N/A')}
Description: {previous_video.get('description', 'N/A')[:300]}...

{improvement_prompt}

Generate an IMPROVED version with:
1. An SEO-optimized title (max 60 characters)
2. A compelling description (150-200 words)
3. 10-15 relevant tags
4. A thumbnail prompt for image generation
5. A complete script (800-1500 words) with:
   - Hook (first 15 seconds)
   - Introduction
   - Main content (3-5 key points with technical details)
   - Conclusion
   - Call to action
   - [PAUSE] markers for pacing

Format your response as JSON with keys: title, description, tags, thumbnail_prompt, script
IMPORTANT: Respond ONLY with valid JSON, no markdown or code blocks.
"""

        # Try Groq first
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are an expert YouTube content creator for industrial automation. Respond with valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4000
                )
                content = response.choices[0].message.content.strip()
                # Clean markdown
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                return json.loads(content)
            except Exception as e:
                print(f"    [!] Groq regeneration failed: {e}")

        # Fallback to Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=anthropic_key)
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                return json.loads(content)
            except Exception as e:
                print(f"    [!] Anthropic regeneration failed: {e}")

        return None

    def _build_improvement_prompt(self, evaluation: QualityEvaluation) -> str:
        """Build a prompt incorporating judge feedback for regeneration."""

        prompt_parts = [
            f"Previous attempt scored {evaluation.score:.1f}/10 and needs improvement.",
            "",
            "SPECIFIC ISSUES TO FIX:"
        ]

        # Add rejections
        for rejection in evaluation.rejections:
            prompt_parts.append(f"- {rejection}")

        prompt_parts.append("")
        prompt_parts.append("REQUIRED IMPROVEMENTS:")

        # Add improvement suggestions
        for issue, fix in evaluation.improvement_suggestions.items():
            prompt_parts.append(f"- [{issue}]: {fix}")

        prompt_parts.extend([
            "",
            "COMPONENT SCORES TO IMPROVE:",
            f"- Script Quality: {evaluation.script_quality}/10 (need >= 7)",
            f"- Visual Assets: {evaluation.visual_assets}/10 (need >= 7)",
            f"- Audio/Narration: {evaluation.audio_narration}/10 (need >= 7)",
            f"- Metadata Quality: {evaluation.metadata_quality}/10 (need >= 7)",
            "",
            "Generate an IMPROVED version addressing ALL issues above.",
            "Be MORE specific, MORE technical, and MORE actionable."
        ])

        return "\n".join(prompt_parts)

    async def generate_with_quality_gate(
        self,
        topic: str,
        style: str = "educational",
        initial_prompt: Optional[str] = None,
        assemble_video: bool = False  # Don't assemble until passed
    ) -> QualityIterationResult:
        """
        Generate video with quality iteration loop.

        Args:
            topic: Video topic
            style: Video style (educational, tutorial, review)
            initial_prompt: Optional custom prompt for first attempt
            assemble_video: Whether to assemble final MP4 (only on pass)

        Returns:
            QualityIterationResult with video data and iteration history
        """

        result = QualityIterationResult(
            topic=topic,
            final_score=0.0,
            passed=False,
            iterations_used=0,
            max_iterations=self.max_iterations
        )

        current_video = None
        improvement_prompt = initial_prompt
        improvements_applied: List[str] = []

        for iteration in range(1, self.max_iterations + 1):
            result.iterations_used = iteration

            print(f"\n{'='*60}")
            print(f"[Iteration {iteration}/{self.max_iterations}] Generating: {topic}")
            print(f"{'='*60}")

            # Step 1: Generate video (without final assembly)
            try:
                # Generate with topic only - feedback is used to improve prompts internally
                video = await self.generator.generate_video(
                    topic=topic,
                    style=style,
                    assemble_video=False  # Skip assembly until passed
                )

                # For iteration > 1, we'll need to regenerate the script with improvements
                # This is done by calling the generator again - LLM will produce different output
                if iteration > 1 and improvement_prompt:
                    print(f"    Applying improvements from previous feedback...")
                    # Re-generate just the script with the improvement context
                    improved_script = await self._regenerate_script_with_feedback(
                        topic=topic,
                        style=style,
                        improvement_prompt=improvement_prompt,
                        previous_video=current_video
                    )
                    if improved_script:
                        video = GeneratedVideo(
                            topic=video.topic,
                            title=improved_script.get("title", video.title),
                            description=improved_script.get("description", video.description),
                            script=improved_script.get("script", video.script),
                            tags=improved_script.get("tags", video.tags),
                            thumbnail_prompt=improved_script.get("thumbnail_prompt", video.thumbnail_prompt),
                            voice_file=video.voice_file,
                            thumbnail_file=video.thumbnail_file,
                            output_dir=video.output_dir,
                            created_at=video.created_at,
                            voice_provider=video.voice_provider,
                            image_provider=video.image_provider
                        )

                current_video = video.to_dict()
                result.total_cost_estimate += self.cost_per_generation

            except Exception as e:
                print(f"    [!] Generation failed: {e}")
                result.iteration_history.append(IterationRecord(
                    iteration=iteration,
                    score=0.0,
                    passed=False,
                    rejections=[f"Generation error: {str(e)}"]
                ))
                continue

            # Step 2: Evaluate with judge
            print(f"\n[Iteration {iteration}] Evaluating quality...")

            try:
                evaluation = await self.judge.evaluate(current_video)
                result.total_cost_estimate += self.cost_per_evaluation

                print(f"    Score: {evaluation.score:.1f}/10")
                print(f"    Script: {evaluation.script_quality}/10 | Visual: {evaluation.visual_assets}/10")
                print(f"    Audio: {evaluation.audio_narration}/10 | Metadata: {evaluation.metadata_quality}/10")
                print(f"    Status: {'PASSED' if evaluation.passed else 'FAILED'}")

            except Exception as e:
                print(f"    [!] Evaluation failed: {e}")
                evaluation = QualityEvaluation(
                    score=5.0,
                    passed=False,
                    rejections=[f"Evaluation error: {str(e)}"]
                )

            # Record iteration
            record = IterationRecord(
                iteration=iteration,
                score=evaluation.score,
                passed=evaluation.passed,
                rejections=evaluation.rejections,
                improvements_applied=improvements_applied.copy()
            )
            result.iteration_history.append(record)

            # Step 3: Check if passed
            if evaluation.passed:
                print(f"\n[+] Video PASSED quality gate at iteration {iteration}!")
                result.passed = True
                result.final_score = evaluation.score
                result.video = current_video
                result.video["quality_evaluation"] = evaluation.to_dict()
                result.video["iterations_used"] = iteration

                # Now assemble final video if requested
                if assemble_video and current_video.get("voice_file"):
                    print("\n[*] Assembling final MP4...")
                    try:
                        from ycb.pipeline.video_assembler import VideoAssembler
                        assembler = VideoAssembler()
                        video_path = await self._assemble_passed_video(current_video)
                        if video_path:
                            result.video["video_file"] = str(video_path)
                    except Exception as e:
                        print(f"    [!] Assembly failed: {e}")

                break

            # Step 4: Build improvement prompt for next iteration
            if iteration < self.max_iterations:
                print(f"\n[*] Building improvement prompt for iteration {iteration + 1}...")

                if evaluation.rejections:
                    print(f"    Rejections to fix:")
                    for r in evaluation.rejections[:3]:  # Show top 3
                        print(f"      - {r[:80]}...")

                improvement_prompt = self._build_improvement_prompt(evaluation)
                improvements_applied = list(evaluation.improvement_suggestions.keys())

        # Final result
        if not result.passed:
            print(f"\n[!] Max iterations reached. Best score: {result.final_score:.1f}/10")
            result.video = current_video
            if current_video:
                result.video["quality_evaluation"] = evaluation.to_dict()
                result.video["iterations_used"] = result.iterations_used

        print(f"\n[*] Total estimated cost: ${result.total_cost_estimate:.3f}")

        return result

    async def _assemble_passed_video(self, video_data: Dict[str, Any]) -> Optional[Path]:
        """Assemble final MP4 for a passed video."""
        from ycb.pipeline.video_assembler import VideoAssembler

        output_dir = Path(video_data.get("output_dir", "./ycb_output"))
        voice_file = video_data.get("voice_file")

        if not voice_file:
            return None

        assembler = VideoAssembler()
        output_path = output_dir / "final_video.mp4"

        result = assembler.assemble(
            audio_path=Path(voice_file),
            script=video_data.get("script", ""),
            output_path=output_path,
            title=video_data.get("title", "Video")
        )

        return result

    def generate_sync(
        self,
        topic: str,
        style: str = "educational",
        assemble_video: bool = False
    ) -> QualityIterationResult:
        """Synchronous wrapper for generate_with_quality_gate()."""
        return asyncio.run(
            self.generate_with_quality_gate(topic, style, assemble_video=assemble_video)
        )


async def main():
    """CLI entry point for testing quality iteration."""
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python -m ycb.pipeline.quality_iteration \"Your Topic\"")
        print("\nOptions:")
        print("  --max-iterations N  Maximum iterations (default: 4)")
        print("  --target-score N    Target score 0-10 (default: 8.0)")
        print("  --assemble          Assemble final MP4 on pass")
        print("\nExample:")
        print("  python -m ycb.pipeline.quality_iteration \"PLC Basics\" --max-iterations 3")
        sys.exit(1)

    # Parse args
    args = sys.argv[1:]
    topic = args[0]
    max_iterations = 4
    target_score = 8.0
    assemble = False

    for i, arg in enumerate(args):
        if arg == "--max-iterations" and i + 1 < len(args):
            max_iterations = int(args[i + 1])
        elif arg == "--target-score" and i + 1 < len(args):
            target_score = float(args[i + 1])
        elif arg == "--assemble":
            assemble = True

    print(f"\n[*] Quality Iterative Generation")
    print(f"    Topic: {topic}")
    print(f"    Max iterations: {max_iterations}")
    print(f"    Target score: {target_score}/10")
    print(f"    Assemble video: {assemble}")

    gen = QualityIterativeGenerator(
        max_iterations=max_iterations,
        target_score=target_score
    )

    result = await gen.generate_with_quality_gate(
        topic=topic,
        assemble_video=assemble
    )

    print(f"\n{'='*60}")
    print("QUALITY ITERATION RESULT")
    print(f"{'='*60}")
    print(f"Topic: {result.topic}")
    print(f"Final Score: {result.final_score:.1f}/10")
    print(f"Status: {'PASSED' if result.passed else 'FAILED'}")
    print(f"Iterations: {result.iterations_used}/{result.max_iterations}")
    print(f"Estimated Cost: ${result.total_cost_estimate:.3f}")

    print(f"\nIteration History:")
    for record in result.iteration_history:
        status = "PASS" if record.passed else "FAIL"
        print(f"  [{record.iteration}] {record.score:.1f}/10 ({status})")
        if record.rejections:
            print(f"      Issues: {len(record.rejections)}")

    if result.video:
        print(f"\nOutput: {result.video.get('output_dir', 'N/A')}")
        if result.video.get("video_file"):
            print(f"Video: {result.video['video_file']}")

    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
