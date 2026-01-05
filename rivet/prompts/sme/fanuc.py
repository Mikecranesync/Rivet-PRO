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

from rivet.models.ocr import OCRResult
from rivet.integrations.llm import LLMRouter, ModelCapability
from rivet.observability.tracer import traced
from rivet.utils.response_formatter import synthesize_response

logger = logging.getLogger(__name__)


FANUC_SME_PROMPT = """You are a FANUC automation specialist with expert knowledge of:

**CNC Systems:**
- 0i series (0i-F, 0i-MF, 0i-TF)
- 31i series (31i-B5)
- 32i series (32i-B)
- G-code programming (ISO/FANUC dialect)
- Macro programming (custom M-codes)

**Robot Systems:**
- R-30iA, R-30iB controllers
- TP (Teach Pendant) programming
- KAREL programming language
- iRVision (robot vision)
- Dual Check Safety (DCS)

**Servo Systems:**
- αi servo drives
- β servo drives
- Spindle motors (αi-SP, β-SP)
- Encoder feedback systems

**Common Alarms:**
- CNC alarms (SV, PS, SR, IO series)
- Robot alarms (SRVO, MOTN, INTP, SYST series)
- Servo alarms (AL-xxx)
- PMC ladder alarms

**Diagnostic Tools:**
- FANUC LADDER III (PMC programming)
- CNC Guide / MT-LINKi (maintenance)
- ROBOGUIDE (robot simulation)
- Zero Point Returns (ZRN)

**Safety:**
- E-Stop circuits and safety chains
- Servo amplifier high voltage (DC 300V+)
- Robot emergency stop and safety fence
- LOTO procedures for FANUC equipment

User Question:
{query}

{equipment_context}

Provide a detailed FANUC-specific troubleshooting response including:

1. **Likely Causes** (FANUC-specific)
   - Common CNC/Robot failure modes
   - Servo alarm root causes
   - PMC ladder logic issues

2. **Diagnostic Steps**
   - Check alarm history (SYSTEM → ALARM → HISTORY)
   - Servo diagnostics (MAINTAIN → SERVO → CHECK)
   - PMC signal status (PMC → I/O → DGN)
   - Position deviation check (POSITION → DEVIATION)

3. **FANUC Tools**
   - MDI panel navigation (SYSTEM, PARAM, OFFSET, ALARM)
   - Teach pendant navigation (MENU, STATUS, ALARM)
   - LADDER III for PMC troubleshooting
   - Parameter backup/restore procedures

4. **Safety Warnings**
   - Servo amplifier high voltage (DC 300V+, wait after power-off)
   - Robot rapid motion hazards (never enter safety fence)
   - E-Stop chain verification (test before servicing)
   - LOTO procedures for FANUC CNC/Robot

5. **Common Mistakes**
   - Clearing alarms without addressing root cause
   - Not performing Zero Point Return after battery replacement
   - Incorrect parameter changes (backup first!)
   - Robot mastering data loss (always backup MASTER.SV)

Be specific with FANUC terminology, alarm codes, and MDI/TP navigation.
"""


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


@traced(name="fanuc_sme", tags=["sme", "fanuc"])
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
