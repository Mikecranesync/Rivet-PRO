"""
YCB Video Generator Pipeline

Complete pipeline to generate a video from a topic:
1. Generate script with LLM (Groq -> Anthropic -> OpenAI)
2. Generate voice narration (ElevenLabs -> Edge TTS -> Piper)
3. Generate thumbnail (Pollinations -> Stability -> Placeholder)
4. Create video metadata package

Usage:
    python -m ycb.pipeline.video_generator "How to Wire a PLC"

Cost: $0/month with free fallback providers.
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Import MediaAssetsService for voice and image generation
from ycb.services import MediaAssetsService, get_media_service


@dataclass
class GeneratedVideo:
    """Complete generated video package."""
    topic: str
    title: str
    description: str
    script: str
    tags: list
    thumbnail_prompt: str
    voice_file: Optional[str] = None
    thumbnail_file: Optional[str] = None
    video_file: Optional[str] = None  # Final assembled MP4
    output_dir: str = ""
    created_at: str = ""
    voice_provider: str = ""
    image_provider: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VideoGenerator:
    """Generate complete video packages from topics."""

    def __init__(self, output_dir: str = "./ycb_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # API clients (lazy init)
        self._openai_client = None
        self._anthropic_client = None
        self._groq_client = None

        # Media assets service for voice and images
        self.media_service = get_media_service()

        # Determine which LLM to use
        self.llm_provider = self._detect_llm_provider()
        print(f"    LLM Provider: {self.llm_provider}")
        print(f"    Voice Providers: {self.media_service.get_available_voice_providers()}")
        print(f"    Image Providers: {self.media_service.get_available_image_providers()}")

    def _detect_llm_provider(self) -> str:
        """Detect which LLM provider to use based on available API keys."""
        # Prefer Groq (fast and free tier), then Anthropic, then OpenAI
        if os.getenv("GROQ_API_KEY"):
            return "groq"
        elif os.getenv("ANTHROPIC_API_KEY"):
            return "anthropic"
        elif os.getenv("OPENAI_API_KEY"):
            return "openai"
        else:
            return "none"

    @property
    def openai_client(self):
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._openai_client

    @property
    def anthropic_client(self):
        if self._anthropic_client is None:
            import anthropic
            self._anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return self._anthropic_client

    @property
    def groq_client(self):
        if self._groq_client is None:
            from groq import Groq
            self._groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        return self._groq_client

    async def generate_video(
        self,
        topic: str,
        style: str = "educational",
        assemble_video: bool = True
    ) -> GeneratedVideo:
        """
        Generate complete video package from topic.

        Args:
            topic: Video topic/subject
            style: Video style (educational, tutorial, review)
            assemble_video: If True, assemble final MP4 video

        Returns:
            GeneratedVideo with all components
        """
        print(f"\n[*] Generating video for: {topic}")
        print(f"    Style: {style}")
        print(f"    Assemble MP4: {assemble_video}")

        # Create output directory for this video
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_topic = safe_topic.replace(' ', '_')[:50]
        video_dir = self.output_dir / f"{safe_topic}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        video_dir.mkdir(parents=True, exist_ok=True)

        print(f"    Output: {video_dir}")

        # Determine steps (5 if assembling video, 4 if not)
        total_steps = 5 if assemble_video else 4

        # Step 1: Generate script and metadata
        print(f"\n[1/{total_steps}] Generating script with {self.llm_provider}...")
        script_data = await self._generate_script(topic, style)

        # Step 2: Generate voice narration
        print(f"\n[2/{total_steps}] Generating voice narration...")
        voice_result = await self._generate_voice(script_data["script"], video_dir)

        # Step 3: Generate thumbnail
        print(f"\n[3/{total_steps}] Generating thumbnail...")
        thumbnail_result = await self._generate_thumbnail(script_data["thumbnail_prompt"], video_dir)

        # Step 4: Create metadata package
        print(f"\n[4/{total_steps}] Creating metadata package...")

        video = GeneratedVideo(
            topic=topic,
            title=script_data["title"],
            description=script_data["description"],
            script=script_data["script"],
            tags=script_data["tags"],
            thumbnail_prompt=script_data["thumbnail_prompt"],
            voice_file=str(voice_result["file"]) if voice_result["file"] else None,
            thumbnail_file=str(thumbnail_result["file"]) if thumbnail_result["file"] else None,
            output_dir=str(video_dir),
            created_at=datetime.now().isoformat(),
            voice_provider=voice_result["provider"],
            image_provider=thumbnail_result["provider"]
        )

        # Save metadata
        metadata_file = video_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(video.to_dict(), f, indent=2, ensure_ascii=False)

        # Save script separately
        script_file = video_dir / "script.md"
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(f"# {video.title}\n\n")
            f.write(f"**Topic:** {topic}\n")
            f.write(f"**Style:** {style}\n")
            f.write(f"**Generated:** {video.created_at}\n\n")
            f.write("---\n\n")
            f.write(video.script)

        print(f"\n[+] Video package created: {video_dir}")

        # Step 5: Assemble final video (if requested and audio exists)
        if assemble_video and voice_result["file"]:
            print(f"\n[5/{total_steps}] Assembling final MP4 video...")
            video_file = await self._assemble_video(
                audio_path=voice_result["file"],
                script=script_data["script"],
                title=script_data["title"],
                output_dir=video_dir
            )
            if video_file:
                video.video_file = str(video_file)
                # Update metadata with video file
                with open(metadata_file, "w", encoding="utf-8") as f:
                    json.dump(video.to_dict(), f, indent=2, ensure_ascii=False)

        # Print quota status
        print("\n[*] Quota Status:")
        for provider, stats in self.media_service.get_quota_status().items():
            if stats["usage"] > 0:
                print(f"    {provider}: {stats['usage']}/{stats['limit']} {stats['unit']}")

        return video

    async def _generate_script(self, topic: str, style: str) -> Dict[str, Any]:
        """Generate script and metadata using available LLM."""

        prompt = f"""You are a professional YouTube scriptwriter. Generate a complete video script for the following:

