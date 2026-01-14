import requests
import json

url = "https://mikecranesync.app.n8n.cloud/webhook/rivet-url-validator"
payload = {"url": "https://www.google.com"}

print("Testing URL Validator...")
print(f"Webhook: {url}")
print(f"Payload: {json.dumps(payload)}")
print("\n" + "="*60)

response = requests.post(url, json=payload)

print(f"Status Code: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print(f"Content-Length: {len(response.content)}")
print(f"Response Text: {response.text}")
print("\n" + "="*60)

if response.text:
    try:
        data = response.json()
        print("\nParsed JSON:")
        print(json.dumps(data, indent=2))

        if data.get('valid'):
            print(f"\n[SUCCESS] URL is valid!")
            print(f"  Score: {data.get('score')}")
            print(f"  Status Code: {data.get('status_code')}")
            print(f"  Content Type: {data.get('content_type')}")
        else:
            print(f"\n[FAILED] URL validation failed")
            print(f"  Error: {data.get('error')}")
    except:
        print("[ERROR] Response is not valid JSON")
else:
    print("\n[ERROR] Empty response body")
