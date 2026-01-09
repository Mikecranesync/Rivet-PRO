"""RIVET Pro Test Fixtures

Canonical test data for the RIVET Pro pipeline.
The ABB ACS580 test case is the golden standard - it must always pass.
"""

from .abb_test_case import (
    ORIGINAL_ABB_TEST,
    ABB_VARIATIONS,
    KNOWN_EQUIPMENT,
    EDGE_CASES,
    get_all_test_cases,
    get_abb_test_payload,
    validate_result,
    OCROutput,
    ExpectedResult,
    TelegramPayload
)

__all__ = [
    "ORIGINAL_ABB_TEST",
    "ABB_VARIATIONS", 
    "KNOWN_EQUIPMENT",
    "EDGE_CASES",
    "get_all_test_cases",
    "get_abb_test_payload",
    "validate_result",
    "OCROutput",
    "ExpectedResult",
    "TelegramPayload"
]
