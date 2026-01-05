"""
Verify that Phase 1 directory structure is complete.
This script checks files and directories without requiring .env configuration.
"""

import os
from pathlib import Path


def check_directory_structure():
    """Check that all required directories exist."""
    print("=" * 80)
    print("Checking Directory Structure")
    print("=" * 80)

    required_dirs = [
        "core",
        "core/ocr",
        "core/knowledge",
        "core/matching",
        "core/reasoning",
        "core/models",
        "core/workflows",
        "core/nodes",
        "adapters",
        "adapters/telegram",
        "adapters/whatsapp",
        "infra",
        "config",
        "../tests",
        "../tests/core",
        "../tests/adapters",
    ]

    all_exist = True
    for directory in required_dirs:
        exists = Path(directory).is_dir()
        status = "[OK]" if exists else "[MISSING]"
        print(f"{status} {directory}")
        if not exists:
            all_exist = False

    return all_exist


def check_core_files():
    """Check that all core files exist."""
    print("\n" + "=" * 80)
    print("Checking Core Files")
    print("=" * 80)

    required_files = [
        "__init__.py",
        "main.py",
        "config/settings.py",
        "infra/database.py",
        "infra/observability.py",
        "adapters/telegram/bot.py",
        "requirements.txt",
        ".env.example",
        ".gitignore",
        "README.md",
    ]

    all_exist = True
    for file_path in required_files:
        exists = Path(file_path).is_file()
        status = "[OK]" if exists else "[MISSING]"
        print(f"{status} {file_path}")
        if not exists:
            all_exist = False

    return all_exist


def check_env_setup():
    """Check .env file status."""
    print("\n" + "=" * 80)
    print("Checking Environment Setup")
    print("=" * 80)

    env_exists = Path(".env").is_file()
    env_example_exists = Path(".env.example").is_file()

    if env_example_exists:
        print("[OK] .env.example exists")
    else:
        print("[MISSING] .env.example missing")

    if env_exists:
        print("[OK] .env file exists")
    else:
        print("[WARNING] .env file not found")
        print("\n   Next step: Copy .env.example to .env and configure it")
        print("   Command: cd rivet_pro && cp .env.example .env")

    return env_example_exists


def main():
    """Run all verification checks."""
    print("\n")
    print("Rivet Pro - Phase 1 Structure Verification")
    print("\n")

    results = []

    # Run checks
    results.append(check_directory_structure())
    results.append(check_core_files())
    results.append(check_env_setup())

    # Summary
    print("\n" + "=" * 80)
    print("Verification Summary")
    print("=" * 80)

    if all(results):
        print("\n[SUCCESS] Phase 1 structure is complete!")
        print("\nNext steps:")
        print("1. cd rivet_pro")
        print("2. cp .env.example .env")
        print("3. Edit .env and add your TELEGRAM_BOT_TOKEN and DATABASE_URL")
        print("4. pip install -r requirements.txt")
        print("5. python test_setup.py  # Test configuration")
        print("6. python -m rivet_pro.main  # Run the bot")
    else:
        print("\n[FAILED] Some files or directories are missing")
        print("Please review the errors above")

    print("\n")


if __name__ == "__main__":
    main()
