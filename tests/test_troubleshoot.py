"""
Tests for troubleshooting orchestrator (4-route system).

Tests Route A (KB Search), Route B (SME Dispatch), Route C (Research Trigger),
and Route D (General Fallback) decision logic.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from rivet.workflows.troubleshoot import troubleshoot
from rivet.models.ocr import OCRResult


@pytest.mark.asyncio
async def test_route_a_high_kb_confidence():
    """Test Route A: KB returns high confidence (>= 0.85) → return immediately."""
    query = "How to reset F0002 fault on Siemens S7-1200?"

    # Mock KB search to return high confidence
    mock_kb_result = {
        "answer": "F0002 indicates communication timeout. Check PROFINET cable...",
        "confidence": 0.90,  # High confidence
        "sources": ["kb_atom_123"],
        "safety_warnings": [],
        "llm_calls": 0,
        "cost_usd": 0.0,
    }

    with patch("rivet.workflows.troubleshoot.search_knowledge_base", return_value=mock_kb_result):
        result = await troubleshoot(query)

    # Verify KB route was used
    assert result.route == "kb"
    assert result.confidence == 0.90
    assert result.kb_attempted is True
    assert result.sme_attempted is False  # SME not called (short-circuit)
    assert result.research_triggered is False
    assert "F0002" in result.answer or "communication" in result.answer.lower()


@pytest.mark.asyncio
async def test_route_b_vendor_sme_success():
    """Test Route B: KB low confidence → SME high confidence (>= 0.70) → return SME answer."""
    query = "Siemens S7-1200 showing F0002 fault, motor won't start"

    # Mock KB search (low confidence)
    mock_kb_result = {
        "answer": "KB placeholder",
        "confidence": 0.40,  # Low confidence
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 0,
        "cost_usd": 0.0,
    }

    # Mock SME router (high confidence)
    mock_sme_result = {
        "answer": "Siemens-specific troubleshooting steps...",
        "confidence": 0.85,  # High confidence
        "vendor": "siemens",
        "sources": [],
        "safety_warnings": ["⚠️ HIGH VOLTAGE"],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    with patch("rivet.workflows.troubleshoot.search_knowledge_base", return_value=mock_kb_result), \
         patch("rivet.workflows.troubleshoot.route_to_sme", return_value=mock_sme_result):
        result = await troubleshoot(query)

    # Verify SME route was used
    assert result.route == "sme"
    assert result.confidence == 0.85
    assert result.kb_attempted is True
    assert result.kb_confidence == 0.40
    assert result.sme_attempted is True
    assert result.sme_vendor == "siemens"
    assert result.research_triggered is False  # SME succeeded, no research needed


@pytest.mark.asyncio
async def test_route_c_research_trigger():
    """Test Route C: KB low, SME low (< 0.70) → trigger research, use general fallback."""
    query = "Rare fault: unknown equipment XYZ showing error 9999"

    # Mock KB search (low confidence)
    mock_kb_result = {
        "answer": "KB placeholder",
        "confidence": 0.30,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 0,
        "cost_usd": 0.0,
    }

    # Mock SME router (low confidence)
    mock_sme_result = {
        "answer": "SME can't help with unknown equipment",
        "confidence": 0.50,  # Below threshold (0.70)
        "vendor": "generic",
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 1,
        "cost_usd": 0.001,
    }

    # Mock general fallback
    mock_general_result = {
        "answer": "General troubleshooting approach...",
        "confidence": 0.70,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 1,
        "cost_usd": 0.005,
    }

    # Mock research trigger (async, returns None)
    mock_trigger_research = AsyncMock(return_value=None)

    with patch("rivet.workflows.troubleshoot.search_knowledge_base", return_value=mock_kb_result), \
         patch("rivet.workflows.troubleshoot.route_to_sme", return_value=mock_sme_result), \
         patch("rivet.workflows.troubleshoot.trigger_research", mock_trigger_research), \
         patch("rivet.workflows.troubleshoot.general_troubleshoot", return_value=mock_general_result):
        result = await troubleshoot(query)

    # Verify research was triggered
    assert result.research_triggered is True
    assert result.route == "general"  # Fell back to general
    assert result.kb_confidence == 0.30
    assert result.sme_confidence == 0.50
    # Verify trigger_research was called
    mock_trigger_research.assert_called_once()


@pytest.mark.asyncio
async def test_ocr_context_passed_to_sme():
    """Test that OCR equipment data is passed to SME router."""
    query = "Motor won't start"
    ocr_data = OCRResult(
        manufacturer="Siemens",
        model_number="S7-1200",
        fault_code="F0002",
        confidence=0.95,
    )

    # Mock KB (low confidence)
    mock_kb_result = {
        "answer": "KB placeholder",
        "confidence": 0.40,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 0,
        "cost_usd": 0.0,
    }

    # Mock SME (check it receives OCR data)
    mock_sme_result = {
        "answer": "Siemens-specific with OCR context",
        "confidence": 0.80,
        "vendor": "siemens",
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    with patch("rivet.workflows.troubleshoot.search_knowledge_base", return_value=mock_kb_result), \
         patch("rivet.workflows.troubleshoot.route_to_sme", return_value=mock_sme_result) as mock_sme_call:
        result = await troubleshoot(query, ocr_result=ocr_data)

    # Verify OCR data was passed to SME router
    mock_sme_call.assert_called_once()
    call_args = mock_sme_call.call_args
    assert call_args.kwargs["ocr_result"] == ocr_data
    assert result.manufacturer == "Siemens"
    assert result.model_number == "S7-1200"
    assert result.fault_code == "F0002"


@pytest.mark.asyncio
async def test_cost_accumulation():
    """Test that LLM costs are accumulated across routes."""
    query = "Test cost tracking"

    # Mock KB (has cost)
    mock_kb_result = {
        "answer": "KB answer",
        "confidence": 0.40,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 2,
        "cost_usd": 0.001,
    }

    # Mock SME (has cost)
    mock_sme_result = {
        "answer": "SME answer",
        "confidence": 0.65,  # Below threshold
        "vendor": "generic",
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    # Mock general (has cost)
    mock_general_result = {
        "answer": "General answer",
        "confidence": 0.70,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 1,
        "cost_usd": 0.005,
    }

    with patch("rivet.workflows.troubleshoot.search_knowledge_base", return_value=mock_kb_result), \
         patch("rivet.workflows.troubleshoot.route_to_sme", return_value=mock_sme_result), \
         patch("rivet.workflows.troubleshoot.trigger_research", AsyncMock()), \
         patch("rivet.workflows.troubleshoot.general_troubleshoot", return_value=mock_general_result):
        result = await troubleshoot(query)

    # Verify costs accumulated
    expected_cost = 0.001 + 0.002 + 0.005  # KB + SME + General
    assert result.cost_usd == pytest.approx(expected_cost, rel=1e-6)
    assert result.llm_calls == 4  # 2 + 1 + 1


@pytest.mark.asyncio
async def test_custom_confidence_thresholds():
    """Test that custom confidence thresholds work correctly."""
    query = "Test with custom thresholds"

    # Mock KB (0.82 confidence)
    mock_kb_result = {
        "answer": "KB answer",
        "confidence": 0.82,  # Below default (0.85), above custom (0.80)
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 0,
        "cost_usd": 0.0,
    }

    with patch("rivet.workflows.troubleshoot.search_knowledge_base", return_value=mock_kb_result):
        # Test with custom KB threshold (0.80)
        result = await troubleshoot(query, min_kb_confidence=0.80)

    # Verify KB route was used (0.82 >= 0.80)
    assert result.route == "kb"
    assert result.confidence == 0.82
    assert result.sme_attempted is False


@pytest.mark.asyncio
async def test_safety_warnings_preserved():
    """Test that safety warnings from routes are preserved in final result."""
    query = "Test safety warnings"

    # Mock SME with safety warnings
    mock_sme_result = {
        "answer": "SME answer with safety info",
        "confidence": 0.85,
        "vendor": "siemens",
        "sources": [],
        "safety_warnings": [
            "⚠️ HIGH VOLTAGE - 480V system",
            "⚠️ LOTO REQUIRED"
        ],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    # Mock KB (low confidence to force SME)
    mock_kb_result = {
        "answer": "KB placeholder",
        "confidence": 0.40,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 0,
        "cost_usd": 0.0,
    }

    with patch("rivet.workflows.troubleshoot.search_knowledge_base", return_value=mock_kb_result), \
         patch("rivet.workflows.troubleshoot.route_to_sme", return_value=mock_sme_result):
        result = await troubleshoot(query)

    # Verify safety warnings preserved
    assert len(result.safety_warnings) == 2
    assert "HIGH VOLTAGE" in result.safety_warnings[0]
    assert "LOTO" in result.safety_warnings[1]


@pytest.mark.asyncio
async def test_processing_time_tracked():
    """Test that processing time is tracked in result."""
    query = "Test timing"

    # Mock KB (immediate return)
    mock_kb_result = {
        "answer": "KB answer",
        "confidence": 0.90,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 0,
        "cost_usd": 0.0,
    }

    with patch("rivet.workflows.troubleshoot.search_knowledge_base", return_value=mock_kb_result):
        result = await troubleshoot(query)

    # Verify processing time is reasonable (< 5 seconds for immediate mock)
    assert result.processing_time_ms > 0
    assert result.processing_time_ms < 5000  # Should be nearly instant with mocks
