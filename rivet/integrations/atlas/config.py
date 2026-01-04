"""Atlas CMMS configuration from environment variables.

This module provides a Pydantic settings model for Atlas CMMS integration configuration.
All settings can be overridden via environment variables or .env file.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class AtlasConfig(BaseSettings):
    """Atlas CMMS integration settings.

    Configuration is loaded from environment variables with fallback to .env file.
    All settings have sensible defaults for local development.

    Environment Variables:
        ATLAS_BASE_URL: Base URL for Atlas API (default: http://localhost:8080/api)
        ATLAS_EMAIL: Admin email for authentication (default: admin@example.com)
        ATLAS_PASSWORD: Admin password (default: admin)
        ATLAS_TIMEOUT: Request timeout in seconds (default: 30.0)
        ATLAS_MAX_RETRIES: Max retries for failed requests (default: 3)
        ATLAS_ENABLED: Feature flag to enable/disable Atlas integration (default: true)
        ATLAS_TOKEN_TTL: JWT token TTL in seconds (default: 86400 = 24 hours)
        ATLAS_TOKEN_REFRESH_BUFFER: Seconds before expiry to refresh token (default: 300 = 5 minutes)

    Example:
        >>> from agent_factory.integrations.atlas.config import atlas_config
        >>> print(atlas_config.atlas_base_url)
        http://localhost:8080/api
        >>> print(atlas_config.atlas_enabled)
        True
    """

    # API Connection
    atlas_base_url: str = "http://localhost:8080/api"
    atlas_email: str = "admin@example.com"
    atlas_password: str = "admin"

    # Request Settings
    atlas_timeout: float = 30.0
    atlas_max_retries: int = 3

    # Feature Flag
    atlas_enabled: bool = True

    # Token Management
    atlas_token_ttl: int = 86400  # 24 hours
    atlas_token_refresh_buffer: int = 300  # 5 minutes

    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )

    def validate_config(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of error messages. Empty list if configuration is valid.

        Example:
            >>> errors = atlas_config.validate_config()
            >>> if errors:
            ...     print("Configuration errors:", errors)
        """
        errors = []

        # Validate base URL
        if not self.atlas_base_url:
            errors.append("ATLAS_BASE_URL is required")
        elif not self.atlas_base_url.startswith(("http://", "https://")):
            errors.append("ATLAS_BASE_URL must start with http:// or https://")

        # Validate credentials
        if not self.atlas_email:
            errors.append("ATLAS_EMAIL is required")
        if not self.atlas_password:
            errors.append("ATLAS_PASSWORD is required")

        # Validate numeric settings
        if self.atlas_timeout <= 0:
            errors.append("ATLAS_TIMEOUT must be positive")
        if self.atlas_max_retries < 0:
            errors.append("ATLAS_MAX_RETRIES must be non-negative")
        if self.atlas_token_ttl <= 0:
            errors.append("ATLAS_TOKEN_TTL must be positive")
        if self.atlas_token_refresh_buffer < 0:
            errors.append("ATLAS_TOKEN_REFRESH_BUFFER must be non-negative")
        if self.atlas_token_refresh_buffer >= self.atlas_token_ttl:
            errors.append("ATLAS_TOKEN_REFRESH_BUFFER must be less than ATLAS_TOKEN_TTL")

        return errors

    @property
    def is_production(self) -> bool:
        """Check if running in production based on base URL.

        Returns:
            True if base URL is not localhost, False otherwise.
        """
        return "localhost" not in self.atlas_base_url and "127.0.0.1" not in self.atlas_base_url


# Global singleton instance
atlas_config = AtlasConfig()

# Validate configuration on import
_config_errors = atlas_config.validate_config()
if _config_errors and atlas_config.atlas_enabled:
    import warnings
    warnings.warn(
        f"Atlas configuration has errors: {', '.join(_config_errors)}. "
        "Atlas integration may not work correctly.",
        UserWarning
    )
