"""
Response Synthesis - Format agent responses with citations and safety warnings.

Provides functions to enhance raw LLM responses with:
- Inline citations [1], [2] with source footnotes
- Safety warning extraction and highlighting
- Confidence badges
- Troubleshooting step checkboxes
- Search transparency reports (what we searched and why)

Extracted from rivet/utils/response_formatter.py - Production-ready
"""

import re
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rivet_pro.core.models.search_report import SearchReport


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


def format_search_transparency(report: 'SearchReport') -> str:
    """
    Format search transparency section showing what was searched.
    Only shown when manual not found, to prove thorough searching.

    Args:
        report: SearchReport with search attempt details

    Returns:
        HTML formatted search transparency section
    """
    from rivet_pro.core.models.search_report import SearchStage, SearchStatus

    if report is None:
        return ""

    lines = ["<b>Search Details:</b>"]

    # Stage names for display
    stage_names = {
        SearchStage.LOCAL_FILES: "Local Files",
        SearchStage.DATABASE_CACHE: "Database Cache",
        SearchStage.EXTERNAL_SEARCH: "Web Search",
        SearchStage.LLM_VALIDATION: "AI Validation"
    }

    # Status emojis
    status_emojis = {
        SearchStatus.SUCCESS: "✅",
        SearchStatus.NOT_FOUND: "❌",
        SearchStatus.REJECTED: "⚠️",
        SearchStatus.SKIPPED: "⏭️",
        SearchStatus.ERROR: "❓"
    }

    # Format each stage
    for stage in report.stages:
        emoji = status_emojis.get(stage.status, "❓")
        name = stage_names.get(stage.stage, stage.stage.value)
        details = stage.details or stage.status.value
        lines.append(f"• {emoji} {name}: {details}")

    # Show rejected URLs (max 3 to keep response concise)
    if report.rejected_urls:
        lines.append("")
        lines.append(f"<b>URLs Evaluated ({len(report.rejected_urls)} rejected):</b>")
        for rejected in report.rejected_urls[:3]:
            # Truncate URL for display
            display_url = rejected.url[:45] + "..." if len(rejected.url) > 45 else rejected.url
            conf_pct = int(rejected.confidence * 100)
            # Truncate reason
            reason = rejected.rejection_reason[:60] if rejected.rejection_reason else "No reason"
            lines.append(f"• {display_url}")
            lines.append(f"  └ {conf_pct}% - {reason}")

        if len(report.rejected_urls) > 3:
            lines.append(f"  <i>...and {len(report.rejected_urls) - 3} more</i>")

    # Search timing
    lines.append("")
    lines.append(f"⏱️ <i>Search completed in {report.total_duration_ms}ms</i>")

    return "\n".join(lines)


