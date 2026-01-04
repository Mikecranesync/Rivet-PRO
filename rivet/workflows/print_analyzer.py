"""
Print/Schematic Analyzer - Analyze technical drawings and wiring diagrams

Supports:
- Ladder logic diagrams
- Electrical schematics
- P&ID diagrams
- Control panel layouts
- Wiring diagrams

Uses vision AI (GPT-4o → Claude fallback) for high-accuracy technical analysis.
"""

import logging
from typing import Optional

from rivet.integrations.llm import LLMRouter, ModelCapability
from rivet.observability.tracer import traced

logger = logging.getLogger(__name__)


class PrintAnalyzer:
    """
    Analyze technical prints, schematics, and wiring diagrams.

    Supports:
    - Ladder logic diagrams
    - Electrical schematics
    - P&ID diagrams
    - Control panel layouts
    - Wiring diagrams
    """

    def __init__(self):
        self.router = LLMRouter()

    @traced(name="print_analyze", tags=["schematic", "vision"])
    async def analyze(self, image_bytes: bytes, caption: Optional[str] = None) -> str:
        """
        Comprehensive analysis of technical schematic.

        Args:
            image_bytes: Raw image bytes of the schematic/diagram
            caption: Optional user-provided caption/description

        Returns:
            Detailed analysis of the schematic including:
            - Diagram type identification
            - Key components identified
            - System overview
            - Notable features or concerns

        Example:
            >>> analyzer = PrintAnalyzer()
            >>> result = await analyzer.analyze(image_bytes, "ladder logic diagram")
            >>> print(result)
        """
        logger.info(f"[Print Analyzer] Analyzing schematic (caption: {caption})")

        prompt = """Analyze this technical schematic/diagram in detail.

Provide a comprehensive analysis including:

1. **Diagram Type**
   - What type of diagram is this? (ladder logic, electrical schematic, P&ID, wiring diagram, control panel layout, etc.)
   - Industry/application area (manufacturing, process control, building automation, etc.)

2. **Key Components Identified**
   - List all major components visible (PLCs, motors, contactors, relays, sensors, etc.)
   - Include component identifiers/labels if visible (M1, CR1, PLC-01, etc.)
   - Note any manufacturer-specific equipment

3. **System Overview**
   - What is the overall function/purpose of this system?
   - Main control logic or electrical flow
   - Input/output relationships

4. **Power Distribution**
   - Voltage levels identified (120V, 240V, 480V, 24VDC, etc.)
   - Power sources and distribution
   - Grounding and bonding

5. **Safety Features**
   - E-stops, safety relays, interlocks
   - Overcurrent protection (fuses, breakers)
   - Any safety-critical components or circuits

6. **Notable Features or Concerns**
   - Any unusual configurations
   - Potential issues or areas of concern
   - Missing or unclear information

Be specific with component identifiers and connections. Use technical terminology appropriate for industrial electricians and controls engineers."""

        if caption:
            prompt = f"User context: {caption}\n\n{prompt}"

        # Use vision capability with high-quality model for technical accuracy
        response = await self.router.call_vision(
            image_bytes=image_bytes,
            prompt=prompt,
            capability=ModelCapability.COMPLEX,  # Use GPT-4o or Claude Sonnet for technical diagrams
            max_tokens=2000,
        )

        logger.info(
            f"[Print Analyzer] Analysis complete: "
            f"cost=${response.cost_usd:.6f}, "
            f"length={len(response.text)} chars"
        )

        return response.text

    @traced(name="print_question", tags=["schematic", "vision", "qa"])
    async def answer_question(
        self,
        image_bytes: bytes,
        question: str,
    ) -> str:
        """
        Answer specific question about schematic.

        Args:
            image_bytes: Raw image bytes of the schematic/diagram
            question: User's specific question about the diagram

        Returns:
            Detailed answer to the question with reference to diagram elements

        Example:
            >>> analyzer = PrintAnalyzer()
            >>> result = await analyzer.answer_question(
            ...     image_bytes,
            ...     "What is the voltage rating of motor M1?"
            ... )
            >>> print(result)
        """
        logger.info(f"[Print Analyzer] Answering question: {question[:100]}...")

        prompt = f"""Analyze this technical schematic/diagram and answer the following question:

**Question:** {question}

Provide a detailed answer that:
1. References specific components or areas in the diagram (use labels/identifiers if visible)
2. Explains the technical reasoning
3. Cites any visible specifications, ratings, or values
4. Notes any safety considerations if relevant
5. Acknowledges if information is unclear or not visible in the diagram

Be specific and technical. If you cannot determine something from the diagram, clearly state what additional information would be needed."""

        response = await self.router.call_vision(
            image_bytes=image_bytes,
            prompt=prompt,
            capability=ModelCapability.COMPLEX,
            max_tokens=1500,
        )

        logger.info(
            f"[Print Analyzer] Question answered: "
            f"cost=${response.cost_usd:.6f}"
        )

        return response.text

    @traced(name="print_fault_location", tags=["schematic", "vision", "troubleshooting"])
    async def identify_fault_location(
        self,
        image_bytes: bytes,
        fault_description: str,
    ) -> str:
        """
        Identify where fault might be occurring in schematic.

        Args:
            image_bytes: Raw image bytes of the schematic/diagram
            fault_description: Description of the fault/symptom

        Returns:
            Analysis of likely fault locations and troubleshooting guidance

        Example:
            >>> analyzer = PrintAnalyzer()
            >>> result = await analyzer.identify_fault_location(
            ...     image_bytes,
            ...     "Motor M1 trips after 10 seconds"
            ... )
            >>> print(result)
        """
        logger.info(f"[Print Analyzer] Identifying fault location: {fault_description[:100]}...")

        prompt = f"""Analyze this technical schematic/diagram to identify where the following fault might be occurring:

**Fault/Symptom:** {fault_description}

Provide troubleshooting guidance including:

1. **Likely Fault Locations** (ranked by probability)
   - Identify specific components or circuit sections to check
   - Reference component labels/identifiers visible in diagram
   - Explain why each location is suspect

2. **Diagnostic Procedure**
   - Step-by-step troubleshooting sequence
   - What to measure/check at each point
   - Expected readings vs. fault conditions

3. **Test Points**
   - Where to place multimeter probes
   - What signals/voltages to check
   - Reference wire numbers or terminal labels if visible

4. **Safety Warnings**
   - Voltage hazards at test points
   - Required PPE (voltage-rated gloves, etc.)
   - LOTO requirements
   - Arc flash considerations

5. **Common Causes**
   - Typical failure modes for this symptom
   - Related components to inspect
   - Environmental factors to consider

Be specific with component identifiers, test points, and voltage levels. Prioritize electrician safety."""

        response = await self.router.call_vision(
            image_bytes=image_bytes,
            prompt=prompt,
            capability=ModelCapability.COMPLEX,
            max_tokens=2000,
        )

        logger.info(
            f"[Print Analyzer] Fault location identified: "
            f"cost=${response.cost_usd:.6f}"
        )

        return response.text


