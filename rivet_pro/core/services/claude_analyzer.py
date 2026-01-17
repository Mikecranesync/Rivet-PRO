"""
Claude AI Analysis and KB Synthesis Service (PHOTO-CLAUDE-001)

Third-pass analysis using Claude claude-sonnet-4-20250514 for troubleshooting synthesis.
Combines component specs, maintenance history, and KB atoms to provide
comprehensive troubleshooting guidance.

Cost: ~$0.01 per analysis
Only called on confirmed/tagged photos with equipment_id.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from rivet_pro.config.settings import settings
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


@dataclass
class AnalysisResult:
    """
    Result from Claude AI analysis with KB synthesis.

    Attributes:
        analysis: Synthesized troubleshooting analysis text
        solutions: List of recommended solutions in order of likelihood
        kb_citations: List of citations with source URLs from KB atoms
        recommendations: List of actionable next steps
        confidence: Analysis confidence score (0.0-1.0)
        safety_warnings: Extracted safety warnings from response
        cost_usd: Estimated cost of this analysis
        model: Model used for analysis
    """
    analysis: str
    solutions: List[str] = field(default_factory=list)
    kb_citations: List[Dict[str, str]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    safety_warnings: List[str] = field(default_factory=list)
    cost_usd: float = 0.0
    model: str = "claude-sonnet-4-20250514"


class ClaudeAnalyzer:
    """
    Claude-based third-pass analysis for equipment troubleshooting.

    Synthesizes:
    - Component specs from DeepSeek extraction
    - Maintenance history from work orders
    - Knowledge atoms from KB vector search

    Into actionable troubleshooting guidance with citations.
    """

    # Cost per 1K tokens for claude-sonnet-4-20250514
    COST_PER_1K_INPUT = 0.003
    COST_PER_1K_OUTPUT = 0.015
    MODEL_ID = "claude-sonnet-4-20250514"

    def __init__(self):
        """Initialize Claude analyzer with Anthropic client."""
        self._client = None

    def _get_client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured")
            from anthropic import Anthropic
            self._client = Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def _format_specs_context(self, specs: Dict[str, Any]) -> str:
        """
        Format component specifications into context string.

        Args:
            specs: Dict with component specs from DeepSeek extraction

        Returns:
            Formatted specs context for prompt
        """
        if not specs:
            return "No component specifications available."

        parts = ["Component Specifications:"]

        for key, value in specs.items():
            if value and value != "Unknown":
                # Clean up key for display
                display_key = key.replace("_", " ").title()
                parts.append(f"- {display_key}: {value}")

        return "\n".join(parts) if len(parts) > 1 else "No component specifications available."

    def _format_history_context(self, history: List[Dict[str, Any]]) -> str:
        """
        Format maintenance history into context string.

        Args:
            history: List of work order history records

        Returns:
            Formatted history context for prompt
        """
        if not history:
            return "No maintenance history available for this equipment."

        parts = [f"Maintenance History (last {len(history)} records):"]

        for i, record in enumerate(history[:5], 1):  # Limit to 5 most recent
            wo_num = record.get("work_order_number", "Unknown")
            title = record.get("title", "No title")
            status = record.get("status", "unknown")
            fault_codes = record.get("fault_codes", [])
            created = record.get("created_at", "")
            resolution = record.get("resolution_time_hours")

            entry = f"\n{i}. {wo_num} - {title}"
            entry += f"\n   Status: {status}"

            if fault_codes:
                entry += f"\n   Fault Codes: {', '.join(fault_codes)}"

            if created:
                if isinstance(created, datetime):
                    entry += f"\n   Date: {created.strftime('%Y-%m-%d')}"
                else:
                    entry += f"\n   Date: {str(created)[:10]}"

            if resolution:
                entry += f"\n   Resolution Time: {resolution:.1f} hours"

            parts.append(entry)

        return "\n".join(parts)

    def _format_kb_context(self, kb_atoms: List[Dict[str, Any]]) -> str:
        """
        Format KB atoms into context string with source references.

        Args:
            kb_atoms: List of KB atom records

        Returns:
            Formatted KB context for prompt
        """
        if not kb_atoms:
            return "No relevant knowledge base entries found."

        parts = ["Knowledge Base Information:"]

        for i, atom in enumerate(kb_atoms[:5], 1):  # Limit to 5 atoms
            title = atom.get("title", "Untitled")
            content = atom.get("content", "")
            source_url = atom.get("source_url", "")
            atom_type = atom.get("type", "general")
            confidence = atom.get("confidence", 0.0)

            # Truncate content if too long
            if len(content) > 500:
                content = content[:500] + "..."

            entry = f"\n[Source {i}] ({atom_type.upper()}, confidence: {confidence:.0%})"
            entry += f"\nTitle: {title}"
            entry += f"\nContent: {content}"

            if source_url:
                entry += f"\nURL: {source_url}"

            parts.append(entry)

        return "\n".join(parts)

    def _extract_safety_warnings(self, response_text: str) -> List[str]:
        """
        Extract safety warnings from Claude response.

        Args:
            response_text: Full response text from Claude

        Returns:
            List of extracted safety warning strings
        """
        warnings = []

        # Safety keywords to search for
        safety_keywords = [
            "warning:", "danger:", "caution:", "safety:",
            "lock out", "lockout", "tag out", "tagout",
            "high voltage", "electric shock", "arc flash",
            "ppe required", "personal protective",
            "do not", "never", "must not",
            "hazard", "risk of injury", "risk of death"
        ]

        # Split into sentences
        sentences = response_text.replace("\n", " ").split(". ")

        for sentence in sentences:
            sentence_lower = sentence.lower()
            for keyword in safety_keywords:
                if keyword in sentence_lower:
                    # Clean up and add
                    clean_warning = sentence.strip()
                    if clean_warning and len(clean_warning) > 10:
                        # Add warning symbol if not present
                        if not clean_warning.startswith(("WARNING", "DANGER", "CAUTION", "SAFETY")):
                            clean_warning = "WARNING: " + clean_warning
                        warnings.append(clean_warning)
                    break  # Only add once per sentence

        # Deduplicate while preserving order
        seen = set()
        unique_warnings = []
        for w in warnings:
            w_lower = w.lower()
            if w_lower not in seen:
                seen.add(w_lower)
                unique_warnings.append(w)

        return unique_warnings[:5]  # Limit to 5 warnings

    def _parse_structured_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude response into structured components.

        Args:
            response_text: Raw response text from Claude

        Returns:
            Dict with analysis, solutions, recommendations
        """
        result = {
            "analysis": "",
            "solutions": [],
            "recommendations": []
        }

        # Split by common section headers
        sections = response_text.split("\n\n")

        current_section = "analysis"
        analysis_parts = []

        for section in sections:
            section_lower = section.lower().strip()

            # Detect section headers
            if section_lower.startswith(("solutions:", "solution:", "possible solutions:")):
                current_section = "solutions"
                # Extract list items
                lines = section.split("\n")[1:]  # Skip header
                for line in lines:
                    line = line.strip()
                    if line and (line.startswith(("-", "*", "•")) or line[0].isdigit()):
                        # Clean up list markers
                        clean = line.lstrip("-*• 0123456789.)")
                        if clean:
                            result["solutions"].append(clean.strip())

            elif section_lower.startswith(("recommendations:", "recommended actions:", "next steps:")):
                current_section = "recommendations"
                lines = section.split("\n")[1:]
                for line in lines:
                    line = line.strip()
                    if line and (line.startswith(("-", "*", "•")) or line[0].isdigit()):
                        clean = line.lstrip("-*• 0123456789.)")
                        if clean:
                            result["recommendations"].append(clean.strip())

            else:
                if current_section == "analysis":
                    analysis_parts.append(section)

        result["analysis"] = "\n\n".join(analysis_parts).strip()

        # If no structured sections found, use whole response as analysis
        if not result["analysis"]:
            result["analysis"] = response_text

        return result

    def _format_kb_citations(self, kb_atoms: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Format KB atoms into citation list with source URLs.

        Args:
            kb_atoms: List of KB atom records

        Returns:
            List of citation dicts with title, url, type
        """
        citations = []

        for atom in kb_atoms:
            citation = {
                "title": atom.get("title", "Untitled"),
                "url": atom.get("source_url", ""),
                "type": atom.get("type", "general"),
                "atom_id": str(atom.get("atom_id", ""))
            }
            citations.append(citation)

        return citations

    async def analyze_with_kb(
        self,
        equipment_id: UUID,
        specs: Dict[str, Any],
        history: List[Dict[str, Any]],
        kb_context: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """
        Perform Claude-based third-pass analysis with KB synthesis.

        Combines component specs, maintenance history, and KB atoms
        into comprehensive troubleshooting guidance.

        Args:
            equipment_id: UUID of the equipment being analyzed
            specs: Component specifications from DeepSeek extraction
            history: Maintenance history from work orders
            kb_context: Relevant KB atoms from vector search

        Returns:
            AnalysisResult with analysis, solutions, citations, recommendations

        Note:
            Only called on confirmed/tagged photos with equipment_id.
            Cost: ~$0.01 per analysis.
        """
        logger.info(f"Claude analysis starting | equipment_id={equipment_id}")

        try:
            # Format context sections
            specs_text = self._format_specs_context(specs)
            history_text = self._format_history_context(history)
            kb_text = self._format_kb_context(kb_context)

            # Build analysis prompt
            prompt = f"""You are an expert industrial equipment troubleshooting assistant.
Analyze the following equipment information and provide troubleshooting guidance.

Equipment ID: {equipment_id}

{specs_text}

{history_text}

{kb_text}

Based on this information, provide:

1. **Analysis**: A concise analysis of the equipment's current state and potential issues.
   - Consider patterns in the maintenance history
   - Reference relevant knowledge base information
   - Identify any concerning trends

2. **Solutions**: A prioritized list of the most likely solutions, ordered by probability.
   - Be specific and actionable
   - Reference any relevant fault codes from history

3. **Recommendations**: Specific next steps the technician should take.
   - Include any preventive maintenance suggestions
   - Note any parts that may need ordering

4. **Safety Warnings**: Any critical safety considerations.
   - Include lockout/tagout requirements if applicable
   - Note any PPE requirements

Format your response with clear section headers. Be concise and practical - this is for field technicians who need quick, actionable guidance."""

            # Call Claude claude-sonnet-4-20250514
            client = self._get_client()

            response = client.messages.create(
                model=self.MODEL_ID,
                max_tokens=1500,
                temperature=0.3,  # Lower temperature for factual responses
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Calculate cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost_usd = (input_tokens / 1000) * self.COST_PER_1K_INPUT
            cost_usd += (output_tokens / 1000) * self.COST_PER_1K_OUTPUT

            logger.info(
                f"Claude analysis complete | equipment_id={equipment_id} | "
                f"tokens={input_tokens}+{output_tokens} | cost=${cost_usd:.4f}"
            )

            # Parse structured response
            parsed = self._parse_structured_response(response_text)

            # Extract safety warnings
            safety_warnings = self._extract_safety_warnings(response_text)

            # Format citations
            citations = self._format_kb_citations(kb_context)

            # Calculate confidence based on available context
            confidence = self._calculate_confidence(specs, history, kb_context)

            return AnalysisResult(
                analysis=parsed["analysis"],
                solutions=parsed["solutions"],
                kb_citations=citations,
                recommendations=parsed["recommendations"],
                confidence=confidence,
                safety_warnings=safety_warnings,
                cost_usd=cost_usd,
                model=self.MODEL_ID
            )

        except Exception as e:
            logger.error(f"Claude analysis failed: {e}", exc_info=True)

            # Fallback: return specs + history without synthesis
            return self._create_fallback_result(specs, history, kb_context, str(e))

    def _calculate_confidence(
        self,
        specs: Dict[str, Any],
        history: List[Dict[str, Any]],
        kb_context: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate analysis confidence based on available context.

        Args:
            specs: Component specifications
            history: Maintenance history
            kb_context: KB atoms

        Returns:
            Confidence score 0.0-1.0
        """
        confidence = 0.5  # Base confidence

        # Boost for specs
        if specs and len(specs) > 3:
            confidence += 0.15
        elif specs:
            confidence += 0.05

        # Boost for history
        if history and len(history) >= 3:
            confidence += 0.15
        elif history:
            confidence += 0.05

        # Boost for KB context
        if kb_context and len(kb_context) >= 2:
            # Also consider KB atom confidence
            avg_kb_conf = sum(a.get("confidence", 0.5) for a in kb_context) / len(kb_context)
            confidence += 0.10 * avg_kb_conf
        elif kb_context:
            confidence += 0.05

        return min(confidence, 0.95)  # Cap at 0.95

    def _create_fallback_result(
        self,
        specs: Dict[str, Any],
        history: List[Dict[str, Any]],
        kb_context: List[Dict[str, Any]],
        error_msg: str
    ) -> AnalysisResult:
        """
        Create fallback result when Claude fails.

        Returns specs + history without AI synthesis.

        Args:
            specs: Component specifications
            history: Maintenance history
            kb_context: KB atoms
            error_msg: Error message from failed analysis

        Returns:
            AnalysisResult with fallback content
        """
        logger.warning(f"Using fallback result due to error: {error_msg}")

        # Build fallback analysis from available data
        analysis_parts = ["Analysis unavailable (Claude synthesis failed)."]

        if specs:
            analysis_parts.append("\n\nComponent Information:")
            for key, value in specs.items():
                if value and value != "Unknown":
                    display_key = key.replace("_", " ").title()
                    analysis_parts.append(f"- {display_key}: {value}")

        if history:
            analysis_parts.append("\n\nRecent Maintenance:")
            for record in history[:3]:
                wo_num = record.get("work_order_number", "Unknown")
                title = record.get("title", "No title")
                analysis_parts.append(f"- {wo_num}: {title}")

        # Extract any solutions/recommendations from KB atoms
        solutions = []
        for atom in kb_context[:3]:
            if atom.get("type") in ("procedure", "tip"):
                solutions.append(atom.get("title", ""))

        return AnalysisResult(
            analysis="\n".join(analysis_parts),
            solutions=solutions,
            kb_citations=self._format_kb_citations(kb_context),
            recommendations=["Manual review recommended due to analysis failure."],
            confidence=0.3,  # Low confidence for fallback
            safety_warnings=["Ensure proper safety procedures before proceeding."],
            cost_usd=0.0,  # No cost for fallback
            model="fallback"
        )


# Module-level singleton
_analyzer: Optional[ClaudeAnalyzer] = None


def get_claude_analyzer() -> ClaudeAnalyzer:
    """Get or create the ClaudeAnalyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ClaudeAnalyzer()
    return _analyzer
