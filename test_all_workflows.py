#!/usr/bin/env python3
"""Test all three RIVET workflows"""

import requests
import time

print("="*70)
print("TESTING ALL RIVET WORKFLOWS")
print("="*70)

test_url = "https://www.google.com"

# Test 1: URL Validator
print("\n1. Testing URL Validator...")
print(f"URL: {test_url}")
try:
    r = requests.post(
        'https://mikecranesync.app.n8n.cloud/webhook/rivet-url-validator',
        json={'url': test_url},
        timeout=15
    )
    print(f"Status: {r.status_code}")
    if r.text:
        result = r.json()
        print(f"Valid: {result.get('valid')}, Score: {result.get('score')}/10")
        if result.get('error'):
            print(f"Error: {result.get('error')}")
    else:
        print("Response: EMPTY")
except Exception as e:
    print(f"Error: {e}")

time.sleep(2)

# Test 2: LLM Judge
print("\n2. Testing LLM Judge...")
print(f"URL: {test_url}")
print("Note: This will call OpenAI API and may take 5-10 seconds...")
try:
    r = requests.post(
        'https://mikecranesync.app.n8n.cloud/webhook/rivet-llm-judge',
        json={'url': test_url, 'equipment_type': 'search engine', 'manufacturer': 'Google'},
        timeout=60
    )
    print(f"Status: {r.status_code}")
    if r.text:
        result = r.json()
        print(f"Quality Score: {result.get('quality_score')}/10")
        if result.get('feedback'):
            print(f"Feedback: {result.get('feedback')[:100]}...")
        if result.get('error'):
            print(f"Error: {result.get('error')}")
    else:
        print("Response: EMPTY")
except Exception as e:
    print(f"Error: {e}")

time.sleep(2)

# Test 3: Test Runner (Full E2E)
print("\n3. Testing Test Runner (Full End-to-End)...")
print(f"URL: {test_url}")
print("Note: This runs validator + judge and may take 10-15 seconds...")
try:
    r = requests.post(
        'https://mikecranesync.app.n8n.cloud/webhook/rivet-test-runner',
        json={'url': test_url},
        timeout=90
    )
    print(f"Status: {r.status_code}")
    if r.text:
        result = r.json()
        print(f"Overall: {result.get('overall', 'N/A').upper()}")
        print(f"Validation Score: {result.get('validation', {}).get('score', 'N/A')}/10")
        print(f"Quality Score: {result.get('quality', {}).get('quality_score', 'N/A')}/10")
        print(f"Duration: {result.get('test_duration_ms', 'N/A')}ms")
    else:
        print("Response: EMPTY")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*70)
print("TEST COMPLETE!")
print("="*70)