# Convenience function for quick schematic analysis
async def analyze_schematic(image_bytes: bytes, caption: Optional[str] = None) -> str:
    """
    Quick schematic analysis.

    Args:
        image_bytes: Raw image bytes
        caption: Optional user description

    Returns:
        Analysis text

    Example:
        >>> result = await analyze_schematic(image_bytes, "motor control diagram")
        >>> print(result)
    """
    analyzer = PrintAnalyzer()
    return await analyzer.analyze(image_bytes, caption)


if __name__ == "__main__":
    import asyncio

    # Test print analyzer (requires actual schematic image)
    async def test_analyzer():
        print("\n=== Print Analyzer Test ===\n")

        # This would need a real schematic image file
        # For demonstration, we'd need to load an image:
        # with open("test_schematic.jpg", "rb") as f:
        #     image_bytes = f.read()

        # analyzer = PrintAnalyzer()

        # Test 1: Full analysis
        # result = await analyzer.analyze(image_bytes, "ladder logic diagram")
        # print(f"Analysis:\n{result}\n")

        # Test 2: Specific question
        # result = await analyzer.answer_question(
        #     image_bytes,
        #     "What is the voltage rating of the main contactor?"
        # )
        # print(f"Answer:\n{result}\n")

        # Test 3: Fault identification
        # result = await analyzer.identify_fault_location(
        #     image_bytes,
        #     "Motor trips immediately after start button pressed"
        # )
        # print(f"Fault Analysis:\n{result}\n")

        print("Print analyzer ready (need actual schematic image for testing)")

    asyncio.run(test_analyzer())
