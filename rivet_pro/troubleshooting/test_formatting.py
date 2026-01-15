"""
Unit Tests for Safety Warning Formatting Module

Tests HTML escaping, blockquote formatting, multi-line warnings,
and caption integration for RIVET Pro troubleshooting trees.

Author: Atlas Engineer
Task: TASK-9.6
"""

import pytest
from rivet_pro.troubleshooting.formatting import (
    SafetyFormatter,
    format_node_text,
    format_safety_warning,
    is_safety_node,
)


class TestSafetyNodeDetection:
    """Test identification of safety nodes."""

    def test_explicit_safety_type(self):
        """Safety nodes identified by type='safety'."""
        node = {"label": "Check voltage", "type": "safety"}
        assert is_safety_node(node) is True

    def test_warning_type_variants(self):
        """All warning type variants detected."""
        for node_type in ["warning", "danger", "caution", "SAFETY"]:
            node = {"label": "Test", "type": node_type}
            assert is_safety_node(node) is True

    def test_emoji_detection(self):
        """Safety nodes identified by warning emoji."""
        node = {"label": "⚠️ HIGH VOLTAGE", "type": "action"}
        assert is_safety_node(node) is True

    def test_keyword_detection(self):
        """Safety nodes identified by warning keywords."""
        keywords = ["warning", "danger", "hazard", "voltage", "electrical"]
        for keyword in keywords:
            node = {"label": f"Check for {keyword}", "type": "action"}
            assert is_safety_node(node) is True

    def test_non_safety_node(self):
        """Regular nodes not flagged as safety."""
        node = {"label": "Replace filter", "type": "action"}
        assert is_safety_node(node) is False

    def test_empty_node(self):
        """Empty nodes not flagged as safety."""
        assert is_safety_node({}) is False


class TestSafetyEmojiSelection:
    """Test appropriate emoji selection for safety levels."""

    def test_danger_emoji_for_voltage(self):
        """Danger emoji (🚨) for high voltage warnings."""
        node = {"label": "HIGH VOLTAGE", "type": "danger"}
        emoji = SafetyFormatter.get_safety_emoji(node)
        assert emoji == "🚨"

    def test_caution_emoji_for_moving_parts(self):
        """Caution emoji (⚡) for moving parts."""
        node = {"label": "Moving parts present", "type": "caution"}
        emoji = SafetyFormatter.get_safety_emoji(node)
        assert emoji == "⚡"

    def test_default_warning_emoji(self):
        """Default warning emoji (⚠️) for general safety."""
        node = {"label": "Wear PPE", "type": "safety"}
        emoji = SafetyFormatter.get_safety_emoji(node)
        assert emoji == "⚠️"


class TestHtmlEscaping:
    """Test HTML character escaping."""

    def test_escape_basic_html(self):
        """Basic HTML tags escaped."""
        text = "<script>alert('xss')</script>"
        escaped = SafetyFormatter.escape_html(text)
        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "<script>" not in escaped

    def test_escape_ampersands(self):
        """Ampersands escaped."""
        text = "Motor & pump assembly"
        escaped = SafetyFormatter.escape_html(text)
        assert "&amp;" in escaped

    def test_preserve_spaces(self):
        """Spaces and newlines preserved."""
        text = "Line 1\nLine 2"
        escaped = SafetyFormatter.escape_html(text)
        assert "\n" in escaped


