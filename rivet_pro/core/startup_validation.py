"""
RIVET PRO Startup Validation
Ensures correct database endpoint and configuration before starting.
"""

import os
import sys
from urllib.parse import urlparse


class StartupValidationError(Exception):
    """Raised when startup validation fails."""
    pass


def validate_database_endpoint() -> bool:
    """
    Validate that DATABASE_URL points to the correct Neon endpoint.

    Returns:
        bool: True if validation passes

    Raises:
        StartupValidationError: If validation fails
    """
    db_url = os.getenv("DATABASE_URL", "")

    if not db_url:
        raise StartupValidationError(
            "DATABASE_URL not set!\n"
            "Please set DATABASE_URL in your .env file."
        )

    # Parse the URL
    parsed = urlparse(db_url)
    host = parsed.hostname or ""

    # CORRECT endpoint
    correct_endpoint = "ep-purple-hall-ahimeyn0"

    # WRONG endpoint (empty database)
    wrong_endpoint = "ep-lingering-salad-ahbmzx98"

    if wrong_endpoint in host:
        raise StartupValidationError(
            f"WRONG DATABASE ENDPOINT!\n"
            f"\n"
            f"You are connecting to: {host}\n"
            f"This endpoint has only 4 empty tables.\n"
            f"\n"
            f"CORRECT endpoint: {correct_endpoint}-pooler.c-3.us-east-1.aws.neon.tech\n"
            f"\n"
            f"Update your .env file with the correct DATABASE_URL."
        )

    if correct_endpoint not in host:
        # Allow other databases (Supabase, local, etc.) but warn
        print(f"[WARNING] Non-standard database endpoint: {host}")
        print(f"          Expected endpoint containing: {correct_endpoint}")
        return True

    return True


def validate_required_env_vars() -> bool:
    """
    Validate that required environment variables are set.

    Returns:
        bool: True if all required vars are set

    Raises:
        StartupValidationError: If required vars are missing
    """
    required_vars = [
        "DATABASE_URL",
    ]

    optional_vars = [
        "TELEGRAM_BOT_TOKEN",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        raise StartupValidationError(
            f"Missing required environment variables:\n"
            f"  {', '.join(missing)}\n"
            f"\n"
            f"Please set these in your .env file."
        )

    # Warn about optional vars
    missing_optional = [v for v in optional_vars if not os.getenv(v)]
    if missing_optional:
        print(f"[INFO] Optional vars not set: {', '.join(missing_optional)}")

    return True


def run_startup_validation() -> bool:
    """
    Run all startup validations.

    Returns:
        bool: True if all validations pass

    Raises:
        StartupValidationError: If any validation fails
    """
    print("=" * 50)
    print("  RIVET PRO Startup Validation")
    print("=" * 50)

    try:
        print("\n[1/2] Validating environment variables...")
        validate_required_env_vars()
        print("      [OK] Environment variables valid")

        print("\n[2/2] Validating database endpoint...")
        validate_database_endpoint()
        print("      [OK] Database endpoint valid")

        print("\n" + "=" * 50)
        print("  All validations passed!")
        print("=" * 50 + "\n")
        return True

    except StartupValidationError as e:
        print("\n" + "=" * 50)
        print("  VALIDATION FAILED!")
        print("=" * 50)
        print(f"\n{e}\n")
        return False


if __name__ == "__main__":
    # Load .env if python-dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    if not run_startup_validation():
        sys.exit(1)
