"""
LLM Adapter Layer - Multi-provider LLM routing

Exports:
- LLMRouter: Main router class
- get_llm_router: Singleton access
- ModelCapability: Capability tiers
- ProviderConfig: Provider configuration
- VISION_PROVIDER_CHAIN: Vision providers in cost order
"""

from .router import (
    LLMRouter,
    get_llm_router,
    ModelCapability,
    ProviderConfig,
    LLMResponse,
    VISION_PROVIDER_CHAIN,
    TEXT_GENERATION_MODELS,
)

__all__ = [
    "LLMRouter",
    "get_llm_router",
    "ModelCapability",
    "ProviderConfig",
    "LLMResponse",
    "VISION_PROVIDER_CHAIN",
    "TEXT_GENERATION_MODELS",
]
