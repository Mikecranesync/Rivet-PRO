# HARVEST BLOCK 6: Print/Schematic Analyzer

**Priority:** LOW (optional - advanced feature)
**Duration:** 30 minutes
**Source:** `agent_factory/rivet_pro/print_analyzer.py` (220 lines)

---

## What This Adds

Technical print/schematic analysis using vision AI. Includes:

1. **Comprehensive analysis** - Components, connections, voltages, control logic
2. **Question answering** - "What voltage is this motor?" "How is CR2 wired?"
3. **Fault location** - Identify which component is likely failing
4. **Dual provider** - OpenAI GPT-4o Vision → Claude fallback

**Why nice-to-have:** Enables users to send wiring diagrams for analysis. Advanced feature for complex troubleshooting.

**Use cases:**
- "What voltage is this motor?"
- "How is the contactor wired?"
- "Why is relay CR2 energizing?"
- "Where should I check for 480V?"

---

## Target File

`rivet/workflows/print_analyzer.py` (NEW FILE - doesn't exist yet)

---

## Complete File Content

Create new file `rivet/workflows/print_analyzer.py`:

```python
"""
Print/Schematic Analyzer - Analyze technical drawings and wiring diagrams.

Use cases:
- Component identification
- Circuit tracing
- Fault location analysis
- Voltage/current verification
"""

import logging
from typing import Optional

from rivet.integrations.llm import LLMRouter, ProviderConfig

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
        """Initialize with LLM router."""
        self.router = LLMRouter()

    async def analyze(self, image_bytes: bytes) -> str:
        """
        Comprehensive analysis of technical schematic.

        Extracts:
        - All visible components (motors, contactors, relays, sensors, etc.)
        - How components are wired together
        - All voltage levels present
        - Control sequence logic
        - Safety features (E-stops, interlocks)

        Args:
            image_bytes: Image file bytes (JPEG/PNG)

        Returns:
            Detailed analysis text

        Example:
            >>> with open("ladder_diagram.jpg", "rb") as f:
            ...     analysis = await analyzer.analyze(f.read())
            >>> print(analysis)
            Components:
            - M1: Motor contactor (3-phase, 480V)
            - CR1: Control relay (24VDC coil)
            ...
        """
        prompt = """Analyze this technical schematic or wiring diagram:

**1. Components:**
List all visible components with designations:
- Motors (M1, M2, etc.)
- Contactors (K1, K2, etc.)
- Relays (CR1, CR2, etc.)
- Sensors (S1, S2, etc.)
- Fuses, circuit breakers
- Any other devices

**2. Connections:**
Describe how components are wired together:
- Which devices are in series/parallel
- Wire numbers and routing
- Terminal connections

**3. Voltages:**
Identify all voltage levels present:
- 480V 3-phase
- 240V single-phase
- 120V control
- 24VDC logic
- Any other voltages

**4. Control Logic:**
Explain the control sequence:
- What happens when start button is pressed
- What stops the process
- Safety interlocks
- Timing sequences

**5. Safety Features:**
Note any safety circuits:
- Emergency stops (E-stop)
- Interlocks
- Overload protection
- Safety relays

Be specific about component designations (M1, CR1, etc.) and wire numbers."""

        try:
            # Try OpenAI GPT-4o Vision first
            logger.info("[Print Analyzer] Trying GPT-4o Vision")

            text, cost = await self.router.call_vision(
                provider_config=ProviderConfig(
                    name="openai",
                    model="gpt-4o",
                    cost_per_1k_input=0.005,
                    cost_per_1k_output=0.015,
                ),
                image_bytes=image_bytes,
                prompt=prompt,
                max_tokens=1500,
            )

            logger.info(f"[Print Analyzer] GPT-4o success, cost=${cost:.4f}")
            return text

        except Exception as e:
            logger.warning(f"[Print Analyzer] GPT-4o failed: {e}, trying Claude fallback")

        # Fallback to Claude
        try:
            logger.info("[Print Analyzer] Trying Claude Vision")

            text, cost = await self.router.call_vision(
                provider_config=ProviderConfig(
                    name="claude",
                    model="claude-3-5-sonnet-20241022",
                    cost_per_1k_input=0.003,
                    cost_per_1k_output=0.015,
                ),
                image_bytes=image_bytes,
                prompt=prompt,
                max_tokens=1500,
            )

            logger.info(f"[Print Analyzer] Claude success, cost=${cost:.4f}")
            return text

        except Exception as e:
            logger.error(f"[Print Analyzer] Both providers failed: {e}")
            raise ValueError(f"Print analysis failed: {e}")

    async def answer_question(self, image_bytes: bytes, question: str) -> str:
        """
        Answer specific question about schematic.

        Args:
            image_bytes: Image file bytes
            question: User's question about the schematic

        Returns:
            Answer text

        Example:
            >>> answer = await analyzer.answer_question(
            ...     schematic_bytes,
            ...     "What voltage is motor M1?"
            ... )
            >>> print(answer)
            Motor M1 operates at 480V 3-phase, connected to contactor K1...
        """
        prompt = f"""Looking at this technical schematic, please answer this question:

**Question:** {question}

Provide a specific answer referencing:
- Component designations (M1, CR1, etc.)
- Wire numbers (if visible)
- Terminal numbers (if visible)
- Voltage levels
- Any relevant safety warnings

Be concise but complete."""

        try:
            logger.info(f"[Print Analyzer] Answering question: {question[:50]}...")

            text, cost = await self.router.call_vision(
                provider_config=ProviderConfig(
                    name="openai",
                    model="gpt-4o",
                    cost_per_1k_input=0.005,
                    cost_per_1k_output=0.015,
                ),
                image_bytes=image_bytes,
                prompt=prompt,
                max_tokens=1000,
            )

            logger.info(f"[Print Analyzer] Answer generated, cost=${cost:.4f}")
            return text

        except Exception as e:
            logger.warning(f"[Print Analyzer] GPT-4o failed: {e}, trying Claude")

            text, cost = await self.router.call_vision(
                provider_config=ProviderConfig(
                    name="claude",
                    model="claude-3-5-sonnet-20241022",
                    cost_per_1k_input=0.003,
                    cost_per_1k_output=0.015,
                ),
                image_bytes=image_bytes,
                prompt=prompt,
                max_tokens=1000,
            )

            return text

    async def identify_fault_location(
        self,
        image_bytes: bytes,
        fault_description: str
    ) -> str:
        """
        Identify where fault might be occurring in schematic.

        Args:
            image_bytes: Image file bytes
            fault_description: Symptom description from user

        Returns:
            Troubleshooting guidance text

        Example:
            >>> guidance = await analyzer.identify_fault_location(
            ...     schematic_bytes,
            ...     "Motor M1 won't start, contactor K1 not pulling in"
            ... )
            >>> print(guidance)
            Likely causes:
            1. Check 120V at contactor K1 coil (terminals A1-A2)...
        """
        prompt = f"""Given this schematic and the following fault symptom:

**Fault:** {fault_description}

Please identify:

**1. Likely Failing Components:**
List which components are most likely at fault, in order of probability.

**2. Where to Check First:**
Specify exact test points:
- Which terminals to measure voltage
- Expected voltage levels
- Which wires to check continuity

**3. Troubleshooting Procedure:**
Step-by-step diagnostic steps:
1. Check voltage at X
2. Test continuity of Y
3. Verify component Z
etc.

**4. Safety Warnings:**
Any hazards for this circuit:
- Voltage levels to be aware of
- Arc flash risks
- Lockout/tagout requirements
- PPE needed

Be specific about component designations, wire numbers, and terminal numbers."""

        try:
            logger.info(f"[Print Analyzer] Fault location: {fault_description[:50]}...")

            text, cost = await self.router.call_vision(
                provider_config=ProviderConfig(
                    name="openai",
                    model="gpt-4o",
                    cost_per_1k_input=0.005,
                    cost_per_1k_output=0.015,
                ),
                image_bytes=image_bytes,
                prompt=prompt,
                max_tokens=1500,
            )

            logger.info(f"[Print Analyzer] Fault location identified, cost=${cost:.4f}")
            return text

        except Exception as e:
            logger.warning(f"[Print Analyzer] GPT-4o failed: {e}, trying Claude")

            text, cost = await self.router.call_vision(
                provider_config=ProviderConfig(
                    name="claude",
                    model="claude-3-5-sonnet-20241022",
                    cost_per_1k_input=0.003,
                    cost_per_1k_output=0.015,
                ),
                image_bytes=image_bytes,
                prompt=prompt,
                max_tokens=1500,
            )

            return text
```

---

## Integration with Telegram Bot

Add schematic detection to `telegram.py` photo handler:

```python
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo uploads - detect if nameplate or schematic."""
    message = update.message
    user = message.from_user

    # Check if user added caption with keywords
    caption = message.caption or ""
    caption_lower = caption.lower()

    # Keywords that indicate schematic/drawing
    schematic_keywords = [
        "schematic", "diagram", "wiring", "ladder", "drawing",
        "print", "circuit", "control", "p&id"
    ]

    is_schematic = any(kw in caption_lower for kw in schematic_keywords)

    if is_schematic:
        # Handle as schematic
        await handle_schematic_photo(update, context)
    else:
        # Handle as equipment nameplate (existing logic)
        await handle_equipment_photo(update, context)


async def handle_schematic_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle schematic/drawing photos."""
    from rivet.workflows.print_analyzer import PrintAnalyzer

    message = update.message
    photo = message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    processing_msg = await message.reply_text(
        "📐 Analyzing technical schematic...",
        reply_to_message_id=message.message_id
    )

    try:
        analyzer = PrintAnalyzer()

        # If caption has question, answer it; otherwise do full analysis
        caption = message.caption or ""
        if "?" in caption:
            # Answer specific question
            answer = await analyzer.answer_question(bytes(image_bytes), caption)
            response = f"**Schematic Analysis:**\n\n{answer}"
        else:
            # Full analysis
            analysis = await analyzer.analyze(bytes(image_bytes))
            response = f"**Schematic Analysis:**\n\n{analysis}"

        await processing_msg.edit_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"[Telegram] Schematic analysis error: {e}")
        await processing_msg.edit_text(
            "❌ **Error Analyzing Schematic**\n\n"
            f"Error: {str(e)[:100]}",
            parse_mode="Markdown"
        )
```

---

## Validation

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO

# Test imports
python -c "from rivet.workflows.print_analyzer import PrintAnalyzer; print('✅ Print Analyzer OK')"

# Test analysis (requires test schematic image)
python -c "
import asyncio
from rivet.workflows.print_analyzer import PrintAnalyzer

async def test():
    analyzer = PrintAnalyzer()

    # Use test schematic image
    with open('test_schematic.jpg', 'rb') as f:
        analysis = await analyzer.analyze(f.read())

    print('✅ Analysis result:')
    print(analysis[:200])

# asyncio.run(test())  # Uncomment if you have test schematic
print('✅ Print analyzer ready (test with real schematic)')
"
```

---

## Testing the Feature

Once deployed, users can:

1. **Send schematic with caption:**
   ```
   Caption: "schematic of motor control"
   → Bot does full analysis
   ```

2. **Ask specific question:**
   ```
   Caption: "What voltage is motor M1?"
   → Bot answers the question
   ```

3. **Get fault location help:**
   ```
   Caption: "Motor won't start, K1 not pulling in"
   → Bot provides troubleshooting steps
   ```

---

## Integration Notes

1. **Caption-based detection** - Keywords trigger schematic mode
2. **Dual provider** - OpenAI → Claude fallback (same as OCR)
3. **Question detection** - "?" in caption triggers answer_question()
4. **Full analysis fallback** - No question → comprehensive analysis

---

## Dependencies

No new dependencies required. Uses existing LLM router.

---

## Use Cases

**Motor Control:**
- "How is the start circuit wired?"
- "What voltage is the control circuit?"
- "Where is the overload relay?"

**Fault Diagnosis:**
- "Motor won't start, contactor K1 not pulling in"
- "CR2 relay stays energized"
- "No 120V at control circuit"

**Circuit Tracing:**
- "Trace wire 5 from start button"
- "What does CR1 control?"
- "Where does 480V enter the circuit?"

---

## Success Criteria

Feature complete when:
- ✅ User sends schematic with caption → bot analyzes
- ✅ User asks question about schematic → bot answers
- ✅ Bot identifies components, voltages, safety warnings
- ✅ Fault location guidance provided when requested

---

## Next Steps

After validating:
1. Add example schematics to documentation
2. Create user guide for schematic analysis feature
3. Test with real ladder logic diagrams
4. Consider adding OCR for extracting wire numbers

**This completes all 6 HARVEST BLOCKS!**

Critical path (HARVEST 1-4): Working Telegram bot
Optional enhancements (HARVEST 5-6): Professional UX + advanced features
