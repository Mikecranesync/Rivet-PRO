"""
Media Assets Service for YCB

Unified interface for media generation with intelligent fallback.
Automatically selects providers based on availability and quota.

Voice Priority: ElevenLabs → Edge TTS → Piper
Image Priority: Pollinations → Stability → Placeholder
"""

import logging
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from .quota_tracker import QuotaTracker, get_tracker
from .voice_providers import (
    VoiceProvider,
    VoiceResult,
    ElevenLabsProvider,
    EdgeTTSProvider,
    PiperProvider,
    get_voice_provider,
    get_available_voice_providers
)
from .image_providers import (
    ImageProvider,
    ImageResult,
    PollinationsProvider,
    StabilityProvider,
    PlaceholderProvider,
    get_image_provider,
    get_available_image_providers
)

logger = logging.getLogger(__name__)


@dataclass
class MediaResult:
    """Result from media generation."""
    success: bool
    file_path: Optional[Path] = None
    provider_used: str = ""
    providers_tried: List[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.providers_tried is None:
            self.providers_tried = []


class MediaAssetsService:
    """
    Unified media generation with automatic fallback.

    Manages voice and image generation across multiple providers,
    tracking quotas and selecting the best available option.

    Usage:
        service = MediaAssetsService()

        # Generate voice narration
        result = await service.generate_voice(
            "Hello world, this is a test.",
            Path("./output/narration.mp3")
        )

        # Generate thumbnail
        result = await service.generate_thumbnail(
            "A professional industrial control panel",
            Path("./output/thumbnail.png")
        )
    """

    # Provider priority chains
    VOICE_PRIORITY = ["elevenlabs", "edge_tts", "piper"]
    IMAGE_PRIORITY = ["pollinations", "stability", "placeholder"]

    def __init__(self, quota_tracker: Optional[QuotaTracker] = None):
        """
        Initialize media assets service.

        Args:
            quota_tracker: Optional custom quota tracker. Uses global if not provided.
        """
        self.quota_tracker = quota_tracker or get_tracker()

        # Initialize providers
        self._voice_providers = {
            "elevenlabs": ElevenLabsProvider(),
            "edge_tts": EdgeTTSProvider(),
            "piper": PiperProvider(),
        }

        self._image_providers = {
            "pollinations": PollinationsProvider(),
            "stability": StabilityProvider(),
            "placeholder": PlaceholderProvider(),
        }

        logger.info(f"MediaAssetsService initialized")
        logger.info(f"  Voice providers: {self.get_available_voice_providers()}")
        logger.info(f"  Image providers: {self.get_available_image_providers()}")

    def get_available_voice_providers(self) -> List[str]:
        """Get list of available voice providers."""
        return [
            name for name, provider in self._voice_providers.items()
            if provider.is_available()
        ]

    def get_available_image_providers(self) -> List[str]:
        """Get list of available image providers."""
        return [
            name for name, provider in self._image_providers.items()
            if provider.is_available()
        ]

    def _should_use_provider(self, provider_name: str) -> bool:
        """
        Check if provider should be used (available and under quota).

        Args:
            provider_name: Name of the provider

        Returns:
            True if provider should be tried
        """
        # Check quota
        if self.quota_tracker.is_quota_exceeded(provider_name):
            logger.info(f"Skipping {provider_name}: quota exceeded")
            return False

        # Check availability
        voice_provider = self._voice_providers.get(provider_name)
        if voice_provider and not voice_provider.is_available():
            return False

        image_provider = self._image_providers.get(provider_name)
        if image_provider and not image_provider.is_available():
            return False

        return True

    async def generate_voice(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> MediaResult:
        """
        Generate voice audio from text with automatic fallback.

        Tries providers in priority order: ElevenLabs → Edge TTS → Piper

        Args:
            text: Text to convert to speech
            output_path: Where to save the audio file
            voice_id: Optional voice ID (provider-specific)
            preferred_provider: Optional preferred provider to try first

        Returns:
            MediaResult with success status and file path
        """
        providers_tried = []
        last_error = None

        # Build priority list
        priority = list(self.VOICE_PRIORITY)
        if preferred_provider and preferred_provider in priority:
            priority.remove(preferred_provider)
            priority.insert(0, preferred_provider)

        for provider_name in priority:
            if not self._should_use_provider(provider_name):
                continue

            provider = self._voice_providers.get(provider_name)
            if not provider:
                continue

            providers_tried.append(provider_name)
            logger.info(f"Trying voice provider: {provider_name}")

            try:
                result = await provider.generate(text, output_path, voice_id)

                if result.success:
                    # Track usage
                    self.quota_tracker.add_usage(provider_name, result.chars_used)

                    logger.info(f"Voice generated successfully with {provider_name}")
                    return MediaResult(
                        success=True,
                        file_path=result.file_path,
                        provider_used=provider_name,
                        providers_tried=providers_tried
                    )
                else:
                    last_error = result.error
                    logger.warning(f"{provider_name} failed: {result.error}")

            except Exception as e:
                last_error = str(e)
                logger.error(f"{provider_name} exception: {e}")

        # All providers failed
        return MediaResult(
            success=False,
            providers_tried=providers_tried,
            error=f"All voice providers failed. Last error: {last_error}"
        )

    async def generate_thumbnail(
        self,
        prompt: str,
        output_path: Path,
        width: int = 1280,
        height: int = 720,
        preferred_provider: Optional[str] = None
    ) -> MediaResult:
        """
        Generate thumbnail image from prompt with automatic fallback.

        Tries providers in priority order: Pollinations → Stability → Placeholder

        Args:
            prompt: Image generation prompt
            output_path: Where to save the image
            width: Image width (default 1280)
            height: Image height (default 720)
            preferred_provider: Optional preferred provider to try first

        Returns:
            MediaResult with success status and file path
        """
        providers_tried = []
        last_error = None

        # Build priority list
        priority = list(self.IMAGE_PRIORITY)
        if preferred_provider and preferred_provider in priority:
            priority.remove(preferred_provider)
            priority.insert(0, preferred_provider)

        for provider_name in priority:
            if not self._should_use_provider(provider_name):
                continue

            provider = self._image_providers.get(provider_name)
            if not provider:
                continue

            providers_tried.append(provider_name)
            logger.info(f"Trying image provider: {provider_name}")

            try:
                result = await provider.generate(prompt, output_path, width, height)

                if result.success:
                    # Track usage (1 image = 1 unit)
                    self.quota_tracker.add_usage(provider_name, 1)

                    logger.info(f"Thumbnail generated successfully with {provider_name}")
                    return MediaResult(
                        success=True,
                        file_path=result.file_path,
                        provider_used=provider_name,
                        providers_tried=providers_tried
                    )
                else:
                    last_error = result.error
                    logger.warning(f"{provider_name} failed: {result.error}")

            except Exception as e:
                last_error = str(e)
                logger.error(f"{provider_name} exception: {e}")

        # All providers failed
        return MediaResult(
            success=False,
            providers_tried=providers_tried,
            error=f"All image providers failed. Last error: {last_error}"
        )

    def get_quota_status(self) -> dict:
        """
        Get current quota status for all providers.

        Returns:
            Dict with provider -> quota info
        """
        return self.quota_tracker.get_all_usage()

    def __str__(self) -> str:
        """Return human-readable status."""
        voice_available = self.get_available_voice_providers()
        image_available = self.get_available_image_providers()

        lines = [
            "MediaAssetsService Status:",
            f"  Voice providers: {', '.join(voice_available) or 'none'}",
            f"  Image providers: {', '.join(image_available) or 'none'}",
            "",
            str(self.quota_tracker)
        ]
        return "\n".join(lines)


# Convenience function for quick access
_service: Optional[MediaAssetsService] = None


def get_media_service() -> MediaAssetsService:
    """Get or create global media assets service instance."""
    global _service
    if _service is None:
        _service = MediaAssetsService()
    return _service
