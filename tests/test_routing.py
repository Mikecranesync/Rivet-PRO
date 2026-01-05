"""
Tests for vendor detection and SME routing logic.

Tests manufacturer detection from OCR, query text, and fault code patterns.
"""

import pytest
from unittest.mock import AsyncMock, patch

from rivet.workflows.sme_router import (
    detect_manufacturer,
    detect_manufacturer_from_query,
    detect_manufacturer_from_fault_code,
    normalize_manufacturer,
    route_to_sme,
)
from rivet.models.ocr import OCRResult


# ============================================================================
# Manufacturer Detection Tests
# ============================================================================

def test_detect_manufacturer_from_ocr():
    """Test Priority 1: OCR result (highest priority)."""
    # Siemens from OCR
    ocr = OCRResult(manufacturer="Siemens", model_number="S7-1200", confidence=0.95)
    assert detect_manufacturer("generic query", ocr) == "siemens"

    # Rockwell from OCR
    ocr = OCRResult(manufacturer="Allen-Bradley", model_number="1756-L73", confidence=0.95)
    assert detect_manufacturer("generic query", ocr) == "rockwell"

    # ABB from OCR
    ocr = OCRResult(manufacturer="ABB", model_number="ACS880", confidence=0.95)
    assert detect_manufacturer("generic query", ocr) == "abb"


def test_detect_manufacturer_from_query_keywords():
    """Test Priority 2: Query text patterns."""
    # Siemens keywords
    assert detect_manufacturer("Siemens S7-1200 PLC", None) == "siemens"
    assert detect_manufacturer("TIA Portal configuration issue", None) == "siemens"
    assert detect_manufacturer("PROFINET communication error", None) == "siemens"

    # Rockwell keywords
    assert detect_manufacturer("ControlLogix 1756-L73 fault", None) == "rockwell"
    assert detect_manufacturer("Allen-Bradley PLC", None) == "rockwell"
    assert detect_manufacturer("Studio 5000 programming", None) == "rockwell"
    assert detect_manufacturer("CompactLogix 1769", None) == "rockwell"

    # ABB keywords
    assert detect_manufacturer("ABB ACS880 drive alarm", None) == "abb"
    assert detect_manufacturer("IRB robot fault", None) == "abb"
    assert detect_manufacturer("ACH580 HVAC drive", None) == "abb"

    # Schneider keywords
    assert detect_manufacturer("Modicon M340 PLC", None) == "schneider"
    assert detect_manufacturer("Schneider Electric Altivar", None) == "schneider"
    assert detect_manufacturer("Square D breaker", None) == "schneider"

    # Mitsubishi keywords
    assert detect_manufacturer("MELSEC iQ-R PLC", None) == "mitsubishi"
    assert detect_manufacturer("Mitsubishi FX3U", None) == "mitsubishi"
    assert detect_manufacturer("GOT HMI error", None) == "mitsubishi"

    # FANUC keywords
    assert detect_manufacturer("FANUC 0i-F CNC alarm", None) == "fanuc"
    assert detect_manufacturer("R-30iB robot controller", None) == "fanuc"
    assert detect_manufacturer("CNC G-code issue", None) == "fanuc"


def test_detect_manufacturer_from_fault_code():
    """Test Priority 3: Fault code format patterns."""
    # Siemens fault code pattern (F-xxxx)
    assert detect_manufacturer_from_fault_code("F-0002 error on display") == "siemens"
    assert detect_manufacturer_from_fault_code("showing F0042 fault") == "siemens"
    assert detect_manufacturer_from_fault_code("F-1234 alarm") == "siemens"

    # Rockwell fault code pattern (Fault xxx)
    assert detect_manufacturer_from_fault_code("Fault 123 major fault") == "rockwell"
    assert detect_manufacturer_from_fault_code("Error 456 on controller") == "rockwell"

    # Non-matching patterns
    assert detect_manufacturer_from_fault_code("Alarm 9999") is None
    assert detect_manufacturer_from_fault_code("No fault code") is None


