"""
Test Manual Hunter Integration with URL Validator
Tests all 5 scenarios from the integration plan
"""
import requests
import time
import json

MANUAL_HUNTER_WEBHOOK = "https://mikecranesync.app.n8n.cloud/webhook/rivet-manual-hunter"

print("="*80)
print("TESTING MANUAL HUNTER INTEGRATION WITH URL VALIDATOR")
print("="*80)

test_cases = [
    {
        "name": "Test 1: Valid PDF URL (Tier 1)",
        "manufacturer": "Caterpillar",
        "model_number": "320D",
        "product_family": "Excavator",
        "ocr_text": "CAT 320D EXCAVATOR HYDRAULIC",
        "expected": "Tier 1 finds valid PDF, score >= 6, cached"
    },
    {
        "name": "Test 2: Valid HTML URL (Tier 1)",
        "manufacturer": "John Deere",
        "model_number": "6120M",
        "product_family": "Tractor",
        "ocr_text": "JOHN DEERE 6120M UTILITY TRACTOR",
        "expected": "Tier 1 finds HTML manual, score >= 6, cached"
    },
    {
        "name": "Test 3: Common Equipment (Tier 1)",
        "manufacturer": "Bobcat",
        "model_number": "S650",
        "product_family": "Skid Steer",
        "ocr_text": "BOBCAT S650 SKID STEER LOADER",
        "expected": "Tier 1 finds manual, validates, caches"
    },
    {
        "name": "Test 4: Less Common Equipment",
        "manufacturer": "Komatsu",
        "model_number": "PC200",
        "product_family": "Excavator",
        "ocr_text": "KOMATSU PC200 HYDRAULIC EXCAVATOR",
        "expected": "May use Tier 1 or Tier 2, but validates before cache"
    },
    {
        "name": "Test 5: Very Specific Model",
        "manufacturer": "Hitachi",
        "model_number": "ZX350LC",
        "product_family": "Excavator",
        "ocr_text": "HITACHI ZX350LC-6 EXCAVATOR",
        "expected": "Tests URL validation and escalation logic"
    }
]

results = []

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"{test['name']}")
    print(f"{'='*80}")
    print(f"Manufacturer: {test['manufacturer']}")
    print(f"Model: {test['model_number']}")
    print(f"Expected: {test['expected']}")

    payload = {
        "manufacturer": test['manufacturer'],
        "model_number": test['model_number'],
        "product_family": test['product_family'],
        "ocr_text": test['ocr_text']
    }

    print("\n[1/2] Sending request to Manual Hunter...")

    try:
        response = requests.post(
            MANUAL_HUNTER_WEBHOOK,
            json=payload,
            timeout=60  # 60 second timeout (validation adds ~2-3 seconds per tier)
        )

        print(f"       Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("\n[2/2] Response received:")
            print(f"       Found: {'YES' if result.get('found') else 'NO'}")

            if result.get('found'):
                print(f"       PDF URL: {result.get('pdf_url', 'N/A')}")
                print(f"       Confidence: {result.get('confidence', 'N/A')}%")
                print(f"       Tier: {result.get('tier', 'N/A')}")

                # Check if validation data is included
                validation = result.get('validation', {})
                if validation:
                    print(f"       Validation Score: {validation.get('score', 'N/A')}/10")
                    print(f"       Content Type: {validation.get('content_type', 'N/A')}")
                    print(f"       Valid: {validation.get('valid', 'N/A')}")
                else:
                    print("       [WARNING] No validation data in response")

                results.append({
                    "test": test['name'],
                    "status": "PASS",
                    "found": True,
                    "tier": result.get('tier'),
                    "validation_score": validation.get('score') if validation else None
                })
            else:
                # Manual sent to human queue
                print(f"       Sent to: {result.get('destination', 'Unknown')}")
                results.append({
                    "test": test['name'],
                    "status": "PASS" if result.get('destination') == 'human_queue' else "FAIL",
                    "found": False,
                    "destination": result.get('destination')
                })

        else:
            print(f"       [ERROR] HTTP {response.status_code}")
            print(f"       Response: {response.text[:200]}")
            results.append({
                "test": test['name'],
                "status": "FAIL",
                "error": f"HTTP {response.status_code}"
            })

    except Exception as e:
        print(f"       [ERROR] {e}")
        results.append({
            "test": test['name'],
            "status": "ERROR",
            "error": str(e)
        })

    # Wait 5 seconds between tests to avoid rate limiting
    if i < len(test_cases):
        print("\nWaiting 5 seconds before next test...")
        time.sleep(5)

# Print summary
print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] in ['FAIL', 'ERROR'])

print(f"\nTotal Tests: {len(test_cases)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Success Rate: {passed/len(test_cases)*100:.0f}%")

print("\nDetailed Results:")
print("-"*80)

for i, result in enumerate(results, 1):
    status_symbol = "[PASS]" if result['status'] == 'PASS' else "[FAIL]"
    print(f"{status_symbol} Test {i}: {result['test']}")

    if result.get('found'):
        print(f"         Found via: {result.get('tier', 'Unknown')}")
        print(f"         Validation score: {result.get('validation_score', 'N/A')}/10")
    elif result.get('destination'):
        print(f"         Destination: {result.get('destination')}")
    if result.get('error'):
        print(f"         Error: {result.get('error')}")

print("\n" + "="*80)

# Save results to file
with open('manual_hunter_test_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nResults saved to: manual_hunter_test_results.json")
print("="*80)
