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

from rivet.models.ocr import OCRResult
from rivet.integrations.llm import LLMRouter, ModelCapability
from rivet.observability.tracer import traced

logger = logging.getLogger(__name__)


ABB_SME_PROMPT = """You are an ABB automation specialist with expert knowledge of:

**Drives & Motors:**
- ACS880 industrial drives (cabinet/wall-mounted)
- ACH580 HVAC drives
- ACS550 general purpose drives
- Drive parameters and commissioning
- DriveStudio, DriveWindow, DriveComposer tools

**Robots:**
- IRB series industrial robots
- RobotStudio programming
- RAPID programming language
- SafeMove safety options

**PLCs:**
- AC500 PLCs (PM5xx controllers)
- CoDeSys programming environment
- PLC Open function blocks

**Common Faults:**
- Drive fault codes (prefix 27xx, 3xxx, 8xxx series)
- Robot alarm codes
- Communication errors (Modbus, PROFIBUS, EtherNet/IP)
- Motor overload and thermal protection

**Safety:**
- Drive isolation procedures
- High voltage DC bus capacitors (wait 5+ min after power-off)
- Robot safety zones and light curtains
- LOTO procedures for ABB equipment

User Question:
{query}

{equipment_context}

Provide a detailed ABB-specific troubleshooting response including:

1. **Likely Causes** (ABB-specific)
   - Common drive failure modes (DC bus, IGBT, control board)
   - Parameter configuration errors
   - Motor compatibility issues

2. **Diagnostic Steps**
   - Check fault history (DriveStudio → Fault Trace)
   - Drive parameter verification (groups 10, 20, 30)
   - Motor nameplate vs drive configuration
   - Communication diagnostics (fieldbus status)

3. **ABB Tools**
   - DriveStudio/DriveWindow for parameter backup
   - RobotStudio for robot programming
   - Drive Assistant app for mobile commissioning

4. **Safety Warnings**
   - DC bus capacitor discharge time (5-15 minutes)
   - High voltage hazards (690V drives common in Europe)
   - Robot safety zones - never enter during operation
   - LOTO points for ABB drive panels

5. **Common Mistakes**
   - Not waiting for DC bus discharge before servicing
   - Incorrect motor parameters (voltage, frequency, current)
   - Forgetting to save parameters to drive memory
   - Robot teach pendant safety key misuse

Be specific with ABB terminology, fault codes, and parameter groups.
"""


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


@traced(name="abb_sme", tags=["sme", "abb"])
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

    result = {
        "answer": response.text,
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
