import requests
import time

urls = [
    'https://www.google.com',
    'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf',
    'not-a-valid-url'
]

print("Triggering 3 test executions with fixed code...")

for url in urls:
    print(f'\nTest: {url}')
    try:
        r = requests.post(
            'https://mikecranesync.app.n8n.cloud/webhook/rivet-url-validator',
            json={'url': url},
            timeout=15
        )
        print(f'Status: {r.status_code}, Content-Length: {r.headers.get("Content-Length", "0")}')
        if r.text:
            print(f'Response: {r.text[:200]}')
    except Exception as e:
        print(f'Error: {e}')
    time.sleep(1.5)

print("\nDone! Check n8n UI for execution logs.")
