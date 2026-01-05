"""
Pydantic settings configuration for Rivet Pro.
Loads all configuration from environment variables.
"""

from typing import Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings can be overridden via .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Telegram Configuration
    telegram_bot_token: str = Field(..., description="Telegram bot token from @BotFather")
    telegram_webhook_url: Optional[str] = Field(None, description="Webhook URL for production")
    telegram_webhook_secret: Optional[str] = Field(None, description="Webhook secret token")

    # WhatsApp Configuration (Future)
    whatsapp_phone_id: Optional[str] = None
    whatsapp_token: Optional[str] = None
    whatsapp_verify_token: Optional[str] = None
    whatsapp_app_secret: Optional[str] = None

    # Database Configuration
    database_url: str = Field(..., description="PostgreSQL connection URL (Neon)")
    database_pool_min_size: int = Field(2, description="Min connections in pool")
    database_pool_max_size: int = Field(10, description="Max connections in pool")

    # Redis Configuration
    redis_url: Optional[str] = Field(None, description="Redis connection URL for caching")

    # AI Provider API Keys
    groq_api_key: Optional[str] = Field(None, description="Groq API key for OCR")
    google_api_key: Optional[str] = Field(None, description="Google API key for Gemini")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key for Claude")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key for GPT-4o")

    # Orchestrator Configuration
    orchestrator_model: str = Field(
        "claude-3-5-sonnet-20241022",
        description="Model to use for orchestration"
    )
    orchestrator_provider: Literal["anthropic", "openai"] = Field(
        "anthropic",
        description="Provider for orchestrator LLM"
    )

    # Storage Configuration
    s3_bucket: Optional[str] = Field(None, description="S3 bucket for manual storage")
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_endpoint: Optional[str] = Field(None, description="S3 endpoint (for non-AWS)")

    # Observability
    langchain_tracing_v2: bool = Field(False, description="Enable LangSmith tracing")
    langchain_api_key: Optional[str] = None
    langchain_project: str = Field("rivet-pro", description="LangSmith project name")

    # Feature Flags
    beta_mode: bool = Field(True, description="Unlock all features during beta")

    # Application Settings
    log_level: str = Field("INFO", description="Logging level")
    environment: Literal["development", "staging", "production"] = Field(
        "development",
        description="Runtime environment"
    )


# Singleton settings instance
settings = Settings()
