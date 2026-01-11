"""
Schneider Electric SME - Subject Matter Expert for Schneider Equipment

Specializes in:
- Modicon PLCs (M340, M580, M221)
- Altivar drives (ATV320, ATV630, ATV930)
- EcoStruxure platform
- Square D electrical distribution
"""

import logging
from typing import Optional, Dict, Any

from rivet_pro.core.models.ocr import OCRResult
from rivet_pro.adapters.llm.router import LLMRouter, ModelCapability
# from rivet_pro.infra.observability import traced
from rivet_pro.core.utils.response_formatter import synthesize_response

logger = logging.getLogger(__name__)


SCHNEIDER_SME_PROMPT = """Schneider Electric specialist. PLCs: Modicon M340/M580 (Unity Pro), M221 (SoMachine). Networks: Modbus TCP/RTU, EtherNet/IP. Drives: Altivar ATV320/630/930 (SoMove). Faults: InF/ObF/SOF/SCF, HALTED, APP_FAULT. Electrical: Square D, PowerPact.

Question: {query}
{equipment_context}

Respond with:
1. **Causes** - Modicon failures, Altivar param errors, Modbus issues
2. **Diagnostics** - Unity Pro diagnostics, drive keypad (SUP→FLt), Modbus status
3. **Tools** - Unity Pro, SoMachine, SoMove, PowerSuite
4. **Safety** - 480V hazards, arc flash in Square D panels, DC bus discharge, LOTO required
5. **Avoid** - Modbus address conflicts, motor kW mismatch, not saving PLC changes

Use Schneider terminology."""


def format_schneider_context(ocr_result: Optional[OCRResult]) -> str:
    """Format Schneider equipment context from OCR."""
    if not ocr_result:
        return "Equipment Context: No Schneider equipment photo provided"

    context = ["Schneider Electric Equipment Context:"]

    if ocr_result.model_number:
        context.append(f"- Model: {ocr_result.model_number}")
        if "m340" in ocr_result.model_number.lower() or "bmxp" in ocr_result.model_number.lower():
            context.append("  (Modicon M340 PLC, Unity Pro)")
        elif "m580" in ocr_result.model_number.lower() or "bmep" in ocr_result.model_number.lower():
            context.append("  (Modicon M580 PLC, Unity Pro)")
        elif "atv" in ocr_result.model_number.lower():
            context.append("  (Altivar drive, SoMove)")

    if ocr_result.fault_code:
        context.append(f"- Fault Code: {ocr_result.fault_code}")

    if ocr_result.serial_number:
        context.append(f"- Serial: {ocr_result.serial_number}")

    return "\n".join(context)


#@traced(name="schneider_sme", tags=["sme", "schneider"])
async def troubleshoot(
    query: str,
    ocr_result: Optional[OCRResult] = None,
) -> Dict[str, Any]:
    """
    Schneider Electric troubleshooting using vendor SME.

    Args:
        query: User's troubleshooting question
        ocr_result: Optional Schneider equipment data from OCR

    Returns:
        Dict with answer, confidence, sources, safety_warnings, cost

    Example:
        >>> result = await troubleshoot("Modicon M340 APP_FAULT")
        >>> print(result["answer"])
    """
    logger.info(f"[Schneider SME] Query: {query[:100]}...")

    equipment_context = format_schneider_context(ocr_result)
    prompt = SCHNEIDER_SME_PROMPT.format(
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
    if "arc flash" in response_lower:
        safety_warnings.append("⚠️ ARC FLASH HAZARD - PPE required")
    if "square d" in response_lower and "panel" in response_lower:
        safety_warnings.append("⚠️ ELECTRICAL PANEL - Follow NFPA 70E")
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
        f"[Schneider SME] Response: confidence={confidence:.0%}, "
        f"cost=${response.cost_usd:.6f}"
    )

    return result
