#!/usr/bin/env python3
"""
Parse Neon PostgreSQL connection URL for n8n credential configuration.
Makes it easy to copy values into n8n UI.
"""

import os
import re
from pathlib import Path


def parse_postgres_url(url: str) -> dict:
    """
    Parse PostgreSQL connection URL into components.

    Format: postgresql://user:password@host:port/database?params
    """
    # Remove any whitespace
    url = url.strip()

    # Parse using regex
    pattern = r'postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?]+)(?:\?(.+))?'
    match = re.match(pattern, url)

    if not match:
        return {
            "error": "Invalid PostgreSQL URL format",
            "expected": "postgresql://user:password@host:port/database"
        }

    user, password, host, port, database, params = match.groups()

    # Default port if not specified
    port = port or "5432"

    # Check for SSL requirement
    ssl_required = "sslmode=require" in (params or "")

    return {
        "host": host,
        "port": int(port),
        "database": database,
        "user": user,
        "password": password,
        "ssl": ssl_required,
        "raw_params": params
    }


def print_n8n_instructions(parsed: dict):
    """Print formatted instructions for n8n UI."""
    if "error" in parsed:
        print(f"❌ Error: {parsed['error']}")
        print(f"Expected format: {parsed['expected']}")
        return

    print("=" * 60)
    print("✅ NEON CREDENTIAL CONFIGURATION FOR N8N")
    print("=" * 60)
    print()
    print("Copy these values into n8n UI:")
    print()
    print(f"Credential Name: Neon PostgreSQL - Ralph")
    print(f"Host:            {parsed['host']}")
    print(f"Port:            {parsed['port']}")
    print(f"Database:        {parsed['database']}")
    print(f"User:            {parsed['user']}")
    print(f"Password:        {parsed['password']}")
    print(f"SSL:             {'ON (Toggle Enabled)' if parsed['ssl'] else 'OFF'}")
    print()
    print("=" * 60)
    print("STEP-BY-STEP INSTRUCTIONS:")
    print("=" * 60)
    print()
    print("1. Open n8n at http://72.60.175.144:5678")
    print("2. Navigate to: Settings → Credentials")
    print("3. Click: + Add Credential")
    print("4. Select: Postgres")
    print("5. Fill in the values above (copy-paste from this output)")
    print("6. Click: Create")
    print()
    print("OR create it directly in a workflow:")
    print()
    print("1. Open 'Ralph Main Loop' workflow")
    print("2. Click any purple Postgres node")
    print("3. Click the credential dropdown → '+ Create New Credential'")
    print("4. Fill in the values above")
    print("5. Click: Create")
    print()
    print("✅ Once created, all 7 Postgres nodes will automatically use it!")
    print()


def main():
    """Main function."""
    # Try to load from .env file
    env_file = Path(__file__).parent.parent.parent / ".env"

    if not env_file.exists():
        print(f"❌ .env file not found at: {env_file}")
        print()
        print("Please provide your NEON_DATABASE_URL:")
        database_url = input("> ")
    else:
        # Read .env file
        database_url = None
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('NEON_DATABASE_URL=') or line.startswith('DATABASE_URL='):
                    database_url = line.split('=', 1)[1].strip()
                    # Remove quotes if present
                    database_url = database_url.strip('"').strip("'")
                    break

        if not database_url:
            print(f"❌ NEON_DATABASE_URL not found in {env_file}")
            print()
            print("Please provide your NEON_DATABASE_URL:")
            database_url = input("> ")

    print()
    print(f"🔍 Parsing connection URL...")
    print()

    # Parse the URL
    parsed = parse_postgres_url(database_url)

    # Print instructions
    print_n8n_instructions(parsed)

    # Also save to a file for easy reference
    output_file = Path(__file__).parent / "neon_credentials.txt"
    with open(output_file, 'w') as f:
        f.write("NEON POSTGRESQL CREDENTIALS FOR N8N\n")
        f.write("=" * 60 + "\n\n")
        if "error" not in parsed:
            f.write(f"Credential Name: Neon PostgreSQL - Ralph\n")
            f.write(f"Host:            {parsed['host']}\n")
            f.write(f"Port:            {parsed['port']}\n")
            f.write(f"Database:        {parsed['database']}\n")
            f.write(f"User:            {parsed['user']}\n")
            f.write(f"Password:        {parsed['password']}\n")
            f.write(f"SSL:             {'ON' if parsed['ssl'] else 'OFF'}\n")
        else:
            f.write(f"Error: {parsed['error']}\n")

    print(f"📁 Credentials also saved to: {output_file}")
    print()


if __name__ == "__main__":
    main()
