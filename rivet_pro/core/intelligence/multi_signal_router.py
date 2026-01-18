"""
Multi-Signal Intent Router (EXPERT-005)

3-signal voting system for high-accuracy intent classification:
- Keyword signal (40%): Fast pattern matching (~0ms, ~85% accuracy)
- Semantic signal (35%): Embedding similarity (~10ms, ~88% accuracy)
- LLM signal (25%): Only when combined confidence < 0.75 (~50ms, ~95% accuracy)

Target: 95%+ accuracy with LLM called for <20% of queries.

Usage:
    router = MultiSignalRouter()
    result = await router.classify("motor is overheating", user_id="123")
    print(result.intent)  # IntentType.TROUBLESHOOT
    print(result.confidence)  # 0.92
    print(result.signals_used)  # ['keyword', 'semantic']
"""

import logging
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

from rivet_pro.core.intelligence.intent_classifier import (
    IntentClassifier,
    IntentClassification,
    IntentType,
)

logger = logging.getLogger(__name__)


# ============================================================================
# SEMANTIC EMBEDDINGS - Intent examples for cosine similarity
# ============================================================================

# Pre-defined example phrases for each intent (used for semantic matching)
INTENT_EXAMPLES: Dict[IntentType, List[str]] = {
    IntentType.EQUIPMENT_SEARCH: [
        "find siemens motors",
        "what equipment do I have",
        "show me my drives",
        "search for pumps",
        "list my gear",
        "VFD fault history",
        "history on motor 7",
        "equipment records",
        "spare parts lookup",
        "serial number check",
    ],
    IntentType.WORK_ORDER_CREATE: [
        "create work order",
        "log this changed belts",
        "document this repair",
        "record maintenance",
        "schedule PM",
        "put in a ticket",
        "report issue",
        "maintenance request",
        "log it replaced filter",
        "new work order for pump",
    ],
    IntentType.WORK_ORDER_STATUS: [
        "check my work orders",
        "WO status",
        "what's open",
        "pending work orders",
        "show work orders",
        "ticket status",
        "open WOs",
        "my tasks",
    ],
    IntentType.MANUAL_QUESTION: [
        "how do I reset",
        "what does error mean",
        "calibration procedure",
        "wiring diagram",
        "lockout procedure",
        "torque spec",
        "parameter setting",
        "alignment tolerance",
        "megger spec",
        "normal operating range",
    ],
    IntentType.TROUBLESHOOT: [
        "motor overheating",
        "drive won't start",
        "error code F0002",
        "pump making noise",
        "tripped again",
        "what does bad motor smell like",
        "amp draw is high",
        "phase imbalance",
        "ground fault",
        "bearing going out",
        "cavitating pump",
        "harmonics on the line",
    ],
    IntentType.GENERAL_CHAT: [
        "hello",
        "thanks",
        "help",
        "what can you do",
        "good morning",
        "bye",
    ],
}


@dataclass
class Signal:
    """Individual signal from a classifier."""
    name: str  # 'keyword', 'semantic', 'llm'
    intent: IntentType
    confidence: float
    latency_ms: float


@dataclass
class MultiSignalResult:
    """Result from multi-signal classification."""
    intent: IntentType
    confidence: float
    signals_used: List[str] = field(default_factory=list)
    signal_details: List[Signal] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    total_latency_ms: float = 0.0
    llm_called: bool = False
    raw_message: str = ""


