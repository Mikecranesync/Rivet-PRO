"""
Test single equipment manual search with unique ID to bypass cache
"""
import requests
import json
import time

WEBHOOK_URL = "https://mikecranesync.app.n8n.cloud/webhook/rivet-manual-hunter"

# Use timestamp to ensure unique model number (won't be in cache)
timestamp = str(int(time.time()))
test_model = f"TEST-{timestamp[-6:]}"

print("="*80)
print("TESTING MANUAL HUNTER WITH UNIQUE MODEL")
print("="*80)

payload = {
    "manufacturer": "Caterpillar",
    "model_number": test_model,  # Unique model to bypass cache
    "product_family": "Excavator",
    "ocr_text": "CAT EXCAVATOR HYDRAULIC 320D"
}

print(f"\nTest Equipment:")
print(f"  Manufacturer: {payload['manufacturer']}")
print(f"  Model: {payload['model_number']}")
print(f"  (Using unique model to bypass cache)")

print(f"\nSending request to: {WEBHOOK_URL}")

try:
    start_time = time.time()
    response = requests.post(
        WEBHOOK_URL,
        json=payload,
        timeout=60
    )
    elapsed = time.time() - start_time

    print(f"\nResponse received in {elapsed:.2f} seconds")
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"\nResponse Body:")
    print(response.text)

    if response.status_code == 200 and response.text:
        try:
            result = response.json()
            print(f"\nParsed JSON:")
            print(json.dumps(result, indent=2))
        except:
            print("[INFO] Response is not JSON")

except Exception as e:
    print(f"\n[ERROR] {e}")

print("\n" + "="*80)
print("NOTE: If execution time < 5 seconds, workflow likely hit cache or failed early")
print("      Tier 1 search should take 5-10 seconds")
print("      Tier 1 + validation should take 7-12 seconds")
print("="*80)
