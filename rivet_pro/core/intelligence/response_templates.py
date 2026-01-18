"""
Expert Response Templates (EXPERT-008)

Provides response templates that respect technician expertise.
Detects technical terminology to set expert mode and customize prompts.

Usage:
    detector = ExpertiseDetector()
    is_expert = detector.detect_expertise("phase imbalance on motor 7")

    template_manager = ResponseTemplateManager()
    prompt = template_manager.get_system_prompt(
        intent=IntentType.TROUBLESHOOT,
        is_expert=True,
        context="Motor overheating"
    )
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum

from rivet_pro.core.intelligence.intent_classifier import IntentType

logger = logging.getLogger(__name__)


class ExpertiseLevel(Enum):
    """Detected expertise level of the user."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


@dataclass
class ExpertiseSignals:
    """Signals that indicate expertise level."""
    technical_terms_found: List[str]
    fault_codes_found: List[str]
    equipment_specifics: List[str]
    expertise_level: ExpertiseLevel
    confidence: float


class ExpertiseDetector:
    """
    Detects user expertise level from their query.

    Uses technical terminology, fault codes, and equipment-specific
    references to determine if the user is likely an expert.
    """

    # Technical terms that indicate expert knowledge
    EXPERT_TERMS: Set[str] = {
        # Electrical/Motor terms
        "phase imbalance", "ground fault", "megger", "insulation resistance",
        "fla", "rla", "locked rotor", "service factor", "power factor",
        "harmonics", "thd", "amps", "voltage imbalance", "single phasing",
        "soft start", "across the line", "delta", "wye", "star",

        # VFD/Drive terms
        "carrier frequency", "pwm", "dc bus", "igbt", "regenerative",
        "dynamic braking", "ramp time", "slip compensation", "flux vector",
        "v/hz", "encoder feedback", "sensorless vector",

        # Mechanical terms
        "cavitation", "impeller", "shaft alignment", "runout",
        "bearing clearance", "vibration analysis", "oil analysis",
        "infrared thermography", "ultrasonic testing",

        # HVAC terms
        "superheat", "subcooling", "delta t", "cfm", "static pressure",
        "economizer", "enthalpy", "psychrometric", "ton",

        # Safety/Procedures
        "loto", "lockout tagout", "arc flash", "ppe", "jsa",
        "sop", "root cause", "mtbf", "mttr",

        # Fault analysis
        "fault code", "error code", "alarm history", "trip log",
        "diagnostic", "parameter", "setup mode",
    }

    # Fault code pattern
    FAULT_CODE_PATTERN = re.compile(r'\b[A-Z]+[\-_]?\d{3,5}\b', re.IGNORECASE)

    # Equipment-specific terms (manufacturer + model type references)
    EQUIPMENT_SPECIFIC_TERMS = [
        "siemens", "allen-bradley", "abb", "danfoss", "yaskawa",
        "trane", "carrier", "lennox", "daikin",
        "grundfos", "flowserve", "goulds",
        "g120", "powerflex", "acs", "vlt", "a1000",
    ]

    def __init__(self):
        """Initialize expertise detector."""
        # Pre-compile expert term pattern
        escaped_terms = [re.escape(t) for t in self.EXPERT_TERMS]
        self._expert_pattern = re.compile(
            r'\b(?:' + '|'.join(escaped_terms) + r')\b',
            re.IGNORECASE
        )

    def detect_expertise(self, message: str) -> ExpertiseSignals:
        """
        Detect expertise level from message.

        Args:
            message: User's natural language message

        Returns:
            ExpertiseSignals with detected level and supporting evidence
        """
        if not message:
            return ExpertiseSignals(
                technical_terms_found=[],
                fault_codes_found=[],
                equipment_specifics=[],
                expertise_level=ExpertiseLevel.BEGINNER,
                confidence=0.5
            )

        message_lower = message.lower()

        # Find technical terms
        tech_terms = self._expert_pattern.findall(message_lower)
        tech_terms = list(set(tech_terms))  # Dedupe

        # Find fault codes
        fault_codes = self.FAULT_CODE_PATTERN.findall(message)
        fault_codes = [fc.upper() for fc in set(fault_codes)]

        # Find equipment-specific references
        equipment_refs = [
            term for term in self.EQUIPMENT_SPECIFIC_TERMS
            if term.lower() in message_lower
        ]

        # Calculate expertise score
        score = 0.0

        # Technical terms are strong indicators
        # Even 1 expert term shows real knowledge
        if len(tech_terms) >= 3:
            score += 0.6
        elif len(tech_terms) >= 2:
            score += 0.5
        elif len(tech_terms) >= 1:
            score += 0.35

        # Fault codes indicate hands-on experience
        if fault_codes:
            score += 0.3

        # Equipment specifics show familiarity
        if len(equipment_refs) >= 2:
            score += 0.25
        elif len(equipment_refs) >= 1:
            score += 0.15

        # Message length and detail
        word_count = len(message.split())
        if word_count > 15 and len(tech_terms) > 0:
            score += 0.1  # Detailed technical query

        # Determine level
        # Using technical terms like "megger", "phase imbalance", "cavitation"
        # is strong evidence of expertise - even a single term
        if score >= 0.35:
            level = ExpertiseLevel.EXPERT
        elif score >= 0.15:
            level = ExpertiseLevel.INTERMEDIATE
        else:
            level = ExpertiseLevel.BEGINNER

        confidence = min(1.0, 0.5 + score)

        logger.debug(
            f"Expertise detected | level={level.value} | score={score:.2f} | "
            f"terms={len(tech_terms)} | faults={len(fault_codes)}"
        )

        return ExpertiseSignals(
            technical_terms_found=tech_terms,
            fault_codes_found=fault_codes,
            equipment_specifics=equipment_refs,
            expertise_level=level,
            confidence=confidence
        )

    def is_expert(self, message: str) -> bool:
        """Quick check if user appears to be an expert."""
        signals = self.detect_expertise(message)
        return signals.expertise_level == ExpertiseLevel.EXPERT


