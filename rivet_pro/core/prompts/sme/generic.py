"""
Generic SME - Subject Matter Expert for Generic Industrial Equipment

Fallback SME when no specific manufacturer is detected.

Specializes in:
- Generic motors, contactors, relays, sensors
- Electrical troubleshooting fundamentals
- Industrial safety protocols
- Basic PLC/control concepts
"""

import logging
from typing import Optional, Dict, Any

from rivet_pro.core.models.ocr import OCRResult
from rivet_pro.adapters.llm.router import LLMRouter, ModelCapability
# from rivet_pro.infra.observability import traced
from rivet_pro.core.utils.response_formatter import synthesize_response

logger = logging.getLogger(__name__)


GENERIC_SME_PROMPT = """Industrial maintenance expert. Knowledge: 3-phase motors, starters, overloads, transformers, relays, sensors (proximity/photoelectric/pressure/temp), troubleshooting (single-phasing, overloads, bearings).

Question: {query}
{equipment_context}

Respond with:
1. **Causes** - Common failure modes, wear items
2. **Diagnostics** - Visual check, voltage/current/resistance, mechanical (bearings, alignment)
3. **Safety** - LOTO required, voltage hazards, arc flash PPE, NFPA 70E
4. **Avoid** - Bypassing safeties, ignoring root cause, not checking all phases
5. **Escalate** - When vendor-specific knowledge needed

Be specific with measurements. Use LOTO always."""


def format_generic_context(ocr_result: Optional[OCRResult]) -> str:
    """Format generic equipment context from OCR."""
    if not ocr_result:
        return "Equipment Context: No equipment photo provided"

    context = ["Equipment Context (Generic):"]

    if ocr_result.manufacturer:
        context.append(f"- Manufacturer: {ocr_result.manufacturer} (no vendor-specific SME available)")

    if ocr_result.model_number:
        context.append(f"- Model: {ocr_result.model_number}")

    if ocr_result.fault_code:
        context.append(f"- Fault/Error: {ocr_result.fault_code}")

    if ocr_result.serial_number:
        context.append(f"- Serial: {ocr_result.serial_number}")

    # Electrical specs (very useful for generic troubleshooting)
    electrical_specs = []
    if ocr_result.voltage:
        electrical_specs.append(f"Voltage: {ocr_result.voltage}")
    if ocr_result.current:
        electrical_specs.append(f"Current: {ocr_result.current}")
    if ocr_result.horsepower:
        electrical_specs.append(f"HP: {ocr_result.horsepower}")
    if ocr_result.phase:
        electrical_specs.append(f"Phase: {ocr_result.phase}")
    if ocr_result.frequency:
        electrical_specs.append(f"Frequency: {ocr_result.frequency}")

    if electrical_specs:
        context.append(f"- Electrical Specs: {', '.join(electrical_specs)}")

    return "\n".join(context)


#@traced(name="generic_sme", tags=["sme", "generic"])
async def troubleshoot(
    query: str,
    ocr_result: Optional[OCRResult] = None,
) -> Dict[str, Any]:
    """
    Generic industrial equipment troubleshooting.

    Used when no vendor-specific SME is available.

    Args:
        query: User's troubleshooting question
        ocr_result: Optional equipment data from OCR

    Returns:
        Dict with answer, confidence, sources, safety_warnings, cost

    Example:
        >>> result = await troubleshoot("Motor trips after 10 seconds")
        >>> print(result["answer"])
    """
    logger.info(f"[Generic SME] Query: {query[:100]}...")

    equipment_context = format_generic_context(ocr_result)
    prompt = GENERIC_SME_PROMPT.format(
        query=query,
        equipment_context=equipment_context,
    )

    router = LLMRouter()
    response = await router.generate(
        prompt=prompt,
        capability=ModelCapability.MODERATE,
        max_tokens=1500,
        temperature=0.7,
    )

    # Extract safety warnings (generic electrical safety)
    safety_warnings = []
    response_lower = response.text.lower()
    if any(voltage in response_lower for voltage in ["480v", "240v", "208v", "120v", "high voltage"]):
        safety_warnings.append("⚠️ ELECTRICAL HAZARD - High voltage present")
    if "arc flash" in response_lower:
        safety_warnings.append("⚠️ ARC FLASH RISK - Follow NFPA 70E")
    if any(kw in response_lower for kw in ["loto", "lockout", "tagout"]):
        safety_warnings.append("⚠️ LOTO REQUIRED - De-energize before servicing")
    if "ppe" in response_lower or "gloves" in response_lower:
        safety_warnings.append("⚠️ PPE REQUIRED - Voltage-rated gloves, face shield")

    # Generic SME has lower confidence than vendor-specific (0.70-0.75)
    confidence = 0.72

    # Format response with confidence badge, safety warnings, and citations
    formatted_answer = synthesize_response(
        answer=response.text,
        confidence=confidence,
        sources=[],
        safety_warnings=safety_warnings
    )

    result = {
        "answer": formatted_answer,  # Use formatted version
        "confidence": confidence,
        "sources": [],
        "safety_warnings": safety_warnings,
        "llm_calls": 1,
        "cost_usd": response.cost_usd,
    }

    logger.info(
        f"[Generic SME] Response: confidence={confidence:.0%}, "
        f"cost=${response.cost_usd:.6f}"
    )

    return result
