"""
Multi-LLM Provider Router

Provides unified interface to multiple LLM providers for OCR and troubleshooting.
Cost-optimized: tries cheaper providers first.

Extracted from rivet/integrations/llm.py - Production-ready
"""

import os
import base64
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """LLM capability tiers for cost optimization."""
    SIMPLE = "simple"      # gpt-3.5-turbo, simple classification/routing
    MODERATE = "moderate"  # gpt-4o-mini, claude-haiku - reasoning tasks
    COMPLEX = "complex"    # gpt-4o, claude-sonnet - complex troubleshooting
    CODING = "coding"      # Code generation/analysis
    RESEARCH = "research"  # Deep research tasks


@dataclass
class LLMResponse:
    """Structured response from text generation."""
    text: str
    cost_usd: float
    model: str
    provider: str


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    model: str
    cost_per_1k_input: float  # USD per 1K input tokens
    cost_per_1k_output: float  # USD per 1K output tokens
    supports_vision: bool = True
    max_image_size_mb: int = 20


# Cost-optimized provider chain for vision tasks
VISION_PROVIDER_CHAIN: List[ProviderConfig] = [
    ProviderConfig(
        name="groq",
        model="llama-3.2-11b-vision-preview",  # Updated: 90b deprecated
        cost_per_1k_input=0.0,  # Currently free
        cost_per_1k_output=0.0,
        max_image_size_mb=20,
    ),
    ProviderConfig(
        name="gemini",
        model="gemini-1.5-flash",
        cost_per_1k_input=0.000075,  # $0.075 per 1M
        cost_per_1k_output=0.0003,
        max_image_size_mb=20,
    ),
    ProviderConfig(
        name="gemini",
        model="gemini-1.5-pro",
        cost_per_1k_input=0.00125,
        cost_per_1k_output=0.005,
        max_image_size_mb=20,
    ),
    ProviderConfig(
        name="claude",
        model="claude-3-haiku-20240307",
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        max_image_size_mb=20,
    ),
    ProviderConfig(
        name="openai",
        model="gpt-4o-mini",
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        max_image_size_mb=20,
    ),
    ProviderConfig(
        name="openai",
        model="gpt-4o",
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        max_image_size_mb=20,
    ),
]


# Text generation model registry by capability tier
# Each tier lists models from cheapest to most expensive
TEXT_GENERATION_MODELS: Dict[ModelCapability, List[Tuple[str, str, float, float]]] = {
    ModelCapability.SIMPLE: [
        ("groq", "llama-3.3-70b-versatile", 0.0, 0.0),  # Free
        ("openai", "gpt-3.5-turbo", 0.0005, 0.0015),
    ],
    ModelCapability.MODERATE: [
        ("groq", "llama-3.3-70b-versatile", 0.0, 0.0),  # Free
        ("openai", "gpt-4o-mini", 0.00015, 0.0006),
        ("claude", "claude-3-haiku-20240307", 0.00025, 0.00125),
    ],
    ModelCapability.COMPLEX: [
        ("claude", "claude-3-5-sonnet-20241022", 0.003, 0.015),
        ("openai", "gpt-4o", 0.005, 0.015),
    ],
    ModelCapability.CODING: [
        ("openai", "gpt-4o", 0.005, 0.015),
        ("claude", "claude-3-5-sonnet-20241022", 0.003, 0.015),
    ],
    ModelCapability.RESEARCH: [
        ("claude", "claude-3-5-sonnet-20241022", 0.003, 0.015),
        ("openai", "gpt-4o", 0.005, 0.015),
    ],
}


