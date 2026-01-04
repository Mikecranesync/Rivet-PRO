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

from rivet.models.ocr import OCRResult
from rivet.integrations.llm import LLMRouter, ModelCapability
from rivet.observability.tracer import traced

logger = logging.getLogger(__name__)


GENERIC_SME_PROMPT = """You are an experienced industrial maintenance technician with broad knowledge of:

**Electrical Fundamentals:**
- 3-phase motors (induction, synchronous)
- Motor starters and contactors
- Overload relays (thermal, electronic)
- Control transformers (480V → 120V)
- Fuses and circuit breakers

**Control Systems:**
- Relay logic and ladder diagrams
- Timers (on-delay, off-delay)
- Counters and sequencers
- Limit switches and proximity sensors
- Push-button stations (start/stop)

**Sensors & Instrumentation:**
- Proximity sensors (inductive, capacitive)
- Photoelectric sensors
- Pressure switches and transducers
- Temperature sensors (RTD, thermocouple)
- Level switches (float, ultrasonic)

**Motor Troubleshooting:**
- Single-phasing conditions
- Overload trips
- Start capacitor failures (single-phase)
- Bearing failures and vibration
- Thermal overload reset procedures

**Safety Fundamentals:**
- LOTO (Lockout/Tagout) procedures
- NFPA 70E arc flash protection
- PPE requirements (voltage-rated gloves, face shields)
- Electrical testing safety (multimeter, megger)
- Energized vs de-energized work

User Question:
{query}

{equipment_context}

Provide a detailed troubleshooting response including:

1. **Likely Causes** (generic electrical/mechanical)
   - Most common failure modes for this type of equipment
   - Typical wear items and maintenance issues

2. **Diagnostic Steps**
   - Visual inspection (burn marks, loose wires, damaged components)
   - Electrical measurements (voltage, current, resistance)
   - Mechanical checks (bearings, couplings, alignment)
   - Sensor testing procedures

3. **Safety Warnings**
   - Voltage hazards (specify voltage if known)
   - Arc flash risks
   - LOTO requirements
   - PPE needed for safe troubleshooting

4. **Common Mistakes to Avoid**
   - Bypassing safety devices
   - Working energized without proper PPE
   - Ignoring root cause (just resetting overloads)
   - Not checking all three phases

5. **When to Escalate**
   - Signs the issue requires a specialist
   - Manufacturer-specific equipment beyond generic knowledge

Be specific with measurements and procedures, but acknowledge when manufacturer-specific knowledge is needed.
"""


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


@traced(name="generic_sme", tags=["sme", "generic"])
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

    result = {
        "answer": response.text,
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
