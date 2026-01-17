"""
Unit Tests for Claude AI Analysis Service

PHOTO-TEST-001: Comprehensive unit tests with mocked Claude API.
Tests analysis synthesis, safety extraction, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rivet_pro.core.services.claude_analyzer import (
    ClaudeAnalyzer,
    AnalysisResult,
    get_claude_analyzer,
)


# =============================================================================
# AnalysisResult Model Tests
# =============================================================================

class TestAnalysisResultModel:
    """Tests for AnalysisResult dataclass."""

    def test_basic_result(self):
        """Test basic analysis result."""
        result = AnalysisResult(
            analysis="This VFD shows signs of overheating.",
            solutions=["Check cooling fan", "Verify ambient temperature"],
            confidence=0.85,
        )

        assert result.analysis == "This VFD shows signs of overheating."
        assert len(result.solutions) == 2
        assert result.confidence == 0.85

    def test_full_result(self):
        """Test fully populated analysis result."""
        result = AnalysisResult(
            analysis="Equipment analysis text",
            solutions=["Solution 1", "Solution 2"],
            kb_citations=[
                {"title": "VFD Troubleshooting", "url": "http://example.com", "type": "procedure"},
            ],
            recommendations=["Order replacement parts", "Schedule preventive maintenance"],
            confidence=0.90,
            safety_warnings=["Lock out/tag out required", "High voltage hazard"],
            cost_usd=0.012,
            model="claude-sonnet-4-20250514",
        )

        assert len(result.kb_citations) == 1
        assert len(result.recommendations) == 2
        assert len(result.safety_warnings) == 2
        assert result.cost_usd == 0.012

    def test_empty_result(self):
        """Test empty analysis result with defaults."""
        result = AnalysisResult(analysis="Minimal analysis")

        assert result.analysis == "Minimal analysis"
        assert result.solutions == []
        assert result.kb_citations == []
        assert result.recommendations == []
        assert result.safety_warnings == []
        assert result.confidence == 0.0
        assert result.cost_usd == 0.0


# =============================================================================
# ClaudeAnalyzer Tests
# =============================================================================

class TestClaudeAnalyzer:
    """Tests for ClaudeAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ClaudeAnalyzer()

    @pytest.fixture
    def sample_specs(self):
        """Sample component specifications."""
        return {
            "manufacturer": "Allen-Bradley",
            "model_number": "PowerFlex 525",
            "voltage": "480V",
            "horsepower": "25HP",
            "phase": "3",
        }

    @pytest.fixture
    def sample_history(self):
        """Sample maintenance history."""
        return [
            {
                "work_order_number": "WO-2024-001",
                "title": "VFD overheating alarm",
                "status": "completed",
                "fault_codes": ["F003", "F007"],
                "resolution_time_hours": 2.5,
            },
            {
                "work_order_number": "WO-2024-002",
                "title": "Routine inspection",
                "status": "completed",
                "fault_codes": [],
                "resolution_time_hours": 0.5,
            },
        ]

    @pytest.fixture
    def sample_kb_atoms(self):
        """Sample KB atoms."""
        return [
            {
                "atom_id": "kb-001",
                "title": "PowerFlex 525 Fault Codes",
                "content": "F003 indicates motor overload. Check current settings.",
                "type": "procedure",
                "source_url": "https://docs.rockwell.com/pf525",
                "confidence": 0.90,
            },
            {
                "atom_id": "kb-002",
                "title": "VFD Cooling Best Practices",
                "content": "Ensure adequate ventilation around VFD enclosure.",
                "type": "tip",
                "source_url": "https://maintenance.guide/vfd",
                "confidence": 0.85,
            },
        ]

    # -------------------------------------------------------------------------
    # Context Formatting Tests
    # -------------------------------------------------------------------------

    def test_format_specs_context_with_data(self, analyzer, sample_specs):
        """Test specs formatting with data."""
        context = analyzer._format_specs_context(sample_specs)

        assert "Component Specifications:" in context
        assert "Allen-Bradley" in context
        assert "PowerFlex 525" in context
        assert "480V" in context

    def test_format_specs_context_empty(self, analyzer):
        """Test specs formatting with empty data."""
        context = analyzer._format_specs_context({})
        assert "No component specifications available" in context

    def test_format_specs_context_with_unknown(self, analyzer):
        """Test specs formatting filters out 'Unknown' values."""
        specs = {"manufacturer": "Unknown", "model": "AB123"}
        context = analyzer._format_specs_context(specs)
        assert "Unknown" not in context

    def test_format_history_context_with_data(self, analyzer, sample_history):
        """Test history formatting with data."""
        context = analyzer._format_history_context(sample_history)

        assert "Maintenance History" in context
        assert "WO-2024-001" in context
        assert "F003" in context
        assert "overheating" in context.lower()

    def test_format_history_context_empty(self, analyzer):
        """Test history formatting with empty data."""
        context = analyzer._format_history_context([])
        assert "No maintenance history available" in context

    def test_format_kb_context_with_data(self, analyzer, sample_kb_atoms):
        """Test KB formatting with data."""
        context = analyzer._format_kb_context(sample_kb_atoms)

        assert "Knowledge Base Information" in context
        assert "PowerFlex 525 Fault Codes" in context
        assert "F003" in context
        assert "Source 1" in context

    def test_format_kb_context_empty(self, analyzer):
        """Test KB formatting with empty data."""
        context = analyzer._format_kb_context([])
        assert "No relevant knowledge base entries" in context

    def test_format_kb_context_truncates_long_content(self, analyzer):
        """Test KB formatting truncates long content."""
        kb_atoms = [{
            "title": "Long Article",
            "content": "A" * 1000,  # Very long content
            "type": "article",
            "confidence": 0.80,
        }]

        context = analyzer._format_kb_context(kb_atoms)
        assert "..." in context  # Should be truncated

    # -------------------------------------------------------------------------
    # Safety Extraction Tests
    # -------------------------------------------------------------------------

    def test_extract_safety_warnings_lockout(self, analyzer):
        """Test extraction of lockout/tagout warnings."""
        text = "Before proceeding, ensure lock out tag out procedures are followed. The equipment should be de-energized."
        warnings = analyzer._extract_safety_warnings(text)

        assert len(warnings) >= 1
        assert any("lock" in w.lower() for w in warnings)

    def test_extract_safety_warnings_high_voltage(self, analyzer):
        """Test extraction of high voltage warnings."""
        text = "Warning: High voltage present. Risk of electric shock if covers are removed."
        warnings = analyzer._extract_safety_warnings(text)

        assert len(warnings) >= 1
        assert any("high voltage" in w.lower() or "electric" in w.lower() for w in warnings)

    def test_extract_safety_warnings_ppe(self, analyzer):
        """Test extraction of PPE warnings."""
        text = "PPE required: safety glasses and gloves. Personal protective equipment is mandatory."
        warnings = analyzer._extract_safety_warnings(text)

        assert len(warnings) >= 1

    def test_extract_safety_warnings_none(self, analyzer):
        """Test no warnings extracted from safe text."""
        text = "The equipment is operating normally. No issues detected."
        warnings = analyzer._extract_safety_warnings(text)

        assert len(warnings) == 0

    def test_extract_safety_warnings_deduplication(self, analyzer):
        """Test warning deduplication."""
        text = "Warning: High voltage. Warning: High voltage present. Warning: High voltage hazard."
        warnings = analyzer._extract_safety_warnings(text)

        # Should deduplicate similar warnings
        assert len(warnings) <= 3

    def test_extract_safety_warnings_limit(self, analyzer):
        """Test warning limit (max 5)."""
        text = """
        Warning: Hazard 1. Warning: Hazard 2. Warning: Hazard 3.
        Warning: Hazard 4. Warning: Hazard 5. Warning: Hazard 6.
        Warning: Hazard 7. Warning: Hazard 8.
        """
        warnings = analyzer._extract_safety_warnings(text)

        assert len(warnings) <= 5

    # -------------------------------------------------------------------------
    # Response Parsing Tests
    # -------------------------------------------------------------------------

    def test_parse_structured_response_with_sections(self, analyzer):
        """Test parsing response with clear sections."""
        response = """This is the main analysis of the equipment.
The VFD appears to have overheating issues.

Solutions:
- Check cooling fan operation
- Verify ambient temperature
- Clean air filters

Recommendations:
1. Schedule preventive maintenance
2. Order replacement fan
"""
        parsed = analyzer._parse_structured_response(response)

        assert "analysis" in parsed
        assert "solutions" in parsed
        assert len(parsed["solutions"]) >= 2
        assert "recommendations" in parsed

    def test_parse_structured_response_no_sections(self, analyzer):
        """Test parsing response without sections (uses whole as analysis)."""
        response = "This is just a plain text response without any sections."
        parsed = analyzer._parse_structured_response(response)

        assert parsed["analysis"] == response

    # -------------------------------------------------------------------------
    # KB Citation Tests
    # -------------------------------------------------------------------------

    def test_format_kb_citations(self, analyzer, sample_kb_atoms):
        """Test KB citation formatting."""
        citations = analyzer._format_kb_citations(sample_kb_atoms)

        assert len(citations) == 2
        assert citations[0]["title"] == "PowerFlex 525 Fault Codes"
        assert citations[0]["type"] == "procedure"
        assert "url" in citations[0]

    def test_format_kb_citations_empty(self, analyzer):
        """Test KB citation formatting with empty list."""
        citations = analyzer._format_kb_citations([])
        assert citations == []

    # -------------------------------------------------------------------------
    # Confidence Calculation Tests
    # -------------------------------------------------------------------------

    def test_calculate_confidence_all_context(self, analyzer, sample_specs, sample_history, sample_kb_atoms):
        """Test confidence calculation with all context available."""
        confidence = analyzer._calculate_confidence(sample_specs, sample_history, sample_kb_atoms)

        # Should be relatively high with good context
        assert confidence >= 0.70
        assert confidence <= 0.95

    def test_calculate_confidence_no_context(self, analyzer):
        """Test confidence calculation with no context."""
        confidence = analyzer._calculate_confidence({}, [], [])

        # Should be base confidence (0.5)
        assert confidence == 0.50

    def test_calculate_confidence_specs_only(self, analyzer, sample_specs):
        """Test confidence with specs only."""
        confidence = analyzer._calculate_confidence(sample_specs, [], [])

        # Should be slightly above base
        assert confidence > 0.50
        assert confidence < 0.70

    def test_calculate_confidence_capped(self, analyzer):
        """Test confidence is capped at 0.95."""
        # Create extensive context
        specs = {f"key{i}": f"value{i}" for i in range(10)}
        history = [{"work_order_number": f"WO-{i}"} for i in range(10)]
        kb = [{"confidence": 1.0} for _ in range(10)]

        confidence = analyzer._calculate_confidence(specs, history, kb)

        assert confidence <= 0.95

    # -------------------------------------------------------------------------
    # Fallback Result Tests
    # -------------------------------------------------------------------------

    def test_create_fallback_result(self, analyzer, sample_specs, sample_history, sample_kb_atoms):
        """Test fallback result creation when Claude fails."""
        result = analyzer._create_fallback_result(
            sample_specs, sample_history, sample_kb_atoms, "API timeout"
        )

        assert "unavailable" in result.analysis.lower() or "failed" in result.analysis.lower()
        assert result.confidence == 0.3
        assert result.cost_usd == 0.0
        assert result.model == "fallback"
        assert len(result.kb_citations) > 0

    def test_create_fallback_result_includes_specs(self, analyzer, sample_specs):
        """Test fallback result includes specs data."""
        result = analyzer._create_fallback_result(sample_specs, [], [], "Error")

        assert "Allen-Bradley" in result.analysis
        assert "PowerFlex 525" in result.analysis

    def test_create_fallback_result_includes_history(self, analyzer, sample_history):
        """Test fallback result includes history data."""
        result = analyzer._create_fallback_result({}, sample_history, [], "Error")

        assert "WO-2024-001" in result.analysis