class LLMRouter:
    """
    Routes requests to appropriate LLM providers.

    Tries providers in cost order until one succeeds with acceptable confidence.
    """

    def __init__(self):
        """Initialize with available API keys."""
        from rivet_pro.config.settings import get_settings

        settings = get_settings()

        self.groq_key = settings.groq_api_key
        self.gemini_key = settings.gemini_api_key
        self.anthropic_key = settings.anthropic_api_key
        self.openai_key = settings.openai_api_key

        # Lazy-loaded clients
        self._groq_client = None
        self._gemini_client = None
        self._anthropic_client = None
        self._openai_client = None

    def get_available_providers(self) -> List[str]:
        """Return list of providers with configured API keys."""
        available = []
        if self.groq_key:
            available.append("groq")
        if self.gemini_key:
            available.append("gemini")
        if self.anthropic_key:
            available.append("claude")
        if self.openai_key:
            available.append("openai")
        return available

    def _get_groq_client(self):
        """Lazy-load Groq client."""
        if self._groq_client is None and self.groq_key:
            from groq import Groq
            self._groq_client = Groq(api_key=self.groq_key)
        return self._groq_client

    def _get_gemini_client(self):
        """Lazy-load Gemini client."""
        if self._gemini_client is None and self.gemini_key:
            from google import genai
            self._gemini_client = genai.Client(api_key=self.gemini_key)
        return self._gemini_client

    def _get_anthropic_client(self):
        """Lazy-load Anthropic client."""
        if self._anthropic_client is None and self.anthropic_key:
            from anthropic import Anthropic
            self._anthropic_client = Anthropic(api_key=self.anthropic_key)
        return self._anthropic_client

    def _get_openai_client(self):
        """Lazy-load OpenAI client."""
        if self._openai_client is None and self.openai_key:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self.openai_key)
        return self._openai_client

    async def call_vision(
        self,
        provider_config: ProviderConfig,
        image_bytes: bytes,
        prompt: str,
        max_tokens: int = 1000,
    ) -> Tuple[str, float]:
        """
        Call a specific provider's vision API.

        Returns:
            Tuple of (response_text, estimated_cost_usd)

        Raises:
            Exception if the call fails
        """
        provider = provider_config.name
        model = provider_config.model

        # Encode image
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        if provider == "groq":
            client = self._get_groq_client()
            if not client:
                raise ValueError("Groq client not available")

            response = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                }],
                max_tokens=max_tokens,
            )
            text = response.choices[0].message.content
            # Groq is currently free
            cost = 0.0

        elif provider == "gemini":
            client = self._get_gemini_client()
            if not client:
                raise ValueError("Gemini client not available")

            response = await client.aio.models.generate_content(
                model=model,
                contents=[
                    prompt,
                    {"mime_type": "image/jpeg", "data": image_b64}
                ]
            )
            text = response.text
            # Estimate cost (rough)
            tokens_est = len(prompt.split()) + 500  # Input + output estimate
            cost = (tokens_est / 1000) * provider_config.cost_per_1k_input

        elif provider == "claude":
            client = self._get_anthropic_client()
            if not client:
                raise ValueError("Anthropic client not available")

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64,
                        }}
                    ]
                }]
            )
            text = response.content[0].text
            cost = (response.usage.input_tokens / 1000) * provider_config.cost_per_1k_input
            cost += (response.usage.output_tokens / 1000) * provider_config.cost_per_1k_output

        elif provider == "openai":
            client = self._get_openai_client()
            if not client:
                raise ValueError("OpenAI client not available")

            response = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                }],
                max_tokens=max_tokens,
            )
            text = response.choices[0].message.content
            cost = (response.usage.prompt_tokens / 1000) * provider_config.cost_per_1k_input
            cost += (response.usage.completion_tokens / 1000) * provider_config.cost_per_1k_output

        else:
            raise ValueError(f"Unknown provider: {provider}")

        return text, cost

    async def generate(
        self,
        prompt: str,
        capability: ModelCapability = ModelCapability.MODERATE,
        max_tokens: int = 1500,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Generate text-only response (no vision).

        Selects cheapest capable model based on capability tier.
        Falls back through model chain if primary fails.

        Args:
            prompt: User prompt
            capability: Required capability tier
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            LLMResponse with text, cost, model, provider

        Raises:
            Exception: If all models in capability tier fail

        Example:
            >>> router = LLMRouter()
            >>> response = await router.generate(
            ...     "Explain F0002 fault on Siemens S7-1200",
            ...     capability=ModelCapability.MODERATE
            ... )
            >>> print(f"Answer: {response.text}")
            >>> print(f"Cost: ${response.cost_usd:.4f}")
        """
        # Get models for this capability tier
        models = TEXT_GENERATION_MODELS.get(capability, [])

        if not models:
            raise ValueError(f"No models configured for capability {capability}")

        # Try each model in order (cheapest first)
        last_error = None

        for provider, model, cost_in, cost_out in models:
            try:
                logger.info(f"[LLM Router] Trying {provider}/{model} for {capability.value}")

                if provider == "groq":
                    client = self._get_groq_client()
                    if not client:
                        logger.warning(f"[LLM Router] Groq client not available")
                        continue

                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )

                    text = response.choices[0].message.content
                    cost = 0.0  # Groq is free

                    logger.info(f"[LLM Router] Success: {provider}/{model}, cost=${cost:.4f}")
                    return LLMResponse(
                        text=text,
                        cost_usd=cost,
                        model=model,
                        provider=provider
                    )

                elif provider == "openai":
                    client = self._get_openai_client()
                    if not client:
                        logger.warning(f"[LLM Router] OpenAI client not available")
                        continue

                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )

                    text = response.choices[0].message.content
                    cost = (response.usage.prompt_tokens / 1000) * cost_in
                    cost += (response.usage.completion_tokens / 1000) * cost_out

                    logger.info(f"[LLM Router] Success: {provider}/{model}, cost=${cost:.4f}")
                    return LLMResponse(
                        text=text,
                        cost_usd=cost,
                        model=model,
                        provider=provider
                    )

                elif provider == "claude":
                    client = self._get_anthropic_client()
                    if not client:
                        logger.warning(f"[LLM Router] Anthropic client not available")
                        continue

                    response = client.messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=[{"role": "user", "content": prompt}]
                    )

                    text = response.content[0].text
                    cost = (response.usage.input_tokens / 1000) * cost_in
                    cost += (response.usage.output_tokens / 1000) * cost_out

                    logger.info(f"[LLM Router] Success: {provider}/{model}, cost=${cost:.4f}")
                    return LLMResponse(
                        text=text,
                        cost_usd=cost,
                        model=model,
                        provider=provider
                    )

            except Exception as e:
                logger.warning(f"[LLM Router] {provider}/{model} failed: {e}")
                last_error = e
                continue  # Try next model

        # All models failed
        raise Exception(
            f"All models failed for capability {capability}. Last error: {last_error}"
        )

    def is_provider_available(self, provider_name: str) -> bool:
        """Check if a provider is configured."""
        return provider_name in self.get_available_providers()


# Module-level singleton
_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """Get or create the LLM router singleton."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
