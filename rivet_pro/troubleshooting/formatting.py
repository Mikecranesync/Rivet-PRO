"""
Safety Warning Formatting Module for RIVET Pro

Formats safety warnings using Telegram blockquote style for visual distinction.
Supports both text and caption contexts with proper HTML escaping.

Author: Atlas Engineer
Task: TASK-9.6
"""

import html
from typing import Dict, Any, Optional


class SafetyFormatter:
    """Formats safety warnings for Telegram with visual distinction."""

    # Safety indicators
    SAFETY_TYPES = {"safety", "warning", "danger", "caution"}
    WARNING_EMOJI = "⚠️"
    DANGER_EMOJI = "🚨"
    CAUTION_EMOJI = "⚡"

    # HTML formatting
    BLOCKQUOTE_START = "<blockquote>"
    BLOCKQUOTE_END = "</blockquote>"
    EXPANDABLE_START = "<blockquote expandable>"

    @classmethod
    def is_safety_node(cls, node: Dict[str, Any]) -> bool:
        """
        Check if a node represents a safety warning.

        Args:
            node: Tree node dictionary with 'type' and/or 'label' fields

        Returns:
            True if node is a safety warning
        """
        # Check explicit type
        node_type = node.get("type", "").lower()
        if node_type in cls.SAFETY_TYPES:
            return True

        # Check for warning emoji in label
        label = node.get("label", "")
        if any(emoji in label for emoji in [cls.WARNING_EMOJI, cls.DANGER_EMOJI, cls.CAUTION_EMOJI]):
            return True

        # Check for warning keywords
        warning_keywords = ["warning", "danger", "caution", "hazard", "risk", "voltage", "electrical"]
        label_lower = label.lower()
        return any(keyword in label_lower for keyword in warning_keywords)

    @classmethod
    def get_safety_emoji(cls, node: Dict[str, Any]) -> str:
        """
        Get appropriate emoji for safety level.

        Args:
            node: Tree node dictionary

        Returns:
            Emoji string for the safety level
        """
        node_type = node.get("type", "").lower()
        label = node.get("label", "").lower()

        # Danger level (high voltage, electrical hazards)
        if node_type == "danger" or "voltage" in label or "electrical" in label:
            return cls.DANGER_EMOJI

        # Caution level (moving parts, sharp edges)
        if node_type == "caution" or "moving" in label or "sharp" in label:
            return cls.CAUTION_EMOJI

        # Default warning level
        return cls.WARNING_EMOJI

    @classmethod
    def escape_html(cls, text: str) -> str:
        """
        Escape HTML special characters for Telegram.

        Args:
            text: Raw text to escape

        Returns:
            HTML-escaped text
        """
        return html.escape(text, quote=False)

    @classmethod
    def format_safety_warning(
        cls,
        text: str,
        node: Optional[Dict[str, Any]] = None,
        expandable: bool = False
    ) -> str:
        """
        Format text as a safety warning blockquote.

        Args:
            text: Warning text to format
            node: Optional node dict for context
            expandable: Use expandable blockquote if True

        Returns:
            HTML-formatted safety warning
        """
        # Get appropriate emoji
        emoji = cls.get_safety_emoji(node or {})

        # Escape HTML
        escaped_text = cls.escape_html(text)

        # Remove existing emoji from text if present
        for safety_emoji in [cls.WARNING_EMOJI, cls.DANGER_EMOJI, cls.CAUTION_EMOJI]:
            escaped_text = escaped_text.replace(safety_emoji, "").strip()

        # Format as blockquote
        blockquote_start = cls.EXPANDABLE_START if expandable else cls.BLOCKQUOTE_START

        # Multi-line support: add emoji only to first line
        lines = escaped_text.split("\n")
        if lines:
            lines[0] = f"{emoji} <b>WARNING</b>\n\n{lines[0]}"
            formatted_text = "\n".join(lines)
        else:
            formatted_text = f"{emoji} <b>WARNING</b>\n\n{escaped_text}"

        return f"{blockquote_start}{formatted_text}{cls.BLOCKQUOTE_END}"

    @classmethod
    def format_node_text(
        cls,
        node: Dict[str, Any],
        escape: bool = True,
        expandable: bool = False
    ) -> str:
        """
        Format a tree node's text with appropriate safety styling.

        Args:
            node: Tree node dictionary with 'label' and optional 'type'
            escape: Apply HTML escaping (default True)
            expandable: Use expandable blockquote for safety warnings

        Returns:
            Formatted text string
        """
        label = node.get("label", "")

        if not label:
            return ""

        # Check if this is a safety node
        if cls.is_safety_node(node):
            return cls.format_safety_warning(label, node, expandable)

        # Regular node: just escape if needed
        if escape:
            return cls.escape_html(label)

        return label

    @classmethod
    def format_caption_with_safety(
        cls,
        caption: str,
        safety_warnings: list[str],
        expandable: bool = True
    ) -> str:
        """
        Format a photo/video caption with embedded safety warnings.

        Args:
            caption: Main caption text
            safety_warnings: List of safety warning texts
            expandable: Use expandable blockquotes

        Returns:
            HTML-formatted caption with warnings
        """
        parts = []

        # Add main caption
        if caption:
            parts.append(cls.escape_html(caption))

        # Add safety warnings
        if safety_warnings:
            parts.append("")  # Blank line separator
            for warning in safety_warnings:
                formatted_warning = cls.format_safety_warning(
                    warning,
                    {"type": "safety"},
                    expandable=expandable
                )
                parts.append(formatted_warning)

        return "\n".join(parts)


