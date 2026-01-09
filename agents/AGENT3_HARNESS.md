# AGENT 3: DEBUG HARNESS

**Status:** Fixtures already created! ✅

---

## YOUR MISSION

Build debug utilities and test infrastructure that make testing fast and easy.

---

## ALREADY DONE

✅ ABB test fixtures (`fixtures/abb_test_case.py`)
✅ Test scripts (`scripts/test_abb_pipeline.sh`, `.ps1`)
✅ E2E tests (`tests/e2e/test_abb_pipeline.py`)

---

## STILL TO BUILD

### 1. Debug CLI Tool

```python
#!/usr/bin/env python3
# bin/rivet-debug

import click
import httpx
from fixtures import get_abb_test_payload, KNOWN_EQUIPMENT

@click.group()
def cli():
    """RIVET Pro Debug Utilities"""
    pass

@cli.command()
@click.argument('workflow_id')
@click.option('--fixture', '-f', default='abb', help='Test fixture to use')
def test(workflow_id, fixture):
    """Test a workflow with fixture data"""
    payload = get_abb_test_payload() if fixture == 'abb' else {}
    # Call Test Orchestrator
    result = call_orchestrator(workflow_id, payload)
    print_results(result)

@cli.command()
@click.argument('node_type')
@click.option('--config', '-c', help='Node config JSON')
def node(node_type, config):
    """Test a single node"""
    # Call Node Tester
    result = call_node_tester(node_type, config)
    print_results(result)

@cli.command()
@click.option('--limit', '-n', default=10)
def errors(limit):
    """Show recent errors"""
    # Query database
    pass

@cli.command()
def fixtures():
    """List available test fixtures"""
    print("ABB ACS580 (original test case)")
    for eq in KNOWN_EQUIPMENT:
        print(f"  - {eq['name']}")

if __name__ == '__main__':
    cli()
```

---

### 2. Telegram Debug Console (n8n Workflow)

A workflow that provides interactive debugging via Telegram:

```
[Telegram Trigger]
    ↓
[Parse Command]
    /test <workflow_id>  → Run test
    /node <type>         → Test node
    /errors              → Show errors
    /status              → System status
    /help                → Show help
    ↓
[Route to Handler]
    ↓
[Execute & Format Response]
    ↓
[Send Telegram Message]
```

---

### 3. Performance Benchmark

```python
# benchmark/pipeline_performance.py
import time
import statistics
from fixtures import get_abb_test_payload

def benchmark_manual_hunter(iterations=10):
    """Benchmark Manual Hunter response times"""
    times = []
    
    for i in range(iterations):
        start = time.time()
        result = call_manual_hunter(get_abb_test_payload())
        duration = (time.time() - start) * 1000
        times.append(duration)
        print(f"  Iteration {i+1}: {duration:.0f}ms")
    
    print(f"\nResults ({iterations} iterations):")
    print(f"  Min: {min(times):.0f}ms")
    print(f"  Max: {max(times):.0f}ms")
    print(f"  Avg: {statistics.mean(times):.0f}ms")
    print(f"  P95: {statistics.quantiles(times, n=20)[18]:.0f}ms")
```

---

### 4. Test Report Generator

```python
# reports/generate_report.py
import json
from datetime import datetime

def generate_html_report(executions):
    """Generate HTML test report"""
    
    passed = sum(1 for e in executions if e['success'])
    failed = len(executions) - passed
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>RIVET Pro Test Report</title>
        <style>
            body {{ font-family: Arial; padding: 20px; }}
            .passed {{ color: green; }}
            .failed {{ color: red; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        </style>
    </head>
    <body>
        <h1>RIVET Pro Test Report</h1>
        <p>Generated: {datetime.now().isoformat()}</p>
        
        <h2>Summary</h2>
        <p class="passed">✅ Passed: {passed}</p>
        <p class="failed">❌ Failed: {failed}</p>
        
        <h2>Executions</h2>
        <table>
            <tr>
                <th>Workflow</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Errors</th>
            </tr>
            {''.join(f'''
            <tr>
                <td>{e['workflow_name']}</td>
                <td class="{"passed" if e['success'] else "failed"}">
                    {"✅" if e['success'] else "❌"}
                </td>
                <td>{e['duration_ms']}ms</td>
                <td>{e.get('error_count', 0)}</td>
            </tr>
            ''' for e in executions)}
        </table>
    </body>
    </html>
    """
    
    return html
```

---

## OUTPUT FILES

```
bin/
└── rivet-debug              # CLI tool

n8n/workflows/testing/
└── debug_console.json       # Telegram debug workflow

benchmark/
└── pipeline_performance.py

reports/
├── generate_report.py
└── templates/
    └── report.html
```

---

## QUICK WIN: Test Now

The ABB test is ready to run:

```bash
# Set your n8n Cloud URL
export N8N_CLOUD_URL="https://your-instance.app.n8n.cloud"

# Run the test
./scripts/test_abb_pipeline.sh
```

Or with Python:

```python
from fixtures import get_abb_test_payload, validate_result, ORIGINAL_ABB_TEST

# Get test data
payload = get_abb_test_payload()
print(payload)
# {'manufacturer': 'ABB', 'model_number': 'ACS580-01-12A5-4', ...}

# After calling Manual Hunter
result = call_manual_hunter(payload)
validation = validate_result(result, ORIGINAL_ABB_TEST["expected"])

if validation["passed"]:
    print("✅ ABB test passed!")
else:
    print("❌ Failed:", validation["validations"])
```

---

## COMPLETION SIGNAL

Create `AGENT3_COMPLETE.md` with:
- Tools created
- Test results
- Benchmark numbers
