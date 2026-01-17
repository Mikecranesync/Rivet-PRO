"""
Voice Generation Providers for YCB

Implements multiple TTS providers with fallback support:
1. ElevenLabs (premium, quota-limited)
2. Edge TTS (free, Microsoft)
3. Piper TTS (local, offline)
"""

import os
import asyncio
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class VoiceResult:
    """Result from voice generation."""
    success: bool
    file_path: Optional[Path] = None
    provider: str = ""
    chars_used: int = 0
    error: Optional[str] = None


class VoiceProvider(ABC):
    """Base class for voice providers."""

    name: str = "base"

    @abstractmethod
    async def generate(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None
    ) -> VoiceResult:
        """Generate voice audio from text."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available/configured."""
        pass


class ElevenLabsProvider(VoiceProvider):
    """
    ElevenLabs TTS - Premium quality, quota-limited.

    Free tier: ~10,000 chars/month
    """

    name = "elevenlabs"

    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.default_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None
    ) -> VoiceResult:
        if not self.is_available():
            return VoiceResult(
                success=False,
                provider=self.name,
                error="ELEVENLABS_API_KEY not set"
            )

        try:
            import httpx

            voice = voice_id or self.default_voice_id

            # Truncate text if too long
            if len(text) > 5000:
                text = text[:5000] + "..."

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                    headers={
                        "xi-api-key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75
                        }
                    }
                )

                if response.status_code == 200:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(response.content)

                    return VoiceResult(
                        success=True,
                        file_path=output_path,
                        provider=self.name,
                        chars_used=len(text)
                    )
                else:
                    return VoiceResult(
                        success=False,
                        provider=self.name,
                        chars_used=0,
                        error=f"API error {response.status_code}: {response.text[:200]}"
                    )

        except Exception as e:
            return VoiceResult(
                success=False,
                provider=self.name,
                error=str(e)
            )


class EdgeTTSProvider(VoiceProvider):
    """
    Microsoft Edge TTS - Free, no API key required.

    Uses the edge-tts package which interfaces with Microsoft's
    free text-to-speech service.
    """

    name = "edge_tts"

    # Quality voices for different use cases
    VOICES = {
        "default": "en-US-AriaNeural",
        "male": "en-US-GuyNeural",
        "female": "en-US-JennyNeural",
        "narrator": "en-US-ChristopherNeural",
        "friendly": "en-US-SaraNeural"
    }

    def __init__(self):
        self.default_voice = os.getenv("EDGE_TTS_VOICE", self.VOICES["default"])

    def is_available(self) -> bool:
        try:
            import edge_tts
            return True
        except ImportError:
            return False

    async def generate(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None
    ) -> VoiceResult:
        if not self.is_available():
            return VoiceResult(
                success=False,
                provider=self.name,
                error="edge-tts package not installed. Run: pip install edge-tts"
            )

        try:
            import edge_tts

            voice = voice_id or self.default_voice
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate speech
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))

            if output_path.exists() and output_path.stat().st_size > 0:
                return VoiceResult(
                    success=True,
                    file_path=output_path,
                    provider=self.name,
                    chars_used=len(text)
                )
            else:
                return VoiceResult(
                    success=False,
                    provider=self.name,
                    error="Output file empty or not created"
                )

        except Exception as e:
            return VoiceResult(
                success=False,
                provider=self.name,
                error=str(e)
            )


class PiperProvider(VoiceProvider):
    """
    Piper TTS - Local, offline, unlimited.

    Runs entirely locally, no API calls, no limits.
    Requires: pip install piper-tts
    """

    name = "piper"

    # Quality models (auto-downloaded on first use)
    MODELS = {
        "default": "en_US-lessac-medium",
        "high_quality": "en_US-lessac-high",
        "fast": "en_US-lessac-low"
    }

    def __init__(self):
        self.model = os.getenv("PIPER_MODEL", self.MODELS["default"])
        self._piper_available = None

    def is_available(self) -> bool:
        if self._piper_available is not None:
            return self._piper_available

        try:
            # Check if piper is installed
            import subprocess
            result = subprocess.run(
                ["piper", "--help"],
                capture_output=True,
                timeout=5
            )
            self._piper_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Try Python package import
            try:
                from piper import PiperVoice
                self._piper_available = True
            except ImportError:
                self._piper_available = False

        return self._piper_available

    async def generate(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None
    ) -> VoiceResult:
        if not self.is_available():
            return VoiceResult(
                success=False,
                provider=self.name,
                error="Piper TTS not installed. Run: pip install piper-tts"
            )

        try:
            import subprocess

            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Use command-line piper
            process = await asyncio.create_subprocess_exec(
                "piper",
                "--model", self.model,
                "--output_file", str(output_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate(input=text.encode())

            if process.returncode == 0 and output_path.exists():
                return VoiceResult(
                    success=True,
                    file_path=output_path,
                    provider=self.name,
                    chars_used=len(text)
                )
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                return VoiceResult(
                    success=False,
                    provider=self.name,
                    error=error_msg[:200]
                )

        except Exception as e:
            return VoiceResult(
                success=False,
                provider=self.name,
                error=str(e)
            )


# Provider registry
VOICE_PROVIDERS = {
    "elevenlabs": ElevenLabsProvider,
    "edge_tts": EdgeTTSProvider,
    "piper": PiperProvider,
}


def get_voice_provider(name: str) -> VoiceProvider:
    """Get a voice provider instance by name."""
    provider_class = VOICE_PROVIDERS.get(name)
    if provider_class is None:
        raise ValueError(f"Unknown voice provider: {name}")
    return provider_class()


def get_available_voice_providers() -> list:
    """Get list of available voice provider names."""
    available = []
    for name, provider_class in VOICE_PROVIDERS.items():
        try:
            provider = provider_class()
            if provider.is_available():
                available.append(name)
        except Exception:
            pass
    return available
