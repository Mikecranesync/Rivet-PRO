# stabilize-rivet.ps1 - RIVET PRO Stability Setup Script
# Run once to lock down configuration and prevent accidents

param(
    [switch]$Force,
    [switch]$SkipHooks
)

$ErrorActionPreference = "Stop"
# Use current directory as project root
$ProjectRoot = (Get-Location).Path
Write-Host "Project Root: $ProjectRoot" -ForegroundColor Gray

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "  RIVET PRO Stability Setup" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# 1. Create WORKING_CONFIG.md
Write-Host "[1/3] Creating WORKING_CONFIG.md..." -ForegroundColor Yellow

$WorkingConfigPath = Join-Path $ProjectRoot ".github\WORKING_CONFIG.md"
$GithubDir = Join-Path $ProjectRoot ".github"

if (-not (Test-Path $GithubDir)) {
    New-Item -ItemType Directory -Path $GithubDir -Force | Out-Null
}

$WorkingConfig = @"
# WORKING_CONFIG.md - FROZEN CONFIGURATION
# DO NOT MODIFY - This documents the KNOWN WORKING configuration
# Last verified: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Database Connections

### PRIMARY DATABASE: Neon PostgreSQL
- **Endpoint**: `ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech`
- **Database**: `neondb`
- **User**: `neondb_owner`
- **Tables**: 120+
- **Status**: PRODUCTION

> **WARNING**: There is another Neon endpoint `ep-lingering-salad-ahbmzx98`
> which has only 4 empty tables. DO NOT USE IT.

### BACKUP DATABASE: Supabase
- **Host**: `db.mggqgrxwumnnujojndub.supabase.co`
- **Database**: `postgres`
- **Status**: Legacy/Archive (1,985 knowledge atoms)

### FAILOVER ORDER
1. Neon (primary)
2. Turso (backup - to be configured)
3. Supabase (archive/read-only)

## Environment Variables

### Required in .env
``````
DATABASE_URL=postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require
DATABASE_PROVIDER=neon
DATABASE_FAILOVER_ORDER=neon,turso,supabase
``````

## Validation

On startup, the application MUST verify:
1. DATABASE_URL contains `ep-purple-hall-ahimeyn0` (correct endpoint)
2. Database connection succeeds
3. Core tables exist (ralph_stories, knowledge_atoms, etc.)

## Change Log

| Date | Change | By |
|------|--------|-----|
| $(Get-Date -Format "yyyy-MM-dd") | Initial frozen config | stabilize-rivet.ps1 |
"@

Set-Content -Path $WorkingConfigPath -Value $WorkingConfig -Encoding UTF8
Write-Host "  [OK] Created $WorkingConfigPath" -ForegroundColor Green

# 2. Set up git hooks
if (-not $SkipHooks) {
    Write-Host ""
    Write-Host "[2/3] Setting up git hooks..." -ForegroundColor Yellow

    $HooksDir = Join-Path $ProjectRoot ".git\hooks"
    $PreCommitPath = Join-Path $HooksDir "pre-commit"

    $PreCommitHook = @'
#!/bin/sh
# RIVET PRO Pre-commit Hook
# Prevents accidental commits of sensitive files

# Check for .env files being committed
if git diff --cached --name-only | grep -E "^\.env$|^\.env\..+$" > /dev/null; then
    echo ""
    echo "ERROR: Attempting to commit .env file!"
    echo "This file contains secrets and should never be committed."
    echo ""
    echo "To remove from staging:"
    echo "  git reset HEAD .env"
    echo ""
    exit 1
fi

# Check for credentials in staged files
if git diff --cached | grep -iE "(api_key|password|secret|token).*=.*['\"][^'\"]{10,}['\"]" > /dev/null; then
    echo ""
    echo "WARNING: Possible secrets detected in staged changes!"
    echo "Please review your changes carefully."
    echo ""
    echo "To proceed anyway (if this is a false positive):"
    echo "  git commit --no-verify"
    echo ""
    exit 1
fi

exit 0
'@

    Set-Content -Path $PreCommitPath -Value $PreCommitHook -Encoding UTF8 -NoNewline
    Write-Host "  [OK] Created pre-commit hook" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[2/3] Skipping git hooks (--SkipHooks specified)" -ForegroundColor Gray
}

# 3. Create validation utility
Write-Host ""
Write-Host "[3/3] Creating validation utility..." -ForegroundColor Yellow

$ValidationPath = Join-Path $ProjectRoot "rivet_pro\core\startup_validation.py"
$CoreDir = Join-Path $ProjectRoot "rivet_pro\core"

if (-not (Test-Path $CoreDir)) {
    New-Item -ItemType Directory -Path $CoreDir -Force | Out-Null
}

$ValidationCode = @'
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
'@

Set-Content -Path $ValidationPath -Value $ValidationCode -Encoding UTF8
Write-Host "  [OK] Created $ValidationPath" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "Files created:" -ForegroundColor White
Write-Host "  - .github/WORKING_CONFIG.md (frozen configuration)" -ForegroundColor Gray
Write-Host "  - .git/hooks/pre-commit (prevents .env commits)" -ForegroundColor Gray
Write-Host "  - rivet_pro/core/startup_validation.py (endpoint validation)" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review WORKING_CONFIG.md" -ForegroundColor Gray
Write-Host "  2. Test validation: python rivet_pro/core/startup_validation.py" -ForegroundColor Gray
Write-Host "  3. Commit these files to git" -ForegroundColor Gray
Write-Host ""
