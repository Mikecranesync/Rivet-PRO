#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search Transparency Test Suite

Tests both Python ManualService and n8n Manual Hunter workflow side-by-side
with the same equipment data to compare search results and transparency output.

Usage:
    python scripts/test_search_transparency.py
    python scripts/test_search_transparency.py --python-only
    python scripts/test_search_transparency.py --n8n-only
    python scripts/test_search_transparency.py --equipment "Siemens" "6SL3210-1PE21-4UL0"
"""

import asyncio
import argparse
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Windows console encoding for Unicode/emoji output
from rivet_pro.core.utils.encoding import fix_windows_encoding
fix_windows_encoding()

import httpx
from dotenv import load_dotenv

load_dotenv()

# Test equipment database - mix of findable and obscure
TEST_EQUIPMENT = [
    # Should find manuals (popular equipment)
    {
        "manufacturer": "Siemens",
        "model": "6SL3210-1PE21-4UL0",
        "description": "Siemens SINAMICS Power Module - should find manual",
        "expect_found": True
    },
    {
        "manufacturer": "ABB",
        "model": "ACS580-01-12A5-4",
        "description": "ABB VFD - popular, should find manual",
        "expect_found": True
    },
    {
        "manufacturer": "Allen-Bradley",
        "model": "1756-L72",
        "description": "Rockwell ControlLogix PLC - should find manual",
        "expect_found": True
    },
    {
        "manufacturer": "Schneider Electric",
        "model": "ATV320U22N4B",
        "description": "Schneider Altivar VFD - should find manual",
        "expect_found": True
    },
    # Obscure equipment (test transparency)
    {
        "manufacturer": "Nextys",
        "model": "NPST96148",
        "description": "Nextys DIN rail power supply - obscure, unlikely to find",
        "expect_found": False
    },
    {
        "manufacturer": "IDEC",
        "model": "PS5R-SF24",
        "description": "IDEC power supply - smaller brand",
        "expect_found": False
    },
    {
        "manufacturer": "Mean Well",
        "model": "HDR-150-24",
        "description": "Mean Well DIN rail power supply",
        "expect_found": True  # Mean Well is common
    },
    # Edge cases
    {
        "manufacturer": "Fanuc",
        "model": "A06B-6117-H303",
        "description": "Fanuc servo amplifier - Japanese industrial",
        "expect_found": False
    },
    {
        "manufacturer": "Yaskawa",
        "model": "CIMR-AU4A0018FAA",
        "description": "Yaskawa VFD - should find",
        "expect_found": True
    },
    {
        "manufacturer": "Mitsubishi",
        "model": "FR-D720-0.4K",
        "description": "Mitsubishi VFD - common",
        "expect_found": True
    },
]


class TestResult:
    """Stores test result for comparison"""
    def __init__(self, source: str, manufacturer: str, model: str):
        self.source = source  # 'python' or 'n8n'
        self.manufacturer = manufacturer
        self.model = model
        self.success = False
        self.manual_url: Optional[str] = None
        self.confidence: float = 0.0
        self.duration_ms: int = 0
        self.error: Optional[str] = None
        self.transparency_report: Optional[Dict] = None
        self.helpful_response: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "success": self.success,
            "manual_url": self.manual_url,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "has_transparency": self.transparency_report is not None,
            "has_helpful_response": self.helpful_response is not None
        }


async def test_python_search(manufacturer: str, model: str) -> TestResult:
    """Test Python ManualService directly"""
    result = TestResult("python", manufacturer, model)
    start_time = time.time()

    try:
        # Import here to avoid issues if dependencies missing
        from rivet_pro.infra.database import Database
        from rivet_pro.core.services.manual_service import ManualService

        # Initialize services
        db = Database()
        await db.connect()

        manual_service = ManualService(db)

        # Search with transparency
        manual_result, search_report = await manual_service.search_manual(
            manufacturer=manufacturer,
            model=model,
            timeout=30,
            collect_report=True
        )

        result.duration_ms = int((time.time() - start_time) * 1000)

        if manual_result:
            result.success = True
            result.manual_url = manual_result.get('url')
            result.confidence = manual_result.get('confidence', 0.0)

        if search_report:
            result.transparency_report = search_report.to_dict()

            # Generate helpful response if not found
            if not manual_result:
                try:
                    result.helpful_response = await manual_service.generate_helpful_response(
                        manufacturer=manufacturer,
                        model=model,
                        search_report=search_report
                    )
                except Exception as e:
                    result.helpful_response = f"(Failed to generate: {e})"

        await db.disconnect()

    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - start_time) * 1000)

    return result


async def test_n8n_search(manufacturer: str, model: str, chat_id: int = 12345) -> TestResult:
    """Test n8n Manual Hunter workflow via webhook with wait for response"""
    result = TestResult("n8n", manufacturer, model)
    start_time = time.time()

    # n8n webhook URL - production endpoint
    # Note: This sends results to Telegram, so we capture what we can from the response
    webhook_url = "https://mikecranesync.app.n8n.cloud/webhook/rivet-manual-hunter"

    payload = {
        "chat_id": chat_id,
        "original_message_id": 1,
        "manufacturer": manufacturer,
        "model_number": model,
        "product_family": None,
        "full_ocr_text": f"{manufacturer} {model}"
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(webhook_url, json=payload)
            result.duration_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                data = response.json()

                # The workflow may return different structures based on the path
                # Check for various success indicators
                if isinstance(data, dict):
                    # Direct result
                    result.success = (
                        data.get('found', False) or
                        data.get('pdf_url') is not None or
                        (data.get('confidence', 0) >= 75 and data.get('pdf_url'))
                    )
                    result.manual_url = data.get('pdf_url') or data.get('url')
                    result.confidence = data.get('confidence', 0.0)

                    # Check for transparency data
                    if 'search_transparency' in data:
                        result.transparency_report = data['search_transparency']
                    if 'message' in data:
                        result.helpful_response = data['message']
                    if 'reasoning' in data:
                        result.helpful_response = data.get('reasoning', '')

                elif isinstance(data, list) and len(data) > 0:
                    # Array result - take last item (final node output)
                    last_item = data[-1]
                    if isinstance(last_item, dict):
                        result.success = last_item.get('pdf_url') is not None
                        result.manual_url = last_item.get('pdf_url')
                        result.confidence = last_item.get('confidence', 0.0)

            else:
                result.error = f"HTTP {response.status_code}: {response.text[:200]}"

    except httpx.TimeoutException:
        result.error = "Timeout (120s)"
        result.duration_ms = 120000
    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - start_time) * 1000)

    return result


def format_result(result: TestResult, verbose: bool = True) -> str:
    """Format a test result for display"""
    status = "✅ FOUND" if result.success else "❌ NOT FOUND"
    if result.error:
        status = f"⚠️ ERROR: {result.error[:50]}"

    output = f"""
{'='*60}
[{result.source.upper()}] {result.manufacturer} {result.model}
{'='*60}
Status: {status}
Duration: {result.duration_ms}ms
"""

    if result.success:
        output += f"URL: {result.manual_url}\n"
        output += f"Confidence: {result.confidence:.0%}\n"

    if verbose and result.transparency_report:
        output += "\n📊 TRANSPARENCY REPORT:\n"
        report = result.transparency_report

        # Show stages
        if 'stages' in report:
            for stage in report['stages']:
                emoji = "✅" if stage.get('status') == 'success' else "❌"
                output += f"  {emoji} {stage.get('stage', 'unknown')}: {stage.get('details', 'N/A')}\n"

        # Show rejected URLs
        if 'rejected_urls' in report and report['rejected_urls']:
            output += f"\n  Rejected URLs ({len(report['rejected_urls'])}):\n"
            for rejected in report['rejected_urls'][:3]:
                url = rejected.get('url', '')[:50]
                conf = rejected.get('confidence', 0)
                reason = rejected.get('rejection_reason', '')[:40]
                output += f"    • {url}...\n      {conf:.0%} - {reason}\n"

        # Show timing
        if 'total_duration_ms' in report:
            output += f"\n  Total search time: {report['total_duration_ms']}ms\n"

    if result.helpful_response:
        output += f"\n💡 HELPFUL RESPONSE:\n{result.helpful_response[:300]}\n"

    return output


def compare_results(python_result: TestResult, n8n_result: TestResult) -> str:
    """Compare Python and n8n results side by side"""
    output = f"""
{'#'*70}
COMPARISON: {python_result.manufacturer} {python_result.model}
{'#'*70}

                    PYTHON              N8N
                    ------              ---
