"""
YCB Video Generator Pipeline

Complete pipeline to generate a video from a topic:
1. Generate script with OpenAI
2. Generate voice narration with ElevenLabs
3. Generate thumbnail with DALL-E
4. Create video metadata package

Usage:
    python -m ycb.pipeline.video_generator "How to Wire a PLC"
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
    output_dir: str = ""
    created_at: str = ""

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
        self._elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

        # Determine which LLM to use
        self.llm_provider = self._detect_llm_provider()
        print(f"    LLM Provider: {self.llm_provider}")

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

    async def generate_video(self, topic: str, style: str = "educational") -> GeneratedVideo:
        """
        Generate complete video package from topic.

        Args:
            topic: Video topic/subject
            style: Video style (educational, tutorial, review)

        Returns:
            GeneratedVideo with all components
        """
        print(f"\n[*] Generating video for: {topic}")
        print(f"    Style: {style}")

        # Create output directory for this video
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_topic = safe_topic.replace(' ', '_')[:50]
        video_dir = self.output_dir / f"{safe_topic}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        video_dir.mkdir(parents=True, exist_ok=True)

        print(f"    Output: {video_dir}")

        # Step 1: Generate script and metadata
        print("\n[1/4] Generating script with OpenAI...")
        script_data = await self._generate_script(topic, style)

        # Step 2: Generate voice narration
        print("\n[2/4] Generating voice narration...")
        voice_file = await self._generate_voice(script_data["script"], video_dir)

        # Step 3: Generate thumbnail
        print("\n[3/4] Generating thumbnail...")
        thumbnail_file = await self._generate_thumbnail(script_data["thumbnail_prompt"], video_dir)

        # Step 4: Create metadata package
        print("\n[4/4] Creating metadata package...")

        video = GeneratedVideo(
            topic=topic,
            title=script_data["title"],
            description=script_data["description"],
            script=script_data["script"],
            tags=script_data["tags"],
            thumbnail_prompt=script_data["thumbnail_prompt"],
            voice_file=str(voice_file) if voice_file else None,
            thumbnail_file=str(thumbnail_file) if thumbnail_file else None,
            output_dir=str(video_dir),
            created_at=datetime.now().isoformat()
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
4. A thumbnail prompt for DALL-E (describe a visually striking thumbnail)
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

    async def _generate_voice(self, script: str, output_dir: Path) -> Optional[Path]:
        """Generate voice narration using ElevenLabs."""

        if not self._elevenlabs_api_key:
            print("    [!] ELEVENLABS_API_KEY not set, skipping voice generation")
            return None

        try:
            import httpx

            # Use default voice or configured voice
            voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel default

            # Clean script for narration (remove markers)
            clean_script = script.replace("[PAUSE]", "...").replace("*", "")

            # Truncate if too long (ElevenLabs has limits)
            if len(clean_script) > 5000:
                clean_script = clean_script[:5000] + "..."

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": self._elevenlabs_api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": clean_script,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75
                        }
                    },
                    timeout=120.0
                )

                if response.status_code == 200:
                    voice_file = output_dir / "narration.mp3"
                    with open(voice_file, "wb") as f:
                        f.write(response.content)
                    print(f"    Voice file: {voice_file}")
                    return voice_file
                else:
                    print(f"    [!] ElevenLabs error: {response.status_code} - {response.text[:100]}")
                    return None

        except Exception as e:
            print(f"    [!] Voice generation error: {e}")
            return None

    async def _generate_thumbnail(self, prompt: str, output_dir: Path) -> Optional[Path]:
        """Generate thumbnail using DALL-E."""

        try:
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=f"YouTube video thumbnail: {prompt}. Make it eye-catching with bold, readable text overlay space. Professional quality, 16:9 aspect ratio.",
                size="1792x1024",
                quality="standard",
                n=1
            )

            # Download the image
            import httpx
            image_url = response.data[0].url

            async with httpx.AsyncClient() as client:
                img_response = await client.get(image_url)
                if img_response.status_code == 200:
                    thumbnail_file = output_dir / "thumbnail.png"
                    with open(thumbnail_file, "wb") as f:
                        f.write(img_response.content)
                    print(f"    Thumbnail: {thumbnail_file}")
                    return thumbnail_file

        except Exception as e:
            print(f"    [!] Thumbnail generation error: {e}")
            return None

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
    print(f"\nFiles created:")
    print(f"  - metadata.json")
    print(f"  - script.md")
    if video.voice_file:
        print(f"  - narration.mp3")
    if video.thumbnail_file:
        print(f"  - thumbnail.png")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
