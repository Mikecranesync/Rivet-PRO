"""
RIVET Test Client - Thin wrapper around n8n test workflows

ALL LOGIC IS IN N8N - This just triggers webhooks and formats results.

Architecture:
  - Agent 1: Creates test workflows in n8n (URL validator, LLM judge, test runner)
  - Agent 2: This client - just calls webhooks, no business logic
  - n8n: Contains all test logic, validation, scoring

Usage:
  python scripts/test_client.py validate-url "https://example.com/manual.pdf"
  python scripts/test_client.py judge-manual manual.json
  python scripts/test_client.py run-test e2e payload.json
  python scripts/test_client.py validate-url "..." --json-output
"""

import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional

import click
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment
WEBHOOK_BASE_URL = os.getenv("N8N_WEBHOOK_BASE_URL", "").rstrip("/")
WEBHOOK_TIMEOUT = int(os.getenv("N8N_WEBHOOK_TIMEOUT", "30"))

# Webhook endpoints (Agent 1 creates these in n8n)
ENDPOINTS = {
    "url_validator": "/webhook/rivet-url-validator",
    "llm_judge": "/webhook/rivet-llm-judge",
    "test_runner": "/webhook/rivet-test-runner",
}


# ======================================================================
# CUSTOM EXCEPTIONS
# ======================================================================


class WebhookError(Exception):
    """Raised when webhook call fails (network, HTTP error, etc)"""
    pass


class ValidationError(Exception):
    """Raised when input validation fails"""
    pass


# ======================================================================
# DATA MODEL
# ======================================================================


@dataclass
class TestResult:
    """Result from a test workflow execution"""
    success: bool                # Did the test pass?
    test_type: str               # Which test (url-validator, llm-judge, etc)
    payload: Dict[str, Any]      # What we sent
    response: Dict[str, Any]     # What we got back
    duration_ms: float           # How long it took
    error: Optional[str] = None  # Error message if failed

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self), indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


# ======================================================================
# CORE FUNCTIONS
# ======================================================================


def _call_webhook(endpoint: str, payload: Dict[str, Any], timeout: int = None) -> TestResult:
    """
    DRY principle - single HTTP caller for all webhooks

    Args:
        endpoint: Webhook path (e.g., /webhook/rivet-url-validator)
        payload: JSON payload to send
        timeout: Request timeout in seconds (defaults to WEBHOOK_TIMEOUT)

    Returns:
        TestResult with success, response, duration

    Raises:
        WebhookError: If network/HTTP error occurs
    """
    if not WEBHOOK_BASE_URL:
        raise WebhookError(
            "N8N_WEBHOOK_BASE_URL not set. Add to .env:\n"
            "N8N_WEBHOOK_BASE_URL=https://your-n8n-instance.com"
        )

    url = f"{WEBHOOK_BASE_URL}{endpoint}"
    timeout = timeout or WEBHOOK_TIMEOUT
    test_type = endpoint.split("/")[-1]  # Extract test name from endpoint

    start_time = time.time()

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        duration_ms = (time.time() - start_time) * 1000

        # Try to parse JSON response
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw": response.text}

        # Success if status code is 2xx or 3xx
        success = 200 <= response.status_code < 400
        error = None if success else response_data.get("error") or f"HTTP {response.status_code}"

        return TestResult(
            success=success,
            test_type=test_type,
            payload=payload,
            response=response_data,
            duration_ms=duration_ms,
            error=error
        )

    except requests.exceptions.Timeout:
        duration_ms = (time.time() - start_time) * 1000
        raise WebhookError(f"Timeout after {timeout}s calling {url}")

    except requests.exceptions.ConnectionError as e:
        duration_ms = (time.time() - start_time) * 1000
        raise WebhookError(f"Connection failed to {url}: {e}")

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        raise WebhookError(f"Unexpected error calling {url}: {e}")


def validate_url(url: str, context: Optional[Dict[str, Any]] = None) -> TestResult:
    """
    Call RIVET-URL-Validator webhook to check if URL is valid

    Args:
        url: URL to validate (e.g., https://example.com/manual.pdf)
        context: Optional context (equipment_type, manufacturer)

    Returns:
        TestResult with validation results

    Example:
        result = validate_url("https://example.com/manual.pdf", {"equipment_type": "motor"})
        if result.success:
            print(f"Score: {result.response['score']}/10")
    """
    if not url:
        raise ValidationError("URL is required")

    if not url.startswith(("http://", "https://")):
        raise ValidationError("URL must start with http:// or https://")

    payload = {"url": url}
    if context:
        payload["context"] = context

    return _call_webhook(ENDPOINTS["url_validator"], payload)


