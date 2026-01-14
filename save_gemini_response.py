"""
Save complete Gemini response to file
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

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

url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GOOGLE_API_KEY}"

response = requests.post(url, headers={"Content-Type": "application/json"}, json=gemini_request, timeout=30)

# Save full response
with open('gemini_full_response.json', 'w') as f:
    json.dump(response.json(), f, indent=2)

print("Saved full response to: gemini_full_response.json")

# Extract and save text
result = response.json()
candidate = result.get('candidates', [])[0]
text = candidate.get('content', {}).get('parts', [])[0].get('text', '')

with open('gemini_text_response.txt', 'w') as f:
    f.write(text)

print("Saved text response to: gemini_text_response.txt")
print(f"\nText length: {len(text)} characters")
print(f"\nFirst 500 chars:")
print(text[:500])
