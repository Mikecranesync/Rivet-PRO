import requests
import json
from datetime import datetime

PROD_WEBHOOK = "https://mikecranesync.app.n8n.cloud/webhook/rivet-url-validator-prod"

test_urls = [
    "https://example.com",
    "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    "",
    "not-a-url"
]

print("="*80)
print("TESTING PRODUCTION ENDPOINT")
print("="*80)
print(f"Endpoint: {PROD_WEBHOOK}")
print(f"Time: {datetime.now().isoformat()}")
print("="*80)
print()

results = []

for url in test_urls:
    print(f"Testing: {url if url else '(empty)'}")

    try:
        response = requests.post(
            PROD_WEBHOOK,
            json={"url": url},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            result = {
                "url": url,
                "valid": data.get('valid'),
                "score": data.get('score'),
                "error": data.get('error'),
                "content_type": data.get('content_type')
            }

            print(f"  Valid: {data.get('valid')}")
            print(f"  Score: {data.get('score')}")
            if data.get('error'):
                print(f"  Error: {data.get('error')}")
            else:
                print(f"  Content-Type: {data.get('content_type')}")

            results.append(result)
        else:
            print(f"  ERROR: HTTP {response.status_code}")

    except Exception as e:
        print(f"  EXCEPTION: {str(e)}")

    print()

# Summary
print("="*80)
print("PRODUCTION TEST SUMMARY")
print("="*80)
passed = sum(1 for r in results if r['valid'] or r['error'] is not None)
print(f"Total: {len(results)} | Passed: {passed}")
print()

# Save results
with open('production_test_results.json', 'w') as f:
    json.dump({
        "endpoint": PROD_WEBHOOK,
        "timestamp": datetime.now().isoformat(),
        "results": results
    }, f, indent=2)

print("Results saved to: production_test_results.json")