def test_normalize_manufacturer():
    """Test manufacturer name normalization."""
    # Siemens variations
    assert normalize_manufacturer("Siemens") == "siemens"
    assert normalize_manufacturer("SIEMENS AG") == "siemens"
    assert normalize_manufacturer("siemens") == "siemens"

    # Rockwell variations
    assert normalize_manufacturer("Allen-Bradley") == "rockwell"
    assert normalize_manufacturer("Allen Bradley") == "rockwell"
    assert normalize_manufacturer("Rockwell Automation") == "rockwell"

    # ABB
    assert normalize_manufacturer("ABB") == "abb"
    assert normalize_manufacturer("abb robotics") == "abb"

    # Schneider variations
    assert normalize_manufacturer("Schneider Electric") == "schneider"
    assert normalize_manufacturer("SCHNEIDER") == "schneider"

    # Mitsubishi
    assert normalize_manufacturer("Mitsubishi Electric") == "mitsubishi"
    assert normalize_manufacturer("MITSUBISHI") == "mitsubishi"

    # FANUC
    assert normalize_manufacturer("FANUC") == "fanuc"
    assert normalize_manufacturer("fanuc america") == "fanuc"

    # Unknown manufacturer
    assert normalize_manufacturer("Unknown Brand XYZ") is None


def test_detect_manufacturer_priority_order():
    """Test that OCR has priority over query patterns."""
    # OCR says Siemens, query says Rockwell → should use OCR (Siemens)
    ocr = OCRResult(manufacturer="Siemens", model_number="S7-1200", confidence=0.95)
    query = "ControlLogix programming issue"  # Rockwell keyword

    result = detect_manufacturer(query, ocr)
    assert result == "siemens"  # OCR takes priority


def test_detect_manufacturer_no_match():
    """Test fallback to None (generic SME) when no manufacturer detected."""
    # No OCR, generic query, no fault code
    assert detect_manufacturer("Motor not starting", None) is None
    assert detect_manufacturer("Unknown equipment error", None) is None


# ============================================================================
# SME Routing Tests
# ============================================================================

