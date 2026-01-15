"""
Unit tests for Claude API fallback troubleshooting module.

Tests cover:
- Telegram markdown escaping
- Step parsing from various formats
- Prompt generation
- API integration (mocked)
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from rivet_pro.troubleshooting.fallback import (
    _escape_telegram_markdown,
    _format_step_for_telegram,
    _parse_numbered_steps,
    _build_troubleshooting_prompt,
    generate_troubleshooting_guide,
    generate_troubleshooting_guide_sync,
    ClaudeFallbackError,
    TroubleshootingGuide,
)


class TestTelegramMarkdownEscaping:
    """Tests for Telegram MarkdownV2 escaping"""

    def test_escape_basic_text(self):
        """Should not modify plain text without special chars"""
        text = "Check motor temperature"
        result = _escape_telegram_markdown(text)
        assert result == text

    def test_escape_parentheses(self):
        """Should escape parentheses"""
        text = "Temperature (85°C)"
        result = _escape_telegram_markdown(text)
        assert result == "Temperature \\(85°C\\)"

    def test_escape_brackets(self):
        """Should escape square brackets"""
        text = "Range [0-100]"
        result = _escape_telegram_markdown(text)
        assert result == "Range \\[0\\-100\\]"

    def test_escape_special_chars(self):
        """Should escape all MarkdownV2 special characters"""
        text = "_*[]()~`>#+-=|{}.!"
        result = _escape_telegram_markdown(text)
        assert result == "\\_\\*\\[\\]\\(\\)\\~\\`\\>\\#\\+\\-\\=\\|\\{\\}\\.\\!"

    def test_escape_mixed_text(self):
        """Should escape special chars while preserving normal text"""
        text = "Check voltage: 24V (nominal) - OK"
        result = _escape_telegram_markdown(text)
        assert "\\(" in result
        assert "\\)" in result
        assert "\\-" in result
        assert "Check voltage" in result


class TestStepFormatting:
    """Tests for Telegram step formatting"""

    def test_format_basic_step(self):
        """Should format step with number and escaped text"""
        result = _format_step_for_telegram(1, "Check power supply")
        assert result == "*1\\.* Check power supply"

    def test_format_removes_existing_numbering(self):
        """Should remove existing step numbers from Claude response"""
        result = _format_step_for_telegram(1, "1. Check power supply")
        assert result == "*1\\.* Check power supply"
        assert "1. " not in result

    def test_format_with_parentheses_numbering(self):
        """Should handle steps numbered with parentheses"""
        result = _format_step_for_telegram(2, "2) Inspect cables")
        assert result == "*2\\.* Inspect cables"

    def test_format_escapes_special_chars(self):
        """Should escape special characters in step text"""
        result = _format_step_for_telegram(3, "Measure voltage (24V)")
        assert result == "*3\\.* Measure voltage \\(24V\\)"


class TestStepParsing:
    """Tests for parsing numbered steps from Claude response"""

    def test_parse_period_numbered_steps(self):
        """Should parse steps numbered with periods"""
        text = """
1. First step
2. Second step
3. Third step
"""
        steps = _parse_numbered_steps(text)
        assert len(steps) == 3
        assert steps[0] == "First step"
        assert steps[1] == "Second step"
        assert steps[2] == "Third step"

    def test_parse_parentheses_numbered_steps(self):
        """Should parse steps numbered with parentheses"""
        text = """
1) First step
2) Second step
"""
        steps = _parse_numbered_steps(text)
        assert len(steps) == 2
        assert steps[0] == "First step"

    def test_parse_colon_numbered_steps(self):
        """Should parse steps numbered with colons"""
        text = """
1: First step
2: Second step
"""
        steps = _parse_numbered_steps(text)
        assert len(steps) == 2

    def test_parse_step_prefix_format(self):
        """Should parse 'Step N:' format"""
        text = """
Step 1: First step
Step 2: Second step
"""
        steps = _parse_numbered_steps(text)
        assert len(steps) == 2
        assert steps[0] == "First step"

    def test_parse_skips_empty_lines(self):
        """Should skip blank lines in response"""
        text = """
