"""
Intelligence Module for Rivet Pro

Provides NLP-first intelligent routing for the always-on assistant:
- Intent classification from natural language
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

__all__ = [
    "IntentClassifier",
    "IntentClassification",
    "IntentType",
    "AdaptiveCommandService",
    "UserCommand",
]
