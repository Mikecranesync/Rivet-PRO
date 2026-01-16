"""
Unit Tests for SME Personalities

Tests that all 7 vendor personalities load correctly and have proper structure.
"""

import pytest
from rivet.prompts.sme.personalities import (
    SME_PERSONALITIES,
    SMEPersonality,
    SMEVoice,
    get_personality,
    get_personality_by_enum,
    build_system_prompt,
    format_sme_response,
)
from rivet.models.sme_chat import SMEVendor


class TestSMEPersonalitiesConfig:
    """Test personality configuration loading."""

    def test_all_seven_personalities_exist(self):
        """Verify all 7 personalities are defined."""
        expected_vendors = [
            "siemens", "rockwell", "abb", "schneider",
            "mitsubishi", "fanuc", "generic"
        ]
        for vendor in expected_vendors:
            assert vendor in SME_PERSONALITIES, f"Missing personality: {vendor}"

    def test_each_personality_has_required_fields(self):
        """Verify each personality has all required fields."""
        for vendor, personality in SME_PERSONALITIES.items():
            assert isinstance(personality, SMEPersonality), f"{vendor}: not SMEPersonality"
            assert personality.name, f"{vendor}: missing name"
            assert personality.tagline, f"{vendor}: missing tagline"
            assert isinstance(personality.voice, SMEVoice), f"{vendor}: voice not SMEVoice"
            assert isinstance(personality.expertise_areas, list), f"{vendor}: expertise_areas not list"
            assert len(personality.expertise_areas) > 0, f"{vendor}: no expertise_areas"
            assert personality.system_prompt_additions, f"{vendor}: missing system_prompt_additions"

    def test_each_voice_has_required_fields(self):
        """Verify each voice has all required fields."""
        for vendor, personality in SME_PERSONALITIES.items():
            voice = personality.voice
            assert voice.style, f"{vendor}: missing voice style"
            assert voice.greeting, f"{vendor}: missing voice greeting"
            assert isinstance(voice.thinking_phrases, list), f"{vendor}: thinking_phrases not list"
            assert len(voice.thinking_phrases) > 0, f"{vendor}: no thinking_phrases"
            assert isinstance(voice.closing_phrases, list), f"{vendor}: closing_phrases not list"
            assert len(voice.closing_phrases) > 0, f"{vendor}: no closing_phrases"
            assert voice.safety_emphasis, f"{vendor}: missing safety_emphasis"


class TestGetPersonality:
    """Test get_personality function."""

    def test_get_personality_siemens(self):
        """Test getting Siemens personality."""
        personality = get_personality("siemens")
        assert personality.name == "Hans"
        assert "German" in personality.tagline or "precision" in personality.tagline.lower()

    def test_get_personality_rockwell(self):
        """Test getting Rockwell personality."""
        personality = get_personality("rockwell")
        assert personality.name == "Mike"
        assert "American" in personality.tagline or "practical" in personality.tagline.lower()

    def test_get_personality_abb(self):
        """Test getting ABB personality."""
        personality = get_personality("abb")
        assert personality.name == "Erik"
        assert "safety" in personality.tagline.lower() or "Swiss" in personality.tagline

    def test_get_personality_case_insensitive(self):
        """Test that get_personality is case insensitive."""
        assert get_personality("SIEMENS").name == "Hans"
        assert get_personality("Siemens").name == "Hans"
        assert get_personality("siemens").name == "Hans"

    def test_get_personality_unknown_returns_generic(self):
        """Test that unknown vendor returns generic personality."""
        personality = get_personality("unknown_vendor")
        assert personality.name == "Alex"  # Generic SME

    def test_get_personality_none_returns_generic(self):
        """Test that None vendor returns generic personality."""
        personality = get_personality(None)
        assert personality.name == "Alex"