def judge_manual(manual_data: Dict[str, Any]) -> TestResult:
    """
    Call RIVET-LLM-Judge webhook to score manual quality

    Args:
        manual_data: Dict with url, content, equipment_type, etc.

    Returns:
        TestResult with quality score and analysis

    Example:
        data = {
            "url": "https://example.com/manual.pdf",
            "content": "Manual content...",
            "equipment_type": "motor"
        }
        result = judge_manual(data)
        print(f"Quality: {result.response['quality_score']}/10")
    """
    if not manual_data:
        raise ValidationError("manual_data is required")

    if not isinstance(manual_data, dict):
        raise ValidationError("manual_data must be a dictionary")

    # Basic validation
    if "url" not in manual_data and "content" not in manual_data:
        raise ValidationError("manual_data must contain 'url' or 'content'")

    return _call_webhook(ENDPOINTS["llm_judge"], manual_data)


def run_test(test_type: str, payload: Dict[str, Any]) -> TestResult:
    """
    Call RIVET-Test-Runner webhook to run generic test

    Args:
        test_type: Type of test to run (e2e, integration, etc.)
        payload: Test-specific payload

    Returns:
        TestResult with test results

    Example:
        result = run_test("e2e", {"test_case": "abb_acs580"})
        if result.success:
            print("Test passed!")
    """
    if not test_type:
        raise ValidationError("test_type is required")

    if not payload:
        raise ValidationError("payload is required")

    if not isinstance(payload, dict):
        raise ValidationError("payload must be a dictionary")

    test_payload = {
        "test_type": test_type,
        **payload
    }

    return _call_webhook(ENDPOINTS["test_runner"], test_payload)


# ======================================================================
# CLI INTERFACE
# ======================================================================


@click.group()
@click.version_option(version="1.0.0", prog_name="rivet-test-client")
def cli():
    """
    RIVET Test Client - Trigger n8n test workflows

    Examples:
      python scripts/test_client.py validate-url "https://example.com/manual.pdf"
      python scripts/test_client.py judge-manual manual.json
      python scripts/test_client.py run-test e2e payload.json
    """
    pass


@cli.command()
@click.argument("url")
@click.option("--equipment-type", help="Equipment type for context")
@click.option("--manufacturer", help="Manufacturer for context")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def validate_url_cmd(url: str, equipment_type: Optional[str], manufacturer: Optional[str], json_output: bool):
    """Validate a URL (check accessibility, format, etc)"""
    try:
        context = {}
        if equipment_type:
            context["equipment_type"] = equipment_type
        if manufacturer:
            context["manufacturer"] = manufacturer

        result = validate_url(url, context if context else None)

        if json_output:
            click.echo(result.to_json())
        else:
            _print_result(result)

        sys.exit(0 if result.success else 1)

    except (WebhookError, ValidationError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("manual_file", type=click.Path(exists=True))
@click.option("--json-output", is_flag=True, help="Output as JSON")
def judge_manual_cmd(manual_file: str, json_output: bool):
    """Score manual quality using LLM judge"""
    try:
        # Load manual data from file
        with open(manual_file, "r") as f:
            manual_data = json.load(f)

        result = judge_manual(manual_data)

        if json_output:
            click.echo(result.to_json())
        else:
            _print_result(result)

        sys.exit(0 if result.success else 1)

    except FileNotFoundError:
        click.echo(f"Error: File not found: {manual_file}", err=True)
        sys.exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in {manual_file}: {e}", err=True)
        sys.exit(1)
    except (WebhookError, ValidationError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("test_type")
@click.argument("payload_file", type=click.Path(exists=True))
@click.option("--json-output", is_flag=True, help="Output as JSON")
def run_test_cmd(test_type: str, payload_file: str, json_output: bool):
    """Run a generic test (e2e, integration, etc)"""
    try:
        # Load payload from file
        with open(payload_file, "r") as f:
            payload = json.load(f)

        result = run_test(test_type, payload)

        if json_output:
            click.echo(result.to_json())
        else:
            _print_result(result)

        sys.exit(0 if result.success else 1)

    except FileNotFoundError:
        click.echo(f"Error: File not found: {payload_file}", err=True)
        sys.exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in {payload_file}: {e}", err=True)
        sys.exit(1)
    except (WebhookError, ValidationError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _print_result(result: TestResult):
    """Pretty print a test result (non-JSON mode)"""
    status = "PASS" if result.success else "FAIL"
    status_color = "green" if result.success else "red"

    click.echo(f"\n{'='*60}")
    click.secho(f"Test Result: {status}", fg=status_color, bold=True)
    click.echo(f"{'='*60}")
    click.echo(f"Test Type:    {result.test_type}")
    click.echo(f"Duration:     {result.duration_ms:.2f}ms")

    if result.error:
        click.secho(f"Error:        {result.error}", fg="red")

    click.echo(f"\nPayload:")
    click.echo(json.dumps(result.payload, indent=2))

    click.echo(f"\nResponse:")
    click.echo(json.dumps(result.response, indent=2))
    click.echo(f"{'='*60}\n")


# ======================================================================
# MAIN
# ======================================================================


if __name__ == "__main__":
    cli()