def format_equipment_response(
    equipment: Dict[str, Any],
    manual: Dict[str, Any] = None,
    search_report: Optional['SearchReport'] = None,
    helpful_response: Optional[str] = None
) -> str:
    """
    Format equipment identification response with optional manual link.

    Uses HTML format for reliable URL handling (Markdown has issues with underscores in URLs).

    Args:
        equipment: Dict with equipment info:
            - manufacturer: str
            - model: str
            - serial: str (optional)
            - error_code: str (optional)
        manual: Optional dict with manual info:
            - url: str
            - title: str
            - source: str
            - cached: bool
        search_report: Optional SearchReport with transparency data
        helpful_response: Optional LLM-generated helpful response when not found

    Returns:
        Formatted HTML string ready for Telegram (use parse_mode="HTML")

    Example (with manual):
        >>> equipment = {
        ...     'manufacturer': 'Siemens',
        ...     'model': 'G120 VFD',
        ...     'serial': '6SL3244-0BB12-1BA1'
        ... }
        >>> manual = {
        ...     'url': 'https://example.com/manual.pdf',
        ...     'title': 'Siemens G120 Operating Instructions',
        ...     'source': 'tavily'
        ... }
        >>> print(format_equipment_response(equipment, manual))
        📋 <b>Equipment Identified</b>
        ...
    """
    # Start with equipment identification (HTML format)
    response = "📋 <b>Equipment Identified</b>\n\n"

    # Add manufacturer
    mfr = equipment.get('manufacturer', 'Unknown')
    response += f"<b>Manufacturer:</b> {mfr}\n"

    # Add model
    model = equipment.get('model', 'Unknown')
    response += f"<b>Model:</b> {model}\n"

    # Add serial if available
    if equipment.get('serial'):
        response += f"<b>Serial:</b> {equipment['serial']}\n"

    # Add error code if detected
    if equipment.get('error_code'):
        response += f"⚠️ <b>Error Code:</b> {equipment['error_code']}\n"

    # Add manual section
    response += "\n"

    if manual and manual.get('url'):
        # Manual found
        response += "📖 <b>User Manual</b>\n"

        title = manual.get('title', f"{mfr} {model} Manual")
        url = manual['url']
        confidence = manual.get('confidence', 1.0)

        # HTML format handles URLs with underscores correctly (no escaping needed)
        response += f'<a href="{url}">{title}</a>\n\n'

        # Add plain URL as fallback (some mobile clients have issues with links)
        response += f"📎 <i>If link doesn't work, copy this URL:</i>\n<code>{url}</code>\n\n"

        # Add confidence indicator if medium confidence (0.5-0.7)
        if 0.5 <= confidence < 0.7:
            response += "⚠️ <i>Link quality uncertain - please verify before use.</i>\n\n"
        elif confidence >= 0.7:
            # High confidence - add helpful tip
            response += "💡 <i>Tap link or copy URL to browser.</i>\n"

        # Add source attribution if available
        if manual.get('source') and manual.get('source') != 'cache':
            source = manual['source'].capitalize()
            response += f"\n<i>Source: {source}</i>"

    else:
        # Manual not found - check for best candidate
        best_candidate = search_report.best_candidate if search_report else None

        if best_candidate and best_candidate.confidence >= 0.5:
            # We have a good candidate - ask user for validation
            response += "📖 <b>Possible Manual Found</b>\n\n"

            # Show the candidate URL
            title = best_candidate.title or f"{mfr} {model} Manual"
            url = best_candidate.url
            conf_pct = int(best_candidate.confidence * 100)

            response += f"🔍 <b>Best match ({conf_pct}% confidence):</b>\n"
            response += f'<a href="{url}">{title}</a>\n\n'
            response += f"📎 <code>{url}</code>\n\n"

            # Explain why it wasn't auto-accepted
            response += f"⚠️ <i>Not auto-verified: {best_candidate.rejection_reason[:80]}...</i>\n\n"

            # Human-in-the-loop prompt
            response += "👆 <b>Is this the correct manual?</b>\n"
            response += "Reply <b>Yes</b> or <b>No</b> to help improve future searches."

        else:
            # No good candidates - show not found
            response += "📖 <b>Manual Not Found</b>\n\n"

            # Add LLM-generated helpful response if available
            if helpful_response:
                response += f"💡 {helpful_response}\n\n"

            # Add search transparency section if report available
            if search_report:
                transparency = format_search_transparency(search_report)
                if transparency:
                    response += f"{transparency}\n\n"

            # Suggest manual search query
            search_query = f"{mfr} {model} manual PDF"
            response += f"Try searching: {search_query}\n\n"

            # Helpful tip - vary based on image issues
            image_issues = equipment.get('image_issues', [])
            if 'upside_down' in image_issues or 'rotated' in image_issues:
                response += "<i>Tip: The image appears rotated. Try taking a photo with the nameplate right-side up.</i>"
            elif 'dirty' in image_issues:
                response += "<i>Tip: The nameplate looks dirty. Try wiping it clean and retaking the photo.</i>"
            elif 'blurry' in image_issues:
                response += "<i>Tip: The image is blurry. Hold the camera steady and ensure good focus.</i>"
            elif 'partial' in image_issues:
                response += "<i>Tip: The nameplate is partially visible. Include the full nameplate in the photo.</i>"
            elif 'glare' in image_issues:
                response += "<i>Tip: There is glare on the nameplate. Try shooting from a different angle.</i>"
            else:
                response += "<i>Send a clearer photo if the ID looks wrong.</i>"

    return response


# Telegram message limit
TELEGRAM_MAX_CHARS = 4096


def _get_confidence_emoji(confidence: float) -> str:
    """Get emoji for confidence level."""
    if confidence >= 0.90:
        return "🟢"  # High
    elif confidence >= 0.80:
        return "✅"  # Good
    elif confidence >= 0.70:
        return "🟡"  # Medium
    else:
        return "🔴"  # Low