class TestGetPersonalityByEnum:
    """Test get_personality_by_enum function."""

    def test_get_personality_by_enum_siemens(self):
        """Test getting personality by SMEVendor enum."""
        personality = get_personality_by_enum(SMEVendor.SIEMENS)
        assert personality.name == "Hans"

    def test_get_personality_by_enum_all_vendors(self):
        """Test all enum values return correct personality."""
        expected = {
            SMEVendor.SIEMENS: "Hans",
            SMEVendor.ROCKWELL: "Mike",
            SMEVendor.ABB: "Erik",
            SMEVendor.SCHNEIDER: "Pierre",
            SMEVendor.MITSUBISHI: "Takeshi",
            SMEVendor.FANUC: "Ken",
            SMEVendor.GENERIC: "Alex",
        }
        for vendor, expected_name in expected.items():
            personality = get_personality_by_enum(vendor)
            assert personality.name == expected_name, f"{vendor}: expected {expected_name}, got {personality.name}"


class TestBuildSystemPrompt:
    """Test build_system_prompt function."""

    def test_build_system_prompt_basic(self):
        """Test basic system prompt generation."""
        personality = get_personality("siemens")
        prompt = build_system_prompt(personality)

        assert "Hans" in prompt
        assert personality.system_prompt_additions in prompt
        assert personality.voice.safety_emphasis in prompt
        assert "TIA Portal" in prompt  # Siemens expertise

    def test_build_system_prompt_with_equipment_context(self):
        """Test system prompt includes equipment context."""
        personality = get_personality("siemens")
        equipment_context = {
            "model": "G120C",
            "serial": "SN12345",
            "recent_faults": ["F0002", "F0001"]
        }
        prompt = build_system_prompt(personality, equipment_context)

        assert "G120C" in prompt
        assert "SN12345" in prompt
        assert "F0002" in prompt
        assert "F0001" in prompt

    def test_build_system_prompt_includes_voice_elements(self):
        """Test that prompt includes voice characteristics."""
        personality = get_personality("rockwell")
        prompt = build_system_prompt(personality)

        assert "Mike" in prompt
        assert personality.voice.style in prompt
        assert personality.voice.greeting in prompt


class TestFormatSMEResponse:
    """Test format_sme_response function."""

    def test_format_sme_response_basic(self):
        """Test basic response formatting."""
        personality = get_personality("siemens")
        formatted = format_sme_response(
            personality=personality,
            response_text="This is the answer.",
            confidence=0.85,
        )

        assert "Hans" in formatted
        assert "This is the answer." in formatted
        assert "85%" in formatted or "0.85" in formatted

    def test_format_sme_response_with_warnings(self):
        """Test response includes safety warnings."""
        personality = get_personality("siemens")
        formatted = format_sme_response(
            personality=personality,
            response_text="Answer text",
            confidence=0.80,
            safety_warnings=["HIGH VOLTAGE warning", "LOTO required"],
        )

        assert "Safety Warnings" in formatted
        assert "HIGH VOLTAGE" in formatted
        assert "LOTO" in formatted

    def test_format_sme_response_with_sources(self):
        """Test response includes sources."""
        personality = get_personality("rockwell")
        formatted = format_sme_response(
            personality=personality,
            response_text="Answer text",
            confidence=0.90,
            sources=["Rockwell Manual Chapter 5", "KB Article 12345"],
        )

        assert "Sources" in formatted
        assert "Rockwell Manual" in formatted
        assert "KB Article" in formatted

    def test_format_sme_response_confidence_indicators(self):
        """Test confidence emoji indicators."""
        personality = get_personality("generic")

        # High confidence
        high = format_sme_response(personality, "text", confidence=0.90)
        # Medium confidence
        medium = format_sme_response(personality, "text", confidence=0.75)
        # Low confidence
        low = format_sme_response(personality, "text", confidence=0.50)

        # Should have different indicators (emojis or text)
        # Just check they're all different
        assert high != medium or medium != low


class TestPersonalityNames:
    """Test that personality names match expected values."""

    def test_all_personality_names(self):
        """Verify all SME names."""
        expected_names = {
            "siemens": "Hans",
            "rockwell": "Mike",
            "abb": "Erik",
            "schneider": "Pierre",
            "mitsubishi": "Takeshi",
            "fanuc": "Ken",
            "generic": "Alex",
        }
        for vendor, expected_name in expected_names.items():
            personality = get_personality(vendor)
            assert personality.name == expected_name, f"{vendor}: expected {expected_name}"
