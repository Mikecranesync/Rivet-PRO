"""
Rockwell/Allen-Bradley SME - Subject Matter Expert for Rockwell Automation Equipment

Specializes in:
- ControlLogix, CompactLogix PLCs
- Studio 5000 (RSLogix 5000) programming
- EtherNet/IP networks
- PanelView HMIs
- PowerFlex drives
"""

import logging
from typing import Optional, Dict, Any

from rivet_pro.core.models.ocr import OCRResult
from rivet_pro.adapters.llm.router import LLMRouter, ModelCapability
# from rivet_pro.infra.observability import traced
from rivet_pro.core.utils.response_formatter import synthesize_response

logger = logging.getLogger(__name__)


ROCKWELL_SME_PROMPT = """Rockwell/Allen-Bradley specialist. PLCs: ControlLogix (1756), CompactLogix (1769), MicroLogix. Software: Studio 5000, RSLogix 500. Networks: EtherNet/IP, DeviceNet. Drives: PowerFlex 525/753/755, Kinetix. Safety: GuardLogix, CIP Safety.

Question: {query}
{equipment_context}

Respond with:
1. **Causes** - Rockwell failure modes, Studio 5000 config errors
2. **Diagnostics** - Controller faults, I/O tree status, EtherNet/IP diagnostics, online vs offline compare
3. **Studio 5000** - Processor mode (Run/Program/Remote), forces tab, watch window, cross-reference
4. **Safety** - 480V hazards, NEVER bypass GuardLogix, LOTO required
5. **Avoid** - Forcing without removing, firmware mismatch on download, ignoring minor faults

Use Rockwell terminology."""


def format_rockwell_context(ocr_result: Optional[OCRResult]) -> str:
    """Format Rockwell equipment context from OCR."""
    if not ocr_result:
        return "Equipment Context: No Rockwell equipment photo provided"

    context = ["Rockwell/Allen-Bradley Equipment Context:"]

    if ocr_result.model_number:
        context.append(f"- Model: {ocr_result.model_number}")
        # Add specific model guidance
        if "1756" in ocr_result.model_number:
            context.append("  (ControlLogix platform, Studio 5000)")
        elif "1769" in ocr_result.model_number:
            context.append("  (CompactLogix platform, Studio 5000)")
        elif "1400" in ocr_result.model_number or "1100" in ocr_result.model_number:
            context.append("  (MicroLogix platform, RSLogix 500)")

    if ocr_result.fault_code:
        context.append(f"- Fault Code: {ocr_result.fault_code}")

    if ocr_result.serial_number:
        context.append(f"- Serial: {ocr_result.serial_number}")

    return "\n".join(context)


#@traced(name="rockwell_sme", tags=["sme", "rockwell"])
async def troubleshoot(
    query: str,
    ocr_result: Optional[OCRResult] = None,
) -> Dict[str, Any]:
    """
    Rockwell/Allen-Bradley troubleshooting using vendor SME.

    Args:
        query: User's troubleshooting question
        ocr_result: Optional Rockwell equipment data from OCR

    Returns:
        Dict with answer, confidence, sources, safety_warnings, cost

    Example:
        >>> result = await troubleshoot("ControlLogix major fault code 1")
        >>> print(result["answer"])
    """
    logger.info(f"[Rockwell SME] Query: {query[:100]}...")

    equipment_context = format_rockwell_context(ocr_result)
    prompt = ROCKWELL_SME_PROMPT.format(
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

    # Extract safety warnings
    safety_warnings = []
    response_lower = response.text.lower()
    if "480v" in response_lower or "high voltage" in response_lower:
        safety_warnings.append("⚠️ HIGH VOLTAGE - 480V system")
    if "guardlogix" in response_lower or "safety" in response_lower:
        safety_warnings.append("⚠️ SAFETY SYSTEM - GuardLogix safety controller")
    if any(kw in response_lower for kw in ["loto", "lockout", "tagout"]):
        safety_warnings.append("⚠️ LOTO REQUIRED - De-energize before servicing")
    if "force" in response_lower:
        safety_warnings.append("⚠️ I/O FORCES - Remove forces before normal operation")

    confidence = 0.80

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
        f"[Rockwell SME] Response: confidence={confidence:.0%}, "
        f"cost=${response.cost_usd:.6f}"
    )

    return result
