"""
Test LLM Judge workflow
"""
import requests
import json

WEBHOOK_URL = "https://mikecranesync.app.n8n.cloud/webhook/rivet-llm-judge"

print("="*80)
print("TESTING LLM JUDGE WORKFLOW")
print("="*80)

# Test payload with manual text
test_payload = {
    "manual_text": "User Manual for XYZ Motor\n\nSpecifications:\n- Model: XYZ-123\n- Power: 5HP\n- Voltage: 240V\n\nTroubleshooting:\n1. Check power connection\n2. Verify voltage\n3. Inspect motor windings",
    "equipment_type": "Electric Motor",
    "manufacturer": "XYZ Corp"
}

print(f"\nSending test request to: {WEBHOOK_URL}")
print(f"\nPayload:")
print(json.dumps(test_payload, indent=2))

try:
    response = requests.post(
        WEBHOOK_URL,
        json=test_payload,
        timeout=60
    )

    print(f"\n{'='*80}")
    print("RESPONSE")
    print("="*80)
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"\nResponse Body:")
    print(response.text)

    if response.status_code == 200:
        try:
            result = response.json()
            print(f"\nParsed Response:")
            print(json.dumps(result, indent=2))

            if result.get('quality_score'):
                print(f"\n[SUCCESS] Quality Score: {result['quality_score']}/10")
            elif result.get('error'):
                print(f"\n[ERROR] {result['error']}")
        except:
            print("\n[WARNING] Response is not JSON")

except Exception as e:
    print(f"\n[ERROR] {e}")