# Convenience functions for direct use
def format_node_text(
    node: Dict[str, Any],
    escape: bool = True,
    expandable: bool = False
) -> str:
    """
    Format a tree node's text with appropriate safety styling.

    Convenience wrapper for SafetyFormatter.format_node_text.

    Args:
        node: Tree node dictionary with 'label' and optional 'type'
        escape: Apply HTML escaping (default True)
        expandable: Use expandable blockquote for safety warnings

    Returns:
        Formatted text string

    Example:
        >>> node = {"label": "Check motor", "type": "action"}
        >>> format_node_text(node)
        'Check motor'

        >>> safety_node = {"label": "HIGH VOLTAGE - Do not touch", "type": "safety"}
        >>> format_node_text(safety_node)
        '<blockquote>⚠️ <b>WARNING</b>\\n\\nHIGH VOLTAGE - Do not touch</blockquote>'
    """
    return SafetyFormatter.format_node_text(node, escape, expandable)


def format_safety_warning(
    text: str,
    node: Optional[Dict[str, Any]] = None,
    expandable: bool = False
) -> str:
    """
    Format text as a safety warning blockquote.

    Convenience wrapper for SafetyFormatter.format_safety_warning.

    Args:
        text: Warning text to format
        node: Optional node dict for context
        expandable: Use expandable blockquote if True

    Returns:
        HTML-formatted safety warning

    Example:
        >>> format_safety_warning("Lockout/tagout required before maintenance")
        '<blockquote>⚠️ <b>WARNING</b>\\n\\nLockout/tagout required before maintenance</blockquote>'
    """
    return SafetyFormatter.format_safety_warning(text, node, expandable)


def is_safety_node(node: Dict[str, Any]) -> bool:
    """
    Check if a node represents a safety warning.

    Convenience wrapper for SafetyFormatter.is_safety_node.

    Args:
        node: Tree node dictionary

    Returns:
        True if node is a safety warning

    Example:
        >>> is_safety_node({"label": "Check filter", "type": "action"})
        False

        >>> is_safety_node({"label": "⚠️ HIGH VOLTAGE", "type": "safety"})
        True
    """
    return SafetyFormatter.is_safety_node(node)