1. First step

2. Second step


3. Third step
"""
        steps = _parse_numbered_steps(text)
        assert len(steps) == 3

    def test_parse_multiline_steps(self):
        """Should only capture first line of each step"""
        text = """
1. First step with details
   Additional details here
2. Second step
"""
        steps = _parse_numbered_steps(text)
        # Should only get the numbered lines
        assert len(steps) == 2
        assert "Additional details" not in steps[0]

    def test_parse_no_steps_returns_empty(self):
        """Should return empty list if no numbered steps found"""
        text = "This is just some text without any numbered steps."
        steps = _parse_numbered_steps(text)
        assert steps == []


class TestPromptGeneration:
    """Tests for troubleshooting prompt generation"""

    def test_build_basic_prompt(self):
        """Should build prompt with equipment and problem"""
        prompt = _build_troubleshooting_prompt(
            equipment_type="Test Motor",
            problem="Overheating"
        )
        assert "Test Motor" in prompt
        assert "Overheating" in prompt
        assert "Generate a step-by-step troubleshooting guide" in prompt

    def test_build_prompt_with_context(self):
        """Should include context when provided"""
        prompt = _build_troubleshooting_prompt(
            equipment_type="Test PLC",
            problem="Communication fault",
            context="Network cable disconnected"
        )
        assert "Test PLC" in prompt
        assert "Communication fault" in prompt
        assert "Network cable disconnected" in prompt

    def test_prompt_includes_requirements(self):
        """Should include troubleshooting requirements"""
        prompt = _build_troubleshooting_prompt(
            equipment_type="Motor",
            problem="Issue"
        )
        assert "5-8 actionable" in prompt
        assert "safety" in prompt.lower()
        assert "numbered list" in prompt.lower()


class TestAPIIntegration:
    """Tests for Claude API integration (mocked)"""

    @pytest.mark.asyncio
    async def test_generate_guide_success(self):
        """Should successfully generate guide from Claude API"""
        # Mock Claude API response
        mock_response = Mock()
        mock_response.content = [Mock(text="""
