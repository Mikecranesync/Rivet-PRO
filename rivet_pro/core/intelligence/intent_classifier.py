"""
Intent Classifier for Always-On Intelligent Assistant

Fast NLP-based intent classification using Groq for low-latency routing.
Designed for speech-to-text input from industrial technicians.

Usage:
    classifier = IntentClassifier(llm_router)
    result = await classifier.classify("find siemens motors", user_id="123")
    print(result.intent)  # IntentType.EQUIPMENT_SEARCH
    print(result.entities)  # {"manufacturer": "siemens"}
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

from rivet_pro.adapters.llm.router import LLMRouter, ModelCapability, get_llm_router

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Supported intent types for routing."""
    EQUIPMENT_SEARCH = "EQUIPMENT_SEARCH"
    EQUIPMENT_ADD = "EQUIPMENT_ADD"
    WORK_ORDER_CREATE = "WORK_ORDER_CREATE"
    WORK_ORDER_STATUS = "WORK_ORDER_STATUS"
    MANUAL_QUESTION = "MANUAL_QUESTION"
    TROUBLESHOOT = "TROUBLESHOOT"
    GENERAL_CHAT = "GENERAL_CHAT"
    UNKNOWN = "UNKNOWN"


@dataclass
class IntentClassification:
    """Result of intent classification."""
    intent: IntentType
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    clarification_needed: bool = False
    suggested_clarification: str = ""
    raw_message: str = ""
    classification_time_ms: int = 0
    model_used: str = ""


# System prompt for intent classification
INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for an industrial technician assistant.
Your job is to classify the user's message into exactly ONE intent category.

## INTENT CATEGORIES

1. **EQUIPMENT_SEARCH** - Finding, listing, searching, or looking up equipment in the CMMS
   Examples: "find siemens drives", "what motors do I have", "show equipment", "list my gear",
   "is there anything about X in my CMMS", "do I have any pumps", "search for", "look up"

2. **EQUIPMENT_ADD** - Adding or registering new equipment (often after sending a photo)
   Examples: "add this motor", "register equipment", "save this to my list"

3. **WORK_ORDER_CREATE** - Creating maintenance work orders
   Examples: "create work order", "I need a WO for pump 3", "report issue with motor", "maintenance request"

4. **WORK_ORDER_STATUS** - Checking work order status or history
   Examples: "check my work orders", "WO status", "open work orders", "what's pending"

5. **MANUAL_QUESTION** - Questions about equipment manuals, procedures, documentation
   Examples: "how do I reset", "what does F0002 mean", "calibration procedure", "wiring diagram"

6. **TROUBLESHOOT** - Equipment problems, faults, debugging, expert help
   Examples: "motor overheating", "drive won't start", "getting error code", "why is it making noise"

7. **GENERAL_CHAT** - Greetings, thanks, meta-questions, help requests
   Examples: "hello", "thanks", "what can you do", "help", "good morning"

## ENTITY EXTRACTION

Also extract these entities if present:
- **manufacturer**: Equipment brand (Siemens, Rockwell, ABB, Allen-Bradley, Schneider, etc.)
- **model**: Model number or name
- **fault_code**: Error/fault codes (F0002, E001, etc.)
- **equipment_number**: Equipment ID or serial number
- **equipment_type**: Type of equipment (motor, drive, pump, VFD, PLC, etc.)

## OUTPUT FORMAT

Respond with ONLY valid JSON (no markdown, no explanation):
{
  "intent": "<INTENT_TYPE>",
  "confidence": <0.0-1.0>,
  "entities": {
    "manufacturer": "<if detected or null>",
    "model": "<if detected or null>",
    "fault_code": "<if detected or null>",
    "equipment_number": "<if detected or null>",
    "equipment_type": "<if detected or null>"
  },
  "clarification_needed": <true/false>,
  "suggested_clarification": "<question to ask if clarification_needed, else empty string>"
}

## GUIDELINES

