"""End-to-End Tests: ABB ACS580 Full Pipeline

Tests the complete flow:
  Photo → OCR → Manual Hunter → Delivery

The ABB ACS580 is the golden test case - it must always pass.
"""

import os
import sys
import pytest
import httpx
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fixtures.abb_test_case import (
    ORIGINAL_ABB_TEST,
    ABB_VARIATIONS,
    KNOWN_EQUIPMENT,
    EDGE_CASES,
    get_abb_test_payload,
    validate_result
)


# =============================================================================
# CONFIGURATION
# =============================================================================

N8N_CLOUD_URL = os.environ.get("N8N_CLOUD_URL", "https://your-instance.app.n8n.cloud")
MANUAL_HUNTER_WEBHOOK = f"{N8N_CLOUD_URL}/webhook/rivet-manual-hunter"
PHOTO_BOT_WEBHOOK = f"{N8N_CLOUD_URL}/webhook/rivet-photo-bot-v2"


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def http_client():
    """HTTP client for API calls"""
    return httpx.Client(timeout=30.0)


@pytest.fixture
def n8n_configured():
    """Skip tests if n8n URL not configured"""
    if "your-instance" in N8N_CLOUD_URL:
        pytest.skip("N8N_CLOUD_URL not configured")
    return True


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def call_manual_hunter(client: httpx.Client, payload: dict) -> Optional[dict]:
    """Call Manual Hunter webhook and return response"""
    try:
        response = client.post(
            MANUAL_HUNTER_WEBHOOK,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        pytest.fail(f"HTTP error calling Manual Hunter: {e}")
        return None


# =============================================================================
# TESTS: ABB ACS580 (Golden Test Case)
# =============================================================================

class TestABBPipeline:
    """Tests for the ABB ACS580 - the equipment that started RIVET Pro"""
    
    def test_abb_original_finds_manual(self, http_client, n8n_configured):
        """The original ABB test case MUST find the manual"""
        payload = get_abb_test_payload()
        result = call_manual_hunter(http_client, payload)
        
        assert result is not None, "No response from Manual Hunter"
        
        # Validate against expected results
        validation = validate_result(result, ORIGINAL_ABB_TEST["expected"])
        
        assert validation["validations"]["manual_found"], \
            f"ABB ACS580 manual not found! This is the golden test case."
        
    def test_abb_response_time_acceptable(self, http_client, n8n_configured):
        """Response should be under 15 seconds"""
        import time
        
        payload = get_abb_test_payload()
        start = time.time()
        result = call_manual_hunter(http_client, payload)
        duration_ms = (time.time() - start) * 1000
        
        assert duration_ms < 15000, \
            f"Response too slow: {duration_ms}ms (expected < 15000ms)"
            
    def test_abb_search_tier_efficient(self, http_client, n8n_configured):
        """Should find ABB manual on Tier 1 or 2 (not 3)"""
        payload = get_abb_test_payload()
        result = call_manual_hunter(http_client, payload)
        
        tier = result.get("search_tier", 99)
        assert tier <= 2, \
            f"Search tier too high: {tier} (expected 1 or 2)"


# =============================================================================
# TESTS: ABB VARIATIONS
# =============================================================================

class TestABBVariations:
    """Test ABB equipment with OCR variations"""
    
    @pytest.mark.parametrize("variation", ABB_VARIATIONS, 
                             ids=[v["name"] for v in ABB_VARIATIONS])
    def test_abb_variation(self, http_client, n8n_configured, variation):
        """Test each ABB variation handles correctly"""
        ocr = variation["ocr_output"]
        expected = variation["expected"]
        
        payload = {
            "manufacturer": ocr.manufacturer,
            "model_number": ocr.model_number,
            "product_family": ocr.product_family,
            "chat_id": 123456789,
            "source": "automated_test"
        }
        
        result = call_manual_hunter(http_client, payload)
        validation = validate_result(result, expected)
        
        # For variations that should find manual
        if expected.manual_found:
            assert validation["validations"]["manual_found"], \
                f"Variation '{variation['name']}' should have found manual"
        else:
            # For variations that shouldn't find (e.g., empty manufacturer)
            found = result.get("found", result.get("manual_found", False))
            assert not found, \
                f"Variation '{variation['name']}' should NOT have found manual"


# =============================================================================
# TESTS: KNOWN EQUIPMENT (Regression Suite)
# =============================================================================

class TestKnownEquipment:
    """Regression tests for known equipment that should always work"""
    
    @pytest.mark.parametrize("equipment", KNOWN_EQUIPMENT,
                             ids=[e["name"] for e in KNOWN_EQUIPMENT])
    def test_known_equipment_finds_manual(self, http_client, n8n_configured, equipment):
        """Each known equipment should find its manual"""
        ocr = equipment["ocr_output"]
        expected = equipment["expected"]
        
        payload = {
            "manufacturer": ocr.manufacturer,
            "model_number": ocr.model_number,
            "product_family": ocr.product_family,
            "chat_id": 123456789,
            "source": "automated_test"
        }
        
        result = call_manual_hunter(http_client, payload)
        validation = validate_result(result, expected)
        
        assert validation["validations"]["manual_found"], \
            f"Equipment '{equipment['name']}' should have found manual"


# =============================================================================
# TESTS: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test handling of edge cases and error conditions"""
    
    @pytest.mark.parametrize("edge_case", EDGE_CASES,
                             ids=[e["name"] for e in EDGE_CASES])
    def test_edge_case_handled(self, http_client, n8n_configured, edge_case):
        """Edge cases should be handled gracefully"""
        ocr = edge_case["ocr_output"]
        expected = edge_case["expected"]
        
        payload = {
            "manufacturer": ocr.manufacturer,
            "model_number": ocr.model_number,
            "product_family": ocr.product_family,
            "chat_id": 123456789,
            "source": "automated_test"
        }
        
        # Should not raise an exception
        result = call_manual_hunter(http_client, payload)
        
        # Should return some response (even if manual not found)
        assert result is not None, "Edge case should return a response"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    # Run just the golden test case
    pytest.main([
        __file__,
        "-v",
        "-k", "test_abb_original_finds_manual",
        "--tb=short"
    ])
