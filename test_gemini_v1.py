"""
Test Gemini API v1 with correct model name
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

print("="*80)
print("TESTING GEMINI API V1 WITH LATEST MODEL")
print("="*80)

if not GOOGLE_API_KEY:
    print("[ERROR] GOOGLE_API_KEY not found in .env")
    exit(1)

# Build the request
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

# Try different model names
models_to_try = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-pro"
]

for model in models_to_try:
    print(f"\n{'='*80}")
    print(f"TESTING MODEL: {model}")
    print("="*80)

    url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={GOOGLE_API_KEY}"

    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=gemini_request,
            timeout=30
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            # Extract text response
            try:
                candidate = result.get('candidates', [])[0]
                content = candidate.get('content', {}).get('parts', [])[0].get('text', '')

                print(f"\nText Response:")
                print(content[:500])  # First 500 chars

                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    print(f"\n[SUCCESS] Valid JSON response!")
                    print(json.dumps(parsed, indent=2))

                    if 'completeness' in parsed:
                        print(f"\n[SUCCESS] Model {model} works! Use this one.")
                        break

                except json.JSONDecodeError:
                    print("\n[WARNING] Response not valid JSON")

            except (IndexError, KeyError) as e:
                print(f"[ERROR] Failed to extract response: {e}")

        else:
            error = response.json()
            print(f"Error: {error.get('error', {}).get('message', 'Unknown error')}")

    except Exception as e:
        print(f"[ERROR] {e}")

    print()
