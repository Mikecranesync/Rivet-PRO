"""
Tests for Claude AI Analysis and KB Synthesis Service (PHOTO-CLAUDE-001)
"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from rivet_pro.core.services.claude_analyzer import (
    ClaudeAnalyzer,
    AnalysisResult,
    get_claude_analyzer
)


class TestAnalysisResult:
    """Test AnalysisResult dataclass."""

    def test_default_values(self):
        """Test AnalysisResult has correct default values."""
        result = AnalysisResult(analysis="Test analysis")

        assert result.analysis == "Test analysis"
        assert result.solutions == []
        assert result.kb_citations == []
        assert result.recommendations == []
        assert result.confidence == 0.0
        assert result.safety_warnings == []
        assert result.cost_usd == 0.0
        assert result.model == "claude-sonnet-4-20250514"

    def test_full_initialization(self):
        """Test AnalysisResult with all fields."""
        result = AnalysisResult(
            analysis="Full analysis text",
            solutions=["Solution 1", "Solution 2"],
            kb_citations=[{"title": "Manual", "url": "http://example.com"}],
            recommendations=["Check voltage", "Replace filter"],
            confidence=0.85,
            safety_warnings=["LOCKOUT required"],
            cost_usd=0.012,
            model="claude-sonnet-4-20250514"
        )

        assert len(result.solutions) == 2
        assert len(result.kb_citations) == 1
        assert result.confidence == 0.85
        assert result.cost_usd == 0.012


class TestClaudeAnalyzer:
    """Test ClaudeAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ClaudeAnalyzer()

    @pytest.fixture
    def sample_specs(self):
        """Sample component specifications."""
        return {
            "manufacturer": "Siemens",
            "model": "G120C",
            "voltage": "480V",
            "horsepower": "10HP",
            "serial_number": "SN-12345"
        }

    @pytest.fixture
    def sample_history(self):
        """Sample maintenance history."""
        return [
            {
                "work_order_number": "WO-2026-000001",
                "title": "Drive fault F0002 - Overvoltage",
                "status": "completed",
                "fault_codes": ["F0002"],
                "created_at": datetime.now() - timedelta(days=30),
                "resolution_time_hours": 2.5
            },
            {
                "work_order_number": "WO-2026-000002",
                "title": "Preventive maintenance",
                "status": "completed",
                "fault_codes": [],
                "created_at": datetime.now() - timedelta(days=60),
                "resolution_time_hours": 1.0
            }
        ]

    @pytest.fixture
    def sample_kb_context(self):
        """Sample KB atoms."""
        return [
            {
                "atom_id": str(uuid4()),
                "title": "F0002 - Overvoltage Fault",
                "content": "F0002 indicates DC bus overvoltage. Common causes: regenerative energy not dissipated, input voltage spike, or faulty braking resistor.",
                "type": "fault",
                "source_url": "https://support.siemens.com/cs/document/67854244",
                "confidence": 0.95
            },
            {
                "atom_id": str(uuid4()),
                "title": "G120C Troubleshooting Guide",
                "content": "Check braking resistor connections. Verify DC bus voltage levels. Review motor acceleration settings.",
                "type": "procedure",
                "source_url": "https://support.siemens.com/cs/document/109760000",
                "confidence": 0.88
            }
        ]

    def test_format_specs_context_with_data(self, analyzer, sample_specs):
        """Test specs formatting with data."""
        result = analyzer._format_specs_context(sample_specs)

        assert "Component Specifications:" in result
        assert "Siemens" in result
        assert "G120C" in result
        assert "480V" in result

    def test_format_specs_context_empty(self, analyzer):
        """Test specs formatting with empty data."""
        result = analyzer._format_specs_context({})
        assert "No component specifications available" in result

        result = analyzer._format_specs_context(None)
        assert "No component specifications available" in result

    def test_format_history_context_with_data(self, analyzer, sample_history):
        """Test history formatting with data."""
        result = analyzer._format_history_context(sample_history)

        assert "Maintenance History" in result
        assert "WO-2026-000001" in result
        assert "F0002" in result
        assert "completed" in result

    def test_format_history_context_empty(self, analyzer):
        """Test history formatting with empty data."""
        result = analyzer._format_history_context([])
        assert "No maintenance history available" in result

    def test_format_kb_context_with_data(self, analyzer, sample_kb_context):
        """Test KB context formatting with data."""
        result = analyzer._format_kb_context(sample_kb_context)

        assert "Knowledge Base Information:" in result
        assert "F0002 - Overvoltage Fault" in result
        assert "FAULT" in result
        assert "95%" in result  # Confidence display

    def test_format_kb_context_empty(self, analyzer):
        """Test KB context formatting with empty data."""
        result = analyzer._format_kb_context([])
        assert "No relevant knowledge base entries found" in result

    def test_extract_safety_warnings(self, analyzer):
        """Test safety warning extraction."""
        response = """
        Analysis of the equipment shows issues.

        WARNING: Ensure lockout/tagout procedures are followed before maintenance.

        The motor may still be running. DANGER: High voltage present.

        Solutions include checking the bearings. Caution: Use PPE when working near rotating equipment.

        Never attempt repairs without proper training.
        """

        warnings = analyzer._extract_safety_warnings(response)

        assert len(warnings) > 0
        assert any("lockout" in w.lower() for w in warnings)
        assert any("high voltage" in w.lower() or "danger" in w.lower() for w in warnings)

    def test_extract_safety_warnings_empty(self, analyzer):
        """Test safety warning extraction with no warnings."""
        response = "The equipment is operating normally. No issues detected."
        warnings = analyzer._extract_safety_warnings(response)
        assert len(warnings) == 0

    def test_parse_structured_response(self, analyzer):
        """Test structured response parsing."""
        response = """
        The equipment shows signs of overvoltage issues based on the fault history.

        Solutions:
        - Check braking resistor connections
        - Verify DC bus voltage levels
        - Review acceleration/deceleration ramp settings

        Recommendations:
        1. Schedule preventive maintenance
        2. Order replacement braking resistor as backup
        3. Monitor fault frequency
        """

        parsed = analyzer._parse_structured_response(response)

        assert "overvoltage" in parsed["analysis"].lower()
        assert len(parsed["solutions"]) >= 1
        assert len(parsed["recommendations"]) >= 1

    def test_format_kb_citations(self, analyzer, sample_kb_context):
        """Test KB citation formatting."""
        citations = analyzer._format_kb_citations(sample_kb_context)

        assert len(citations) == 2
        assert citations[0]["title"] == "F0002 - Overvoltage Fault"
        assert citations[0]["type"] == "fault"
        assert "siemens.com" in citations[0]["url"]

    def test_calculate_confidence(self, analyzer, sample_specs, sample_history, sample_kb_context):
        """Test confidence calculation."""
        # Full context - high confidence
        confidence = analyzer._calculate_confidence(sample_specs, sample_history, sample_kb_context)
        assert confidence >= 0.7
        assert confidence <= 0.95

        # No context - low confidence
        confidence = analyzer._calculate_confidence({}, [], [])
        assert confidence == 0.5

        # Partial context
        confidence = analyzer._calculate_confidence(sample_specs, [], [])
        assert confidence > 0.5
        assert confidence < 0.7

    def test_create_fallback_result(self, analyzer, sample_specs, sample_history, sample_kb_context):
        """Test fallback result creation."""
        result = analyzer._create_fallback_result(
            sample_specs,
            sample_history,
            sample_kb_context,
            "Test error"
        )

        assert isinstance(result, AnalysisResult)
        assert "Analysis unavailable" in result.analysis
        assert "Siemens" in result.analysis  # Specs included
        assert result.confidence == 0.3  # Low confidence
        assert result.cost_usd == 0.0  # No cost
        assert result.model == "fallback"

    @pytest.mark.asyncio
    async def test_analyze_with_kb_mock_success(self, analyzer, sample_specs, sample_history, sample_kb_context):
        """Test analyze_with_kb with mocked Claude API."""
        equipment_id = uuid4()

        # Mock the Claude response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = """
        Based on the maintenance history showing F0002 overvoltage faults,
        this Siemens G120C drive appears to have issues with regenerative energy dissipation.

        Solutions:
        - Check braking resistor for damage
        - Verify proper braking resistor sizing for load
        - Review deceleration ramp time settings

        Recommendations:
        - Schedule electrical inspection
        - Order backup braking resistor
        - Monitor fault frequency over next 30 days

        WARNING: Always perform lockout/tagout before inspecting braking circuits.
        """
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 800
        mock_response.usage.output_tokens = 200

        with patch.object(analyzer, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await analyzer.analyze_with_kb(
                equipment_id=equipment_id,
                specs=sample_specs,
                history=sample_history,
                kb_context=sample_kb_context
            )

        assert isinstance(result, AnalysisResult)
        assert "F0002" in result.analysis or "overvoltage" in result.analysis.lower()
        assert len(result.solutions) >= 1
        assert len(result.kb_citations) == 2
        assert result.confidence > 0.5
        assert result.cost_usd > 0
        assert result.model == "claude-sonnet-4-20250514"
        assert len(result.safety_warnings) >= 1

    @pytest.mark.asyncio
    async def test_analyze_with_kb_fallback_on_error(self, analyzer, sample_specs, sample_history, sample_kb_context):
        """Test analyze_with_kb falls back gracefully on error."""
        equipment_id = uuid4()

        with patch.object(analyzer, '_get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("API Error")

            result = await analyzer.analyze_with_kb(
                equipment_id=equipment_id,
                specs=sample_specs,
                history=sample_history,
                kb_context=sample_kb_context
            )

        assert isinstance(result, AnalysisResult)
        assert "Analysis unavailable" in result.analysis
        assert result.model == "fallback"
        assert result.cost_usd == 0.0

    def test_get_claude_analyzer_singleton(self):
        """Test singleton pattern for analyzer."""
        analyzer1 = get_claude_analyzer()
        analyzer2 = get_claude_analyzer()

        assert analyzer1 is analyzer2


class TestAnalysisResultSerialization:
    """Test AnalysisResult can be serialized for API responses."""

    def test_to_dict(self):
        """Test AnalysisResult can be converted to dict."""
        result = AnalysisResult(
            analysis="Test",
            solutions=["A", "B"],
            kb_citations=[{"title": "X", "url": "http://x.com"}],
            recommendations=["Do this"],
            confidence=0.8,
            safety_warnings=["Be careful"],
            cost_usd=0.01,
            model="claude-sonnet-4-20250514"
        )

        # Dataclasses support __dict__ via asdict
        from dataclasses import asdict
        result_dict = asdict(result)

        assert result_dict["analysis"] == "Test"
        assert len(result_dict["solutions"]) == 2
        assert result_dict["confidence"] == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
