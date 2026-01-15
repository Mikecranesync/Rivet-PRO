"""
RIVET Pro Troubleshooting Module

Provides interactive troubleshooting tree navigation for equipment diagnostics.
Includes Claude API fallback for dynamic troubleshooting when no tree exists.
Includes draft system for saving Claude-generated guides as reviewable trees.
"""

from .callback import encode_callback, decode_callback, CallbackData
from .mermaid_parser import MermaidParser, parse_mermaid
from .history import NavigationHistory, NavigationSession, get_navigation_history
from .formatting import (
    format_node_text,
    format_safety_warning,
    is_safety_node,
    SafetyFormatter,
)
from .fallback import (
    generate_troubleshooting_guide,
    generate_troubleshooting_guide_sync,
    get_or_generate_troubleshooting,
    check_tree_exists,
    ClaudeFallbackError,
    TroubleshootingGuide,
)
from .drafts import (
    save_draft,
    get_draft,
    list_drafts,
    approve_draft,
    reject_draft,
    delete_draft,
    get_draft_stats,
    DraftStatus,
)

__all__ = [
    "encode_callback",
    "decode_callback",
    "CallbackData",
    "MermaidParser",
    "parse_mermaid",
    "NavigationHistory",
    "NavigationSession",
    "get_navigation_history",
    "format_node_text",
    "format_safety_warning",
    "is_safety_node",
    "SafetyFormatter",
    "generate_troubleshooting_guide",
    "generate_troubleshooting_guide_sync",
    "get_or_generate_troubleshooting",
    "check_tree_exists",
    "ClaudeFallbackError",
    "TroubleshootingGuide",
    "save_draft",
    "get_draft",
    "list_drafts",
    "approve_draft",
    "reject_draft",
    "delete_draft",
    "get_draft_stats",
    "DraftStatus",
]
