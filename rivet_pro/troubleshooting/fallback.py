"""
Claude API Fallback for Unknown Equipment Troubleshooting

When equipment has no predefined troubleshooting tree, this module dynamically
generates step-by-step troubleshooting guidance using Claude API.

Features:
- Detects missing troubleshooting trees
- Calls Anthropic Claude API with structured prompts
- Generates numbered troubleshooting steps
- Formats responses for Telegram with proper escaping
- Offers to save generated guides as tree drafts

Usage:
    from rivet_pro.troubleshooting.fallback import generate_troubleshooting_guide

    result = await generate_troubleshooting_guide(
        equipment_type="Siemens S7-1200 PLC",
        problem="Communication fault",
        context="Profinet connection lost"
    )
"""

import logging
import os
import re
from typing import Dict, List, Optional, TypedDict
from anthropic import Anthropic, AsyncAnthropic
from rivet_pro.config.settings import settings

logger = logging.getLogger(__name__)


class TroubleshootingGuide(TypedDict):
    """Generated troubleshooting guide structure"""
    equipment_type: str
    problem: str
    steps: List[str]
    formatted_text: str
    can_save: bool
    raw_response: str


class ClaudeFallbackError(Exception):
    """Raised when Claude API fallback fails"""
    pass


def _escape_telegram_markdown(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2.

    MarkdownV2 requires escaping: _ * [ ] ( ) ~ ` > # + - = | { } . !

    Args:
        text: Raw text to escape

    Returns:
        Telegram-safe markdown text

    Examples:
        >>> _escape_telegram_markdown("Motor temp: 85°C (warning)")
        "Motor temp: 85°C \\(warning\\)"
    """
    # Characters that need escaping in MarkdownV2
    special_chars = r'_*[]()~`>#+-=|{}.!'

    # Escape each special character
    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    return text


def _format_step_for_telegram(step_num: int, step_text: str) -> str:
    """
    Format a single troubleshooting step for Telegram display.

    Args:
        step_num: Step number (1-indexed)
        step_text: Step description

    Returns:
        Formatted step with number and escaped text
    """
    # Remove any existing numbering from Claude's response
    clean_text = re.sub(r'^\d+[\.\)]\s*', '', step_text.strip())

    # Escape for Telegram
    escaped_text = _escape_telegram_markdown(clean_text)

    return f"*{step_num}\\.* {escaped_text}"


def _build_troubleshooting_prompt(
    equipment_type: str,
    problem: str,
    context: Optional[str] = None
) -> str:
    """
    Build the system prompt for Claude to generate troubleshooting steps.

    Args:
        equipment_type: Type of equipment (e.g., "Siemens S7-1200 PLC")
        problem: Problem description (e.g., "Communication fault")
        context: Additional context (e.g., "Profinet connection lost")

    Returns:
        Formatted prompt for Claude API
    """
    prompt = f"""You are an expert industrial maintenance technician specializing in {equipment_type}.

A technician is experiencing the following issue:
- Equipment: {equipment_type}
- Problem: {problem}"""

    if context:
        prompt += f"\n- Additional Context: {context}"

    prompt += """

Generate a step-by-step troubleshooting guide with 5-8 actionable diagnostic steps.

Requirements:
1. Each step must be specific and actionable (not vague)
2. Steps should follow a logical diagnostic flow (check simple things first)
3. Include safety warnings where relevant
4. Use clear, concise language a field technician can follow
5. Include expected results or what to look for
6. Number each step clearly (1., 2., 3., etc.)

Format your response as a numbered list ONLY. Do not include introductions, conclusions, or explanations outside the steps.

Example format:
1. Check physical power connection at terminals L1, L2, L3 - verify 24VDC is present
2. Inspect Ethernet cable for damage - should have solid green link LED
3. Verify IP address configuration in TIA Portal - must match network subnet
...

Generate the troubleshooting steps now:"""

    return prompt


async def generate_troubleshooting_guide(
    equipment_type: str,
    problem: str,
    context: Optional[str] = None,
    max_tokens: int = 1024
) -> TroubleshootingGuide:
    """
    Generate dynamic troubleshooting guide using Claude API.

    This function is called when no predefined troubleshooting tree exists
    for the equipment type. It uses Claude API to generate contextual
    troubleshooting steps based on equipment type and problem description.

    Args:
        equipment_type: Type of equipment (e.g., "Siemens S7-1200 PLC")
        problem: Problem description (e.g., "Communication fault")
        context: Additional context (e.g., "Profinet connection lost")
        max_tokens: Maximum tokens for Claude response (default: 1024)

    Returns:
        TroubleshootingGuide dictionary with steps and formatted text

    Raises:
        ClaudeFallbackError: If API call fails or response is invalid

    Example:
        >>> guide = await generate_troubleshooting_guide(
        ...     equipment_type="Siemens S7-1200 PLC",
        ...     problem="Communication fault",
        ...     context="Profinet connection lost"
        ... )
        >>> print(guide["formatted_text"])
        🔧 Troubleshooting: Siemens S7-1200 PLC
        Problem: Communication fault

        *1.* Check physical power connection...
        *2.* Inspect Ethernet cable...
        ...
    """
    # Validate inputs
    if not equipment_type or not equipment_type.strip():
        raise ClaudeFallbackError("equipment_type cannot be empty")

    if not problem or not problem.strip():
        raise ClaudeFallbackError("problem cannot be empty")

    # Get API key from settings
    api_key = settings.anthropic_api_key
    if not api_key:
        raise ClaudeFallbackError(
            "ANTHROPIC_API_KEY not found in environment. "
            "Cannot generate dynamic troubleshooting guide."
        )

    logger.info(
        f"Generating troubleshooting guide for {equipment_type} - {problem}",
        extra={"equipment_type": equipment_type, "problem": problem, "context": context}
    )

    # Build prompt
    prompt = _build_troubleshooting_prompt(equipment_type, problem, context)

    # Call Claude API
    try:
        client = AsyncAnthropic(api_key=api_key)

        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Use latest Sonnet model
            max_tokens=max_tokens,
            temperature=0.3,  # Low temperature for consistent, factual responses
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Extract text from response
        if not response.content or len(response.content) == 0:
            raise ClaudeFallbackError("Claude API returned empty response")

        raw_text = response.content[0].text.strip()

        logger.info(
            f"Received troubleshooting guide from Claude API ({len(raw_text)} chars)",
            extra={
                "response_length": len(raw_text),
                "model": response.model,
                "usage": response.usage.dict() if response.usage else None
            }
        )

    except Exception as e:
        logger.error(f"Claude API call failed: {e}", exc_info=True)
        raise ClaudeFallbackError(f"Failed to generate troubleshooting guide: {str(e)}")

    # Parse response into numbered steps
    steps = _parse_numbered_steps(raw_text)

    if not steps or len(steps) == 0:
        logger.error(f"Failed to parse steps from Claude response: {raw_text[:200]}")
        raise ClaudeFallbackError("Could not extract troubleshooting steps from response")

    # Format for Telegram
    formatted_text = _format_guide_for_telegram(
        equipment_type=equipment_type,
        problem=problem,
        steps=steps,
        context=context
    )

    logger.info(f"Successfully generated {len(steps)} troubleshooting steps")

    return TroubleshootingGuide(
        equipment_type=equipment_type,
        problem=problem,
        steps=steps,
        formatted_text=formatted_text,
        can_save=True,  # Always offer to save generated guides
        raw_response=raw_text
    )


def _parse_numbered_steps(text: str) -> List[str]:
    """
    Parse numbered steps from Claude's response.

    Handles various numbering formats:
    - "1. Step text"
    - "1) Step text"
    - "1: Step text"
    - "Step 1: text"

    Args:
        text: Raw text from Claude API

    Returns:
        List of step descriptions (without numbering)
    """
    # Split by lines
    lines = text.strip().split('\n')
    steps = []

    # Pattern to match numbered steps
    # Matches: "1.", "1)", "1:", or "Step 1:"
    pattern = re.compile(r'^(?:Step\s+)?(\d+)[\.\)\:]\s*(.+)')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = pattern.match(line)
        if match:
            step_text = match.group(2).strip()
            if step_text:
                steps.append(step_text)

    return steps


def _format_guide_for_telegram(
    equipment_type: str,
    problem: str,
    steps: List[str],
    context: Optional[str] = None
) -> str:
    """
    Format the complete troubleshooting guide for Telegram display.

    Args:
        equipment_type: Type of equipment
        problem: Problem description
        steps: List of troubleshooting steps
        context: Additional context

    Returns:
        Telegram MarkdownV2 formatted text
    """
    # Escape header text
    escaped_equipment = _escape_telegram_markdown(equipment_type)
    escaped_problem = _escape_telegram_markdown(problem)

    # Build header
    lines = [
        "🔧 *Troubleshooting Guide*",
        "",
        f"*Equipment:* {escaped_equipment}",
        f"*Problem:* {escaped_problem}",
    ]

    if context:
        escaped_context = _escape_telegram_markdown(context)
        lines.append(f"*Context:* {escaped_context}")

    lines.append("")
    lines.append("*Steps:*")
    lines.append("")

    # Add each step
    for i, step in enumerate(steps, start=1):
        formatted_step = _format_step_for_telegram(i, step)
        lines.append(formatted_step)
        lines.append("")  # Blank line between steps

    # Add save option footer
    lines.append("💾 _Want to save this guide for future use?_")
    lines.append("Tap *Save Guide* below\\.")

    return '\n'.join(lines)


def check_tree_exists(equipment_type: str) -> bool:
    """
    Check if a troubleshooting tree exists for the equipment type.

    This function queries the database to see if there's a predefined
    troubleshooting tree for this equipment type.

    Args:
        equipment_type: Type of equipment to check

    Returns:
        True if tree exists, False if fallback needed

    Note:
        This is a placeholder. Actual implementation should query
        the troubleshooting_trees table in PostgreSQL.
    """
    # TODO: Implement database query
    # Example query:
    # SELECT COUNT(*) FROM troubleshooting_trees
    # WHERE equipment_type ILIKE %s
    # LIMIT 1

    logger.warning(
        f"check_tree_exists not yet implemented - assuming no tree for {equipment_type}"
    )
    return False


async def get_or_generate_troubleshooting(
    equipment_type: str,
    problem: str,
    context: Optional[str] = None
) -> TroubleshootingGuide:
    """
    Get existing troubleshooting tree or generate new guide via Claude API.

    This is the main entry point for troubleshooting flow. It first checks
    if a predefined tree exists, and falls back to Claude API if not.

    Args:
        equipment_type: Type of equipment
        problem: Problem description
        context: Additional context

    Returns:
        TroubleshootingGuide with steps and formatted text

    Example:
        >>> guide = await get_or_generate_troubleshooting(
        ...     equipment_type="Siemens S7-1200 PLC",
        ...     problem="Communication fault"
        ... )
        >>> print(guide["formatted_text"])
    """
    # Check if tree exists
    has_tree = check_tree_exists(equipment_type)

    if has_tree:
        logger.info(f"Found existing troubleshooting tree for {equipment_type}")
        # TODO: Load and return tree from database
        raise NotImplementedError("Tree loading not yet implemented")

    # No tree found - generate via Claude API
    logger.info(f"No tree found for {equipment_type} - using Claude fallback")
    return await generate_troubleshooting_guide(
        equipment_type=equipment_type,
        problem=problem,
        context=context
    )


# Synchronous wrapper for non-async contexts
def generate_troubleshooting_guide_sync(
    equipment_type: str,
    problem: str,
    context: Optional[str] = None,
    max_tokens: int = 1024
) -> TroubleshootingGuide:
    """
    Synchronous version of generate_troubleshooting_guide.

    Uses the sync Anthropic client instead of async.

    Args:
        equipment_type: Type of equipment
        problem: Problem description
        context: Additional context
        max_tokens: Maximum tokens for Claude response

    Returns:
        TroubleshootingGuide dictionary

    Raises:
        ClaudeFallbackError: If API call fails
    """
    # Validate inputs
    if not equipment_type or not equipment_type.strip():
        raise ClaudeFallbackError("equipment_type cannot be empty")

    if not problem or not problem.strip():
        raise ClaudeFallbackError("problem cannot be empty")

    # Get API key
    api_key = settings.anthropic_api_key
    if not api_key:
        raise ClaudeFallbackError("ANTHROPIC_API_KEY not found in environment")

    logger.info(f"Generating troubleshooting guide (sync) for {equipment_type}")

    # Build prompt
    prompt = _build_troubleshooting_prompt(equipment_type, problem, context)

    # Call Claude API (sync)
    try:
        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            temperature=0.3,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        raw_text = response.content[0].text.strip()
        logger.info(f"Received guide from Claude API ({len(raw_text)} chars)")

    except Exception as e:
        logger.error(f"Claude API call failed: {e}", exc_info=True)
        raise ClaudeFallbackError(f"Failed to generate guide: {str(e)}")

    # Parse and format
    steps = _parse_numbered_steps(raw_text)
    if not steps:
        raise ClaudeFallbackError("Could not extract steps from response")

    formatted_text = _format_guide_for_telegram(
        equipment_type=equipment_type,
        problem=problem,
        steps=steps,
        context=context
    )

    return TroubleshootingGuide(
        equipment_type=equipment_type,
        problem=problem,
        steps=steps,
        formatted_text=formatted_text,
        can_save=True,
        raw_response=raw_text
    )


if __name__ == '__main__':
    # Demo/testing
    import asyncio

    async def demo():
        print("=== Claude Fallback Demo ===\n")

        # Test case 1: PLC communication issue
        guide = await generate_troubleshooting_guide(
            equipment_type="Siemens S7-1200 PLC",
            problem="Communication fault",
            context="Profinet connection lost to HMI"
        )

        print("Generated guide:")
        print(guide["formatted_text"])
        print(f"\nTotal steps: {len(guide['steps'])}")
        print(f"Can save: {guide['can_save']}")

        # Test case 2: Motor overheating
        print("\n" + "="*50 + "\n")

        guide2 = await generate_troubleshooting_guide(
            equipment_type="ABB M3BP 315 SMB Motor",
            problem="Overheating during operation",
            context="Motor reaches 95°C within 30 minutes of startup"
        )

        print("Generated guide:")
        print(guide2["formatted_text"])

    # Run demo
    asyncio.run(demo())
