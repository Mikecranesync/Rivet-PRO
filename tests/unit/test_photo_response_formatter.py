"""
Unit tests for format_photo_pipeline_response function (PHOTO-RESP-001)

Tests the Telegram response formatting for photo pipeline results.
"""

import pytest
from rivet_pro.core.utils.response_formatter import (
    format_photo_pipeline_response,
    _get_confidence_emoji,
    _truncate_to_limit,
    TELEGRAM_MAX_CHARS,
)


class TestConfidenceEmoji:
    """Tests for _get_confidence_emoji helper."""

    def test_high_confidence(self):
        assert _get_confidence_emoji(0.95) == "🟢"
        assert _get_confidence_emoji(0.90) == "🟢"

    def test_good_confidence(self):
        assert _get_confidence_emoji(0.85) == "✅"
        assert _get_confidence_emoji(0.80) == "✅"

    def test_medium_confidence(self):
        assert _get_confidence_emoji(0.75) == "🟡"
        assert _get_confidence_emoji(0.70) == "🟡"

    def test_low_confidence(self):
        assert _get_confidence_emoji(0.65) == "🔴"
        assert _get_confidence_emoji(0.50) == "🔴"
        assert _get_confidence_emoji(0.0) == "🔴"


class TestTruncateToLimit:
    """Tests for _truncate_to_limit helper."""

    def test_under_limit(self):
        text = "Short text"
        result = _truncate_to_limit(text, 100)
        assert result == text

    def test_at_limit(self):
        text = "a" * 100
        result = _truncate_to_limit(text, 100)
        assert result == text

    def test_over_limit_truncates(self):
        text = "a" * 200
        result = _truncate_to_limit(text, 100)
        assert len(result) <= 100
        assert "truncated" in result.lower()

    def test_truncates_at_newline(self):
        text = "Line 1\nLine 2\nLine 3\nLine 4"
        result = _truncate_to_limit(text, 25)
        assert "truncated" in result.lower()


