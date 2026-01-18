"""
Image Generation Providers for YCB

Implements multiple image providers with fallback support:
1. Pollinations.ai (free, no API key, DALL-E 3 compatible)
2. Stability AI (optional, if API key provided)
3. Placeholder (local PIL, always works)
"""

import os
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from urllib.parse import quote


@dataclass
class ImageResult:
    """Result from image generation."""
    success: bool
    file_path: Optional[Path] = None
    provider: str = ""
    error: Optional[str] = None


class ImageProvider(ABC):
    """Base class for image providers."""

    name: str = "base"

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        output_path: Path,
        width: int = 1280,
        height: int = 720
    ) -> ImageResult:
        """Generate image from prompt."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available/configured."""
        pass


class PollinationsProvider(ImageProvider):
    """
    Pollinations.ai - Free, no API key required.

    Uses DALL-E 3 compatible API. Simply encode prompt in URL.
    https://image.pollinations.ai/prompt/{encoded_prompt}
    """

    name = "pollinations"
    base_url = "https://image.pollinations.ai/prompt"

    def __init__(self):
        self.timeout = 120.0  # Image generation can be slow

    def is_available(self) -> bool:
        # Always available - no API key needed
        return True

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        width: int = 1280,
        height: int = 720
    ) -> ImageResult:
        try:
            import httpx

            # URL encode the prompt
            encoded_prompt = quote(prompt)

            # Build URL with size parameters
            url = f"{self.base_url}/{encoded_prompt}?width={width}&height={height}&nologo=true"

            output_path.parent.mkdir(parents=True, exist_ok=True)

            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    # Verify it's an image
                    content_type = response.headers.get("content-type", "")
                    if "image" in content_type or len(response.content) > 1000:
                        with open(output_path, "wb") as f:
                            f.write(response.content)

                        if output_path.exists() and output_path.stat().st_size > 0:
                            return ImageResult(
                                success=True,
                                file_path=output_path,
                                provider=self.name
                            )
                        else:
                            return ImageResult(
                                success=False,
                                provider=self.name,
                                error="Output file empty"
                            )
                    else:
                        return ImageResult(
                            success=False,
                            provider=self.name,
                            error=f"Invalid content type: {content_type}"
                        )
                else:
                    return ImageResult(
                        success=False,
                        provider=self.name,
                        error=f"HTTP {response.status_code}"
                    )

        except Exception as e:
            return ImageResult(
                success=False,
                provider=self.name,
                error=str(e)
            )


class StabilityProvider(ImageProvider):
    """
    Stability AI - Optional premium provider.

    Requires API key. Free tier: ~25 images/month.
    """

    name = "stability"

    def __init__(self):
        self.api_key = os.getenv("STABILITY_API_KEY")
        self.api_host = "https://api.stability.ai"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        width: int = 1280,
        height: int = 720
    ) -> ImageResult:
        if not self.is_available():
            return ImageResult(
                success=False,
                provider=self.name,
                error="STABILITY_API_KEY not set"
            )

        try:
            import httpx

            # Stability AI requires specific dimensions (multiples of 64)
            width = (width // 64) * 64
            height = (height // 64) * 64

            # Use SDXL 1.0
            engine_id = "stable-diffusion-xl-1024-v1-0"

            output_path.parent.mkdir(parents=True, exist_ok=True)

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.api_host}/v1/generation/{engine_id}/text-to-image",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "image/png"
                    },
                    json={
                        "text_prompts": [{"text": prompt, "weight": 1}],
                        "cfg_scale": 7,
                        "width": min(width, 1024),
                        "height": min(height, 1024),
                        "samples": 1,
                        "steps": 30
                    }
                )

                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)

                    return ImageResult(
                        success=True,
                        file_path=output_path,
                        provider=self.name
                    )
                else:
                    return ImageResult(
                        success=False,
                        provider=self.name,
                        error=f"API error {response.status_code}: {response.text[:200]}"
                    )

        except Exception as e:
            return ImageResult(
                success=False,
                provider=self.name,
                error=str(e)
            )