Topic: {topic}
Style: {style}
Target Duration: 5-8 minutes

Please provide:
1. An SEO-optimized title (max 60 characters)
2. A compelling description (150-200 words)
3. 10 relevant tags
4. A thumbnail prompt for image generation (describe a visually striking thumbnail)
5. The complete script with:
   - Hook (first 15 seconds to grab attention)
   - Introduction
   - Main content (3-5 key points)
   - Conclusion
   - Call to action

Format your response as JSON with these keys:
- title
- description
- tags (array)
- thumbnail_prompt
- script (the full narration script)

Make the script conversational, engaging, and easy to follow. Include natural pauses and emphasis markers like [PAUSE] or *emphasis*.

IMPORTANT: Respond ONLY with valid JSON, no markdown formatting or code blocks.
"""

        try:
            if self.llm_provider == "groq":
                result = await self._generate_with_groq(prompt)
            elif self.llm_provider == "anthropic":
                result = await self._generate_with_anthropic(prompt)
            elif self.llm_provider == "openai":
                result = await self._generate_with_openai(prompt)
            else:
                raise ValueError("No LLM provider available")

            print(f"    Title: {result.get('title', 'Untitled')}")
            print(f"    Script length: {len(result.get('script', ''))} chars")
            return result

        except Exception as e:
            print(f"    [!] LLM error: {e}")
            # Return placeholder
            return {
                "title": f"Guide to {topic}",
                "description": f"Learn everything about {topic} in this comprehensive guide.",
                "tags": [topic.lower(), "tutorial", "guide", "how-to", "learn"],
                "thumbnail_prompt": f"Professional YouTube thumbnail about {topic}, bold text, vibrant colors",
                "script": f"Welcome! Today we're exploring {topic}. Let's dive in..."
            }

    async def _generate_with_groq(self, prompt: str) -> Dict[str, Any]:
        """Generate using Groq (Llama/Mixtral)."""
        response = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert YouTube content creator. Always respond with valid JSON only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        content = response.choices[0].message.content
        # Clean up any markdown formatting
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)

    async def _generate_with_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Generate using Anthropic Claude."""
        response = self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000,
            messages=[
                {"role": "user", "content": f"You are an expert YouTube content creator. Always respond with valid JSON only.\n\n{prompt}"}
            ]
        )
        content = response.content[0].text
        # Clean up any markdown formatting
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)

    async def _generate_with_openai(self, prompt: str) -> Dict[str, Any]:
        """Generate using OpenAI."""
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert YouTube content creator. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=2000
        )
        return json.loads(response.choices[0].message.content)

    async def _generate_voice(self, script: str, output_dir: Path) -> Dict[str, Any]:
        """
        Generate voice narration using MediaAssetsService.

        Tries providers in order: ElevenLabs -> Edge TTS -> Piper
        """
        # Clean script for narration (remove markers)
        clean_script = script.replace("[PAUSE]", "...").replace("*", "")

        # Truncate if too long
        if len(clean_script) > 5000:
            clean_script = clean_script[:5000] + "..."

        voice_file = output_dir / "narration.mp3"

        result = await self.media_service.generate_voice(
            text=clean_script,
            output_path=voice_file
        )

        if result.success:
            print(f"    Voice file: {result.file_path}")
            print(f"    Provider used: {result.provider_used}")
            if len(result.providers_tried) > 1:
                print(f"    Providers tried: {result.providers_tried}")
            return {"file": result.file_path, "provider": result.provider_used}
        else:
            print(f"    [!] Voice generation failed: {result.error}")
            print(f"    Providers tried: {result.providers_tried}")
            return {"file": None, "provider": ""}

    async def _generate_thumbnail(self, prompt: str, output_dir: Path) -> Dict[str, Any]:
        """
        Generate thumbnail using MediaAssetsService.

        Tries providers in order: Pollinations -> Stability -> Placeholder
        """
        # Enhance prompt for thumbnail generation
        enhanced_prompt = f"YouTube video thumbnail: {prompt}. Make it eye-catching with bold, readable text overlay space. Professional quality, 16:9 aspect ratio."

        thumbnail_file = output_dir / "thumbnail.png"

        result = await self.media_service.generate_thumbnail(
            prompt=enhanced_prompt,
            output_path=thumbnail_file,
            width=1280,
            height=720
        )

        if result.success:
            print(f"    Thumbnail: {result.file_path}")
            print(f"    Provider used: {result.provider_used}")
            if len(result.providers_tried) > 1:
                print(f"    Providers tried: {result.providers_tried}")
            return {"file": result.file_path, "provider": result.provider_used}
        else:
            print(f"    [!] Thumbnail generation failed: {result.error}")
            print(f"    Providers tried: {result.providers_tried}")
            return {"file": None, "provider": ""}

    async def _assemble_video(
        self,
        audio_path: Path,
        script: str,
        title: str,
        output_dir: Path
    ) -> Optional[Path]:
        """
        Assemble final MP4 video from audio and script.

        Uses MoviePy to create slides from script sections
        and sync with narration audio.
        """
        try:
            from ycb.pipeline.video_assembler import VideoAssembler

            assembler = VideoAssembler(theme="industrial")
            output_path = output_dir / "final_video.mp4"

            result = assembler.assemble(
                audio_path=audio_path,
                script=script,
                output_path=output_path,
                title=title
            )

            if result and result.exists():
                print(f"    Video file: {result}")
                print(f"    Size: {result.stat().st_size / 1024 / 1024:.1f} MB")
                return result
            else:
                print("    [!] Video assembly failed")
                return None

        except ImportError as e:
            print(f"    [!] MoviePy not available: {e}")
            print("    Run: pip install moviepy==1.0.3")
            return None
        except Exception as e:
            print(f"    [!] Video assembly error: {e}")
            return None


async def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m ycb.pipeline.video_generator \"Your Topic Here\"")
        print("\nExample:")
        print("  python -m ycb.pipeline.video_generator \"How to Wire a PLC\"")
        sys.exit(1)

    topic = " ".join(sys.argv[1:])

    generator = VideoGenerator()
    video = await generator.generate_video(topic)

    print("\n" + "="*60)
    print("VIDEO GENERATION COMPLETE")
    print("="*60)
    print(f"Title: {video.title}")
    print(f"Output: {video.output_dir}")
    print(f"\nProviders used:")
    print(f"  - LLM: {generator.llm_provider}")
    print(f"  - Voice: {video.voice_provider or 'none'}")
    print(f"  - Image: {video.image_provider or 'none'}")
    print(f"\nFiles created:")
    print(f"  - metadata.json")
    print(f"  - script.md")
    if video.voice_file:
        print(f"  - narration.mp3")
    if video.thumbnail_file:
        print(f"  - thumbnail.png")
    if video.video_file:
        print(f"  - final_video.mp4  <-- WATCH THIS!")
    print("="*60)

    if video.video_file:
        print(f"\nTo watch: start {video.video_file}")


if __name__ == "__main__":
    asyncio.run(main())
