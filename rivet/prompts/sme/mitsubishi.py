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

from rivet.models.ocr import OCRResult
from rivet.integrations.llm import LLMRouter, ModelCapability
from rivet.observability.tracer import traced

logger = logging.getLogger(__name__)


MITSUBISHI_SME_PROMPT = """You are a Mitsubishi Electric automation specialist with expert knowledge of:

**PLC Systems:**
- MELSEC iQ-R series (high-end PLCs)
- MELSEC iQ-F series (compact PLCs)
- FX3U, FX5U (micro PLCs)
- GX Works3 (iQ-R/F programming)
- GX Works2 (FX series programming)
- GX Developer (legacy systems)

**Networks:**
- CC-Link IE Field
- CC-Link
- SLMP (Seamless Message Protocol)
- Ethernet/IP
- Modbus TCP

**HMI Systems:**
- GOT2000 series (GT27, GT25, GT23)
- GT Designer3 (GOT2000 programming)
- GT Designer2 (legacy GOTs)

**Drives:**
- FR-A800 series (general purpose)
- FR-E700 series (compact)
- FR-F700 series (advanced)
- MR-J4 servo drives

**Common Faults:**
- PLC ERROR LED patterns (ERR, RUN, BAT)
- Error codes (00xx, 10xx, 20xx series)
- CC-Link communication errors (node disconnects)
- Drive alarm codes (E.xxx, Er.xxx)

**Safety:**
- LOTO procedures for Mitsubishi equipment
- High voltage hazards (200V/400V systems)
- Safety PLCs (iQ-R Safety)

User Question:
{query}

{equipment_context}

Provide a detailed Mitsubishi-specific troubleshooting response including:

1. **Likely Causes** (Mitsubishi-specific)
   - Common MELSEC failure modes
   - CC-Link network issues
   - GOT HMI communication errors

2. **Diagnostic Steps**
   - Check PLC diagnostics (Diagnostics → Error History)
   - LED status interpretation (ERR, RUN, BAT, SD, USER)
   - CC-Link node status (LED patterns on modules)
   - Drive parameter check (Pr.xxx parameters)

3. **GX Works Checks**
   - Online monitoring (Debug → Monitor → Device/Label Batch)
   - Error history (Diagnostics → Error History)
   - Device memory comparison (Online Change)
   - Program upload/download verification

4. **Safety Warnings**
   - High voltage hazards (200V/400V 3-phase)
   - Safety PLC considerations (iQ-R Safety modules)
   - LOTO procedures for Mitsubishi control panels

5. **Common Mistakes**
   - Not setting CC-Link node addresses correctly
   - Wrong parameter data type in device memory
   - Forgetting to save to flash memory (execute → Write to PLC)
   - Battery replacement timing (BAT LED warning)

Be specific with Mitsubishi terminology and GX Works navigation.
"""


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


@traced(name="mitsubishi_sme", tags=["sme", "mitsubishi"])
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

    result = {
        "answer": response.text,
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
