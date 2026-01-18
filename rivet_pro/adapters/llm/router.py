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
from typing import Optional, Dict, Any, List, Tuple, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from contextlib import contextmanager
import asyncio

logger = logging.getLogger(__name__)

# Langfuse tracing (optional - graceful fallback if not configured)
_langfuse = None

def _get_langfuse():
    """Lazy-load Langfuse client."""
    global _langfuse
    if _langfuse is None:
        try:
            from langfuse import Langfuse
            from rivet_pro.config.settings import settings
            if settings.langfuse_public_key and settings.langfuse_secret_key:
                _langfuse = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_base_url or "https://us.cloud.langfuse.com",
                )
                logger.info("Langfuse tracing enabled")
            else:
                _langfuse = False  # Explicitly disabled
                logger.debug("Langfuse not configured (no keys)")
        except Exception as e:
            logger.warning(f"Langfuse init failed: {e}")
            _langfuse = False
    return _langfuse if _langfuse else None


@contextmanager
def langfuse_generation(name: str, model: str, user_id: Optional[str] = None, metadata: Optional[Dict] = None):
    """Context manager for Langfuse generation tracing."""
    lf = _get_langfuse()
    if not lf:
        yield None
        return

    trace = lf.trace(name=name, user_id=user_id, metadata=metadata or {})
    generation = trace.generation(name=name, model=model, metadata=metadata or {})
    try:
        yield generation
    finally:
        generation.end()
        lf.flush()


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
# NOTE: Groq first (Gemini API key currently leaked - 403 errors waste 1-2s)
VISION_PROVIDER_CHAIN: List[ProviderConfig] = [
    ProviderConfig(
        name="groq",
        model="meta-llama/llama-4-scout-17b-16e-instruct",  # Llama 4 Scout - 460 tokens/s, FAST
        cost_per_1k_input=0.00011,  # $0.11 per 1M
        cost_per_1k_output=0.00034,
        max_image_size_mb=20,
    ),
    ProviderConfig(
        name="gemini",
        model="gemini-2.5-flash",  # Updated to Gemini 2.5 (1.5 deprecated)
        cost_per_1k_input=0.000075,  # $0.075 per 1M - CHEAPEST (when key works)
        cost_per_1k_output=0.0003,
        max_image_size_mb=20,
    ),
    ProviderConfig(
        name="openai",
        model="gpt-4o-mini",
        cost_per_1k_input=0.00015,  # $0.15 per 1M
        cost_per_1k_output=0.0006,
        max_image_size_mb=20,
    ),
    ProviderConfig(
        name="claude",
        model="claude-3-haiku-20240307",
        cost_per_1k_input=0.00025,  # $0.25 per 1M
        cost_per_1k_output=0.00125,
        max_image_size_mb=20,
    ),
    ProviderConfig(
        name="groq",
        model="meta-llama/llama-4-maverick-17b-128e-instruct",  # Llama 4 Maverick - better vision
        cost_per_1k_input=0.00050,  # $0.50 per 1M
        cost_per_1k_output=0.00077,
        max_image_size_mb=20,
    ),
    ProviderConfig(
        name="gemini",
        model="gemini-2.5-pro",  # Updated to Gemini 2.5 (1.5 deprecated)
        cost_per_1k_input=0.00125,  # $1.25 per 1M
        cost_per_1k_output=0.005,
        max_image_size_mb=20,
    ),
    ProviderConfig(
        name="openai",
        model="gpt-4o",
        cost_per_1k_input=0.005,  # $5.00 per 1M - MOST EXPENSIVE
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
        from rivet_pro.config.settings import settings

        self.groq_key = settings.groq_api_key
        self.gemini_key = settings.google_api_key  # Google API key for Gemini
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
        user_id: Optional[str] = None,
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
        start_time = datetime.utcnow()

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
            # Calculate cost (Groq doesn't return usage tokens, estimate from response)
            tokens_est = len(prompt.split()) + len(text.split())
            cost = (tokens_est / 1000) * provider_config.cost_per_1k_input

        elif provider == "gemini":
            client = self._get_gemini_client()
            if not client:
                raise ValueError("Gemini client not available")

            # Google GenAI SDK format
            from google import genai
            from google.genai import types

            response = await client.aio.models.generate_content(
                model=model,
                contents=types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),  # Add text= parameter name
                        types.Part.from_bytes(
                            data=base64.b64decode(image_b64),
                            mime_type="image/jpeg"
                        )
                    ]
                )
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

        # Log to Langfuse for cost tracking
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        lf = _get_langfuse()
        if lf:
            try:
                trace = lf.trace(
                    name="vision_ocr",
                    user_id=user_id,
                    metadata={"provider": provider, "model": model},
                )
                trace.generation(
                    name="ocr_extraction",
                    model=model,
                    input=prompt[:500],  # Truncate for logging
                    output=text[:1000] if text else None,
                    usage={
                        "input_tokens": len(prompt.split()),
                        "output_tokens": len(text.split()) if text else 0,
                    },
                    metadata={
                        "provider": provider,
                        "cost_usd": cost,
                        "duration_ms": duration_ms,
                        "image_size_kb": len(image_bytes) / 1024,
                    },
                )
                lf.flush()
                logger.debug(f"Langfuse: logged vision call | provider={provider} | cost=${cost:.4f}")
            except Exception as e:
                logger.warning(f"Langfuse logging failed: {e}")

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

    async def generate_stream(
        self,
        prompt: str,
        capability: ModelCapability = ModelCapability.MODERATE,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Generate text-only response with streaming.

        Yields tokens as they arrive for real-time response feel.
        Falls back through model chain if primary fails.

        Args:
            prompt: User prompt
            capability: Required capability tier
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system_prompt: Optional system prompt for response style

        Yields:
            str: Individual tokens or chunks as they arrive

        Raises:
            Exception: If all models in capability tier fail

        Example:
            >>> router = LLMRouter()
            >>> async for token in router.generate_stream(
            ...     "Explain F0002 fault on Siemens S7-1200",
            ...     capability=ModelCapability.MODERATE
            ... ):
            ...     print(token, end="", flush=True)
        """
        # Get models for this capability tier
        models = TEXT_GENERATION_MODELS.get(capability, [])

        if not models:
            raise ValueError(f"No models configured for capability {capability}")

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Try each model in order (cheapest first)
        last_error = None

        for provider, model, cost_in, cost_out in models:
            try:
                logger.info(f"[LLM Router] Streaming from {provider}/{model} for {capability.value}")

                if provider == "groq":
                    client = self._get_groq_client()
                    if not client:
                        logger.warning(f"[LLM Router] Groq client not available")
                        continue

                    # Groq streaming
                    stream = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stream=True,
                    )

                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content

                    logger.info(f"[LLM Router] Stream complete: {provider}/{model}")
                    return

                elif provider == "openai":
                    client = self._get_openai_client()
                    if not client:
                        logger.warning(f"[LLM Router] OpenAI client not available")
                        continue

                    # OpenAI streaming
                    stream = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stream=True,
                    )

                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content

                    logger.info(f"[LLM Router] Stream complete: {provider}/{model}")
                    return

                elif provider == "claude":
                    client = self._get_anthropic_client()
                    if not client:
                        logger.warning(f"[LLM Router] Anthropic client not available")
                        continue

                    # Anthropic streaming
                    with client.messages.stream(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=messages,
                    ) as stream:
                        for text in stream.text_stream:
                            yield text

                    logger.info(f"[LLM Router] Stream complete: {provider}/{model}")
                    return

            except Exception as e:
                logger.warning(f"[LLM Router] {provider}/{model} streaming failed: {e}")
                last_error = e
                continue  # Try next model

        # All models failed
        raise Exception(
            f"All models failed for capability {capability} streaming. Last error: {last_error}"
        )


# Module-level singleton
_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """Get or create the LLM router singleton."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