Found:              {'Yes' if python_result.success else 'No':<20}{'Yes' if n8n_result.success else 'No'}
Duration:           {python_result.duration_ms}ms{' '*(16-len(str(python_result.duration_ms)))}{n8n_result.duration_ms}ms
Confidence:         {python_result.confidence:.0%}{' '*(18-len(f'{python_result.confidence:.0%}'))}{n8n_result.confidence:.0%}
Has Transparency:   {'Yes' if python_result.transparency_report else 'No':<20}{'Yes' if n8n_result.transparency_report else 'No'}
Has Helpful Resp:   {'Yes' if python_result.helpful_response else 'No':<20}{'Yes' if n8n_result.helpful_response else 'No'}
"""

    if python_result.error or n8n_result.error:
        output += f"\nErrors:\n"
        if python_result.error:
            output += f"  Python: {python_result.error[:60]}\n"
        if n8n_result.error:
            output += f"  n8n: {n8n_result.error[:60]}\n"

    # URL comparison
    if python_result.manual_url or n8n_result.manual_url:
        output += f"\nURLs Found:\n"
        if python_result.manual_url:
            output += f"  Python: {python_result.manual_url[:70]}...\n"
        if n8n_result.manual_url:
            output += f"  n8n:    {n8n_result.manual_url[:70]}...\n"

        # Check if same URL
        if python_result.manual_url and n8n_result.manual_url:
            if python_result.manual_url == n8n_result.manual_url:
                output += "  ✅ MATCH - Same URL found!\n"
            else:
                output += "  ⚠️ DIFFERENT - URLs don't match\n"

    return output


async def run_single_test(manufacturer: str, model: str, python_only: bool, n8n_only: bool, verbose: bool) -> Tuple[Optional[TestResult], Optional[TestResult]]:
    """Run test for single equipment"""
    python_result = None
    n8n_result = None

    if not n8n_only:
        print(f"\n🐍 Testing Python: {manufacturer} {model}...")
        python_result = await test_python_search(manufacturer, model)
        print(format_result(python_result, verbose))

    if not python_only:
        print(f"\n⚙️ Testing n8n: {manufacturer} {model}...")
        n8n_result = await test_n8n_search(manufacturer, model)
        print(format_result(n8n_result, verbose))

    if python_result and n8n_result:
        print(compare_results(python_result, n8n_result))

    return python_result, n8n_result


async def run_all_tests(python_only: bool, n8n_only: bool, verbose: bool, limit: int = None):
    """Run tests on all equipment in database"""
    equipment_list = TEST_EQUIPMENT[:limit] if limit else TEST_EQUIPMENT

    print(f"""