class MultiSignalRouter:
    """
    Multi-signal intent router with weighted voting.

    Combines fast keyword matching with semantic similarity,
    only falling back to LLM when combined confidence is low.
    """

    # Signal weights for voting (used when signals disagree)
    KEYWORD_WEIGHT = 0.45
    SEMANTIC_WEIGHT = 0.35
    LLM_WEIGHT = 0.20

    # Confidence threshold for LLM fallback
    # Only call LLM if BOTH keyword and semantic have low confidence
    LLM_THRESHOLD = 0.70

    # If keyword has HIGH confidence, skip LLM entirely
    KEYWORD_SKIP_THRESHOLD = 0.80

    def __init__(self):
        """Initialize router with keyword classifier and semantic embeddings."""
        self._keyword_classifier = IntentClassifier()
        self._intent_embeddings: Optional[Dict[IntentType, np.ndarray]] = None
        self._embedding_model = None

        logger.info("MultiSignalRouter initialized")

    def _get_embedding_model(self):
        """Lazy-load embedding model (sentence-transformers)."""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Use a small, fast model for embeddings
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded sentence-transformers model: all-MiniLM-L6-v2")
            except ImportError:
                logger.warning("sentence-transformers not installed, semantic signal disabled")
                self._embedding_model = False  # Mark as unavailable
        return self._embedding_model if self._embedding_model else None

    def _compute_intent_embeddings(self) -> Dict[IntentType, np.ndarray]:
        """Compute and cache embeddings for intent examples."""
        if self._intent_embeddings is not None:
            return self._intent_embeddings

        model = self._get_embedding_model()
        if not model:
            return {}

        self._intent_embeddings = {}

        for intent, examples in INTENT_EXAMPLES.items():
            # Embed all examples and average them
            embeddings = model.encode(examples)
            self._intent_embeddings[intent] = np.mean(embeddings, axis=0)

        logger.info(f"Computed intent embeddings for {len(self._intent_embeddings)} intents")
        return self._intent_embeddings

    def _keyword_signal(self, message: str) -> Optional[Signal]:
        """
        Fast keyword-based classification (~0ms).
        Uses the quick_classify patterns from IntentClassifier.
        """
        start = time.perf_counter()

        result = self._keyword_classifier._quick_classify(message)

        latency = (time.perf_counter() - start) * 1000

        if result:
            return Signal(
                name="keyword",
                intent=result.intent,
                confidence=result.confidence,
                latency_ms=latency
            )
        return None

    def _semantic_signal(self, message: str) -> Optional[Signal]:
        """
        Semantic similarity classification (~10ms).
        Compares message embedding to intent prototypes.
        """
        model = self._get_embedding_model()
        if not model:
            return None

        start = time.perf_counter()

        # Ensure intent embeddings are computed
        intent_embeddings = self._compute_intent_embeddings()
        if not intent_embeddings:
            return None

        # Embed the message
        message_embedding = model.encode([message])[0]

        # Compute cosine similarity to each intent
        similarities = {}
        for intent, intent_emb in intent_embeddings.items():
            # Cosine similarity
            sim = np.dot(message_embedding, intent_emb) / (
                np.linalg.norm(message_embedding) * np.linalg.norm(intent_emb)
            )
            similarities[intent] = float(sim)

        # Get best match
        best_intent = max(similarities, key=similarities.get)
        best_score = similarities[best_intent]

        latency = (time.perf_counter() - start) * 1000

        # Convert similarity to confidence (scale 0.5-1.0 to 0.0-1.0)
        confidence = max(0.0, min(1.0, (best_score - 0.3) / 0.5))

        return Signal(
            name="semantic",
            intent=best_intent,
            confidence=confidence,
            latency_ms=latency
        )

    async def _llm_signal(self, message: str, user_id: str) -> Optional[Signal]:
        """
        LLM-based classification (~50ms with Groq).
        Only called when other signals have low confidence.
        """
        start = time.perf_counter()

        try:
            result = await self._keyword_classifier._llm_classify(message, user_id)

            latency = (time.perf_counter() - start) * 1000

            return Signal(
                name="llm",
                intent=result.intent,
                confidence=result.confidence,
                latency_ms=latency
            )
        except Exception as e:
            logger.warning(f"LLM signal failed: {e}")
            return None

    def _aggregate_signals(
        self,
        signals: List[Signal],
        include_llm: bool = False
    ) -> Tuple[IntentType, float]:
        """
        Aggregate signals using weighted voting.

        Returns (best_intent, confidence).
        """
        if not signals:
            return IntentType.GENERAL_CHAT, 0.5

        # Calculate weighted scores for each intent
        intent_scores: Dict[IntentType, float] = {}
        total_weight = 0.0

        weights = {
            "keyword": self.KEYWORD_WEIGHT,
            "semantic": self.SEMANTIC_WEIGHT,
            "llm": self.LLM_WEIGHT if include_llm else 0.0
        }

        for signal in signals:
            weight = weights.get(signal.name, 0.0)
            if weight == 0.0:
                continue

            if signal.intent not in intent_scores:
                intent_scores[signal.intent] = 0.0

            intent_scores[signal.intent] += signal.confidence * weight
            total_weight += weight

        if not intent_scores:
            return IntentType.GENERAL_CHAT, 0.5

        # Normalize by actual weights used
        for intent in intent_scores:
            intent_scores[intent] /= total_weight

        # Get best intent
        best_intent = max(intent_scores, key=intent_scores.get)
        best_confidence = intent_scores[best_intent]

        return best_intent, best_confidence

    async def classify(
        self,
        message: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MultiSignalResult:
        """
        Classify intent using multi-signal voting.

        1. Always runs keyword + semantic signals
        2. Only calls LLM if combined confidence < 0.75

        Args:
            message: User's natural language message
            user_id: User identifier
            context: Optional context (not currently used)

        Returns:
            MultiSignalResult with intent, confidence, and signal details
        """
        start_time = time.perf_counter()
        signals: List[Signal] = []
        llm_called = False

        # Handle empty messages
        if not message or not message.strip():
            return MultiSignalResult(
                intent=IntentType.GENERAL_CHAT,
                confidence=1.0,
                signals_used=["default"],
                raw_message=message,
            )

        # Signal 1: Keyword (~0ms) - PRIMARY SIGNAL
        keyword_result = self._keyword_signal(message)
        if keyword_result:
            signals.append(keyword_result)
            logger.debug(f"Keyword signal: {keyword_result.intent} ({keyword_result.confidence:.2f})")

        # HIGH CONFIDENCE KEYWORD? Skip other signals entirely for speed
        if keyword_result and keyword_result.confidence >= self.KEYWORD_SKIP_THRESHOLD:
            logger.info(f"High-confidence keyword match ({keyword_result.confidence:.2f}), skipping semantic/LLM")
            return MultiSignalResult(
                intent=keyword_result.intent,
                confidence=keyword_result.confidence,
                signals_used=["keyword"],
                signal_details=signals,
                total_latency_ms=(time.perf_counter() - start_time) * 1000,
                llm_called=False,
                raw_message=message,
            )

        # Signal 2: Semantic (~10ms) - SECONDARY SIGNAL
        semantic_result = self._semantic_signal(message)
        if semantic_result:
            signals.append(semantic_result)
            logger.debug(f"Semantic signal: {semantic_result.intent} ({semantic_result.confidence:.2f})")

        # Check if signals AGREE on intent with decent confidence
        keyword_conf = keyword_result.confidence if keyword_result else 0.0
        semantic_conf = semantic_result.confidence if semantic_result else 0.0

        # If keyword and semantic AGREE on intent, use that
        if keyword_result and semantic_result and keyword_result.intent == semantic_result.intent:
            # Agreement boost: average confidence + 10%
            combined_conf = min(1.0, (keyword_conf + semantic_conf) / 2 + 0.10)
            if combined_conf >= self.LLM_THRESHOLD:
                logger.info(f"Keyword+Semantic agree on {keyword_result.intent} ({combined_conf:.2f})")
                return MultiSignalResult(
                    intent=keyword_result.intent,
                    confidence=combined_conf,
                    signals_used=["keyword", "semantic"],
                    signal_details=signals,
                    total_latency_ms=(time.perf_counter() - start_time) * 1000,
                    llm_called=False,
                    raw_message=message,
                )

        # Aggregate without LLM first
        best_intent, confidence = self._aggregate_signals(signals, include_llm=False)

        # Signal 3: LLM (only if combined confidence still low AND keyword is uncertain)
        if confidence < self.LLM_THRESHOLD and keyword_conf < self.KEYWORD_SKIP_THRESHOLD:
            logger.info(f"Low confidence ({confidence:.2f}), calling LLM fallback")
            llm_result = await self._llm_signal(message, user_id)
            if llm_result:
                signals.append(llm_result)
                llm_called = True
                logger.debug(f"LLM signal: {llm_result.intent} ({llm_result.confidence:.2f})")

            # Re-aggregate with LLM
            best_intent, confidence = self._aggregate_signals(signals, include_llm=True)

        total_latency = (time.perf_counter() - start_time) * 1000

        # Extract entities from keyword classifier if available
        entities = {}
        if keyword_result and hasattr(self._keyword_classifier, '_extract_entities'):
            # Could add entity extraction here in future
            pass

        logger.info(
            f"MultiSignal classified | intent={best_intent.value} | "
            f"confidence={confidence:.2f} | signals={[s.name for s in signals]} | "
            f"llm_called={llm_called} | latency={total_latency:.1f}ms"
        )

        return MultiSignalResult(
            intent=best_intent,
            confidence=confidence,
            signals_used=[s.name for s in signals],
            signal_details=signals,
            entities=entities,
            total_latency_ms=total_latency,
            llm_called=llm_called,
            raw_message=message,
        )


# Module-level singleton
_router: Optional[MultiSignalRouter] = None


def get_multi_signal_router() -> MultiSignalRouter:
    """Get or create the multi-signal router singleton."""
    global _router
    if _router is None:
        _router = MultiSignalRouter()
    return _router


__all__ = [
    "MultiSignalRouter",
    "MultiSignalResult",
    "Signal",
    "get_multi_signal_router",
]
