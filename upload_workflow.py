import requests
import json

# Read the workflow
with open('rivet-pro/n8n-workflows/rivet_photo_bot_v2_hybrid.json', 'r') as f:
    workflow = json.load(f)

# Upload to n8n
response = requests.post(
    'http://72.60.175.144:5678/api/v1/workflows',
    headers={
        'X-N8N-API-KEY': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNzBlNDViYy1iNjFjLTQwOGItYTFmYS00OGQyMTA5Y2FjZWMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY3ODU5OTc0LCJleHAiOjE3NzA0NDA0MDB9.UW7Z-lSRZ9at6M1l_MwRj3SMBkf2SkzTCagFyu3Ohv4',
        'Content-Type': 'application/json'
    },
    json=workflow
)

print(f'Status Code: {response.status_code}')
if response.status_code == 200 or response.status_code == 201:
    result = response.json()
    print(f'Success! Workflow created')
    print(f'Workflow ID: {result.get("id")}')
    print(f'Workflow Name: {result.get("name")}')
else:
    print(f'Error: {response.text}')