======================================================================
           SEARCH TRANSPARENCY TEST SUITE
======================================================================
  Testing {len(equipment_list)} equipment items
  Python: {'[x] Enabled' if not n8n_only else '[ ] Disabled'}
  n8n:    {'[x] Enabled' if not python_only else '[ ] Disabled'}
======================================================================
""")

    results = []

    for i, equipment in enumerate(equipment_list, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(equipment_list)}: {equipment['description']}")
        print(f"{'='*70}")

        python_result, n8n_result = await run_single_test(
            equipment['manufacturer'],
            equipment['model'],
            python_only,
            n8n_only,
            verbose
        )

        results.append({
            "equipment": equipment,
            "python": python_result.to_dict() if python_result else None,
            "n8n": n8n_result.to_dict() if n8n_result else None,
            "expected_found": equipment.get('expect_found', None)
        })

        # Small delay between tests to avoid rate limiting
        if i < len(equipment_list):
            print("\n⏳ Waiting 2 seconds before next test...")
            await asyncio.sleep(2)

    # Summary
    print(f"""
======================================================================
                         SUMMARY
======================================================================
""")

    python_found = sum(1 for r in results if r['python'] and r['python']['success'])
    python_errors = sum(1 for r in results if r['python'] and r['python']['error'])
    n8n_found = sum(1 for r in results if r['n8n'] and r['n8n']['success'])
    n8n_errors = sum(1 for r in results if r['n8n'] and r['n8n']['error'])

    if not n8n_only:
        print(f"Python: {python_found}/{len(equipment_list)} found, {python_errors} errors")
    if not python_only:
        print(f"n8n:    {n8n_found}/{len(equipment_list)} found, {n8n_errors} errors")

    # Save results to file
    output_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Test Search Transparency - Python vs n8n")
    parser.add_argument('--python-only', action='store_true', help='Only test Python implementation')
    parser.add_argument('--n8n-only', action='store_true', help='Only test n8n workflow')
    parser.add_argument('--equipment', nargs=2, metavar=('MANUFACTURER', 'MODEL'), help='Test specific equipment')
    parser.add_argument('--verbose', '-v', action='store_true', default=True, help='Show detailed output')
    parser.add_argument('--quiet', '-q', action='store_true', help='Show minimal output')
    parser.add_argument('--limit', '-l', type=int, help='Limit number of tests')

    args = parser.parse_args()

    verbose = not args.quiet

    if args.equipment:
        # Test specific equipment
        asyncio.run(run_single_test(
            args.equipment[0],
            args.equipment[1],
            args.python_only,
            args.n8n_only,
            verbose
        ))
    else:
        # Run all tests
        asyncio.run(run_all_tests(
            args.python_only,
            args.n8n_only,
            verbose,
            args.limit
        ))


if __name__ == "__main__":
    main()
