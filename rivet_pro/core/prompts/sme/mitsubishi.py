"""
Mitsubishi SME - Subject Matter Expert for Mitsubishi Equipment

Specializes in:
- MELSEC iQ-R, iQ-F PLCs
- GX Works2, GX Works3 programming
- GOT HMIs
- CC-Link networks
- FR-A/E/F series drives
"""

import logging
from typing import Optional, Dict, Any

from rivet_pro.core.models.ocr import OCRResult
from rivet_pro.adapters.llm.router import LLMRouter, ModelCapability
# from rivet_pro.infra.observability import traced
from rivet_pro.core.utils.response_formatter import synthesize_response

logger = logging.getLogger(__name__)


MITSUBISHI_SME_PROMPT = """Mitsubishi specialist. PLCs: MELSEC iQ-R/F, FX3U/FX5U (GX Works2/3). Networks: CC-Link IE Field, CC-Link, SLMP. HMI: GOT2000 (GT Designer3). Drives: FR-A800/E700/F700, MR-J4. Faults: ERR/RUN/BAT LEDs, E.xxx/Er.xxx alarms.

Question: {query}
{equipment_context}

Respond with:
1. **Causes** - MELSEC failures, CC-Link network issues, GOT comm errors
2. **Diagnostics** - Error history, LED status (ERR/RUN/BAT/SD), CC-Link node LEDs, Pr.xxx params
3. **GX Works** - Online monitoring, error history, device memory compare, upload/download
4. **Safety** - 200V/400V hazards, iQ-R Safety modules, LOTO required
5. **Avoid** - CC-Link address errors, wrong data types, not saving to flash, BAT LED ignored

Use Mitsubishi terminology."""


def format_mitsubishi_context(ocr_result: Optional[OCRResult]) -> str:
    """Format Mitsubishi equipment context from OCR."""
    if not ocr_result:
        return "Equipment Context: No Mitsubishi equipment photo provided"

    context = ["Mitsubishi Electric Equipment Context:"]

    if ocr_result.model_number:
        context.append(f"- Model: {ocr_result.model_number}")
        if "iq-r" in ocr_result.model_number.lower():
            context.append("  (MELSEC iQ-R PLC, GX Works3)")
        elif "iq-f" in ocr_result.model_number.lower():
            context.append("  (MELSEC iQ-F PLC, GX Works3)")
        elif "fx3u" in ocr_result.model_number.lower() or "fx5u" in ocr_result.model_number.lower():
            context.append("  (FX Series micro PLC, GX Works2)")
        elif "got" in ocr_result.model_number.lower():
            context.append("  (GOT HMI, GT Designer3)")

    if ocr_result.fault_code:
        context.append(f"- Fault/Alarm Code: {ocr_result.fault_code}")

    if ocr_result.serial_number:
        context.append(f"- Serial: {ocr_result.serial_number}")

    return "\n".join(context)


#@traced(name="mitsubishi_sme", tags=["sme", "mitsubishi"])
async def troubleshoot(
    query: str,
    ocr_result: Optional[OCRResult] = None,
) -> Dict[str, Any]:
    """
    Mitsubishi-specific troubleshooting using vendor SME.

    Args:
        query: User's troubleshooting question
        ocr_result: Optional Mitsubishi equipment data from OCR

    Returns:
        Dict with answer, confidence, sources, safety_warnings, cost

    Example:
        >>> result = await troubleshoot("MELSEC iQ-R ERR LED blinking")
        >>> print(result["answer"])
    """
    logger.info(f"[Mitsubishi SME] Query: {query[:100]}...")

    equipment_context = format_mitsubishi_context(ocr_result)
    prompt = MITSUBISHI_SME_PROMPT.format(
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
    if "400v" in response_lower or "200v" in response_lower or "high voltage" in response_lower:
        safety_warnings.append("⚠️ HIGH VOLTAGE - 200V/400V system")
    if "safety" in response_lower and "iq-r" in response_lower:
        safety_warnings.append("⚠️ SAFETY PLC - Do not bypass safety modules")
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
        f"[Mitsubishi SME] Response: confidence={confidence:.0%}, "
        f"cost=${response.cost_usd:.6f}"
    )

    return result
