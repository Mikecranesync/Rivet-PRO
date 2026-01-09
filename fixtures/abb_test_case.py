"""ABB ACS580 Test Fixture - The Equipment That Started RIVET Pro

This fixture represents the original ABB VFD nameplate that kicked off
the entire RIVET Pro project. It serves as the canonical test case
for the full pipeline: Photo → OCR → Manual Hunter → Delivery
"""

from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class ExpectedResult:
    """What SHOULD happen when this equipment is processed"""
    manual_found: bool
    manual_source: str
    manual_url_pattern: str  # Regex pattern
    search_tier: int  # 1=Tavily, 2=Serper, 3=Perplexity
    confidence_score_min: int
    response_time_max_ms: int
    notes: str = ""


@dataclass  
class OCROutput:
    """What the OCR should extract from the nameplate"""
    manufacturer: str
    model_number: str
    product_family: str
    serial_number: Optional[str] = None
    voltage: Optional[str] = None
    power: Optional[str] = None
    additional_codes: Optional[list] = None


@dataclass
class TelegramPayload:
    """Simulated Telegram message for testing"""
    chat_id: int
    photo_file_id: Optional[str] = None
    photo_base64: Optional[str] = None
    caption: str = ""


# =============================================================================
# THE ORIGINAL TEST CASE - ABB ACS580 VFD
# =============================================================================

ORIGINAL_ABB_TEST = {
    "name": "ABB ACS580 VFD - Original RIVET Test",
    "description": "The exact equipment from Mike's original photo that started RIVET Pro",
    
    "ocr_output": OCROutput(
        manufacturer="ABB",
        model_number="ACS580-01-12A5-4",
        product_family="ACS580",
        serial_number="3AUA0000123456",
        voltage="480V",
        power="5.5kW / 7.5HP"
    ),
    
    "expected": ExpectedResult(
        manual_found=True,
        manual_source="ABB Library",
        manual_url_pattern=r"library\.abb\.com.*ACS580|search\.abb\.com.*ACS580",
        search_tier=1,  # Should find on first tier (Tavily)
        confidence_score_min=85,
        response_time_max_ms=10000,
        notes="This is the golden test case - must always pass"
    ),
    
    "telegram_payload": TelegramPayload(
        chat_id=123456789,  # Replace with actual test chat ID
        caption="What's this equipment?"
    )
}


# =============================================================================
# VARIATIONS FOR THOROUGH TESTING
# =============================================================================

ABB_VARIATIONS = [
    {
        "name": "ABB ACS580 - Partial Model Number",
        "description": "Only family name extracted, not full model",
        "ocr_output": OCROutput(
            manufacturer="ABB",
            model_number="ACS580",
            product_family="ACS580"
        ),
        "expected": ExpectedResult(
            manual_found=True,
            manual_source="ABB Library",
            manual_url_pattern=r"library\.abb\.com.*ACS580",
            search_tier=1,
            confidence_score_min=75,
            response_time_max_ms=12000,
            notes="Should still find family manual"
        )
    },
    {
        "name": "ABB ACS580 - OCR Typo (O vs 0)",
        "description": "Common OCR error: letter O instead of zero",
        "ocr_output": OCROutput(
            manufacturer="ABB",
            model_number="ACS58O-01-12A5-4",  # O instead of 0
            product_family="ACS580"
        ),
        "expected": ExpectedResult(
            manual_found=True,
            manual_source="ABB Library",
            manual_url_pattern=r"library\.abb\.com.*ACS580",
            search_tier=2,  # Might need fuzzy match on Tier 2
            confidence_score_min=70,
            response_time_max_ms=15000,
            notes="Tests fuzzy matching capability"
        )
    },
    {
        "name": "ABB ACS580 - Manufacturer Only",
        "description": "OCR failed to extract model number",
        "ocr_output": OCROutput(
            manufacturer="ABB",
            model_number="",
            product_family=""
        ),
        "expected": ExpectedResult(
            manual_found=False,
            manual_source="",
            manual_url_pattern="",
            search_tier=0,
            confidence_score_min=0,
            response_time_max_ms=5000,
            notes="Should trigger clarification request, not search"
        )
    },
    {
        "name": "ABB ACS580 - Wrong Manufacturer Guess",
        "description": "OCR misread manufacturer as 'A8B'",
        "ocr_output": OCROutput(
            manufacturer="A8B",  # Misread
            model_number="ACS580-01-12A5-4",
            product_family="ACS580"
        ),
        "expected": ExpectedResult(
            manual_found=True,
            manual_source="ABB Library",
            manual_url_pattern=r"library\.abb\.com.*ACS580",
            search_tier=2,
            confidence_score_min=65,
            response_time_max_ms=15000,
            notes="Model number should still match ABB products"
        )
    }
]