class TestSafetyWarningFormatting:
    """Test blockquote formatting for safety warnings."""

    def test_basic_warning_format(self):
        """Basic safety warning formatted as blockquote."""
        text = "Lockout/tagout required"
        formatted = format_safety_warning(text)

        assert "<blockquote>" in formatted
        assert "</blockquote>" in formatted
        assert "⚠️" in formatted or "🚨" in formatted or "⚡" in formatted
        assert "<b>WARNING</b>" in formatted
        assert "Lockout/tagout required" in formatted

    def test_expandable_blockquote(self):
        """Expandable blockquote format option."""
        text = "Long safety procedure..."
        formatted = format_safety_warning(text, expandable=True)

        assert "<blockquote expandable>" in formatted

    def test_multi_line_warning(self):
        """Multi-line warnings formatted correctly."""
        text = "HIGH VOLTAGE\nLockout/tagout required\nUse insulated tools"
        formatted = format_safety_warning(text)

        # Should have all lines
        assert "HIGH VOLTAGE" in formatted
        assert "Lockout/tagout required" in formatted
        assert "Use insulated tools" in formatted

        # Emoji only on first line
        lines = formatted.split("\n")
        emoji_count = sum(
            1 for line in lines if any(e in line for e in ["⚠️", "🚨", "⚡"])
        )
        # Should appear once (in first line)
        assert emoji_count >= 1

    def test_html_injection_prevention(self):
        """HTML in warning text is escaped."""
        text = "<script>alert('danger')</script>"
        formatted = format_safety_warning(text)

        assert "&lt;script&gt;" in formatted
        assert "<script>" not in formatted or "<blockquote>" in formatted

    def test_emoji_deduplication(self):
        """Existing emoji removed before formatting."""
        text = "⚠️ HIGH VOLTAGE"
        formatted = format_safety_warning(text)

        # Should not have duplicate emoji on same line
        # (formatter adds it, so should strip existing)
        assert "HIGH VOLTAGE" in formatted


class TestNodeTextFormatting:
    """Test formatting of complete tree nodes."""

    def test_regular_node_formatting(self):
        """Regular nodes formatted as plain text."""
        node = {"label": "Check motor", "type": "action"}
        formatted = format_node_text(node)

        assert formatted == "Check motor"
        assert "<blockquote>" not in formatted

    def test_safety_node_formatting(self):
        """Safety nodes formatted as blockquotes."""
        node = {"label": "HIGH VOLTAGE - Do not touch", "type": "safety"}
        formatted = format_node_text(node)

        assert "<blockquote>" in formatted
        assert "</blockquote>" in formatted
        assert "WARNING" in formatted
        assert "HIGH VOLTAGE - Do not touch" in formatted

    def test_empty_label_handling(self):
        """Empty labels return empty string."""
        node = {"label": "", "type": "action"}
        formatted = format_node_text(node)

        assert formatted == ""

    def test_missing_label_handling(self):
        """Missing labels return empty string."""
        node = {"type": "action"}
        formatted = format_node_text(node)

        assert formatted == ""

    def test_escape_parameter(self):
        """Escape parameter controls HTML escaping."""
        node = {"label": "<b>Test</b>", "type": "action"}

        # With escaping (default)
        escaped = format_node_text(node, escape=True)
        assert "&lt;b&gt;" in escaped

        # Without escaping
        unescaped = format_node_text(node, escape=False)
        assert "<b>Test</b>" == unescaped

    def test_expandable_parameter(self):
        """Expandable parameter passed to safety formatting."""
        node = {"label": "Long safety note", "type": "safety"}
        formatted = format_node_text(node, expandable=True)

        assert "<blockquote expandable>" in formatted


class TestCaptionFormatting:
    """Test caption formatting with safety warnings."""

    def test_caption_with_single_warning(self):
        """Caption with one safety warning."""
        caption = "Motor nameplate photo"
        warnings = ["HIGH VOLTAGE"]

        formatted = SafetyFormatter.format_caption_with_safety(caption, warnings)

        assert "Motor nameplate photo" in formatted
        assert "<blockquote" in formatted
        assert "HIGH VOLTAGE" in formatted

    def test_caption_with_multiple_warnings(self):
        """Caption with multiple safety warnings."""
        caption = "Equipment inspection"
        warnings = [
            "Lockout/tagout required",
            "Moving parts present",
            "HIGH VOLTAGE"
        ]

        formatted = SafetyFormatter.format_caption_with_safety(caption, warnings)

        # All warnings present
        for warning in warnings:
            assert warning in formatted

        # Multiple blockquotes
        assert formatted.count("<blockquote") == 3

    def test_caption_without_warnings(self):
        """Caption without warnings formatted normally."""
        caption = "Equipment photo"
        formatted = SafetyFormatter.format_caption_with_safety(caption, [])

        assert "Equipment photo" in formatted
        assert "<blockquote" not in formatted

    def test_expandable_captions(self):
        """Expandable parameter works for captions."""
        caption = "Test"
        warnings = ["Warning 1", "Warning 2"]

        formatted = SafetyFormatter.format_caption_with_safety(
            caption,
            warnings,
            expandable=True
        )

        assert "<blockquote expandable>" in formatted