- Be generous with confidence for clear intents (0.85+)
- If the message mentions specific equipment issues, prefer TROUBLESHOOT over MANUAL_QUESTION
- If the message asks "how to" do something, prefer MANUAL_QUESTION
- Short messages like "motors" or "siemens" should be EQUIPMENT_SEARCH with lower confidence
- Set clarification_needed=true only when genuinely ambiguous
- If someone asks "is there anything about X" or "do I have X" in their CMMS/system, it's EQUIPMENT_SEARCH
- When in doubt between GENERAL_CHAT and a specific intent, prefer the specific intent with moderate confidence (0.70+)
- CMMS = Computerized Maintenance Management System - queries about what's in the CMMS are equipment searches
- Extract manufacturer names even with typos (seimens -> Siemens)"""


class IntentClassifier:
    """
    Fast intent classification for NLP-first routing.

    Uses Groq for low-latency (~100ms) classification.
    Extracts entities (manufacturer, model, fault codes) for context enrichment.
    """

    def __init__(self, llm_router: Optional[LLMRouter] = None):
        """
        Initialize classifier.

        Args:
            llm_router: LLMRouter instance. Uses singleton if None.
        """
        self.llm_router = llm_router or get_llm_router()
        logger.info("IntentClassifier initialized")

    async def classify(
        self,
        message: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentClassification:
        """
        Classify user message intent.

        Args:
            message: User's natural language message
            user_id: User identifier for logging
            context: Optional context (previous messages, etc.)

        Returns:
            IntentClassification with intent, confidence, and entities
        """
        start_time = time.perf_counter()

        # Handle empty/whitespace messages
        if not message or not message.strip():
            return IntentClassification(
                intent=IntentType.GENERAL_CHAT,
                confidence=1.0,
                raw_message=message,
                classification_time_ms=0
            )

        # Quick pattern matching for obvious intents (skip LLM call)
        quick_result = self._quick_classify(message)
        if quick_result:
            quick_result.classification_time_ms = int((time.perf_counter() - start_time) * 1000)
            logger.debug(f"Quick classification: {quick_result.intent} ({quick_result.confidence:.2f})")
            return quick_result

        # LLM-based classification
        try:
            result = await self._llm_classify(message, user_id)
            result.classification_time_ms = int((time.perf_counter() - start_time) * 1000)

            logger.info(
                f"Intent classified | user={user_id} | intent={result.intent} | "
                f"confidence={result.confidence:.2f} | time={result.classification_time_ms}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Classification error: {e}", exc_info=True)
            # Fallback to GENERAL_CHAT on error
            return IntentClassification(
                intent=IntentType.GENERAL_CHAT,
                confidence=0.5,
                raw_message=message,
                classification_time_ms=int((time.perf_counter() - start_time) * 1000),
                clarification_needed=True,
                suggested_clarification="I had trouble understanding. What would you like help with?"
            )

    def _quick_classify(self, message: str) -> Optional[IntentClassification]:
        """
        Quick pattern-based classification for obvious intents.
        Skips LLM call for common patterns to reduce latency.

        PATTERN ORDER IS CRITICAL - more specific patterns must come first.
        """
        msg_lower = message.lower().strip()

        # Greetings and general chat (exact matches only)
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
                     'thanks', 'thank you', 'thx', 'bye', 'goodbye', 'menu', 'help', 'start']
        if msg_lower in greetings or msg_lower.startswith('/'):
            return IntentClassification(
                intent=IntentType.GENERAL_CHAT,
                confidence=0.95,
                raw_message=message
            )

        # ============================================================
        # EXPERT-001: SYMPTOM OVERRIDE - Must come BEFORE manual patterns
        # "what does a bad motor smell like?" is troubleshooting, not manual
        # ============================================================
        symptom_words = ['smell', 'sound', 'feel', 'look', 'taste', 'noise',
                        'vibration', 'temperature', 'heat']
        bad_words = ['bad', 'failing', 'broken', 'wrong', 'weird', 'strange',
                    'funny', 'off', 'abnormal']

        has_symptom = any(s in msg_lower for s in symptom_words)
        has_bad = any(b in msg_lower for b in bad_words)

        if has_symptom and has_bad:
            return IntentClassification(
                intent=IntentType.TROUBLESHOOT,
                confidence=0.90,
                raw_message=message
            )

        # ============================================================
        # EXPERT-002: LOGGING PATTERNS - Documentation of completed work
        # "log this: changed belts" = WORK_ORDER_CREATE
        # ============================================================
        logging_patterns = ['log this', 'log it', 'log:', 'document this', 'document it',
                           'record this', 'record it', 'record:', 'log the following']
        for pattern in logging_patterns:
            if pattern in msg_lower:
                return IntentClassification(
                    intent=IntentType.WORK_ORDER_CREATE,
                    confidence=0.92,
                    raw_message=message
                )

        # ============================================================
        # EXPERT-003: HISTORY PATTERNS - Equipment history lookup
        # "VFD fault history" = EQUIPMENT_SEARCH (not WO status)
        # ============================================================
        history_patterns = ['fault history', 'history on', 'history of', 'records for',
                           'failure history', 'maintenance history', 'past faults',
                           'previous issues', 'all faults']
        for pattern in history_patterns:
            if pattern in msg_lower:
                return IntentClassification(
                    intent=IntentType.EQUIPMENT_SEARCH,
                    confidence=0.88,
                    raw_message=message
                )

        # Work order creation patterns
        wo_patterns = ['create wo', 'new work order', 'create work order', 'wo create',
                       'make wo', 'open work order', 'report issue', 'report an issue',
                       'need a wo', 'need work order', 'submit wo', 'schedule pm',
                       'put in a ticket', 'maintenance request']
        for pattern in wo_patterns:
            if pattern in msg_lower:
                return IntentClassification(
                    intent=IntentType.WORK_ORDER_CREATE,
                    confidence=0.90,
                    raw_message=message
                )

        # Manual/how-to patterns - procedures, specs, documentation
        # NOTE: "what does X smell/sound like" is caught above by symptom override
        manual_patterns = ['how do i', 'how to', 'procedure', 'instructions', 'manual',
                          'what does', 'what is', 'calibrat', 'configure', 'spec for',
                          'setup', 'set up', 'explain', 'tell me about', 'describe',
                          'error code', 'fault code', 'code mean', 'lockout', 'tolerance',
                          'torque spec', 'alignment', 'what should', 'normal']
        for pattern in manual_patterns:
            if pattern in msg_lower:
                return IntentClassification(
                    intent=IntentType.MANUAL_QUESTION,
                    confidence=0.85,
                    raw_message=message
                )

        # Troubleshooting patterns (active problems, symptoms)
        trouble_patterns = ['won\'t', 'wont', 'doesn\'t', 'doesnt', 'can\'t', 'cant',
                           'not working', 'broken', 'failed', 'overheating',
                           'vibrating', 'smoking', 'tripped', 'alarm',
                           'burning', 'hot', 'loud', 'stuck', 'leak', 'problem',
                           'getting error', 'throwing error', 'acting up',
                           'keeps failing', 'stopped working', 'shut down',
                           'pulling more', 'amp draw', 'phase imbalance', 'ground fault',
                           'harmonics', 'cavitating', 'going out', 'high on']
        for pattern in trouble_patterns:
            if pattern in msg_lower:
                return IntentClassification(
                    intent=IntentType.TROUBLESHOOT,
                    confidence=0.85,
                    raw_message=message
                )

        # Work order status patterns
        wo_status_patterns = ['my work orders', 'wo status', 'work order status', 'open wos',
                             'pending work orders', 'check wo', 'wo list', 'show work orders',
                             'what\'s open', 'whats open']
        for pattern in wo_status_patterns:
            if pattern in msg_lower:
                return IntentClassification(
                    intent=IntentType.WORK_ORDER_STATUS,
                    confidence=0.90,
                    raw_message=message
                )

        # Equipment search patterns
        equip_search_phrases = ['find', 'search for', 'list my', 'show my', 'show me my',
                               'what equipment', 'my equipment', 'my motors', 'my drives',
                               'my pumps', 'do i have', 'in my cmms', 'pull up',
                               'serial number', 'what model', 'spare']
        if any(p in msg_lower for p in equip_search_phrases):
            return IntentClassification(
                intent=IntentType.EQUIPMENT_SEARCH,
                confidence=0.85,
                raw_message=message
            )

        # No quick match - need LLM
        return None

    async def _llm_classify(self, message: str, user_id: str) -> IntentClassification:
        """
        Use LLM for intent classification.

        Uses Groq for fast, cheap classification (~$0.001 per call).
        """
        prompt = f"{INTENT_CLASSIFICATION_PROMPT}\n\n## USER MESSAGE\n{message}"

        # Use SIMPLE capability for fast classification
        llm_response = await self.llm_router.generate(
            prompt=prompt,
            capability=ModelCapability.SIMPLE,
            max_tokens=500,
            temperature=0.1  # Low temperature for consistent classification
        )

        # Parse JSON response
        try:
            # Clean response (remove markdown if present)
            clean_response = llm_response.text.strip()
            if clean_response.startswith('```'):
                clean_response = clean_response.split('```')[1]
                if clean_response.startswith('json'):
                    clean_response = clean_response[4:]
            clean_response = clean_response.strip()

            data = json.loads(clean_response)

            # Parse intent
            intent_str = data.get('intent', 'GENERAL_CHAT')
            try:
                intent = IntentType(intent_str)
            except ValueError:
                intent = IntentType.UNKNOWN

            # Parse entities (filter nulls)
            entities = {k: v for k, v in data.get('entities', {}).items() if v}

            return IntentClassification(
                intent=intent,
                confidence=float(data.get('confidence', 0.5)),
                entities=entities,
                clarification_needed=data.get('clarification_needed', False),
                suggested_clarification=data.get('suggested_clarification', ''),
                raw_message=message,
                model_used=llm_response.model or "groq"
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse classification response: {e}")
            logger.debug(f"Raw response: {llm_response.text}")

            # Fallback: try to extract intent from response text
            return self._extract_intent_from_text(llm_response.text, message)

    def _extract_intent_from_text(self, response: str, message: str) -> IntentClassification:
        """
        Fallback intent extraction when JSON parsing fails.
        """
        response_upper = response.upper()

        for intent_type in IntentType:
            if intent_type.value in response_upper:
                return IntentClassification(
                    intent=intent_type,
                    confidence=0.6,  # Lower confidence for fallback
                    raw_message=message
                )

        return IntentClassification(
            intent=IntentType.GENERAL_CHAT,
            confidence=0.5,
            raw_message=message,
            clarification_needed=True,
            suggested_clarification="I'm not sure what you need. Could you try rephrasing?"
        )


__all__ = [
    "IntentClassifier",
    "IntentClassification",
    "IntentType",
]
