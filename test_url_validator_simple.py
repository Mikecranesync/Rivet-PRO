"""
Simple test for LLM URL validation without database dependency.

Tests just the core validation logic.
"""

import asyncio
import httpx
import json
from rivet_pro.config.settings import settings


async def validate_url(url: str, manufacturer: str, model: str) -> dict:
    """
    Validate URL using LLM judge.

    Copied from ManualService._validate_manual_url for standalone testing.
    """

    # Check LLM configuration
    if not settings.anthropic_api_key and not settings.openai_api_key:
        return {
            'is_direct_pdf': False,
            'confidence': 0.0,
            'reasoning': 'No LLM configured'
        }

    # Build prompt
    prompt = f"""You are validating equipment manual URLs. Analyze this URL and determine if it's a DIRECT link to a PDF manual or just a search/catalog page.

Equipment: {manufacturer} {model}
URL: {url}

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "is_direct_pdf": true or false,
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation",
  "likely_pdf_extension": true or false
}}

Direct PDF indicators:
- Ends with .pdf
- Contains /documents/ or /manuals/ or /literature/ or /support/
- Has specific model number in path
- URL path suggests a document download

Search page indicators:
- Contains /search?q= or ?query= or /results
- Generic product listing page
- Catalog or category page without specific document
- E-commerce or shopping cart URLs
- Generic homepage or landing page

Be strict: only return is_direct_pdf=true if you're confident it's a real manual."""

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Try Anthropic Claude first
            if settings.anthropic_api_key:
                try:
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": settings.anthropic_api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json={
                            "model": "claude-3-5-sonnet-20241022",
                            "max_tokens": 200,
                            "messages": [
                                {"role": "user", "content": prompt}
                            ]
                        }
                    )

                    if response.status_code == 200:
                        data = response.json()
                        content = data.get('content', [{}])[0].get('text', '{}')
                        result = json.loads(content)
                        print(f"  [Claude validated]")
                        return result
                    else:
                        print(f"  [Claude failed: {response.status_code}]")

                except Exception as e:
                    print(f"  [Claude error: {e}]")

            # Fallback to OpenAI
            if settings.openai_api_key:
                try:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.openai_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "gpt-4o-mini",
                            "max_tokens": 200,
                            "temperature": 0.1,
                            "messages": [
                                {"role": "user", "content": prompt}
                            ]
                        }
                    )

                    if response.status_code == 200:
                        data = response.json()
                        content = data.get('choices', [{}])[0].get('message', {}).get('content', '{}')
                        result = json.loads(content)
                        print(f"  [GPT-4o-mini validated]")
                        return result
                    else:
                        print(f"  [OpenAI failed: {response.status_code}]")

                except Exception as e:
                    print(f"  [OpenAI error: {e}]")

    except Exception as e:
        print(f"  [Validation failed: {e}]")

    # Safety default
    return {
        'is_direct_pdf': False,
        'confidence': 0.0,
        'reasoning': 'LLM validation failed'
    }


async def main():
    """Run URL validation tests."""

    print("\n" + "="*80)
    print("LLM URL VALIDATION TEST (No Database)")
    print("="*80)

    # Check LLM configuration
    if not settings.anthropic_api_key and not settings.openai_api_key:
        print("\nERROR: No LLM API keys configured!")
        print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env")
        return

    print(f"\nLLM Provider:")
    if settings.anthropic_api_key:
        print(f"  - Claude 3.5 Sonnet (Anthropic)")
    if settings.openai_api_key:
        print(f"  - GPT-4o-mini (OpenAI)")

    # Test cases
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
            'name': 'Manual Library Page (Not Direct)',
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

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test {i}/{len(test_cases)}: {test['name']} ---")
        print(f"URL: {test['url']}")
        print(f"Equipment: {test['manufacturer']} {test['model']}")
        print(f"Expected: {'VALID PDF' if test['expected'] else 'REJECT'}")

        # Run validation
        result = await validate_url(
            url=test['url'],
            manufacturer=test['manufacturer'],
            model=test['model']
        )

        is_valid = result.get('is_direct_pdf', False)
        confidence = result.get('confidence', 0.0)
        reasoning = result.get('reasoning', 'No reasoning')

        print(f"\nLLM Result: {'VALID' if is_valid else 'REJECTED'}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Reasoning: {reasoning}")

        # Check if matches expected
        matches = (is_valid == test['expected'])

        if matches:
            print(f"\nTEST PASSED")
            passed += 1
        else:
            print(f"\nTEST FAILED - LLM got it wrong")
            failed += 1

    print("\n" + "="*80)
    print(f"RESULTS: {passed}/{len(test_cases)} tests passed")
    print("="*80)

    if failed > 0:
        print(f"\n{failed} tests failed - may need to tune prompt or threshold")
    else:
        print("\nAll tests passed!")


if __name__ == '__main__':
    asyncio.run(main())
