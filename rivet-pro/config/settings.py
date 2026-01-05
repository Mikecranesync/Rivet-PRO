"""
RIVET Pro Configuration Settings

Pydantic-based settings loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via .env file or environment variables.
    """

    # Telegram Bot Configuration
    telegram_bot_token: str

    # Database Configuration
    database_url: str

    # AI Provider API Keys
    groq_api_key: str
    google_api_key: str
    anthropic_api_key: str
    openai_api_key: str

    # LLM Orchestrator Configuration
    orchestrator_model: str = "claude-3-5-sonnet-20241022"
    orchestrator_provider: str = "anthropic"  # anthropic, openai, google, groq

    # Redis Configuration (Optional)
    redis_url: Optional[str] = None

    # Storage Configuration (Optional)
    s3_bucket: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_endpoint: Optional[str] = None

    # Observability (Optional)
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "rivet-pro"

    # Feature Flags
    beta_mode: bool = True  # Unlock all features during testing

    # Application Settings
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings singleton.

    Returns:
        Settings instance loaded from environment.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
