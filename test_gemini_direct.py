"""
Test Gemini API directly to diagnose LLM Judge issue
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

print("="*80)
print("TESTING GEMINI API DIRECTLY")
print("="*80)

if not GOOGLE_API_KEY:
    print("[ERROR] GOOGLE_API_KEY not found in .env")
    exit(1)

# Build the request exactly as the workflow does
system_prompt = """You are an expert industrial equipment manual evaluator. Your task is to score manual quality on 5 criteria (each 0-10):

1. Completeness: Does it cover all necessary topics?
2. Technical accuracy: Is the information correct and precise?
3. Clarity: Is it easy to understand?
4. Troubleshooting usefulness: Does it help solve problems?
5. Metadata quality: Are specs, models, parts clearly identified?

Respond ONLY with valid JSON in this format:
{
  "completeness": <0-10>,
  "technical_accuracy": <0-10>,
  "clarity": <0-10>,
  "troubleshooting_usefulness": <0-10>,
  "metadata_quality": <0-10>,
  "feedback": "<Brief explanation of scores>"
}"""

user_prompt = """Equipment type: Electric Motor
Manufacturer: XYZ Corp

Evaluate this manual:

User Manual for XYZ Motor

Specifications:
- Model: XYZ-123
- Power: 5HP
- Voltage: 240V

Troubleshooting:
1. Check power connection
2. Verify voltage
3. Inspect motor windings"""

gemini_request = {
    "contents": [{
        "parts": [{
            "text": system_prompt + "\n\n" + user_prompt
        }]
    }],
    "generationConfig": {
        "temperature": 0.1,
        "maxOutputTokens": 800
    }
}

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"

print("\nSending request to Gemini API...")

try:
    response = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json=gemini_request,
        timeout=30
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"\nFull Response:")
    print(json.dumps(response.json(), indent=2))

    if response.status_code == 200:
        result = response.json()

        # Try to extract the text response
        try:
            candidate = result.get('candidates', [])[0]
            content = candidate.get('content', {}).get('parts', [])[0].get('text', '')

            print(f"\n{'='*80}")
            print("EXTRACTED TEXT RESPONSE:")
            print("="*80)
            print(content)

            # Try to parse as JSON
            try:
                parsed = json.loads(content)
                print(f"\n{'='*80}")
                print("PARSED JSON:")
                print("="*80)
                print(json.dumps(parsed, indent=2))

                if 'completeness' in parsed:
                    print("\n[SUCCESS] Response is in expected format!")
                else:
                    print("\n[WARNING] Response is JSON but missing expected fields")

            except json.JSONDecodeError as e:
                print(f"\n[ERROR] Failed to parse as JSON: {e}")
                print("Response is not valid JSON")

        except (IndexError, KeyError) as e:
            print(f"\n[ERROR] Failed to extract response: {e}")

except Exception as e:
    print(f"\n[ERROR] {e}")
