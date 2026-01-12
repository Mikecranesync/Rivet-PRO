#!/usr/bin/env python3
"""
RIVET Test CLI - Thin wrapper around n8n test workflows

ALL LOGIC IS IN N8N - This just triggers webhooks.

Usage:
    python rivet-test.py validate-url <url> [OPTIONS]
    python rivet-test.py judge-manual <url> [OPTIONS]
    python rivet-test.py run-full <url> [OPTIONS]

Options:
    --equipment-type TYPE    Equipment type for context
    --manufacturer MFR       Manufacturer for context
    --json                   Output as JSON (for scripting)
"""

import click
import requests
import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
N8N_URL = os.getenv("N8N_WEBHOOK_BASE_URL", os.getenv("N8N_URL", "https://mikecranesync.app.n8n.cloud"))
TIMEOUT = int(os.getenv("N8N_WEBHOOK_TIMEOUT", "30"))


def _call_webhook(endpoint: str, payload: dict) -> dict:
    """
    Single HTTP caller for all webhooks (DRY principle)

    Args:
        endpoint: Webhook endpoint path (e.g., "/webhook/rivet-url-validator")
        payload: JSON payload to send

    Returns:
        dict: Response JSON from webhook
    """
    url = f"{N8N_URL}{endpoint}"
    try:
        response = requests.post(url, json=payload, timeout=TIMEOUT)
        response.raise_for_status()

        # Check if response has content
        if not response.text or response.text.strip() == '':
            return {"error": "Workflow returned empty response. Check n8n workflow execution logs.", "success": False}

        return response.json()
    except requests.exceptions.JSONDecodeError as e:
        return {"error": f"Invalid JSON response: {e}. Response text: {response.text[:200]}", "success": False}
    except requests.exceptions.Timeout:
        return {"error": f"Request timed out after {TIMEOUT}s", "success": False}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to n8n at {N8N_URL}", "success": False}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}", "success": False}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "success": False}


@click.group()
@click.version_option(version="1.0.0", prog_name="rivet-test")
def cli():
    """RIVET Test CLI - Validate URLs and judge manual quality"""
    pass


@cli.command()
@click.argument("url")
@click.option("--equipment-type", help="Equipment type for context")
@click.option("--manufacturer", help="Manufacturer for context")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def validate_url(url, equipment_type, manufacturer, json_output):
    """
    Validate a URL (check accessibility, format, etc)

    Examples:
        rivet-test validate-url "https://example.com/manual.pdf"
        rivet-test validate-url "https://abb.com/motor.pdf" --equipment-type "motor"
        rivet-test validate-url "https://example.com/manual.pdf" --json
    """
    payload = {"url": url}

    if equipment_type or manufacturer:
        payload["context"] = {}
        if equipment_type:
            payload["context"]["equipment_type"] = equipment_type
        if manufacturer:
            payload["context"]["manufacturer"] = manufacturer

    result = _call_webhook("/webhook/rivet-url-validator", payload)

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        _print_validation_result(result)

    # Exit with appropriate code
    if result.get("error"):
        sys.exit(1)
    sys.exit(0 if result.get("valid") else 1)


@cli.command()
@click.argument("url")
@click.option("--equipment-type", help="Equipment type for context")
@click.option("--manufacturer", help="Manufacturer for context")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def judge_manual(url, equipment_type, manufacturer, json_output):
    """
    Score manual quality using LLM

    Examples:
        rivet-test judge-manual "https://example.com/manual.pdf"
        rivet-test judge-manual "https://abb.com/motor.pdf" --equipment-type "motor" --manufacturer "ABB"
        rivet-test judge-manual "https://example.com/manual.pdf" --json
    """
    payload = {"url": url}

    if equipment_type:
        payload["equipment_type"] = equipment_type
    if manufacturer:
        payload["manufacturer"] = manufacturer

    result = _call_webhook("/webhook/rivet-llm-judge", payload)

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        _print_judge_result(result)

    # Exit with appropriate code
    if result.get("error"):
        sys.exit(1)
    score = result.get("quality_score", 0)
    sys.exit(0 if score >= 6 else 1)