class TestFormatPhotoPipelineResponse:
    """Tests for format_photo_pipeline_response function."""

    def test_minimal_screening_only(self):
        """Test with just screening result."""
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.92, "category": "vfd"}
        )

        assert "VFD" in result
        assert "92%" in result
        assert "🟢" in result  # High confidence

    def test_screening_with_extraction(self):
        """Test with screening and extraction results."""
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.85, "category": "motor"},
            extraction_result={
                "manufacturer": "Siemens",
                "model_number": "1LA7096-4AA10",
                "serial_number": "SN12345",
                "specs": {"voltage": "480V", "hp": "5", "rpm": "1750"},
                "confidence": 0.88,
            },
        )

        assert "MOTOR" in result
        assert "Siemens" in result
        assert "1LA7096-4AA10" in result
        assert "SN12345" in result
        assert "480V" in result
        assert "Equipment Details" in result

    def test_equipment_info_new(self):
        """Test with new equipment created."""
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.80, "category": "plc"},
            equipment_info={
                "equipment_id": "uuid-123",
                "equipment_number": "EQ-001",
                "is_new": True,
            },
        )

        assert "EQ-001" in result
        assert "Created" in result
        assert "🆕" in result

    def test_equipment_info_matched(self):
        """Test with existing equipment matched."""
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.80, "category": "pump"},
            equipment_info={
                "equipment_id": "uuid-456",
                "equipment_number": "EQ-002",
                "is_new": False,
            },
        )

        assert "EQ-002" in result
        assert "Matched" in result

    def test_safety_warnings_prominent(self):
        """Test safety warnings are displayed prominently."""
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.85, "category": "vfd"},
            analysis_result={
                "analysis": "VFD shows fault code F0001",
                "safety_warnings": [
                    "DANGER: High voltage 480V - do not touch",
                    "Lockout/Tagout required before servicing",
                    "PPE required: safety glasses and gloves",
                ],
                "confidence": 0.75,
            },
        )

        assert "SAFETY WARNINGS" in result
        assert "480V" in result
        assert "🔴" in result  # Danger emoji
        assert "🟡" in result  # Lockout/tagout warning

    def test_ai_analysis_section(self):
        """Test Claude analysis formatting."""
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.90, "category": "vfd"},
            analysis_result={
                "analysis": "Based on the fault history and specifications, this VFD appears to be experiencing intermittent overcurrent faults.",
                "solutions": [
                    "Check motor insulation resistance",
                    "Verify motor cable shielding",
                    "Review parameter P1000 settings",
                ],
                "confidence": 0.82,
            },
        )

        assert "AI Analysis" in result
        assert "overcurrent" in result.lower()
        assert "Recommended Solutions" in result
        assert "1." in result  # Numbered list

    def test_kb_citations_numbered(self):
        """Test KB citations are numbered references."""
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.85, "category": "plc"},
            analysis_result={
                "analysis": "PLC communication error detected",
                "kb_citations": [
                    {"title": "Siemens S7-1200 Troubleshooting", "url": "https://example.com/manual1"},
                    {"title": "Ethernet/IP Configuration Guide", "url": "https://example.com/guide"},
                ],
                "confidence": 0.78,
            },
        )

        assert "Sources" in result
        assert "[1]" in result
        assert "[2]" in result
        assert "Siemens S7-1200" in result

    def test_maintenance_history_summary(self):
        """Test maintenance history is summarized."""
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.88, "category": "motor"},
            maintenance_history=[
                {"work_order_number": "WO-2026-001", "title": "Motor bearing replacement", "status": "completed"},
                {"work_order_number": "WO-2026-002", "title": "VFD parameter adjustment", "status": "in_progress"},
            ],
        )

        assert "Recent History" in result
        assert "WO-2026-001" in result
        assert "WO-2026-002" in result
        assert "✅" in result  # Completed
        assert "🔄" in result  # In progress

    def test_cache_indicator(self):
        """Test cache indicator shown when from_cache=True."""
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.92, "category": "sensor"},
            from_cache=True,
        )

        assert "cache" in result.lower()
        assert "📦" in result

    def test_under_telegram_limit(self):
        """Test response is always under 4096 chars."""
        # Create a very full response
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.95, "category": "control_panel"},
            extraction_result={
                "manufacturer": "Allen-Bradley" * 5,
                "model_number": "1756-L71" * 3,
                "serial_number": "SN" + "1234567890" * 5,
                "specs": {
                    "voltage": "24VDC",
                    "current": "2A",
                    "hp": "N/A",
                    "rpm": "N/A",
                    "phase": "DC",
                    "frequency": "N/A",
                },
                "confidence": 0.91,
            },
            equipment_info={
                "equipment_id": "uuid-789",
                "equipment_number": "EQ-CTRL-001",
                "is_new": True,
            },
            analysis_result={
                "analysis": "This is a very long analysis. " * 100,  # Very long
                "solutions": [
                    "Solution 1 that is quite detailed and long " * 3,
                    "Solution 2 with more information " * 3,
                    "Solution 3 describing steps " * 3,
                    "Solution 4 with technical details " * 3,
                ],
                "safety_warnings": [
                    "Warning about high voltage systems",
                    "Lockout/Tagout procedures required",
                    "PPE equipment needed",
                ],
                "kb_citations": [
                    {"title": "Manual Title " * 5, "url": "https://example.com/" + "a" * 100},
                    {"title": "Guide Title", "url": ""},
                    {"title": "Reference Doc", "url": "https://docs.example.com/ref"},
                ],
                "recommendations": [
                    "Recommendation 1 " * 10,
                    "Recommendation 2 " * 10,
                ],
                "confidence": 0.85,
            },
            maintenance_history=[
                {"work_order_number": "WO-001", "title": "Title " * 20, "status": "completed"},
                {"work_order_number": "WO-002", "title": "Another long title", "status": "open"},
                {"work_order_number": "WO-003", "title": "Third WO", "status": "completed"},
            ],
            from_cache=True,
        )

        assert len(result) <= TELEGRAM_MAX_CHARS, f"Response too long: {len(result)} chars"

    def test_empty_input(self):
        """Test with no data - should still produce valid output."""
        result = format_photo_pipeline_response()

        assert "Identified" in result  # Default header
        assert len(result) > 0
        assert len(result) <= TELEGRAM_MAX_CHARS

    def test_markdown_formatting(self):
        """Test markdown formatting is used correctly."""
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.88, "category": "vfd"},
            extraction_result={
                "manufacturer": "ABB",
                "model_number": "ACS880",
                "confidence": 0.85,
            },
        )

        # Check for markdown bold
        assert "*" in result
        # Check for code blocks
        assert "```" in result

    def test_recommendations_shown_if_space(self):
        """Test recommendations shown when space permits."""
        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.80, "category": "sensor"},
            analysis_result={
                "recommendations": ["Order replacement sensor", "Schedule PM"],
                "confidence": 0.70,
            },
        )

        assert "Next Steps" in result
        assert "☐" in result  # Checkbox

    def test_analysis_truncated_when_long(self):
        """Test that long analysis text is truncated."""
        long_analysis = "This is a test. " * 100  # Very long

        result = format_photo_pipeline_response(
            screening_result={"confidence": 0.85, "category": "motor"},
            analysis_result={
                "analysis": long_analysis,
                "confidence": 0.80,
            },
        )

        # Should be truncated with ellipsis
        assert "..." in result
        # Full text should not be there
        assert long_analysis not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