# =============================================================================
# OTHER KNOWN EQUIPMENT FOR REGRESSION TESTING
# =============================================================================

KNOWN_EQUIPMENT = [
    {
        "name": "Siemens S7-1200 PLC",
        "ocr_output": OCROutput(
            manufacturer="Siemens",
            model_number="6ES7214-1AG40-0XB0",
            product_family="S7-1200"
        ),
        "expected": ExpectedResult(
            manual_found=True,
            manual_source="Siemens Support",
            manual_url_pattern=r"support\.industry\.siemens\.com.*S7-1200|cache\.industry\.siemens\.com",
            search_tier=1,
            confidence_score_min=80,
            response_time_max_ms=10000
        )
    },
    {
        "name": "Allen-Bradley PowerFlex 525",
        "ocr_output": OCROutput(
            manufacturer="Rockwell Automation",
            model_number="25B-D010N104",
            product_family="PowerFlex 525"
        ),
        "expected": ExpectedResult(
            manual_found=True,
            manual_source="Rockwell Literature",
            manual_url_pattern=r"literature\.rockwellautomation\.com.*PowerFlex|rockwellautomation\.com.*525",
            search_tier=1,
            confidence_score_min=80,
            response_time_max_ms=10000
        )
    }
]


# =============================================================================
# EDGE CASES FOR STRESS TESTING
# =============================================================================

EDGE_CASES = [
    {
        "name": "Unknown Chinese VFD",
        "description": "Lesser-known manufacturer, tests tier escalation",
        "ocr_output": OCROutput(
            manufacturer="INVT",
            model_number="GD100-2R2G-4",
            product_family="GD100"
        ),
        "expected": ExpectedResult(
            manual_found=True,  # Should eventually find it
            manual_source="INVT",
            manual_url_pattern=r"invt\.com|en\.invt\.com",
            search_tier=2,  # Likely needs Tier 2
            confidence_score_min=60,
            response_time_max_ms=20000,
            notes="Tests tier escalation for obscure manufacturers"
        )
    },
    {
        "name": "Obsolete Equipment (GE Fanuc)",
        "description": "Old equipment, may require human queue",
        "ocr_output": OCROutput(
            manufacturer="GE Fanuc",
            model_number="IC693CPU331",
            product_family="Series 90-30"
        ),
        "expected": ExpectedResult(
            manual_found=False,  # May go to human queue
            manual_source="",
            manual_url_pattern="",
            search_tier=3,
            confidence_score_min=0,
            response_time_max_ms=30000,
            notes="Obsolete product, tests human queue path"
        )
    },
    {
        "name": "Completely Illegible Nameplate",
        "description": "OCR couldn't extract anything useful",
        "ocr_output": OCROutput(
            manufacturer="",
            model_number="",
            product_family=""
        ),
        "expected": ExpectedResult(
            manual_found=False,
            manual_source="",
            manual_url_pattern="",
            search_tier=0,
            confidence_score_min=0,
            response_time_max_ms=3000,
            notes="Should immediately ask for better photo"
        )
    }
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_all_test_cases():
    """Return all test cases for comprehensive testing"""
    return {
        "original": ORIGINAL_ABB_TEST,
        "variations": ABB_VARIATIONS,
        "known_equipment": KNOWN_EQUIPMENT,
        "edge_cases": EDGE_CASES
    }


def get_abb_test_payload():
    """Return just the ABB test case as a dict for API calls"""
    test = ORIGINAL_ABB_TEST
    return {
        "manufacturer": test["ocr_output"].manufacturer,
        "model_number": test["ocr_output"].model_number,
        "product_family": test["ocr_output"].product_family,
        "chat_id": test["telegram_payload"].chat_id,
        "source": "automated_test"
    }


def validate_result(result: dict, expected: ExpectedResult) -> dict:
    """Validate a search result against expected values"""
    validations = {
        "manual_found": result.get("found", result.get("manual_found")) == expected.manual_found,
        "search_tier": result.get("search_tier", 0) <= expected.search_tier,
        "confidence": result.get("confidence_score", 0) >= expected.confidence_score_min,
        "response_time": result.get("execution_time_ms", 0) <= expected.response_time_max_ms,
    }
    
    if expected.manual_url_pattern and result.get("pdf_url"):
        validations["url_pattern"] = bool(re.search(
            expected.manual_url_pattern, 
            result.get("pdf_url", ""),
            re.IGNORECASE
        ))
    
    return {
        "passed": all(validations.values()),
        "validations": validations,
        "expected": expected,
        "actual": result
    }


if __name__ == "__main__":
    # Quick test
    print("ABB Test Payload:")
    print(get_abb_test_payload())