1. Check power connection at terminals
2. Verify voltage levels
3. Inspect for damage
4. Test under load
5. Monitor temperature
""")]
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.usage = None

        with patch('rivet_pro.troubleshooting.fallback.AsyncAnthropic') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.messages.create.return_value = mock_response
            mock_client.return_value = mock_instance

            guide = await generate_troubleshooting_guide(
                equipment_type="Test Motor",
                problem="Not starting"
            )

            assert isinstance(guide, dict)
            assert guide["equipment_type"] == "Test Motor"
            assert guide["problem"] == "Not starting"
            assert len(guide["steps"]) == 5
            assert guide["can_save"] is True
            assert "Test Motor" in guide["formatted_text"]

    @pytest.mark.asyncio
    async def test_generate_guide_empty_equipment_fails(self):
        """Should raise error if equipment_type is empty"""
        with pytest.raises(ClaudeFallbackError, match="equipment_type cannot be empty"):
            await generate_troubleshooting_guide(
                equipment_type="",
                problem="Issue"
            )

    @pytest.mark.asyncio
    async def test_generate_guide_empty_problem_fails(self):
        """Should raise error if problem is empty"""
        with pytest.raises(ClaudeFallbackError, match="problem cannot be empty"):
            await generate_troubleshooting_guide(
                equipment_type="Motor",
                problem=""
            )

    @pytest.mark.asyncio
    async def test_generate_guide_no_api_key_fails(self):
        """Should raise error if ANTHROPIC_API_KEY not set"""
        with patch('rivet_pro.troubleshooting.fallback.settings') as mock_settings:
            mock_settings.anthropic_api_key = None

            with pytest.raises(ClaudeFallbackError, match="ANTHROPIC_API_KEY not found"):
                await generate_troubleshooting_guide(
                    equipment_type="Motor",
                    problem="Issue"
                )

    @pytest.mark.asyncio
    async def test_generate_guide_api_error_fails(self):
        """Should raise error if Claude API call fails"""
        with patch('rivet_pro.troubleshooting.fallback.AsyncAnthropic') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.messages.create.side_effect = Exception("API Error")
            mock_client.return_value = mock_instance

            with pytest.raises(ClaudeFallbackError, match="Failed to generate"):
                await generate_troubleshooting_guide(
                    equipment_type="Motor",
                    problem="Issue"
                )

    @pytest.mark.asyncio
    async def test_generate_guide_empty_response_fails(self):
        """Should raise error if Claude returns empty response"""
        mock_response = Mock()
        mock_response.content = []

        with patch('rivet_pro.troubleshooting.fallback.AsyncAnthropic') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.messages.create.return_value = mock_response
            mock_client.return_value = mock_instance

            with pytest.raises(ClaudeFallbackError, match="empty response"):
                await generate_troubleshooting_guide(
                    equipment_type="Motor",
                    problem="Issue"
                )

    @pytest.mark.asyncio
    async def test_generate_guide_no_steps_parsed_fails(self):
        """Should raise error if no steps can be parsed from response"""
        mock_response = Mock()
        mock_response.content = [Mock(text="This is just random text without numbered steps.")]
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.usage = None

        with patch('rivet_pro.troubleshooting.fallback.AsyncAnthropic') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.messages.create.return_value = mock_response
            mock_client.return_value = mock_instance

            with pytest.raises(ClaudeFallbackError, match="Could not extract troubleshooting steps"):
                await generate_troubleshooting_guide(
                    equipment_type="Motor",
                    problem="Issue"
                )


class TestSynchronousWrapper:
    """Tests for synchronous API wrapper"""

    def test_sync_generate_guide_success(self):
        """Should successfully generate guide using sync client"""
        mock_response = Mock()
        mock_response.content = [Mock(text="""
1. First step
2. Second step
3. Third step
""")]
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.usage = None

        with patch('rivet_pro.troubleshooting.fallback.Anthropic') as mock_client:
            mock_instance = Mock()
            mock_instance.messages.create.return_value = mock_response
            mock_client.return_value = mock_instance

            guide = generate_troubleshooting_guide_sync(
                equipment_type="Test Equipment",
                problem="Test Problem"
            )

            assert len(guide["steps"]) == 3
            assert guide["can_save"] is True

    def test_sync_generate_guide_validates_inputs(self):
        """Should validate inputs in sync version"""
        with pytest.raises(ClaudeFallbackError, match="equipment_type cannot be empty"):
            generate_troubleshooting_guide_sync(
                equipment_type="",
                problem="Issue"
            )


class TestFormattingOutput:
    """Tests for complete Telegram output formatting"""

    def test_formatted_text_includes_header(self):
        """Should include equipment and problem in header"""
        from rivet_pro.troubleshooting.fallback import _format_guide_for_telegram

        formatted = _format_guide_for_telegram(
            equipment_type="Test Motor",
            problem="Overheating",
            steps=["Step 1", "Step 2"],
            context=None
        )

        assert "Test Motor" in formatted
        assert "Overheating" in formatted
        assert "🔧" in formatted

    def test_formatted_text_includes_context(self):
        """Should include context if provided"""
        from rivet_pro.troubleshooting.fallback import _format_guide_for_telegram

        formatted = _format_guide_for_telegram(
            equipment_type="Motor",
            problem="Issue",
            steps=["Step 1"],
            context="Additional info"
        )

        assert "Additional info" in formatted
        assert "Context" in formatted

    def test_formatted_text_includes_save_option(self):
        """Should include save guide footer"""
        from rivet_pro.troubleshooting.fallback import _format_guide_for_telegram

        formatted = _format_guide_for_telegram(
            equipment_type="Motor",
            problem="Issue",
            steps=["Step 1"],
            context=None
        )

        assert "💾" in formatted
        assert "Save Guide" in formatted


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
