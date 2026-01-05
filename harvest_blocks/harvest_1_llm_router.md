# HARVEST BLOCK 1: LLM Router Text Generation Support

**Priority:** CRITICAL (blocks all SME agents)
**Duration:** 30 minutes
**Source:** `agent_factory/llm/router.py` (lines 50-250)

---

## What This Adds

Adds text-generation support to the existing vision-only LLM router. Currently `llm.py` only supports `call_vision()`. This adds:

1. **ModelCapability enum** - Defines cost tiers (SIMPLE, MODERATE, COMPLEX, CODING, RESEARCH)
2. **LLMResponse dataclass** - Structured response with text, cost, model, provider
3. **TEXT_GENERATION_MODELS registry** - Maps capabilities to cheapest models
4. **generate() method** - Text-only generation with fallback chain

**Why critical:** All 7 SME agents (`rivet/prompts/sme/*.py`) need text generation to work.

---

## Target File

`rivet/integrations/llm.py`

**Current state:** Vision-only with `call_vision()` method
**After integration:** Vision + text generation

---

## Integration Instructions

### Step 1: Add Imports

At the top of `llm.py`, add `Enum` to imports:

```python
from enum import Enum  # ADD THIS
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
```

### Step 2: Add ModelCapability Enum

After imports, before `@dataclass class ProviderConfig`:

```python
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
```

### Step 3: Add Text Generation Model Registry

After `VISION_PROVIDER_CHAIN`, before `class LLMRouter`:

```python
# Text generation model registry by capability tier
# Each tier lists models from cheapest to most expensive
TEXT_GENERATION_MODELS: Dict[ModelCapability, List[Tuple[str, str, float, float]]] = {
    ModelCapability.SIMPLE: [
        ("groq", "llama-3.1-70b-versatile", 0.0, 0.0),  # Free
        ("openai", "gpt-3.5-turbo", 0.0005, 0.0015),
    ],
    ModelCapability.MODERATE: [
        ("groq", "llama-3.1-70b-versatile", 0.0, 0.0),  # Free
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
```

### Step 4: Add generate() Method to LLMRouter Class

Inside the `LLMRouter` class, after `call_vision()` method:

```python
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
```

---

## Validation

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO

# Test imports
python -c "from rivet.integrations.llm import LLMRouter, ModelCapability, LLMResponse; print('✅ Imports OK')"

# Test text generation (async)
python -c "
import asyncio
from rivet.integrations.llm import LLMRouter, ModelCapability

async def test():
    router = LLMRouter()
    response = await router.generate(
        'What is 2+2?',
        capability=ModelCapability.SIMPLE
    )
    print(f'✅ Text generation OK: {response.text[:50]}...')
    print(f'   Model: {response.model}, Cost: \${response.cost_usd:.4f}')

asyncio.run(test())
"
```

Expected output:
```
✅ Imports OK
✅ Text generation OK: 2+2 equals 4...
   Model: llama-3.1-70b-versatile, Cost: $0.0000
```

---

## Integration Notes

1. **Keeps existing vision support** - `call_vision()` method unchanged
2. **Cost optimization** - Tries free Groq model first for SIMPLE/MODERATE
3. **Fallback chain** - If Groq fails, tries OpenAI → Claude
4. **Proper error handling** - Logs each failure, raises only if all fail
5. **Usage tracking** - Returns cost_usd for all providers

---

## Dependencies

No new dependencies required. Uses existing API clients:
- Groq (`groq` package)
- OpenAI (`openai` package)
- Anthropic (`anthropic` package)

Make sure environment variables are set:
- `GROQ_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

---

## Next Step

After validating this works, proceed to **HARVEST 2** (Manufacturer Patterns).

This unblocks all SME agents in Phase 2.
