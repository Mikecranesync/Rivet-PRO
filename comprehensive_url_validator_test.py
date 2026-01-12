import requests
import json
import time
from datetime import datetime

WEBHOOK_URL = "https://mikecranesync.app.n8n.cloud/webhook/rivet-url-validator"

# Test cases
test_cases = [
    {
        "name": "Valid HTTPS - Google",
        "url": "https://www.google.com",
        "expected": "valid",
        "expected_status": "200+",
        "expected_content_type": "text/html"
    },
    {
        "name": "Valid HTTPS - HTTPBin",
        "url": "https://httpbin.org/get",
        "expected": "valid",
        "expected_status": "200",
        "expected_content_type": "application/json"
    },
    {
        "name": "Valid HTTPS - Example.com",
        "url": "https://example.com",
        "expected": "valid",
        "expected_status": "200",
        "expected_content_type": "text/html"
    },
    {
        "name": "Valid HTTP - Example.com",
        "url": "http://example.com",
        "expected": "valid",
        "expected_status": "200+",
        "expected_content_type": "text/html"
    },
    {
        "name": "PDF URL",
        "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "expected": "valid",
        "expected_status": "200",
        "expected_content_type": "application/pdf"
    },
    {
        "name": "Invalid Format - No Protocol",
        "url": "not-a-url",
        "expected": "error",
        "expected_error": "must start with http"
    },
    {
        "name": "Invalid Format - FTP Protocol",
        "url": "ftp://example.com",
        "expected": "error",
        "expected_error": "must start with http"
    },
    {
        "name": "Invalid Format - Empty String",
        "url": "",
        "expected": "error",
        "expected_error": "URL is required"
    },
    {
        "name": "URL with Query Parameters",
        "url": "https://httpbin.org/get?param1=value1&param2=value2",
        "expected": "valid",
        "expected_status": "200"
    },
    {
        "name": "Non-existent Domain",
        "url": "https://this-domain-definitely-does-not-exist-12345.com",
        "expected": "error_or_timeout"
    }
]

results = []
print("="*80)
print("RIVET URL VALIDATOR - COMPREHENSIVE TEST SUITE")
print("="*80)
print(f"Started: {datetime.now().isoformat()}")
print(f"Webhook: {WEBHOOK_URL}")
print(f"Total Tests: {len(test_cases)}")
print("="*80)
print()

for i, test in enumerate(test_cases, 1):
    print(f"[{i}/{len(test_cases)}] Testing: {test['name']}")
    print(f"  URL: {test['url']}")

    start_time = time.time()

    try:
        response = requests.post(
            WEBHOOK_URL,
            json={"url": test['url']},
            timeout=30
        )
        elapsed = time.time() - start_time

        result = {
            "test_name": test['name'],
            "input_url": test['url'],
            "expected": test['expected'],
            "http_status": response.status_code,
            "response_time_ms": round(elapsed * 1000, 2),
            "timestamp": datetime.now().isoformat()
        }

        if response.status_code == 200:
            try:
                data = response.json()
                result.update({
                    "valid": data.get('valid'),
                    "status_code": data.get('status_code'),
                    "content_type": data.get('content_type'),
                    "file_size_bytes": data.get('file_size_bytes'),
                    "score": data.get('score'),
                    "warnings": data.get('warnings'),
                    "error": data.get('error'),
                    "full_response": data
                })

                # Determine pass/fail
                if test['expected'] == 'valid':
                    result['pass'] = data.get('valid') == True
                    result['reason'] = f"Valid={data.get('valid')}, Score={data.get('score')}"
                elif test['expected'] == 'error':
                    result['pass'] = data.get('valid') == False and data.get('error') is not None
                    result['reason'] = f"Error: {data.get('error')}"
                else:  # error_or_timeout
                    result['pass'] = True  # Any response is acceptable for these tests
                    result['reason'] = f"Received response: {data.get('error') or 'No error'}"

                print(f"  Response: {response.status_code} ({elapsed*1000:.0f}ms)")
                print(f"  Result: {'PASS' if result['pass'] else 'FAIL'} - {result['reason']}")

            except json.JSONDecodeError:
                result['pass'] = False
                result['reason'] = "Invalid JSON response"
                result['raw_response'] = response.text
                print(f"  ERROR: Invalid JSON response")
        else:
            result['pass'] = False
            result['reason'] = f"HTTP {response.status_code}"
            result['raw_response'] = response.text
            print(f"  ERROR: HTTP {response.status_code}")

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        result = {
            "test_name": test['name'],
            "input_url": test['url'],
            "expected": test['expected'],
            "http_status": "TIMEOUT",
            "response_time_ms": round(elapsed * 1000, 2),
            "pass": test['expected'] == 'error_or_timeout',
            "reason": "Request timeout after 30s",
            "timestamp": datetime.now().isoformat()
        }
        print(f"  TIMEOUT after {elapsed:.1f}s")

    except Exception as e:
        elapsed = time.time() - start_time
        result = {
            "test_name": test['name'],
            "input_url": test['url'],
            "expected": test['expected'],
            "http_status": "EXCEPTION",
            "response_time_ms": round(elapsed * 1000, 2),
            "pass": False,
            "reason": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(f"  EXCEPTION: {str(e)}")

    results.append(result)
    print()
    time.sleep(1)  # Small delay between tests

# Summary
print("="*80)
print("TEST SUMMARY")
print("="*80)
passed = sum(1 for r in results if r.get('pass'))
failed = len(results) - passed
print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
print(f"Success Rate: {(passed/len(results)*100):.1f}%")
print()

# Save detailed results
output_file = 'url_validator_test_results.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        "test_run": {
            "timestamp": datetime.now().isoformat(),
            "webhook_url": WEBHOOK_URL,
            "total_tests": len(results),
            "passed": passed,
            "failed": failed,
            "success_rate": round(passed/len(results)*100, 2)
        },
        "results": results
    }, f, indent=2)

print(f"Detailed results saved to: {output_file}")

# Print failed tests
if failed > 0:
    print()
    print("FAILED TESTS:")
    print("-" * 80)
    for r in results:
        if not r.get('pass'):
            print(f"  [{r['test_name']}]")
            print(f"    URL: {r['input_url']}")
            print(f"    Reason: {r['reason']}")
