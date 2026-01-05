"""
Response Synthesis - Format agent responses with citations and safety warnings.

Provides functions to enhance raw LLM responses with:
- Inline citations [1], [2] with source footnotes
- Safety warning extraction and highlighting
- Confidence badges
- Troubleshooting step checkboxes
"""

import re
from typing import List, Dict, Any


def add_citations(text: str, sources: List[Dict[str, str]]) -> str:
    """
    Add inline citations [1], [2] and footer with sources.

    Args:
        text: Raw agent response
        sources: List of {"title": "...", "url": "..."} dicts

    Returns:
        Text with sources footer

    Example:
        >>> sources = [
        ...     {"title": "Siemens Manual", "url": "https://example.com/manual.pdf"}
        ... ]
        >>> add_citations("Check the parameters", sources)
        'Check the parameters\n\n**Sources:**\n[1] Siemens Manual - https://...'
    """
    if not sources:
        return text

    # Add citations footer
    footer = "\n\n**Sources:**\n"
    for i, source in enumerate(sources, 1):
        title = source.get("title", "Unknown")
        url = source.get("url", "")
        footer += f"[{i}] {title}"
        if url:
            footer += f" - {url}"
        footer += "\n"

    return text + footer


def extract_safety_warnings(text: str) -> List[Dict[str, str]]:
    """
    Extract safety warnings from response text.

    Detects keywords and classifies by severity:
    - DANGER: High voltage, arc flash, electrocution, fatal
    - WARNING: VFD DC bus, capacitor, moving parts, pinch point
    - CAUTION: PPE required, lockout/tagout

    Returns:
        List of {"severity": "DANGER|WARNING|CAUTION", "text": "..."}

    Example:
        >>> text = "Warning: High voltage 480V system. Use PPE."
        >>> extract_safety_warnings(text)
        [{'severity': 'DANGER', 'text': 'Warning: High voltage 480V system.'},
         {'severity': 'CAUTION', 'text': 'Use PPE.'}]
    """
    warnings = []

    # DANGER keywords
    danger_patterns = [
        r"480v", r"high voltage", r"arc flash", r"electrocution",
        r"lethal", r"fatal", r"death", r"severe injury"
    ]

    # WARNING keywords
    warning_patterns = [
        r"vfd", r"dc bus", r"capacitor", r"residual voltage",
        r"moving parts", r"pinch point", r"crush hazard"
    ]

    # CAUTION keywords
    caution_patterns = [
        r"ppe required", r"gloves", r"face shield", r"safety glasses",
        r"lockout", r"tagout", r"loto"
    ]

    text_lower = text.lower()

    # Extract paragraphs with safety content
    for line in text.split('\n'):
        line_lower = line.lower()

        # Check for DANGER
        if any(re.search(p, line_lower) for p in danger_patterns):
            warnings.append({
                "severity": "DANGER",
                "text": line.strip()
            })
        # Check for WARNING
        elif any(re.search(p, line_lower) for p in warning_patterns):
            warnings.append({
                "severity": "WARNING",
                "text": line.strip()
            })
        # Check for CAUTION
        elif any(re.search(p, line_lower) for p in caution_patterns):
            warnings.append({
                "severity": "CAUTION",
                "text": line.strip()
            })

    return warnings


def format_safety_section(warnings: List[Dict[str, str]]) -> str:
    """
    Format safety warnings as prominent section.

    Sorts by severity (DANGER > WARNING > CAUTION) and adds emojis.

    Args:
        warnings: List from extract_safety_warnings()

    Returns:
        Formatted Markdown safety section

    Example:
        >>> warnings = [
        ...     {"severity": "DANGER", "text": "High voltage 480V"},
        ...     {"severity": "CAUTION", "text": "PPE required"}
        ... ]
        >>> print(format_safety_section(warnings))
        ⚠️ **SAFETY WARNINGS**
        🔴 **DANGER:** High voltage 480V
        🟢 **CAUTION:** PPE required
    """
    if not warnings:
        return ""

    # Sort by severity
    severity_order = {"DANGER": 0, "WARNING": 1, "CAUTION": 2}
    sorted_warnings = sorted(warnings, key=lambda w: severity_order.get(w["severity"], 3))

    section = "\n\n⚠️ **SAFETY WARNINGS**\n\n"

    for warning in sorted_warnings:
        emoji = {
            "DANGER": "🔴",
            "WARNING": "🟡",
            "CAUTION": "🟢"
        }.get(warning["severity"], "⚠️")

        section += f"{emoji} **{warning['severity']}:** {warning['text']}\n\n"

    return section