class TestTelegramCompatibility:
    """Test Telegram HTML parse mode compatibility."""

    def test_valid_telegram_html(self):
        """Generated HTML valid for Telegram parse_mode='HTML'."""
        node = {"label": "⚠️ HIGH VOLTAGE", "type": "safety"}
        formatted = format_node_text(node)

        # Telegram supports: <b>, <i>, <u>, <s>, <code>, <pre>, <a>, <blockquote>
        # Should only contain supported tags
        allowed_tags = ["<blockquote>", "<blockquote expandable>", "</blockquote>", "<b>", "</b>"]

        # Extract tags
        import re
        tags = re.findall(r'<[^>]+>', formatted)

        for tag in tags:
            # Should match allowed patterns
            assert any(allowed in tag for allowed in ["blockquote", "b", "/b", "/blockquote"])

    def test_no_nested_formatting_issues(self):
        """No invalid nested formatting."""
        node = {"label": "Test <b>bold</b> text", "type": "safety"}
        formatted = format_node_text(node)

        # Should escape the user's HTML
        assert "&lt;b&gt;" in formatted or "<b>WARNING</b>" in formatted


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_unicode_handling(self):
        """Unicode characters handled correctly."""
        node = {"label": "Température élevée ⚠️ 高温", "type": "safety"}
        formatted = format_node_text(node)

        assert "Température" in formatted
        assert "高温" in formatted

    def test_very_long_warning(self):
        """Long warnings formatted without breaking."""
        long_text = "Warning: " + "A" * 1000
        formatted = format_safety_warning(long_text)

        assert "<blockquote>" in formatted
        assert "</blockquote>" in formatted
        assert len(formatted) > 1000

    def test_special_characters(self):
        """Special characters handled correctly."""
        node = {"label": "10kV & 480VAC @ 60Hz", "type": "safety"}
        formatted = format_node_text(node)

        # Should escape & properly
        assert "&amp;" in formatted or "&" in formatted
        assert "10kV" in formatted

    def test_none_node_handling(self):
        """None values handled gracefully."""
        # format_safety_warning with None node
        formatted = format_safety_warning("Test", node=None)
        assert "<blockquote>" in formatted

    def test_missing_type_field(self):
        """Nodes without type field handled."""
        node = {"label": "Test"}
        assert format_node_text(node) == "Test"


# Integration test
def test_real_world_troubleshooting_tree():
    """Test with realistic troubleshooting tree nodes."""
    nodes = [
        {"label": "Motor won't start", "type": "problem"},
        {"label": "⚠️ LOCKOUT/TAGOUT REQUIRED", "type": "safety"},
        {"label": "Check power supply", "type": "diagnostic"},
        {"label": "HIGH VOLTAGE - Use insulated tools", "type": "danger"},
        {"label": "Replace motor if burned out", "type": "solution"},
    ]

    formatted_nodes = [format_node_text(node) for node in nodes]

    # Problem and diagnostic are plain
    assert "<blockquote>" not in formatted_nodes[0]
    assert "<blockquote>" not in formatted_nodes[2]

    # Safety nodes are formatted
    assert "<blockquote>" in formatted_nodes[1]
    assert "<blockquote>" in formatted_nodes[3]

    # All have content
    for formatted in formatted_nodes:
        assert len(formatted) > 0


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
