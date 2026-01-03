"""
Multi-LLM Provider Router

Provides unified interface to multiple LLM providers for OCR and troubleshooting.
Cost-optimized: tries cheaper providers first.
"""

import os
import base64
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


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
        model="llama-3.2-90b-vision-preview",
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


class LLMRouter:
    """
    Routes requests to appropriate LLM providers.

    Tries providers in cost order until one succeeds with acceptable confidence.
    """

    def __init__(self):
        """Initialize with available API keys."""
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

        # Lazy-loaded clients
        self._groq_client = None
        self._gemini_model = None
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

    def _get_gemini_model(self, model_name: str):
        """Lazy-load Gemini model."""
        if self.gemini_key:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            return genai.GenerativeModel(model_name)
        return None

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
            genai_model = self._get_gemini_model(model)
            if not genai_model:
                raise ValueError("Gemini model not available")

            response = await genai_model.generate_content_async([
                prompt,
                {"mime_type": "image/jpeg", "data": image_b64}
            ])
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
