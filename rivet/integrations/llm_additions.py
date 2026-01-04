"""
Phase 2 additions to LLM Router - text-only generation support.

Extends LLMRouter with text-only generation capabilities for SME prompts.
"""

from enum import Enum
from dataclasses import dataclass


class ModelCapability(Enum):
    """LLM capability tiers for cost optimization."""
    SIMPLE = "simple"  # Classification, basic Q&A (gpt-3.5-turbo)
    MODERATE = "moderate"  # Reasoning, vendor SME (gpt-4o-mini, claude-haiku)
    COMPLEX = "complex"  # Complex reasoning, research (gpt-4o, claude-opus)
    CODING = "coding"  # Code generation (gpt-4-turbo)
    RESEARCH = "research"  # Deep research (claude-opus)


@dataclass
class LLMResponse:
    """Structured response from LLM generation."""
    text: str  # Generated text
    cost_usd: float  # Estimated cost
    model: str  # Model used
    provider: str  # Provider used


# Text-only model configurations (no vision)
TEXT_MODEL_CONFIGS = {
    ModelCapability.SIMPLE: [
        ("openai", "gpt-3.5-turbo", 0.0005, 0.0015),  # Cheapest
        ("groq", "llama-3.3-70b-versatile", 0.0, 0.0),  # Free fallback
    ],
    ModelCapability.MODERATE: [
        ("openai", "gpt-4o-mini", 0.00015, 0.0006),
        ("claude", "claude-3-haiku-20240307", 0.00025, 0.00125),
        ("gemini", "gemini-1.5-flash", 0.000075, 0.0003),
    ],
    ModelCapability.COMPLEX: [
        ("claude", "claude-3-5-sonnet-20241022", 0.003, 0.015),
        ("openai", "gpt-4o", 0.005, 0.015),
        ("gemini", "gemini-1.5-pro", 0.00125, 0.005),
    ],
}

