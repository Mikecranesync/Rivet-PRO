"""
YCB Services Module

Media asset generation with intelligent fallback providers.

Voice Priority Chain:
    1. ElevenLabs (premium, quota-limited)
    2. Edge TTS (free, Microsoft)
    3. Piper TTS (local, offline)

Image Priority Chain:
    1. Pollinations.ai (free, no API key)
    2. Stability AI (optional, if API key provided)
    3. Placeholder (local PIL, always works)
"""

from .media_assets import MediaAssetsService, MediaResult, get_media_service
from .quota_tracker import QuotaTracker, get_tracker
from .voice_providers import (
    VoiceProvider,
    VoiceResult,
    ElevenLabsProvider,
    EdgeTTSProvider,
    PiperProvider,
    get_voice_provider,
    get_available_voice_providers,
)
from .image_providers import (
    ImageProvider,
    ImageResult,
    PollinationsProvider,
    StabilityProvider,
    PlaceholderProvider,
    get_image_provider,
    get_available_image_providers,
)

__all__ = [
    # Main service
    "MediaAssetsService",
    "MediaResult",
    "get_media_service",
    # Quota tracking
    "QuotaTracker",
    "get_tracker",
    # Voice
    "VoiceProvider",
    "VoiceResult",
    "ElevenLabsProvider",
    "EdgeTTSProvider",
    "PiperProvider",
    "get_voice_provider",
    "get_available_voice_providers",
    # Image
    "ImageProvider",
    "ImageResult",
    "PollinationsProvider",
    "StabilityProvider",
    "PlaceholderProvider",
    "get_image_provider",
    "get_available_image_providers",
]
