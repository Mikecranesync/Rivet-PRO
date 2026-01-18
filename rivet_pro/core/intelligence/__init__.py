"""
Intelligence Module for Rivet Pro

Provides NLP-first intelligent routing for the always-on assistant:
- Intent classification from natural language
- Multi-signal routing (keyword + semantic + LLM fallback)
- Adaptive command learning per user
- Entity extraction (manufacturers, models, fault codes)
"""

from rivet_pro.core.intelligence.intent_classifier import (
    IntentClassifier,
    IntentClassification,
    IntentType,
)
from rivet_pro.core.intelligence.adaptive_commands import (
    AdaptiveCommandService,
    UserCommand,
)
from rivet_pro.core.intelligence.multi_signal_router import (
    MultiSignalRouter,
    MultiSignalResult,
    Signal,
    get_multi_signal_router,
)
from rivet_pro.core.intelligence.context_retriever import (
    ContextRetriever,
    ContextMatch,
    RetrievedContext,
    get_context_retriever,
)

__all__ = [
    "IntentClassifier",
    "IntentClassification",
    "IntentType",
    "AdaptiveCommandService",
    "UserCommand",
    "MultiSignalRouter",
    "MultiSignalResult",
    "Signal",
    "get_multi_signal_router",
    "ContextRetriever",
    "ContextMatch",
    "RetrievedContext",
    "get_context_retriever",
]
