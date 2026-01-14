"""
Test LLM-based URL validation for manual service.

Tests the new URL validation feature that rejects search pages
and only accepts direct PDF manual links.
"""

import asyncio
import asyncpg
from rivet_pro.config.settings import settings
from rivet_pro.core.services.manual_service import ManualService
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


async def test_url_validation():
    """Test URL validation with various URL types."""

    # Connect to database
    db = await asyncpg.create_pool(
        settings.database_url,
        min_size=1,
        max_size=2
    )

    try:
        service = ManualService(db)

        # Test URLs (mix of good PDFs and bad search pages)
        test_cases = [
            {
                'name': 'Direct PDF - Siemens',
                'url': 'https://support.industry.siemens.com/cs/us/en/ps/13275/man/G120-Manual-EN.pdf',
                'manufacturer': 'Siemens',
                'model': 'G120',
                'expected': True
            },
            {
                'name': 'Search Page - Generic',
                'url': 'https://www.example.com/search?q=siemens+g120+manual',
                'manufacturer': 'Siemens',
                'model': 'G120',
                'expected': False
            },
            {
                'name': 'Direct PDF - ABB',
                'url': 'https://library.abb.com/d/9AKK107045A7379.pdf',
                'manufacturer': 'ABB',
                'model': 'ACS880',
                'expected': True
            },
            {
                'name': 'Product Page - Not Direct PDF',
                'url': 'https://new.abb.com/drives/acs880',
                'manufacturer': 'ABB',
                'model': 'ACS880',
                'expected': False
            },
            {
                'name': 'Manual Page with Download Link',
                'url': 'https://www.rockwellautomation.com/en-us/support/documentation/manuals.html',
                'manufacturer': 'Rockwell',
                'model': 'PowerFlex 525',
                'expected': False
            },
            {
                'name': 'Direct Literature PDF',
                'url': 'https://literature.rockwellautomation.com/idc/groups/literature/documents/um/520-um002_-en-p.pdf',
                'manufacturer': 'Rockwell',
                'model': 'PowerFlex 525',
                'expected': True
            }
        ]

        print("\n" + "="*80)
        print("LLM URL VALIDATION TEST")
        print("="*80)

        passed = 0
        failed = 0

        for i, test in enumerate(test_cases, 1):
            print(f"\n--- Test {i}/{len(test_cases)}: {test['name']} ---")
            print(f"URL: {test['url']}")
            print(f"Equipment: {test['manufacturer']} {test['model']}")
            print(f"Expected: {'VALID PDF' if test['expected'] else 'REJECT'}")

            # Run validation
            result = await service._validate_manual_url(
                url=test['url'],
                manufacturer=test['manufacturer'],
                model=test['model'],
                timeout=10
            )

            is_valid = result.get('is_direct_pdf', False)
            confidence = result.get('confidence', 0.0)
            reasoning = result.get('reasoning', 'No reasoning')

            print(f"\nResult: {'✅ VALID' if is_valid else '❌ REJECTED'}")
            print(f"Confidence: {confidence:.2f}")
            print(f"Reasoning: {reasoning}")

            # Check if result matches expected
            matches_expected = (is_valid == test['expected'])

            if matches_expected:
                print(f"\nTEST PASSED - LLM correctly identified URL type")
                passed += 1
            else:
                print(f"\nTEST FAILED - LLM misidentified URL type")
                failed += 1

        print("\n" + "="*80)
        print(f"RESULTS: {passed}/{len(test_cases)} tests passed")
        print("="*80)

        if failed > 0:
            print(f"\n{failed} tests failed - review LLM prompt or confidence threshold")
        else:
            print("\nAll tests passed - URL validation working correctly!")

    finally:
        await db.close()


async def test_live_tavily_search():
    """Test live Tavily search with LLM validation."""

    print("\n" + "="*80)
    print("LIVE TAVILY SEARCH + LLM VALIDATION TEST")
    print("="*80)

    # Check if Tavily API key is configured
    if not settings.tavily_api_key:
        print("\nTAVILY_API_KEY not configured - skipping live search test")
        return

    # Connect to database
    db = await asyncpg.create_pool(
        settings.database_url,
        min_size=1,
        max_size=2
    )

    try:
        service = ManualService(db)

        # Test with real equipment
        test_equipment = [
            ('Siemens', 'G120'),
            ('ABB', 'ACS880'),
            ('Rockwell Automation', 'PowerFlex 525')
        ]

        for manufacturer, model in test_equipment:
            print(f"\n--- Searching: {manufacturer} {model} ---")

            result = await service.search_manual(
                manufacturer=manufacturer,
                model=model,
                timeout=20
            )

            if result:
                url = result.get('url')
                title = result.get('title')
                confidence = result.get('confidence', 1.0)
                source = result.get('source', 'unknown')

                print(f"Manual Found!")
                print(f"  Title: {title}")
                print(f"  URL: {url}")
                print(f"  Source: {source}")
                print(f"  Confidence: {confidence:.2f}")

                if confidence >= 0.7:
                    print(f"  High confidence - URL should be valid PDF")
                else:
                    print(f"  Lower confidence - URL quality uncertain")
            else:
                print(f"No manual found (or all URLs rejected by LLM)")

        print("\n" + "="*80)
        print("Live search test complete")
        print("="*80)

    finally:
        await db.close()


async def main():
    """Run all tests."""

    print("\nStarting URL Validation Tests...")

    # Check LLM configuration
    if not settings.anthropic_api_key and not settings.openai_api_key:
        print("\nERROR: No LLM API keys configured!")
        print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env")
        return

    print(f"\nLLM configured:")
    if settings.anthropic_api_key:
        print(f"  - Claude (Anthropic): YES")
    if settings.openai_api_key:
        print(f"  - GPT-4o-mini (OpenAI): YES")

    # Test 1: URL validation with test URLs
    await test_url_validation()

    # Test 2: Live Tavily search
    await test_live_tavily_search()

    print("\nAll tests complete!")


if __name__ == '__main__':
    asyncio.run(main())