@cli.command()
@click.argument("url")
@click.option("--equipment-type", help="Equipment type for context")
@click.option("--manufacturer", help="Manufacturer for context")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def run_full(url, equipment_type, manufacturer, json_output):
    """
    Run full end-to-end test (validate + judge)

    Examples:
        rivet-test run-full "https://example.com/manual.pdf"
        rivet-test run-full "https://abb.com/motor.pdf" --equipment-type "motor" --manufacturer "ABB"
        rivet-test run-full "https://example.com/manual.pdf" --json
    """
    payload = {"url": url}

    if equipment_type or manufacturer:
        payload["context"] = {}
        if equipment_type:
            payload["context"]["equipment_type"] = equipment_type
        if manufacturer:
            payload["context"]["manufacturer"] = manufacturer

    result = _call_webhook("/webhook/rivet-test-runner", payload)

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        _print_full_result(result)

    # Exit with appropriate code
    if result.get("error"):
        sys.exit(1)
    sys.exit(0 if result.get("overall") == "pass" else 1)


def _print_validation_result(result):
    """Pretty print validation result"""
    if result.get("error"):
        click.echo(f"\n[ERROR] {result['error']}")
        return

    status = "[OK] VALID" if result.get("valid") else "[FAIL] INVALID"
    click.echo(f"\n{status}")
    click.echo(f"Status Code: {result.get('status_code', 'N/A')}")
    click.echo(f"Content Type: {result.get('content_type', 'N/A')}")
    click.echo(f"File Size: {result.get('file_size_bytes', 0):,} bytes")
    click.echo(f"Score: {result.get('score', 0)}/10")

    if result.get('warnings'):
        click.echo(f"\nWarnings:")
        for warning in result['warnings']:
            click.echo(f"  - {warning}")

    if result.get('error'):
        click.echo(f"\nError: {result['error']}")


def _print_judge_result(result):
    """Pretty print judge result"""
    if result.get("error"):
        click.echo(f"\n[ERROR] {result['error']}")
        return

    score = result.get("quality_score", 0)
    status = "[OK] PASS" if score >= 6 else "[FAIL] FAIL"
    click.echo(f"\n{status} - Quality Score: {score}/10")

    criteria = result.get("criteria", {})
    if criteria:
        click.echo("\nCriteria:")
        for key, val in criteria.items():
            # Convert snake_case to Title Case
            display_name = key.replace('_', ' ').title()
            click.echo(f"  {display_name}: {val}/10")

    feedback = result.get('feedback', 'N/A')
    click.echo(f"\nFeedback: {feedback}")

    click.echo(f"Model: {result.get('llm_model_used', 'N/A')}")


def _print_full_result(result):
    """Pretty print full test result"""
    if result.get("error"):
        click.echo(f"\n[ERROR] {result['error']}")
        return

    overall = result.get("overall", "fail")
    status = "[OK] PASS" if overall == "pass" else "[FAIL] FAIL"
    click.echo(f"\n{status} - Overall: {overall.upper()}")

    # Validation summary
    validation = result.get('validation', {})
    val_score = validation.get('score', 0)
    val_valid = validation.get('valid', False)
    click.echo(f"\nValidation: {'[OK]' if val_valid else '[FAIL]'} {val_score}/10")

    # Quality summary
    quality = result.get('quality', {})
    qual_score = quality.get('quality_score', 0)
    click.echo(f"Quality: {qual_score}/10")

    # Duration
    duration_ms = result.get('test_duration_ms', 0)
    duration_s = duration_ms / 1000
    click.echo(f"Duration: {duration_s:.2f}s")

    # Timestamp
    timestamp = result.get('timestamp', 'N/A')
    click.echo(f"Timestamp: {timestamp}")


if __name__ == "__main__":
    cli()
