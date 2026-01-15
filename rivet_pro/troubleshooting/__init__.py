"""
RIVET Pro Troubleshooting Module

Provides interactive troubleshooting tree navigation for equipment diagnostics.
Includes Claude API fallback for dynamic troubleshooting when no tree exists.
"""

from .callback import encode_callback, decode_callback, CallbackData
from .mermaid_parser import MermaidParser, parse_mermaid
from .history import NavigationHistory, NavigationSession, get_navigation_history
from .fallback import (
from .formatting import (
    format_node_text,
    format_safety_warning,
    is_safety_node,
    SafetyFormatter,
)

    generate_troubleshooting_guide,
    generate_troubleshooting_guide_sync,
    get_or_generate_troubleshooting,
    check_tree_exists,
    ClaudeFallbackError,
    TroubleshootingGuide,
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
    "generate_troubleshooting_guide",
    "generate_troubleshooting_guide_sync",
    "get_or_generate_troubleshooting",
    "check_tree_exists",
    "ClaudeFallbackError",
    "TroubleshootingGuide",
    "format_node_text",
    "format_safety_warning",
    "is_safety_node",
    "SafetyFormatter",
]
