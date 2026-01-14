#!/usr/bin/env python3
"""
Feature Flag Toggle CLI

Manage feature flags without directly editing JSON files.
Provides commands to list, toggle, and validate feature flags.

Usage:
    python toggle_flag.py --list
    python toggle_flag.py --flag-name rivet.migration.new_ocr --enable --env dev
    python toggle_flag.py --validate
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class FlagToggleCLI:
    """CLI tool for managing feature flags"""

    def __init__(self):
        """Initialize CLI"""
        self.project_root = Path(__file__).parent.parent.parent
        self.config_path = self.project_root / 'rivet_pro' / 'config' / 'feature_flags.json'
        self.log_path = Path(__file__).parent / 'flag_changes.log'

    def load_flags(self) -> Dict:
        """Load feature flags from config file"""
        if not self.config_path.exists():
            print(f"❌ Config file not found: {self.config_path}")
            sys.exit(1)

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in config file: {e}")
            sys.exit(1)

    def save_flags(self, flags: Dict) -> None:
        """Save feature flags to config file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(flags, f, indent=2, ensure_ascii=False)
                f.write('\n')  # Add newline at end
        except Exception as e:
            print(f"❌ Failed to save config: {e}")
            sys.exit(1)

    def log_change(self, message: str) -> None:
        """Log flag change to log file"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}\n"

        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"⚠️  Warning: Failed to write to log file: {e}")

    def list_flags(self) -> None:
        """List all feature flags with their current states"""
        flags = self.load_flags()

        if not flags:
            print("No feature flags defined.")
            return

        print("\n" + "=" * 80)
        print("Feature Flags".center(80))
        print("=" * 80 + "\n")

        for flag_name, config in sorted(flags.items()):
            enabled = config.get('default_enabled', False)
            category = config.get('category', 'unknown')
            description = config.get('description', 'No description')

            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            print(f"{status} [{category}] {flag_name}")
            print(f"   {description}")

            # Show environment states
            envs = config.get('environments', {})
            if envs:
                env_states = []
                for env, state in envs.items():
                    symbol = "✓" if state else "✗"
                    env_states.append(f"{env}:{symbol}")
                print(f"   Environments: {', '.join(env_states)}")

            # Show metadata
            created = config.get('created_date', 'unknown')
            owner = config.get('owner', 'unknown')
            print(f"   Created: {created} | Owner: {owner}")
            print()

        print("=" * 80)
        print(f"\nTotal flags: {len(flags)}")
        print(f"Config file: {self.config_path}")
        print()

    def toggle_flag(self, flag_name: str, enable: bool, env: Optional[str], force: bool) -> None:
        """Toggle a feature flag"""
        flags = self.load_flags()

        if flag_name not in flags:
            print(f"❌ Flag '{flag_name}' not found in config")
            print("\nAvailable flags:")
            for name in sorted(flags.keys()):
                print(f"  - {name}")
            sys.exit(1)

        flag_config = flags[flag_name]

        # Show current state
        print("\nCurrent state:")
        print(f"  Flag: {flag_name}")
        print(f"  Default enabled: {flag_config.get('default_enabled', False)}")
        if 'environments' in flag_config:
            print(f"  Environments: {flag_config['environments']}")

        # Check if toggling production
        if env == 'prod' and not force:
            print("\n⚠️  WARNING: You are toggling a production flag!")
            print("This can affect live users. Use --force to confirm.")
            sys.exit(1)

        # Apply change
        if env:
            # Toggle specific environment
            if 'environments' not in flag_config:
                flag_config['environments'] = {}

            flag_config['environments'][env] = enable
            change_desc = f"{'Enabled' if enable else 'Disabled'} {flag_name} in {env}"
        else:
            # Toggle default
            flag_config['default_enabled'] = enable
            change_desc = f"Set {flag_name} default_enabled to {enable}"

        # Save changes
        flags[flag_name] = flag_config
        self.save_flags(flags)

        # Log change
        self.log_change(change_desc)

        # Show new state
        print("\n✅ New state:")
        print(f"  Flag: {flag_name}")
        print(f"  Default enabled: {flag_config.get('default_enabled', False)}")
        if 'environments' in flag_config:
            print(f"  Environments: {flag_config['environments']}")

        print(f"\nChange logged to: {self.log_path}")

    def validate(self) -> None:
        """Validate feature flags configuration"""
        print("Validating feature flags configuration...\n")

        flags = self.load_flags()
        errors = []
        warnings = []

        # Required fields for each flag
        required_fields = ['description', 'default_enabled', 'category']

        for flag_name, config in flags.items():
            # Check naming convention
            if not flag_name.startswith('rivet.'):
                errors.append(f"Flag '{flag_name}' doesn't follow naming convention (must start with 'rivet.')")

            # Check required fields
            for field in required_fields:
                if field not in config:
                    errors.append(f"Flag '{flag_name}' missing required field: {field}")

            # Check category is valid
            valid_categories = ['migration', 'experiment', 'rollout', 'kill_switch']
            category = config.get('category')
            if category and category not in valid_categories:
                warnings.append(f"Flag '{flag_name}' has non-standard category: {category}")

            # Check environments format
            if 'environments' in config:
                envs = config['environments']
                if not isinstance(envs, dict):
                    errors.append(f"Flag '{flag_name}' environments must be a dictionary")
                else:
                    for env, state in envs.items():
                        if not isinstance(state, bool):
                            errors.append(f"Flag '{flag_name}' environment '{env}' state must be boolean")

        # Report results
        if errors:
            print("❌ ERRORS:")
            for error in errors:
                print(f"  - {error}")
            print()

        if warnings:
            print("⚠️  WARNINGS:")
            for warning in warnings:
                print(f"  - {warning}")
            print()

        if not errors and not warnings:
            print("✅ Configuration is valid!")
            print(f"   Validated {len(flags)} flags")
        elif not errors:
            print(f"✅ No errors found ({len(warnings)} warnings)")
        else:
            print(f"❌ Validation failed: {len(errors)} errors, {len(warnings)} warnings")
            sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Feature Flag Toggle CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all flags
  python toggle_flag.py --list

  # Enable a flag in dev
  python toggle_flag.py --flag-name rivet.migration.new_ocr --enable --env dev

  # Disable a flag globally
  python toggle_flag.py --flag-name rivet.experiment.beta --disable

  # Enable in production (requires --force)
  python toggle_flag.py --flag-name rivet.rollout.new_ui --enable --env prod --force

  # Validate config
  python toggle_flag.py --validate
        """
    )

    parser.add_argument('--list', action='store_true', help='List all flags with their states')
    parser.add_argument('--flag-name', type=str, help='Flag name to toggle')
    parser.add_argument('--enable', action='store_true', help='Enable the flag')
    parser.add_argument('--disable', action='store_true', help='Disable the flag')
    parser.add_argument('--env', type=str, choices=['dev', 'stage', 'prod'],
                        help='Specific environment to toggle (optional)')
    parser.add_argument('--force', action='store_true',
                        help='Force toggle in production (required for prod changes)')
    parser.add_argument('--validate', action='store_true', help='Validate configuration JSON schema')

    args = parser.parse_args()

    cli = FlagToggleCLI()

    # Handle commands
    if args.list:
        cli.list_flags()
    elif args.validate:
        cli.validate()
    elif args.flag_name:
        if not (args.enable or args.disable):
            print("❌ Must specify --enable or --disable")
            sys.exit(1)
        if args.enable and args.disable:
            print("❌ Cannot specify both --enable and --disable")
            sys.exit(1)

        cli.toggle_flag(args.flag_name, args.enable, args.env, args.force)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
