"""
FANUC SME - Subject Matter Expert for FANUC Equipment

Specializes in:
- FANUC CNC systems (0i, 31i, 32i series)
- FANUC Robots (R-30iA, R-30iB controllers)
- Servo drives and motors
- LADDER III programming
"""

import logging
from typing import Optional, Dict, Any

from rivet_pro.core.models.ocr import OCRResult
from rivet_pro.adapters.llm.router import LLMRouter, ModelCapability
# from rivet_pro.infra.observability import traced
from rivet_pro.core.utils.response_formatter import synthesize_response

logger = logging.getLogger(__name__)


FANUC_SME_PROMPT = """FANUC specialist. CNC: 0i/31i/32i series (G-code, macros). Robots: R-30iA/B (TP, KAREL, iRVision). Servos: αi/βi drives. Alarms: SV/PS/SR/IO (CNC), SRVO/MOTN/INTP (robot). Tools: LADDER III, ROBOGUIDE.

Question: {query}
{equipment_context}

Respond with:
1. **Causes** - CNC/robot failures, servo alarms, PMC ladder issues
2. **Diagnostics** - SYSTEM→ALARM→HISTORY, MAINTAIN→SERVO→CHECK, PMC→I/O→DGN, position deviation
3. **Navigation** - MDI: SYSTEM/PARAM/OFFSET/ALARM. TP: MENU/STATUS/ALARM
4. **Safety** - DC 300V+ in servo amps (wait!), stay outside robot fence, verify E-stop chain, LOTO required
5. **Avoid** - Clearing alarms without root cause, no ZRN after battery change, param changes without backup

Use FANUC terminology."""


def format_fanuc_context(ocr_result: Optional[OCRResult]) -> str:
    """Format FANUC equipment context from OCR."""
    if not ocr_result:
        return "Equipment Context: No FANUC equipment photo provided"

    context = ["FANUC Equipment Context:"]

    if ocr_result.model_number:
        context.append(f"- Model: {ocr_result.model_number}")
        if "0i" in ocr_result.model_number:
            context.append("  (FANUC 0i CNC series)")
        elif "31i" in ocr_result.model_number or "32i" in ocr_result.model_number:
            context.append("  (FANUC 31i/32i CNC series)")
        elif "r-30i" in ocr_result.model_number.lower():
            context.append("  (FANUC Robot Controller)")

    if ocr_result.fault_code:
        context.append(f"- Alarm Code: {ocr_result.fault_code}")

    if ocr_result.serial_number:
        context.append(f"- Serial: {ocr_result.serial_number}")

    return "\n".join(context)


#@traced(name="fanuc_sme", tags=["sme", "fanuc"])
async def troubleshoot(
    query: str,
    ocr_result: Optional[OCRResult] = None,
) -> Dict[str, Any]:
    """
    FANUC-specific troubleshooting using vendor SME.

    Args:
        query: User's troubleshooting question
        ocr_result: Optional FANUC equipment data from OCR

    Returns:
        Dict with answer, confidence, sources, safety_warnings, cost

    Example:
        >>> result = await troubleshoot("FANUC 0i-F alarm SV0401")
        >>> print(result["answer"])
    """
    logger.info(f"[FANUC SME] Query: {query[:100]}...")

    equipment_context = format_fanuc_context(ocr_result)
    prompt = FANUC_SME_PROMPT.format(
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
    if "300v" in response_lower or "servo amplifier" in response_lower:
        safety_warnings.append("⚠️ HIGH VOLTAGE - DC 300V+ in servo amplifier")
    if "robot" in response_lower and ("rapid" in response_lower or "motion" in response_lower):
        safety_warnings.append("⚠️ ROBOT HAZARD - Rapid motion, stay outside safety fence")
    if "e-stop" in response_lower or "emergency" in response_lower:
        safety_warnings.append("⚠️ E-STOP CIRCUIT - Verify safety chain before servicing")
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
        f"[FANUC SME] Response: confidence={confidence:.0%}, "
        f"cost=${response.cost_usd:.6f}"
    )

    return result