class PlaceholderProvider(ImageProvider):
    """
    Placeholder - Local PIL-based fallback.

    Always works. Generates a text-based thumbnail when all APIs fail.
    """

    name = "placeholder"

    # Color schemes for different topics
    COLOR_SCHEMES = {
        "default": {"bg": (41, 128, 185), "text": (255, 255, 255)},  # Blue
        "electrical": {"bg": (241, 196, 15), "text": (0, 0, 0)},     # Yellow/warning
        "motor": {"bg": (46, 204, 113), "text": (255, 255, 255)},    # Green
        "plc": {"bg": (155, 89, 182), "text": (255, 255, 255)},      # Purple
        "safety": {"bg": (231, 76, 60), "text": (255, 255, 255)},    # Red
        "industrial": {"bg": (52, 73, 94), "text": (255, 255, 255)}, # Dark blue
    }

    def is_available(self) -> bool:
        try:
            from PIL import Image, ImageDraw, ImageFont
            return True
        except ImportError:
            return False

    def _detect_topic(self, prompt: str) -> str:
        """Detect topic from prompt for color selection."""
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["electric", "wire", "voltage", "circuit"]):
            return "electrical"
        if any(w in prompt_lower for w in ["motor", "drive", "vfd"]):
            return "motor"
        if any(w in prompt_lower for w in ["plc", "ladder", "automation", "control"]):
            return "plc"
        if any(w in prompt_lower for w in ["safety", "hazard", "danger", "lockout"]):
            return "safety"
        if any(w in prompt_lower for w in ["factory", "industrial", "machine"]):
            return "industrial"
        return "default"

    def _wrap_text(self, text: str, max_chars: int = 30) -> list:
        """Wrap text to fit within image."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= max_chars:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(" ".join(current_line))

        return lines[:4]  # Max 4 lines

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        width: int = 1280,
        height: int = 720
    ) -> ImageResult:
        if not self.is_available():
            return ImageResult(
                success=False,
                provider=self.name,
                error="Pillow not installed. Run: pip install pillow"
            )

        try:
            from PIL import Image, ImageDraw, ImageFont

            # Get color scheme based on topic
            topic = self._detect_topic(prompt)
            colors = self.COLOR_SCHEMES[topic]

            # Create image
            img = Image.new("RGB", (width, height), colors["bg"])
            draw = ImageDraw.Draw(img)

            # Try to use a nice font, fallback to default
            try:
                # Try common system fonts
                font_size = width // 20
                font_paths = [
                    "C:/Windows/Fonts/arial.ttf",
                    "C:/Windows/Fonts/segoeui.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/System/Library/Fonts/Helvetica.ttc"
                ]
                font = None
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, font_size)
                        break
                if font is None:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()

            # Wrap and draw text
            lines = self._wrap_text(prompt, max_chars=35)
            line_height = height // 8
            start_y = (height - len(lines) * line_height) // 2

            for i, line in enumerate(lines):
                # Get text bounding box for centering
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = start_y + i * line_height
                draw.text((x, y), line, fill=colors["text"], font=font)

            # Add subtle border
            border_width = 10
            for i in range(border_width):
                alpha = int(255 * (1 - i / border_width) * 0.3)
                border_color = tuple(max(0, c - 30) for c in colors["bg"])
                draw.rectangle(
                    [i, i, width - i - 1, height - i - 1],
                    outline=border_color
                )

            # Add "RIVET PRO" watermark
            try:
                small_font = ImageFont.truetype(font_paths[0], width // 40) if font_paths else ImageFont.load_default()
            except Exception:
                small_font = ImageFont.load_default()

            watermark = "RIVET PRO"
            wm_bbox = draw.textbbox((0, 0), watermark, font=small_font)
            wm_width = wm_bbox[2] - wm_bbox[0]
            draw.text(
                (width - wm_width - 20, height - 40),
                watermark,
                fill=(*colors["text"][:3], 180) if len(colors["text"]) >= 3 else colors["text"],
                font=small_font
            )

            # Save
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, "PNG", quality=95)

            return ImageResult(
                success=True,
                file_path=output_path,
                provider=self.name
            )

        except Exception as e:
            return ImageResult(
                success=False,
                provider=self.name,
                error=str(e)
            )


# Provider registry
IMAGE_PROVIDERS = {
    "pollinations": PollinationsProvider,
    "stability": StabilityProvider,
    "placeholder": PlaceholderProvider,
}


def get_image_provider(name: str) -> ImageProvider:
    """Get an image provider instance by name."""
    provider_class = IMAGE_PROVIDERS.get(name)
    if provider_class is None:
        raise ValueError(f"Unknown image provider: {name}")
    return provider_class()


def get_available_image_providers() -> list:
    """Get list of available image provider names."""
    available = []
    for name, provider_class in IMAGE_PROVIDERS.items():
        try:
            provider = provider_class()
            if provider.is_available():
                available.append(name)
        except Exception:
            pass
    return available