@pytest.mark.asyncio
async def test_route_to_sme_siemens():
    """Test routing to Siemens SME."""
    query = "Siemens S7-1200 F0002 fault"

    # Mock Siemens SME
    mock_siemens_result = {
        "answer": "Siemens-specific troubleshooting...",
        "confidence": 0.85,
        "sources": [],
        "safety_warnings": ["⚠️ HIGH VOLTAGE"],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    with patch("rivet.workflows.sme_router.siemens.troubleshoot", return_value=mock_siemens_result):
        result = await route_to_sme(query, vendor="siemens")

    assert result["vendor"] == "siemens"
    assert result["confidence"] == 0.85
    assert "HIGH VOLTAGE" in result["safety_warnings"][0]


@pytest.mark.asyncio
async def test_route_to_sme_rockwell():
    """Test routing to Rockwell SME."""
    query = "ControlLogix major fault"

    mock_rockwell_result = {
        "answer": "Rockwell-specific troubleshooting...",
        "confidence": 0.80,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    with patch("rivet.workflows.sme_router.rockwell.troubleshoot", return_value=mock_rockwell_result):
        result = await route_to_sme(query, vendor="rockwell")

    assert result["vendor"] == "rockwell"
    assert result["confidence"] == 0.80


@pytest.mark.asyncio
async def test_route_to_sme_abb():
    """Test routing to ABB SME."""
    query = "ABB ACS880 drive fault 2710"

    mock_abb_result = {
        "answer": "ABB-specific troubleshooting...",
        "confidence": 0.82,
        "sources": [],
        "safety_warnings": ["⚠️ DC BUS HAZARD"],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    with patch("rivet.workflows.sme_router.abb.troubleshoot", return_value=mock_abb_result):
        result = await route_to_sme(query, vendor="abb")

    assert result["vendor"] == "abb"
    assert "DC BUS" in result["safety_warnings"][0]


@pytest.mark.asyncio
async def test_route_to_sme_schneider():
    """Test routing to Schneider SME."""
    query = "Modicon M340 APP_FAULT"

    mock_schneider_result = {
        "answer": "Schneider-specific troubleshooting...",
        "confidence": 0.78,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    with patch("rivet.workflows.sme_router.schneider.troubleshoot", return_value=mock_schneider_result):
        result = await route_to_sme(query, vendor="schneider")

    assert result["vendor"] == "schneider"
    assert result["confidence"] == 0.78


@pytest.mark.asyncio
async def test_route_to_sme_mitsubishi():
    """Test routing to Mitsubishi SME."""
    query = "MELSEC iQ-R ERR LED blinking"

    mock_mitsubishi_result = {
        "answer": "Mitsubishi-specific troubleshooting...",
        "confidence": 0.80,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    with patch("rivet.workflows.sme_router.mitsubishi.troubleshoot", return_value=mock_mitsubishi_result):
        result = await route_to_sme(query, vendor="mitsubishi")

    assert result["vendor"] == "mitsubishi"


@pytest.mark.asyncio
async def test_route_to_sme_fanuc():
    """Test routing to FANUC SME."""
    query = "FANUC 0i-F alarm SV0401"

    mock_fanuc_result = {
        "answer": "FANUC-specific troubleshooting...",
        "confidence": 0.83,
        "sources": [],
        "safety_warnings": ["⚠️ SERVO AMPLIFIER HIGH VOLTAGE"],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    with patch("rivet.workflows.sme_router.fanuc.troubleshoot", return_value=mock_fanuc_result):
        result = await route_to_sme(query, vendor="fanuc")

    assert result["vendor"] == "fanuc"
    assert "SERVO AMPLIFIER" in result["safety_warnings"][0]


@pytest.mark.asyncio
async def test_route_to_sme_generic():
    """Test routing to generic SME when no vendor detected."""
    query = "Motor not starting, no error codes"

    mock_generic_result = {
        "answer": "Generic troubleshooting...",
        "confidence": 0.72,
        "sources": [],
        "safety_warnings": ["⚠️ ELECTRICAL HAZARD"],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    with patch("rivet.workflows.sme_router.generic.troubleshoot", return_value=mock_generic_result):
        # No vendor specified → should use generic
        result = await route_to_sme(query, vendor=None)

    assert result["vendor"] == "generic"
    assert result["confidence"] == 0.72


@pytest.mark.asyncio
async def test_route_to_sme_auto_detect():
    """Test automatic vendor detection from query."""
    query = "Siemens S7-1200 communication error"

    mock_siemens_result = {
        "answer": "Siemens-specific troubleshooting...",
        "confidence": 0.85,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    with patch("rivet.workflows.sme_router.siemens.troubleshoot", return_value=mock_siemens_result):
        # Don't specify vendor → should auto-detect from query
        result = await route_to_sme(query, vendor=None)

    assert result["vendor"] == "siemens"


@pytest.mark.asyncio
async def test_route_to_sme_with_ocr_context():
    """Test that OCR data is passed to SME."""
    query = "Motor not starting"
    ocr_data = OCRResult(
        manufacturer="Rockwell",
        model_number="1756-L73",
        fault_code="Fault 1",
        confidence=0.95,
    )

    mock_rockwell_result = {
        "answer": "Rockwell-specific with OCR...",
        "confidence": 0.85,
        "sources": [],
        "safety_warnings": [],
        "llm_calls": 1,
        "cost_usd": 0.002,
    }

    with patch("rivet.workflows.sme_router.rockwell.troubleshoot", return_value=mock_rockwell_result) as mock_sme:
        result = await route_to_sme(query, vendor=None, ocr_result=ocr_data)

    # Verify OCR data was passed to SME
    mock_sme.assert_called_once()
    call_args = mock_sme.call_args
    assert call_args[1]["ocr_result"] == ocr_data
    assert result["vendor"] == "rockwell"  # Auto-detected from OCR
