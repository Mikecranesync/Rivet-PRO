"""
List available Gemini models
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    print("[ERROR] GOOGLE_API_KEY not found in .env")
    exit(1)

print("="*80)
print("LISTING AVAILABLE GEMINI MODELS")
print("="*80)

# Try both v1 and v1beta
for api_version in ['v1', 'v1beta']:
    url = f"https://generativelanguage.googleapis.com/{api_version}/models?key={GOOGLE_API_KEY}"

    print(f"\n{'='*80}")
    print(f"API VERSION: {api_version}")
    print("="*80)

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            result = response.json()
            models = result.get('models', [])

            print(f"\nFound {len(models)} models:")

            for model in models:
                name = model.get('name', '')
                display_name = model.get('displayName', '')
                supported_methods = model.get('supportedGenerationMethods', [])

                if 'generateContent' in supported_methods:
                    print(f"\n  Name: {name}")
                    print(f"  Display: {display_name}")
                    print(f"  Methods: {', '.join(supported_methods)}")

        else:
            print(f"Error: {response.status_code}")
            print(response.text[:200])

    except Exception as e:
        print(f"[ERROR] {e}")
