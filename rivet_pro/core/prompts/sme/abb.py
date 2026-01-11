"""
ABB SME - Subject Matter Expert for ABB Equipment

Specializes in:
- ABB Drives (ACS880, ACH580, ACS550)
- ABB Robots (IRB series)
- AC500 PLCs
- System 800xA DCS
"""

import logging
from typing import Optional, Dict, Any

from rivet_pro.core.models.ocr import OCRResult
from rivet_pro.adapters.llm.router import LLMRouter, ModelCapability
# from rivet_pro.infra.observability import traced
from rivet_pro.core.utils.response_formatter import synthesize_response

logger = logging.getLogger(__name__)


ABB_SME_PROMPT = """ABB specialist. Drives: ACS880, ACH580, ACS550 (DriveStudio/DriveWindow). Robots: IRB series (RAPID, RobotStudio). PLCs: AC500 (CoDeSys). Faults: 27xx/3xxx/8xxx series. Safety: DC bus discharge 5+ min, 690V hazards.

Question: {query}
{equipment_context}

Respond with:
1. **Causes** - Drive faults (DC bus, IGBT), parameter errors, motor mismatch
2. **Diagnostics** - Fault trace in DriveStudio, param groups 10/20/30, motor vs drive config
3. **Tools** - DriveStudio, RobotStudio, Drive Assistant app
4. **Safety** - WAIT 5+ MIN DC bus discharge, 690V hazards, robot zones, LOTO required
5. **Avoid** - Servicing before discharge, wrong motor params, not saving to memory

Use ABB terminology."""


def format_abb_context(ocr_result: Optional[OCRResult]) -> str:
    """Format ABB equipment context from OCR."""
    if not ocr_result:
        return "Equipment Context: No ABB equipment photo provided"

    context = ["ABB Equipment Context:"]

    if ocr_result.model_number:
        context.append(f"- Model: {ocr_result.model_number}")
        if "acs880" in ocr_result.model_number.lower():
            context.append("  (Industrial drive, IP21/IP54)")
        elif "ach580" in ocr_result.model_number.lower():
            context.append("  (HVAC drive)")
        elif "irb" in ocr_result.model_number.lower():
            context.append("  (Industrial robot)")

    if ocr_result.fault_code:
        context.append(f"- Fault Code: {ocr_result.fault_code}")

    if ocr_result.serial_number:
        context.append(f"- Serial: {ocr_result.serial_number}")

    return "\n".join(context)


#@traced(name="abb_sme", tags=["sme", "abb"])
async def troubleshoot(
    query: str,
    ocr_result: Optional[OCRResult] = None,
) -> Dict[str, Any]:
    """
    ABB-specific troubleshooting using vendor SME.

    Args:
        query: User's troubleshooting question
        ocr_result: Optional ABB equipment data from OCR

    Returns:
        Dict with answer, confidence, sources, safety_warnings, cost

    Example:
        >>> result = await troubleshoot("ACS880 fault code 2710")
        >>> print(result["answer"])
    """
    logger.info(f"[ABB SME] Query: {query[:100]}...")

    equipment_context = format_abb_context(ocr_result)
    prompt = ABB_SME_PROMPT.format(
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
    if "dc bus" in response_lower or "capacitor" in response_lower:
        safety_warnings.append("⚠️ DC BUS HAZARD - Wait 5+ min after power-off")
    if "690v" in response_lower or "high voltage" in response_lower:
        safety_warnings.append("⚠️ HIGH VOLTAGE - Up to 690V systems")
    if "robot" in response_lower and "safety" in response_lower:
        safety_warnings.append("⚠️ ROBOT SAFETY - Never enter safety zones during operation")
    if any(kw in response_lower for kw in ["loto", "lockout", "tagout"]):
        safety_warnings.append("⚠️ LOTO REQUIRED - De-energize before servicing")

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
        f"[ABB SME] Response: confidence={confidence:.0%}, "
        f"cost=${response.cost_usd:.6f}"
    )

    return result
