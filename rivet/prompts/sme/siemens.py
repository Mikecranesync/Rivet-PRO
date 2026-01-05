"""
Siemens SME - Subject Matter Expert for Siemens Equipment

Specializes in:
- SIMATIC S7 PLCs (S7-1200, S7-1500, S7-300, S7-400)
- TIA Portal programming
- PROFINET and PROFIBUS networks
- HMI systems (WinCC, KTP panels)
- Siemens drives and motors
"""

import logging
from typing import Optional, Dict, Any

from rivet.models.ocr import OCRResult
from rivet.integrations.llm import LLMRouter, ModelCapability
from rivet.observability.tracer import traced
from rivet.utils.response_formatter import synthesize_response

logger = logging.getLogger(__name__)


SIEMENS_SME_PROMPT = """You are a Siemens automation specialist with expert knowledge of:

**PLC Systems:**
- SIMATIC S7-1200, S7-1500 (current generation)
- S7-300, S7-400 (legacy systems)
- TIA Portal (Step 7 V15+)
- STEP 7 Classic (for legacy systems)
- Safety systems (F-CPU, F-modules)

**Networks:**
- PROFINET IO (RT, IRT)
- PROFIBUS DP
- Industrial Ethernet
- S7 Communication protocols

**Common Fault Codes:**
- F-xxxx series (Safety faults)
- A-xxxx series (Alarms)
- Diagnostic buffer interpretation
- LED status patterns (SF, BF, MAINT, ERROR)

**HMI & Visualization:**
- WinCC (Comfort, Advanced, Professional)
- KTP panels (Basic Panels)
- Mobile Panels
- Runtime licenses

**Drives & Motion:**
- SINAMICS G120, S120
- MICROMASTER series
- V90 servo drives
- SIMOTION controllers

**Safety Protocols:**
- LOTO procedures for Siemens equipment
- Arc flash considerations for control panels
- High voltage (3-phase 480V) safety

User Question:
{query}

{equipment_context}

Provide a detailed Siemens-specific troubleshooting response including:

1. **Likely Causes** (Siemens-specific)
   - Common Siemens equipment failure modes
   - Typical configuration errors in TIA Portal

2. **Diagnostic Steps**
   - Check diagnostic buffer (Device & Networks → Diagnostics)
   - LED status interpretation
   - PROFINET/PROFIBUS diagnostics
   - Online monitoring in TIA Portal

3. **TIA Portal Checks**
   - Device configuration (IP addressing, device names)
   - Hardware catalog mismatch
   - Firmware version compatibility
   - Program download issues

4. **Safety Warnings**
   - High voltage hazards (480V 3-phase common)
   - Safety PLC considerations (don't bypass F-modules)
   - LOTO points for Siemens control panels

5. **Common Mistakes**
   - Forgetting to compile hardware after changes
   - PROFINET device name mismatches
   - Safety program forcing (NEVER override safety logic)

Be specific with Siemens terminology and TIA Portal navigation.
"""


def format_siemens_context(ocr_result: Optional[OCRResult]) -> str:
    """Format Siemens equipment context from OCR."""
    if not ocr_result:
        return "Equipment Context: No Siemens equipment photo provided"

    context = ["Siemens Equipment Context:"]

    if ocr_result.model_number:
        context.append(f"- Model: {ocr_result.model_number}")
        # Add specific model guidance
        if "s7-1200" in ocr_result.model_number.lower():
            context.append("  (Compact PLC, TIA Portal V13+)")
        elif "s7-1500" in ocr_result.model_number.lower():
            context.append("  (Advanced PLC, TIA Portal V13+, Safety capable)")
        elif "s7-300" in ocr_result.model_number.lower():
            context.append("  (Legacy PLC, STEP 7 Classic or TIA Portal)")

    if ocr_result.fault_code:
        context.append(f"- Fault Code: {ocr_result.fault_code}")
        if ocr_result.fault_code.upper().startswith("F-"):
            context.append("  (Safety fault - check F-CPU diagnostics)")

    if ocr_result.serial_number:
        context.append(f"- Serial: {ocr_result.serial_number}")

    return "\n".join(context)


@traced(name="siemens_sme", tags=["sme", "siemens"])
async def troubleshoot(
    query: str,
    ocr_result: Optional[OCRResult] = None,
) -> Dict[str, Any]:
    """
    Siemens-specific troubleshooting using vendor SME.

    Args:
        query: User's troubleshooting question
        ocr_result: Optional Siemens equipment data from OCR

    Returns:
        Dict with answer, confidence, sources, safety_warnings, cost

    Example:
        >>> result = await troubleshoot("S7-1200 showing F0002 fault")
        >>> print(result["answer"])
    """
    logger.info(f"[Siemens SME] Query: {query[:100]}...")

    equipment_context = format_siemens_context(ocr_result)
    prompt = SIEMENS_SME_PROMPT.format(
        query=query,
        equipment_context=equipment_context,
    )

    router = LLMRouter()
    response = await router.generate(
        prompt=prompt,
        capability=ModelCapability.MODERATE,  # Vendor SME needs moderate reasoning
        max_tokens=1500,
        temperature=0.7,
    )

    # Extract safety warnings
    safety_warnings = []
    response_lower = response.text.lower()
    if "480v" in response_lower or "high voltage" in response_lower:
        safety_warnings.append("⚠️ HIGH VOLTAGE - 480V 3-phase system")
    if "safety" in response_lower or "f-cpu" in response_lower:
        safety_warnings.append("⚠️ SAFETY SYSTEM - Do not bypass F-modules")
    if any(kw in response_lower for kw in ["loto", "lockout", "tagout"]):
        safety_warnings.append("⚠️ LOTO REQUIRED - De-energize before servicing")

    # Siemens SME has good confidence (0.75-0.85)
    confidence = 0.80

    # Format response with confidence badge, safety warnings, and citations
    formatted_answer = synthesize_response(
        answer=response.text,
        confidence=confidence,
        sources=[],  # TODO Phase 3: Add Siemens KB sources
        safety_warnings=safety_warnings
    )

    result = {
        "answer": formatted_answer,  # Use formatted version
        "confidence": confidence,
        "sources": [],  # TODO Phase 3: Add Siemens KB sources
        "safety_warnings": safety_warnings,
        "llm_calls": 1,
        "cost_usd": response.cost_usd,
    }

    logger.info(
        f"[Siemens SME] Response: confidence={confidence:.0%}, "
        f"cost=${response.cost_usd:.6f}"
    )

    return result
