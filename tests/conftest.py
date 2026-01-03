"""
Pytest configuration and fixtures for RIVET Pro tests.
"""

import pytest


@pytest.fixture
def sample_equipment_data():
    """Sample equipment data for testing."""
    return {
        "manufacturer": "Siemens",
        "model_number": "G120C-5.5",
        "serial_number": "SN123456",
        "equipment_type": "vfd",
        "voltage": "480V",
        "current": "15A",
        "horsepower": "5HP",
        "phase": "3",
        "frequency": "60Hz",
    }


@pytest.fixture
def sample_ocr_response():
    """Sample OCR JSON response."""
    return """
    {
        "manufacturer": "Allen-Bradley",
        "model_number": "1756-L71",
        "equipment_type": "plc",
        "voltage": "24VDC",
        "confidence": 0.85,
        "raw_text": "ALLEN-BRADLEY 1756-L71 24VDC"
    }
    """