# =============================================================================
# Mocked Claude API Tests
# =============================================================================

class TestClaudeAnalysisMocked:
    """Tests for analyze_with_kb with mocked Claude API."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ClaudeAnalyzer()

    @pytest.fixture
    def equipment_id(self):
        """Create test equipment UUID."""
        return uuid4()

    @pytest.fixture
    def mock_claude_response(self):
        """Create mock Claude API response."""
        def _create_response(content="Analysis text", input_tokens=500, output_tokens=300):
            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = content
            mock_response.usage = MagicMock()
            mock_response.usage.input_tokens = input_tokens
            mock_response.usage.output_tokens = output_tokens
            return mock_response
        return _create_response

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.claude_analyzer.settings")
    async def test_missing_api_key(self, mock_settings, analyzer, equipment_id):
        """Test error when Anthropic API key is missing."""
        mock_settings.anthropic_api_key = None

        result = await analyzer.analyze_with_kb(
            equipment_id=equipment_id,
            specs={"manufacturer": "Test"},
            history=[],
            kb_context=[]
        )

        # Should return fallback result
        assert result.model == "fallback"
        assert result.confidence == 0.3

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.claude_analyzer.settings")
    @patch("rivet_pro.core.services.claude_analyzer.Anthropic")
    async def test_successful_analysis(self, mock_anthropic_class, mock_settings,
                                       analyzer, equipment_id, mock_claude_response):
        """Test successful analysis with mocked API."""
        mock_settings.anthropic_api_key = "test-anthropic-key"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_claude_response(
            content="""Analysis of the VFD shows overheating patterns.

