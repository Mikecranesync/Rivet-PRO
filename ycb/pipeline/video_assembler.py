"""
YCB Video Assembler

Assembles final MP4 video from:
- Narration audio (MP3)
- Script text (generates slides with PIL)
- Thumbnail (intro/outro)

Uses FFmpeg directly for video generation (more memory efficient).
No ImageMagick required!
Fully open-source, zero cost.

Usage:
    from ycb.pipeline.video_assembler import VideoAssembler

    assembler = VideoAssembler()
    video_path = assembler.assemble(
        audio_path="narration.mp3",
        script="Your script text...",
        output_path="final_video.mp4"
    )
"""

import os
import re
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class SlideContent:
    """Content for a single slide."""
    text: str
    duration: float  # seconds
    is_title: bool = False
    is_outro: bool = False


class VideoAssembler:
    """
    Assemble MP4 video from audio and script.

    Creates slides from script sections using PIL,
    then uses FFmpeg directly for video assembly.
    Much more memory efficient than MoviePy's in-memory approach.
    """

    # Color schemes
    COLORS = {
        "dark_blue": {"bg": (20, 30, 48), "text": (255, 255, 255), "accent": (74, 144, 226)},
        "industrial": {"bg": (45, 52, 54), "text": (241, 242, 246), "accent": (255, 193, 7)},
        "tech": {"bg": (15, 15, 35), "text": (255, 255, 255), "accent": (0, 255, 136)},
    }

    def __init__(self, theme: str = "industrial", resolution: str = "720p"):
        """
        Initialize video assembler.

        Args:
            theme: Color theme (dark_blue, industrial, tech)
            resolution: Video resolution (720p, 1080p)
        """
        self.theme = self.COLORS.get(theme, self.COLORS["industrial"])

        # Set resolution
        if resolution == "1080p":
            self.width = 1920
            self.height = 1080
        else:  # Default to 720p
            self.width = 1280
            self.height = 720

        self.fps = 24

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file using ffprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(audio_path)
                ],
                capture_output=True,
                text=True
            )
            return float(result.stdout.strip())
        except Exception:
            # Fallback: use moviepy just to get duration
            try:
                from moviepy.editor import AudioFileClip
                audio = AudioFileClip(str(audio_path))
                duration = audio.duration
                audio.close()
                return duration
            except Exception:
                return 60.0  # Default fallback

    def _parse_script_to_slides(self, script: str, audio_duration: float) -> List[SlideContent]:
        """
        Parse script into slides with timing.

        Splits on [PAUSE] markers and distributes time.
        """
        # Clean script
        script = script.replace("*", "")

        # Split on [PAUSE] markers
        sections = re.split(r'\[PAUSE\]', script)
        sections = [s.strip() for s in sections if s.strip()]

        if not sections:
            sections = [script]

        # Calculate duration per section
        # Reserve 3 seconds for title, 3 for outro
        content_duration = max(audio_duration - 6, len(sections) * 3)
        duration_per_section = content_duration / len(sections)

        slides = []

        # Title slide
        first_section = sections[0] if sections else "Welcome"
        title_text = first_section.split('.')[0][:80]
        slides.append(SlideContent(
            text=title_text,
            duration=3.0,
            is_title=True
        ))

        # Content slides
        for section in sections:
            if len(section) > 150:
                section = section[:150] + "..."
            slides.append(SlideContent(
                text=section,
                duration=duration_per_section
            ))

        # Outro slide
        slides.append(SlideContent(
            text="Thanks for watching!\nLike & Subscribe",
            duration=3.0,
            is_outro=True
        ))

        return slides

    def _create_slide_image(
        self,
        text: str,
        output_path: Path,
        is_title: bool = False,
        is_outro: bool = False
    ):
        """Create a slide image using PIL and save to file."""
        from PIL import Image, ImageDraw, ImageFont

        bg_color = self.theme["bg"]
        text_color = self.theme["text"]

        # Font size based on type
        if is_title or is_outro:
            fontsize = 56 if self.height == 720 else 72
        else:
            fontsize = 36 if self.height == 720 else 48

        # Create image
        img = Image.new("RGB", (self.width, self.height), bg_color)
        draw = ImageDraw.Draw(img)

        # Try to use a nice font
        font = None
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc"
        ]
        try:
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, fontsize)
                    break
        except Exception:
            pass

        if font is None:
            font = ImageFont.load_default()

        # Wrap text
        wrap_width = 40 if self.height == 720 else 45
        wrapped = textwrap.fill(text, width=wrap_width)
        lines = wrapped.split('\n')

        # Calculate total text height
        line_height = fontsize + 15
        total_height = len(lines) * line_height

        # Start position (centered vertically)
        start_y = (self.height - total_height) // 2

        # Draw each line centered
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            y = start_y + i * line_height
            draw.text((x, y), line, fill=text_color, font=font)

        # Add accent bar for title/outro
        if is_title or is_outro:
            accent_color = self.theme["accent"]
            draw.rectangle(
                [0, self.height - 8, self.width, self.height],
                fill=accent_color
            )

        # Add watermark
        try:
            small_font = ImageFont.truetype(font_paths[0], 18) if font_paths else font
        except Exception:
            small_font = font

        watermark = "RIVET PRO"
        wm_bbox = draw.textbbox((0, 0), watermark, font=small_font)
        wm_width = wm_bbox[2] - wm_bbox[0]
        draw.text(
            (self.width - wm_width - 20, self.height - 35),
            watermark,
            fill=(100, 100, 100),
            font=small_font
        )

        # Save
        img.save(output_path, "PNG")

    def assemble(
        self,
        audio_path: Path,
        script: str,
        output_path: Path,
        title: Optional[str] = None,
        thumbnail_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Assemble final video from components using FFmpeg.

        Args:
            audio_path: Path to narration MP3
            script: Script text
            output_path: Where to save final MP4
            title: Optional title override
            thumbnail_path: Optional thumbnail for intro

        Returns:
            Path to output video, or None if failed
        """
        temp_dir = None
        try:
            # Create temp directory for slides
            temp_dir = tempfile.mkdtemp(prefix="ycb_video_")
            temp_path = Path(temp_dir)

            print(f"    Loading audio: {audio_path}")
            audio_duration = self._get_audio_duration(audio_path)
            print(f"    Audio duration: {audio_duration:.1f}s")

            # Parse script into slides
            print("    Generating slides from script...")
            slides = self._parse_script_to_slides(script, audio_duration)
            print(f"    Created {len(slides)} slides")

            # Create slide images
            slide_files = []
            for i, slide in enumerate(slides):
                print(f"    Creating slide {i+1}/{len(slides)}: {slide.text[:30]}...")
                slide_path = temp_path / f"slide_{i:03d}.png"
                self._create_slide_image(
                    slide.text,
                    slide_path,
                    slide.is_title,
                    slide.is_outro
                )
                slide_files.append((slide_path, slide.duration))

            # Create concat file for ffmpeg
            concat_file = temp_path / "concat.txt"
            with open(concat_file, "w") as f:
                for slide_path, duration in slide_files:
                    f.write(f"file '{slide_path}'\n")
                    f.write(f"duration {duration}\n")
                # Add last file again (ffmpeg concat demuxer quirk)
                f.write(f"file '{slide_files[-1][0]}'\n")

            # Create video from images using FFmpeg
            print("    Creating video from slides...")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # First pass: create silent video from images
            temp_video = temp_path / "temp_video.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-vf", f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-r", str(self.fps),
                str(temp_video)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"    [!] FFmpeg error: {result.stderr[:500]}")
                return None

            # Second pass: add audio
            print("    Adding audio track...")
            cmd = [
                "ffmpeg", "-y",
                "-i", str(temp_video),
                "-i", str(audio_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"    [!] FFmpeg error: {result.stderr[:500]}")
                return None

            if output_path.exists():
                print(f"    Video created: {output_path}")
                print(f"    Size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
                return output_path
            else:
                print("    [!] Output file not created")
                return None

        except FileNotFoundError:
            print("    [!] FFmpeg not found. Install FFmpeg and add to PATH.")
            print("    Download: https://ffmpeg.org/download.html")
            return None
        except Exception as e:
            print(f"    [!] Video assembly failed: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # Clean up temp directory
            if temp_dir:
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass


def assemble_from_package(package_dir: Path) -> Optional[Path]:
    """
    Assemble video from a generated package directory.

    Args:
        package_dir: Directory containing narration.mp3, script.md, metadata.json

    Returns:
        Path to output video
    """
    import json

    package_dir = Path(package_dir)

    # Load metadata
    metadata_path = package_dir / "metadata.json"
    if not metadata_path.exists():
        print(f"[!] No metadata.json found in {package_dir}")
        return None

    with open(metadata_path) as f:
        metadata = json.load(f)

    # Check for required files
    audio_path = package_dir / "narration.mp3"
    if not audio_path.exists():
        print(f"[!] No narration.mp3 found in {package_dir}")
        return None

    script = metadata.get("script", "")
    if not script:
        script_path = package_dir / "script.md"
        if script_path.exists():
            with open(script_path) as f:
                script = f.read()

    title = metadata.get("title", "Video")
    thumbnail_path = package_dir / "thumbnail.png"
    if not thumbnail_path.exists():
        thumbnail_path = None

    output_path = package_dir / "final_video.mp4"

    # Assemble
    assembler = VideoAssembler()
    return assembler.assemble(
        audio_path=audio_path,
        script=script,
        output_path=output_path,
        title=title,
        thumbnail_path=thumbnail_path
    )


async def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m ycb.pipeline.video_assembler <package_dir>")
        print("\nExample:")
        print("  python -m ycb.pipeline.video_assembler ycb_output/My_Video_20260117_120000")
        sys.exit(1)

    package_dir = Path(sys.argv[1])

    if not package_dir.exists():
        print(f"[!] Directory not found: {package_dir}")
        sys.exit(1)

    print(f"\n[*] Assembling video from: {package_dir}")

    result = assemble_from_package(package_dir)

    if result:
        print("\n" + "="*60)
        print("VIDEO ASSEMBLY COMPLETE")
        print("="*60)
        print(f"Output: {result}")
        print(f"Size: {result.stat().st_size / 1024 / 1024:.1f} MB")
        print("="*60)
    else:
        print("\n[!] Video assembly failed")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
