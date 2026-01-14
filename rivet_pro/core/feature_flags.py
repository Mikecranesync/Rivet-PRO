"""
Feature Flag Management for RIVET Pro

Provides a lightweight feature flag system for safe rollouts and migrations.
Flags are defined in rivet_pro/config/feature_flags.json and can be overridden
via environment variables.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class FeatureFlagManager:
    """
    Manages feature flags for RIVET Pro.

    Flags are loaded from rivet_pro/config/feature_flags.json with support
    for environment-based overrides via RIVET_FLAG_<NAME>=true/false.

    Example usage:
        flags = FeatureFlagManager()
        if flags.is_enabled('rivet.migration.new_ocr'):
            use_new_ocr()
        else:
            use_old_ocr()
    """

    _instance: Optional['FeatureFlagManager'] = None
    _flags: Dict[str, dict] = {}
    _loaded: bool = False

    def __new__(cls):
        """Singleton pattern to avoid reloading flags"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize feature flag manager"""
        if not self._loaded:
            self._load_flags()
            self._loaded = True

    def _load_flags(self) -> None:
        """Load feature flags from JSON config file"""
        try:
            # Find config file
            config_path = Path(__file__).parent.parent / 'config' / 'feature_flags.json'

            if not config_path.exists():
                logger.warning(f"Feature flags config not found: {config_path}")
                self._flags = {}
                return

            # Load and parse JSON
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate structure
            if not isinstance(data, dict):
                logger.error("Feature flags config must be a JSON object")
                self._flags = {}
                return

            self._flags = data
            logger.info(f"Loaded {len(self._flags)} feature flags from {config_path}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in feature flags config: {e}")
            self._flags = {}
        except Exception as e:
            logger.error(f"Failed to load feature flags: {e}")
            self._flags = {}

    def is_enabled(self, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.

        Checks in this order:
        1. Environment variable: RIVET_FLAG_<NAME>=true/false
        2. Config file default_enabled value
        3. Safe default: False

        Args:
            flag_name: The feature flag name (e.g., 'rivet.migration.new_ocr')

        Returns:
            True if enabled, False otherwise
        """
        # Check environment override
        env_var = f"RIVET_FLAG_{flag_name.replace('.', '_').upper()}"
        env_value = os.getenv(env_var)

        if env_value is not None:
            enabled = env_value.lower() in ('true', '1', 'yes', 'on')
            logger.debug(f"Flag '{flag_name}' overridden by env: {enabled}")
            return enabled

        # Check config file
        if flag_name in self._flags:
            flag_config = self._flags[flag_name]
            enabled = flag_config.get('default_enabled', False)
            logger.debug(f"Flag '{flag_name}' from config: {enabled}")
            return enabled

        # Safe default: False
        logger.debug(f"Flag '{flag_name}' not defined, defaulting to False")
        return False

    def get_all_flags(self) -> Dict[str, dict]:
        """
        Get all defined feature flags with their current states.

        Returns:
            Dictionary mapping flag names to their full configuration with
            current enabled state included.
        """
        result = {}

        for flag_name, config in self._flags.items():
            result[flag_name] = {
                **config,
                'current_state': self.is_enabled(flag_name)
            }

        return result

    def get_flag_info(self, flag_name: str) -> Optional[dict]:
        """
        Get detailed information about a specific flag.

        Args:
            flag_name: The feature flag name

        Returns:
            Dictionary with flag configuration and current state, or None if not found
        """
        if flag_name not in self._flags:
            return None

        return {
            **self._flags[flag_name],
            'current_state': self.is_enabled(flag_name)
        }

    def reload(self) -> None:
        """Reload flags from config file (useful for testing)"""
        self._loaded = False
        self._load_flags()
        self._loaded = True
        logger.info("Feature flags reloaded")


# Global instance for convenience
_manager = FeatureFlagManager()


def is_enabled(flag_name: str) -> bool:
    """
    Convenience function to check if a flag is enabled.

    Args:
        flag_name: The feature flag name

    Returns:
        True if enabled, False otherwise
    """
    return _manager.is_enabled(flag_name)


def get_all_flags() -> Dict[str, dict]:
    """
    Convenience function to get all flags.

    Returns:
        Dictionary of all flags with their states
    """
    return _manager.get_all_flags()