Solutions:
- Check cooling fan
- Clean filters
- Verify ambient temperature

Recommendations:
- Schedule PM within 2 weeks
- Order replacement fan

Warning: Lock out tag out required before servicing.""",
            input_tokens=800,
            output_tokens=400
        )
        mock_anthropic_class.return_value = mock_client

        result = await analyzer.analyze_with_kb(
            equipment_id=equipment_id,
            specs={"manufacturer": "Allen-Bradley", "model": "PF525"},
            history=[{"work_order_number": "WO-001", "title": "Overheating"}],
            kb_context=[{"title": "VFD Guide", "content": "Info", "type": "procedure", "confidence": 0.9}]
        )

        assert result.analysis is not None
        assert len(result.analysis) > 0
        assert result.cost_usd > 0
        assert result.model == "claude-sonnet-4-20250514"
        assert len(result.safety_warnings) > 0  # Should extract lockout warning

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.claude_analyzer.settings")
    @patch("rivet_pro.core.services.claude_analyzer.Anthropic")
    async def test_api_error_fallback(self, mock_anthropic_class, mock_settings,
                                      analyzer, equipment_id):
        """Test fallback when API call fails."""
        mock_settings.anthropic_api_key = "test-key"

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API rate limit exceeded")
        mock_anthropic_class.return_value = mock_client

        result = await analyzer.analyze_with_kb(
            equipment_id=equipment_id,
            specs={"manufacturer": "Siemens"},
            history=[],
            kb_context=[]
        )

        # Should return fallback result
        assert result.model == "fallback"
        assert result.confidence == 0.3
        assert result.cost_usd == 0.0

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.claude_analyzer.settings")
    @patch("rivet_pro.core.services.claude_analyzer.Anthropic")
    async def test_cost_calculation(self, mock_anthropic_class, mock_settings,
                                    analyzer, equipment_id, mock_claude_response):
        """Test cost calculation based on token usage."""
        mock_settings.anthropic_api_key = "test-key"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_claude_response(
            content="Analysis",
            input_tokens=1000,  # $0.003 per 1K = $0.003
            output_tokens=500   # $0.015 per 1K = $0.0075
            # Total = $0.0105
        )
        mock_anthropic_class.return_value = mock_client

        result = await analyzer.analyze_with_kb(
            equipment_id=equipment_id,
            specs={},
            history=[],
            kb_context=[]
        )

        # Expected cost: (1000/1000)*0.003 + (500/1000)*0.015 = 0.003 + 0.0075 = 0.0105
        assert abs(result.cost_usd - 0.0105) < 0.001


# =============================================================================
# Singleton Tests
# =============================================================================

class TestClaudeAnalyzerSingleton:
    """Tests for ClaudeAnalyzer singleton pattern."""

    def test_get_analyzer_returns_instance(self):
        """Test get_claude_analyzer returns instance."""
        analyzer = get_claude_analyzer()
        assert analyzer is not None
        assert isinstance(analyzer, ClaudeAnalyzer)

    def test_get_analyzer_same_instance(self):
        """Test get_claude_analyzer returns same instance."""
        analyzer1 = get_claude_analyzer()
        analyzer2 = get_claude_analyzer()
        assert analyzer1 is analyzer2


# =============================================================================
# Retry Logic Tests (Simulated Transient Failures)
# =============================================================================

class TestRetryLogic:
    """Tests for retry behavior with transient failures."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.claude_analyzer.settings")
    @patch("rivet_pro.core.services.claude_analyzer.Anthropic")
    async def test_single_failure_returns_fallback(self, mock_anthropic_class, mock_settings):
        """Test that single API failure returns fallback result."""
        mock_settings.anthropic_api_key = "test-key"

        mock_client = MagicMock()
        # Simulate transient failure
        mock_client.messages.create.side_effect = ConnectionError("Network error")
        mock_anthropic_class.return_value = mock_client

        analyzer = ClaudeAnalyzer()
        equipment_id = uuid4()

        result = await analyzer.analyze_with_kb(
            equipment_id=equipment_id,
            specs={"manufacturer": "Test"},
            history=[],
            kb_context=[]
        )

        # Should gracefully fallback
        assert result.model == "fallback"
        assert "unavailable" in result.analysis.lower() or "failed" in result.analysis.lower()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.claude_analyzer.settings")
    @patch("rivet_pro.core.services.claude_analyzer.Anthropic")
    async def test_timeout_returns_fallback(self, mock_anthropic_class, mock_settings):
        """Test that timeout returns fallback result."""
        mock_settings.anthropic_api_key = "test-key"

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = TimeoutError("Request timed out")
        mock_anthropic_class.return_value = mock_client

        analyzer = ClaudeAnalyzer()
        equipment_id = uuid4()

        result = await analyzer.analyze_with_kb(
            equipment_id=equipment_id,
            specs={"manufacturer": "Test"},
            history=[],
            kb_context=[]
        )

        assert result.model == "fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
