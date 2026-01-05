"""
General Troubleshoot - Route D: Claude Opus Fallback

Best-effort troubleshooting when:
- KB confidence < 0.85
- SME confidence < 0.70
- No vendor-specific knowledge available

Uses Claude Opus for complex reasoning.
"""

import logging
from typing import Optional, Dict, Any

from rivet.models.ocr import OCRResult
from rivet.integrations.llm import LLMRouter, ModelCapability
from rivet.observability.tracer import traced
from rivet.utils.response_formatter import synthesize_response

logger = logging.getLogger(__name__)


GENERAL_TROUBLESHOOT_PROMPT = """You are an expert industrial maintenance technician with deep knowledge of:
- PLC systems (Siemens, Rockwell, ABB, Schneider, Mitsubishi, FANUC)
- Motor controls and drives
- Industrial sensors and instrumentation
- Electrical troubleshooting
- Safety protocols (LOTO, Arc Flash, NFPA 70E)

The user has asked a troubleshooting question. Provide a detailed, step-by-step response that includes:

1. **Likely Causes** (ranked by probability)
   - Most common issues first
   - Consider both electrical and mechanical failures

2. **Diagnostic Procedure**
   - Step-by-step troubleshooting process
   - What to check first, second, third
   - Required tools and measurements

3. **Safety Warnings**
   - Electrical hazards (voltage, arc flash)
   - Lockout/tagout requirements
   - PPE needed (voltage-rated gloves, face shields, etc.)

4. **Common Mistakes to Avoid**
   - Typical errors technicians make
   - What NOT to do

5. **When to Escalate**
   - Signs the issue requires an expert
   - When to call vendor support

Be specific with measurements, test points, and procedures.
If you're uncertain about equipment-specific details, acknowledge the limitation.

User Question:
{query}

{equipment_context}
"""


def format_equipment_context(ocr_result: Optional[OCRResult]) -> str:
    """
    Format OCR data as context for LLM prompt.

    Args:
        ocr_result: Optional OCR equipment data

    Returns:
        Formatted context string

    Example:
        >>> ocr = OCRResult(manufacturer="Siemens", model_number="S7-1200")
        >>> context = format_equipment_context(ocr)
        >>> print(context)
        Equipment Context (from photo):
        - Manufacturer: Siemens
        - Model: S7-1200
    """
    if not ocr_result:
        return "Equipment Context: No equipment photo provided"

    context_lines = ["Equipment Context (from photo):"]

    if ocr_result.manufacturer:
        context_lines.append(f"- Manufacturer: {ocr_result.manufacturer}")

    if ocr_result.model_number:
        context_lines.append(f"- Model: {ocr_result.model_number}")

    if ocr_result.serial_number:
        context_lines.append(f"- Serial Number: {ocr_result.serial_number}")

    if ocr_result.fault_code:
        context_lines.append(f"- Fault Code: {ocr_result.fault_code}")

    # Electrical specs
    electrical_specs = []
    if ocr_result.voltage:
        electrical_specs.append(f"Voltage: {ocr_result.voltage}")
    if ocr_result.current:
        electrical_specs.append(f"Current: {ocr_result.current}")
    if ocr_result.horsepower:
        electrical_specs.append(f"Horsepower: {ocr_result.horsepower}")
    if ocr_result.phase:
        electrical_specs.append(f"Phase: {ocr_result.phase}")
    if ocr_result.frequency:
        electrical_specs.append(f"Frequency: {ocr_result.frequency}")

    if electrical_specs:
        context_lines.append(f"- Electrical: {', '.join(electrical_specs)}")

    return "\n".join(context_lines)


@traced(name="general_troubleshoot", tags=["general", "claude_opus"])
async def general_troubleshoot(
    query: str,
    ocr_result: Optional[OCRResult] = None,
) -> Dict[str, Any]:
    """
    General troubleshooting using Claude Opus.

    This is the fallback route when:
    - KB confidence < 0.85
    - SME confidence < 0.70
    - No vendor-specific SME available

    Args:
        query: User's troubleshooting question
        ocr_result: Optional OCR equipment data

    Returns:
        Dict with:
            - answer: str (troubleshooting response)
            - confidence: float (0.0-1.0, typically 0.65-0.75 for general)
            - sources: list (empty for general - no KB sources)
            - safety_warnings: list (extracted from response)
            - llm_calls: int
            - cost_usd: float

    Example:
        >>> result = await general_troubleshoot("Motor won't start, no error codes")
        >>> print(result["answer"])
        >>> print(f"Confidence: {result['confidence']:.0%}")
    """
    logger.info(f"[General Troubleshoot] Query: {query[:100]}...")

    # Format prompt with equipment context
    equipment_context = format_equipment_context(ocr_result)
    prompt = GENERAL_TROUBLESHOOT_PROMPT.format(
        query=query,
        equipment_context=equipment_context,
    )

    # Use Claude Opus via LLM router
    # General troubleshooting needs complex reasoning capability
    router = LLMRouter()

    response = await router.generate(
        prompt=prompt,
        capability=ModelCapability.COMPLEX,  # Use premium models (Claude Opus, GPT-4)
        max_tokens=2000,
        temperature=0.7,  # Balance creativity with accuracy
    )

    # Extract safety warnings from response
    # Look for keywords: "WARNING", "DANGER", "CAUTION", "HAZARD"
    safety_warnings = []
    response_lower = response.text.lower()
    if any(keyword in response_lower for keyword in ["warning", "danger", "caution", "hazard", "loto", "lockout"]):
        safety_warnings.append("⚠️ Safety-critical response - review all warnings carefully")

    # General fallback has moderate confidence (0.65-0.75)
    # Higher than nothing, but lower than KB or vendor SME
    confidence = 0.70

    # Format response with confidence badge, safety warnings, and citations
    formatted_answer = synthesize_response(
        answer=response.text,
        confidence=confidence,
        sources=[],  # No KB sources for general fallback
        safety_warnings=safety_warnings
    )

    result = {
        "answer": formatted_answer,  # Use formatted version
        "confidence": confidence,
        "sources": [],  # No KB sources for general fallback
        "safety_warnings": safety_warnings,
        "llm_calls": 1,
        "cost_usd": response.cost_usd,
    }

    logger.info(
        f"[General Troubleshoot] Response generated: "
        f"confidence={confidence:.0%}, "
        f"cost=${response.cost_usd:.6f}, "
        f"length={len(response.text)} chars"
    )

    return result


# Convenience sync wrapper
def general_troubleshoot_sync(
    query: str,
    ocr_result: Optional[OCRResult] = None,
) -> Dict[str, Any]:
    """Synchronous wrapper for general_troubleshoot()."""
    import asyncio
    return asyncio.run(general_troubleshoot(query, ocr_result))


if __name__ == "__main__":
    import asyncio

    # Test general troubleshooting
    async def test_general():
        print("\n=== General Troubleshoot Test ===\n")

        query = "Motor trips after 10 seconds of running, no error codes displayed"

        result = await general_troubleshoot(query)

        print(f"Query: {query}\n")
        print(f"Confidence: {result['confidence']:.0%}")
        print(f"Cost: ${result['cost_usd']:.6f}")
        print(f"LLM Calls: {result['llm_calls']}")
        print(f"\nAnswer:\n{result['answer']}\n")

        if result['safety_warnings']:
            print(f"Safety Warnings: {', '.join(result['safety_warnings'])}\n")

    asyncio.run(test_general())