def format_troubleshooting_steps(text: str) -> str:
    """
    Format numbered steps with checkboxes for user to track progress.

    Finds patterns like "1. Step" or "Step 1:" and adds ☐ checkbox.

    Args:
        text: Response with numbered steps

    Returns:
        Text with checkboxes added

    Example:
        >>> text = "1. Check power\\n2. Reset fault"
        >>> print(format_troubleshooting_steps(text))
        ☐ 1. Check power
        ☐ 2. Reset fault
    """
    lines = text.split('\n')
    formatted_lines = []

    for line in lines:
        # Match patterns like "1. Step" or "Step 1:" or "1) Step"
        if re.match(r'^\d+[\.\):]?\s+', line):
            # Add checkbox
            formatted_lines.append("☐ " + line)
        else:
            formatted_lines.append(line)

    return '\n'.join(formatted_lines)


def add_confidence_badge(text: str, confidence: float) -> str:
    """
    Add confidence indicator at top of response.

    Args:
        text: Response text
        confidence: Confidence score 0.0-1.0

    Returns:
        Text with confidence badge prepended

    Example:
        >>> add_confidence_badge("Answer here", 0.92)
        '🟢 **High Confidence**\n\nAnswer here'
    """
    if confidence >= 0.85:
        badge = "🟢 **High Confidence**"
    elif confidence >= 0.70:
        badge = "🟡 **Medium Confidence**"
    else:
        badge = "🔴 **Limited Confidence** - Consider consulting vendor documentation"

    return f"{badge}\n\n{text}"


def synthesize_response(
    answer: str,
    confidence: float,
    sources: List[Dict[str, str]] = None,
    safety_warnings: List[str] = None
) -> str:
    """
    Full response synthesis pipeline.

    Applies all formatting:
    1. Confidence badge at top
    2. Checkboxes on troubleshooting steps
    3. Citations footer
    4. Safety warnings section

    Args:
        answer: Raw agent response
        confidence: Confidence score 0.0-1.0
        sources: Optional list of source dicts
        safety_warnings: Optional list of safety warning strings

    Returns:
        Formatted response ready for user

    Example:
        >>> response = synthesize_response(
        ...     "1. Check voltage\\n2. Reset fault",
        ...     confidence=0.85,
        ...     sources=[{"title": "Manual", "url": "..."}],
        ...     safety_warnings=["⚠️ HIGH VOLTAGE"]
        ... )
        >>> print(response)
        🟢 **High Confidence**
        ☐ 1. Check voltage
        ☐ 2. Reset fault
        **Sources:**
        [1] Manual - ...
        ⚠️ **SAFETY WARNINGS**
        🔴 **DANGER:** ⚠️ HIGH VOLTAGE
    """
    # Add confidence badge
    text = add_confidence_badge(answer, confidence)

    # Format troubleshooting steps
    text = format_troubleshooting_steps(text)

    # Extract and format safety warnings
    if safety_warnings:
        # Convert string warnings to dicts
        extracted = [{"severity": "WARNING", "text": w} for w in safety_warnings]
    else:
        # Auto-extract from text
        extracted = extract_safety_warnings(text)

    safety_section = format_safety_section(extracted)

    # Add citations
    if sources:
        text = add_citations(text, sources)

    # Combine
    return text + safety_section