def _truncate_to_limit(text: str, limit: int = TELEGRAM_MAX_CHARS) -> str:
    """Truncate text to fit Telegram limit, adding ellipsis if needed."""
    if len(text) <= limit:
        return text
    # Find last newline before limit to keep message clean
    truncate_at = text[:limit - 50].rfind('\n')
    if truncate_at < limit // 2:
        truncate_at = limit - 50
    return text[:truncate_at] + "\n\n⋯ _Response truncated_"


def format_photo_pipeline_response(
    screening_result: Optional[Dict[str, Any]] = None,
    extraction_result: Optional[Dict[str, Any]] = None,
    analysis_result: Optional[Dict[str, Any]] = None,
    equipment_info: Optional[Dict[str, Any]] = None,
    maintenance_history: Optional[List[Dict[str, Any]]] = None,
    from_cache: bool = False
) -> str:
    """
    Format photo pipeline response for Telegram (Markdown format).

    Combines results from all pipeline stages into a user-friendly message
    optimized for field technicians. Uses Markdown formatting.

    Args:
        screening_result: Stage 1 Groq screening result dict with keys:
            - is_industrial: bool
            - confidence: float (0.0-1.0)
            - category: str (plc, vfd, motor, etc.)
            - reason: str
        extraction_result: Stage 2 DeepSeek extraction result dict with keys:
            - manufacturer: str
            - model_number: str
            - serial_number: str (optional)
            - specs: dict (voltage, current, hp, etc.)
            - confidence: float
        analysis_result: Stage 3 Claude analysis result dict with keys:
            - analysis: str
            - solutions: List[str]
            - safety_warnings: List[str]
            - kb_citations: List[Dict[str, str]]
            - recommendations: List[str]
            - confidence: float
        equipment_info: Equipment matching info dict with keys:
            - equipment_id: str
            - equipment_number: str
            - is_new: bool
        maintenance_history: List of recent work orders with keys:
            - work_order_number: str
            - title: str
            - status: str
            - created_at: str
        from_cache: Whether extraction came from cache

    Returns:
        Formatted Markdown string for Telegram (< 4096 chars)

    Example:
        >>> result = format_photo_pipeline_response(
        ...     screening_result={"confidence": 0.92, "category": "vfd"},
        ...     extraction_result={"manufacturer": "Siemens", "model_number": "G120"}
        ... )
    """
    parts = []

    # ==========================================
    # HEADER - Screening Status
    # ==========================================
    screening_conf = (screening_result or {}).get('confidence', 0.0)
    screening_emoji = _get_confidence_emoji(screening_conf)
    category = (screening_result or {}).get('category', 'equipment')
    category_display = category.upper() if category else 'EQUIPMENT'

    parts.append(f"{screening_emoji} *{category_display} Identified* ({screening_conf:.0%})")
    parts.append("")

    # ==========================================
    # EQUIPMENT CARD - DeepSeek Extraction
    # ==========================================
    if extraction_result:
        ext_conf = extraction_result.get('confidence', 0.0)
        ext_emoji = _get_confidence_emoji(ext_conf)

        parts.append(f"📋 *Equipment Details* {ext_emoji}")
        parts.append("```")

        if extraction_result.get('manufacturer'):
            parts.append(f"Manufacturer: {extraction_result['manufacturer']}")
        if extraction_result.get('model_number'):
            parts.append(f"Model:        {extraction_result['model_number']}")
        if extraction_result.get('serial_number'):
            parts.append(f"Serial:       {extraction_result['serial_number']}")

        # Key specs in card format
        specs = extraction_result.get('specs', {})
        if specs:
            parts.append("─" * 25)
            for key in ['voltage', 'current', 'horsepower', 'hp', 'rpm', 'phase', 'frequency']:
                if specs.get(key):
                    label = key.upper().replace('HORSEPOWER', 'HP')[:12].ljust(12)
                    parts.append(f"{label}: {specs[key]}")

        parts.append("```")
        parts.append(f"_Confidence: {ext_conf:.0%}_")

    # ==========================================
    # EQUIPMENT ID - Matched/Created
    # ==========================================
    if equipment_info:
        eq_num = equipment_info.get('equipment_number', '')
        is_new = equipment_info.get('is_new', False)
        status_icon = "🆕" if is_new else "✓"
        status_text = "Created" if is_new else "Matched"

        parts.append("")
        parts.append(f"🔧 *Equipment ID:* `{eq_num}` ({status_icon} {status_text})")

    # ==========================================
    # SAFETY WARNINGS - Always prominent (⚠️ first!)
    # ==========================================
    safety_warnings = (analysis_result or {}).get('safety_warnings', [])
    if safety_warnings:
        parts.append("")
        parts.append("⚠️ *SAFETY WARNINGS*")
        for warning in safety_warnings[:3]:  # Limit to top 3
            # Add emoji based on severity keywords
            if any(kw in warning.lower() for kw in ['danger', '480v', 'high voltage', 'lethal']):
                parts.append(f"🔴 {warning}")
            elif any(kw in warning.lower() for kw in ['lockout', 'tagout', 'ppe']):
                parts.append(f"🟡 {warning}")
            else:
                parts.append(f"⚠️ {warning}")

    # ==========================================
    # AI ANALYSIS - Collapsible section
    # ==========================================
    if analysis_result and analysis_result.get('analysis'):
        parts.append("")
        parts.append("━━━━━━━━━━━━━━━━━━━━")

        analysis_conf = analysis_result.get('confidence', 0.0)
        analysis_emoji = _get_confidence_emoji(analysis_conf)
        parts.append(f"🤖 *AI Analysis* {analysis_emoji}")
        parts.append("")

        # Truncate analysis text if too long
        analysis_text = analysis_result['analysis']
        if len(analysis_text) > 600:
            analysis_text = analysis_text[:600] + "..."

        # Use blockquote for analysis text (collapsible feel)
        for line in analysis_text.split('\n')[:8]:  # Max 8 lines
            if line.strip():
                parts.append(f"> {line}")

    # ==========================================
    # SOLUTIONS - Numbered list
    # ==========================================
    solutions = (analysis_result or {}).get('solutions', [])
    if solutions:
        parts.append("")
        parts.append("💡 *Recommended Solutions:*")
        for i, solution in enumerate(solutions[:4], 1):  # Top 4
            # Truncate long solutions
            sol = solution[:100] + "..." if len(solution) > 100 else solution
            parts.append(f"{i}. {sol}")

    # ==========================================
    # MAINTENANCE HISTORY SUMMARY
    # ==========================================
    if maintenance_history:
        parts.append("")
        parts.append("📜 *Recent History:*")
        for record in maintenance_history[:3]:  # Last 3 work orders
            wo_num = record.get('work_order_number', 'WO-???')
            title = record.get('title', 'Unknown')[:40]
            status = record.get('status', 'unknown')
            status_icon = "✅" if status.lower() == 'completed' else "🔄"
            parts.append(f"• `{wo_num}` {title} {status_icon}")

    # ==========================================
    # KB CITATIONS - Numbered references
    # ==========================================
    kb_citations = (analysis_result or {}).get('kb_citations', [])
    if kb_citations:
        parts.append("")
        parts.append("📚 *Sources:*")
        for i, citation in enumerate(kb_citations[:3], 1):  # Top 3
            title = citation.get('title', 'Knowledge Base')[:50]
            url = citation.get('url', '')
            if url:
                parts.append(f"[{i}] [{title}]({url})")
            else:
                parts.append(f"[{i}] {title}")

    # ==========================================
    # RECOMMENDATIONS (if space permits)
    # ==========================================
    recommendations = (analysis_result or {}).get('recommendations', [])
    if recommendations and len('\n'.join(parts)) < 3000:  # Only if space
        parts.append("")
        parts.append("📝 *Next Steps:*")
        for rec in recommendations[:2]:  # Top 2
            rec_text = rec[:80] + "..." if len(rec) > 80 else rec
            parts.append(f"☐ {rec_text}")

    # ==========================================
    # FOOTER - Cache indicator
    # ==========================================
    if from_cache:
        parts.append("")
        parts.append("_📦 From cache (instant response)_")

    # Join and truncate to Telegram limit
    response = '\n'.join(parts)
    return _truncate_to_limit(response, TELEGRAM_MAX_CHARS)