class ResponseTemplateManager:
    """
    Manages response templates for different intents and expertise levels.

    Provides system prompts that:
    - Respect technician expertise (no condescending explanations)
    - Jump to diagnosis for troubleshooting
    - Give specs directly for manual questions
    - Confirm and move on for work orders
    """

    # Phrases to avoid in expert mode
    CONDESCENDING_PHRASES = [
        "as you may know",
        "as you probably know",
        "for safety reasons",
        "always remember to",
        "it's important to note",
        "before we begin",
        "let me explain",
        "first, let's understand",
        "basically,",
        "simply put,",
    ]

    def __init__(self):
        """Initialize template manager."""
        self._templates = self._build_templates()

    def _build_templates(self) -> Dict[IntentType, Dict[str, str]]:
        """Build response templates for each intent."""
        return {
            IntentType.TROUBLESHOOT: {
                "expert": self._troubleshoot_expert_prompt(),
                "standard": self._troubleshoot_standard_prompt(),
            },
            IntentType.MANUAL_QUESTION: {
                "expert": self._manual_expert_prompt(),
                "standard": self._manual_standard_prompt(),
            },
            IntentType.WORK_ORDER_CREATE: {
                "expert": self._work_order_expert_prompt(),
                "standard": self._work_order_standard_prompt(),
            },
            IntentType.WORK_ORDER_STATUS: {
                "expert": self._status_expert_prompt(),
                "standard": self._status_standard_prompt(),
            },
            IntentType.EQUIPMENT_SEARCH: {
                "expert": self._equipment_expert_prompt(),
                "standard": self._equipment_standard_prompt(),
            },
            IntentType.GENERAL_CHAT: {
                "expert": self._chat_expert_prompt(),
                "standard": self._chat_standard_prompt(),
            },
        }

    def _troubleshoot_expert_prompt(self) -> str:
        return """You are a senior maintenance expert helping a fellow technician troubleshoot equipment.

RESPONSE STYLE:
- Jump straight to diagnosis - skip basics they already know
- Lead with the most likely root cause based on symptoms
- Include specific checks with expected values (amps, temps, pressures)
- Mention fault codes to look for if applicable
- Skip safety disclaimers - they're professionals
- Keep it direct and technical

FORMAT:
1. Most likely cause (1-2 sentences)
2. Key diagnostic checks (bullet points with values)
3. Common related issues to rule out
4. Fix approach if diagnosis confirms

Avoid phrases like "As you may know" or "For safety reasons" - get to the point."""

    def _troubleshoot_standard_prompt(self) -> str:
        return """You are a helpful maintenance assistant troubleshooting equipment issues.

RESPONSE STYLE:
- Start with understanding the symptom
- Walk through diagnostic steps methodically
- Explain why each check matters
- Include safety reminders where appropriate
- Suggest when to escalate to specialists

FORMAT:
1. Clarify the symptom
2. Possible causes (most to least likely)
3. Diagnostic steps to narrow down
4. Recommended actions"""

    def _manual_expert_prompt(self) -> str:
        return """You are a technical reference assistant for an experienced technician.

RESPONSE STYLE:
- Give specs, values, and procedures directly
- No introductions or context they don't need
- Include exact numbers, tolerances, torque specs
- Reference specific sections if from a manual
- Assume they know how to use tools and equipment

FORMAT:
- Lead with the specific answer/spec they asked for
- Follow with related specs if relevant
- Note any variations by model/version if applicable

Skip explanations of what things are - just give the data."""

    def _manual_standard_prompt(self) -> str:
        return """You are a helpful technical reference assistant.

RESPONSE STYLE:
- Provide the requested information clearly
- Add context to help understand the specification
- Explain any prerequisites or safety considerations
- Suggest related information they might need

FORMAT:
1. Direct answer to their question
2. Context or explanation
3. Related information or considerations"""

    def _work_order_expert_prompt(self) -> str:
        return """You are a work order assistant for maintenance technicians.

RESPONSE STYLE:
- Confirm the work order creation concisely
- Include the WO number and key details
- Don't over-explain the process
- Mention if any additional info is needed, then stop

FORMAT:
- Confirmation line with WO number
- Equipment linked (if any)
- Note any flags (priority, special requirements)

Keep it brief - they know the system."""

    def _work_order_standard_prompt(self) -> str:
        return """You are a work order assistant helping document maintenance work.

RESPONSE STYLE:
- Confirm what was captured
- Explain what happens next
- Offer to add more details if needed
- Provide the work order reference

FORMAT:
1. Confirmation of work order creation
2. Summary of captured information
3. Next steps or additional options"""

    def _status_expert_prompt(self) -> str:
        return """You are a work order status assistant for maintenance technicians.

RESPONSE STYLE:
- List work orders directly with key info
- Include status, equipment, and age
- Flag overdue or urgent items
- Keep formatting tight and scannable

FORMAT:
Table or list with: WO#, Equipment, Status, Age
Note any requiring attention."""

    def _status_standard_prompt(self) -> str:
        return """You are a work order status assistant.

RESPONSE STYLE:
- Provide a clear summary of work orders
- Explain status meanings if helpful
- Highlight items needing attention
- Offer filtering options

FORMAT:
1. Summary count by status
2. List of work orders with details
3. Any items requiring action"""

    def _equipment_expert_prompt(self) -> str:
        return """You are an equipment search assistant for maintenance technicians.

RESPONSE STYLE:
- Return matching equipment directly
- Include key identifiers (EQ#, serial, location)
- Show maintenance history highlights (WO count, last fault)
- Skip formatting fluff

FORMAT:
Table or list with: EQ#, Make/Model, Location, Last Issue
Note any flagged equipment."""

    def _equipment_standard_prompt(self) -> str:
        return """You are an equipment search assistant.

RESPONSE STYLE:
- Provide equipment information clearly
- Include all relevant identifiers
- Show maintenance history summary
- Offer to drill into specific equipment

FORMAT:
1. Search results summary
2. Equipment details
3. Options for more information"""

    def _chat_expert_prompt(self) -> str:
        return """You are a shop floor assistant helping maintenance technicians.

Be direct and professional. They're here to work, not chat.
Answer questions efficiently and offer relevant assistance.
Don't be overly formal or use unnecessary pleasantries."""

    def _chat_standard_prompt(self) -> str:
        return """You are a friendly maintenance assistant.

Be helpful and conversational. Explain what you can help with.
Offer assistance with equipment, work orders, manuals, and troubleshooting."""

    def get_system_prompt(
        self,
        intent: IntentType,
        is_expert: bool = False,
        context: Optional[str] = None
    ) -> str:
        """
        Get appropriate system prompt for intent and expertise level.

        Args:
            intent: Classified intent type
            is_expert: Whether user appears to be an expert
            context: Optional context to inject (equipment history, etc.)

        Returns:
            System prompt string for LLM
        """
        template_key = "expert" if is_expert else "standard"

        # Get template for intent
        intent_templates = self._templates.get(
            intent,
            self._templates[IntentType.GENERAL_CHAT]
        )
        prompt = intent_templates.get(template_key, intent_templates["standard"])

        # Inject context if provided
        if context:
            prompt = f"{prompt}\n\n## Context\n{context}"

        logger.debug(f"Generated {template_key} prompt for {intent.value}")

        return prompt

    def filter_condescending(self, response: str) -> str:
        """
        Remove condescending phrases from a response.

        Args:
            response: Generated response text

        Returns:
            Response with condescending phrases removed
        """
        result = response
        for phrase in self.CONDESCENDING_PHRASES:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            result = pattern.sub('', result)

        # Clean up any resulting double spaces
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'\s+([.,!?])', r'\1', result)  # Fix space before punctuation

        return result.strip()


# Module-level singletons
_detector: Optional[ExpertiseDetector] = None
_template_manager: Optional[ResponseTemplateManager] = None


def get_expertise_detector() -> ExpertiseDetector:
    """Get or create the expertise detector singleton."""
    global _detector
    if _detector is None:
        _detector = ExpertiseDetector()
    return _detector


def get_template_manager() -> ResponseTemplateManager:
    """Get or create the template manager singleton."""
    global _template_manager
    if _template_manager is None:
        _template_manager = ResponseTemplateManager()
    return _template_manager


def detect_expertise(message: str) -> bool:
    """Convenience function to detect if user is an expert."""
    return get_expertise_detector().is_expert(message)


def get_expert_prompt(intent: IntentType, message: str, context: Optional[str] = None) -> str:
    """Convenience function to get appropriate prompt based on detected expertise."""
    is_expert = detect_expertise(message)
    return get_template_manager().get_system_prompt(intent, is_expert, context)


__all__ = [
    "ExpertiseDetector",
    "ExpertiseLevel",
    "ExpertiseSignals",
    "ResponseTemplateManager",
    "get_expertise_detector",
    "get_template_manager",
    "detect_expertise",
    "get_expert_prompt",
]
